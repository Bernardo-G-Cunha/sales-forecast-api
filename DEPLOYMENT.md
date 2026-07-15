# Automated Deployment — Sales Forecast API

This document describes the continuous deployment architecture implemented for the project, the execution flow, the decisions behind it, and how to diagnose the most common issues. It's aimed at whoever operates or debugs the infrastructure — for a project overview, see `README.md`.

## Architecture overview

Deployment is triggered automatically on every push to the `main` branch (except pushes that only touch `.md` files — see the CI/CD section below). There is no `git clone` and no SSH involved in production — the EC2 instance is managed exclusively via **AWS Systems Manager (SSM)**, and configuration syncing is done via **S3**, following the same pattern already used for the Machine Learning artifacts (trained model and `store.csv`).

```
GitHub Actions (OIDC, no Access Keys)
   │
   ├── 1. Tests (pytest)
   ├── 2. Build Docker images (API + Nginx)
   ├── 3. Push images → Amazon ECR
   ├── 4. Upload docker-compose.yml → S3 (deploy/ prefix)
   └── 5. SSM SendCommand → EC2
              │
              ├── downloads docker-compose.yml from S3
              ├── logs in to ECR
              ├── docker compose pull (new images)
              ├── removes old containers (if any)
              ├── docker compose up -d
              └── docker image prune -a -f (cleans up old images)
```

## Why this architecture (and not `git clone` on the EC2 instance)

The decision was to stay consistent with the pattern already established in the project: **no static credentials anywhere**, everything goes through an IAM Role (Instance Profile on the EC2 instance, OIDC on GitHub Actions). A `git clone` would require a GitHub deploy key or PAT stored on the instance, plus keeping a full copy of the repository in production. Treating `docker-compose.yml` as a deployment artifact in S3 — the same way the model and `store.csv` are already treated — avoids that extra credential and keeps the instance's access surface smaller.

## Authentication: two separate identities

It's important to understand there are **two completely independent IAM roles**, each acting in its own moment — GitHub never talks directly to the EC2 instance, and vice versa. The only bridge between them is the SSM API.

### `SalesForecastGitHubRole` (assumed via OIDC by GitHub Actions)

Exists only during the workflow run. GitHub Actions generates a signed OIDC token (enabled by `permissions: id-token: write` in the YAML), AWS checks that token against a previously configured Identity Provider and against the role's *trust policy* (which restricts who can assume it to this specific repository), and returns temporary credentials valid only for that run.

| Policy                                         | Purpose                                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| `AmazonEC2ContainerRegistryPowerUser`          | Pushing images to ECR                                                                 |
| `SalesForecastS3ReadPolicy` (inline)           | Reading ML artifacts during tests                                                     |
| `SalesForecastDeployPolicy` (customer-managed) | Uploading `docker-compose.yml` to S3 + `ssm:SendCommand` + `ssm:GetCommandInvocation` |

### `SalesForecastEC2Role` (Instance Profile, permanently attached to the EC2 instance)

Different mechanism: it isn't assumed on demand, it's always "worn" by the instance. Any process running inside it can request temporary credentials automatically via the Instance Metadata Service, with no manual configuration.

| Policy                               | Purpose                                                              |
| ------------------------------------ | -------------------------------------------------------------------- |
| `AmazonS3ReadOnlyAccess`             | Reading ML artifacts and the `docker-compose.yml` (`deploy/` prefix) |
| `AmazonEC2ContainerRegistryReadOnly` | Pulling Docker images from ECR                                       |
| `AmazonSSMManagedInstanceCore`       | Allows the instance to receive commands via SSM                      |

> Note: `AmazonS3ReadOnlyAccess` is more permissive than strictly necessary (grants read access to every bucket in the account, not just ours). It works correctly, but is a candidate for tightening later — see Future Improvements.

## Workflow flow (`ci-cd.yml`)

1. **Checkout + tests**: installs dependencies, runs `pytest` (tests download artifacts from S3 using the already-active OIDC credentials).
2. **Build and push**: builds the API and Nginx Docker images and publishes them to ECR with the `latest` tag.
3. **Upload the compose file**: sends the `docker-compose.yml` versioned in the repo to `s3://<bucket>/deploy/docker-compose.yml`.
4. **Deploy via SSM**: fires a `send-command` (`AWS-RunShellScript` document) on the EC2 instance, which runs the following in sequence, as root:

   * downloads the latest `docker-compose.yml` from S3;
   * authenticates with ECR (`aws ecr get-login-password`);
   * `docker compose pull` (downloads the new images);
   * `docker rm -f sales-api nginx || true` (removes existing containers with those names — `|| true` prevents the script from failing if they don't exist);
   * `docker compose up -d` (recreates the containers with the updated images);
   * `docker image prune -a -f` (removes unused old images, **after** `up -d` — never before, or Docker would delete the freshly pulled image before it's actually in use by a container).
5. **Wait for the result**: `aws ssm wait command-executed` waits for the run to finish.
6. **Detailed log**: `aws ssm get-command-invocation` prints the full result (stdout/stderr/status) to the Actions log, even if the deployment fails.

## Workflow trigger

```yaml
on:
  push:
    branches:
      - main
    paths-ignore:
      - '**.md'
```

Pushes that **only** change `.md` files (documentation) don't trigger the pipeline — avoids running tests, build, and deploy just because of a README or documentation tweak.

## Network and access

* **Port 22 (SSH) is not the automated management path** — every workflow action happens via SSM, with no need for an open inbound port (the SSM Agent initiates communication from the inside out, polling the SSM API). Manual SSH (`ssh -i ~/.ssh/sales-forecast-key.pem ubuntu@<ip>`) is still available for ad-hoc use, with port 22 open in the Security Group.
* **Elastic IP attached to the instance** — the EC2 instance's public IP is fixed (Elastic IP), and doesn't change across stop/start cycles.
* **Port 80 and 443 are open in the Security Group** for HTTP and HTTPS traffic.
* **FastAPI is not directly exposed to the internet** — only the Nginx container publishes ports externally. The API container is accessible only through the internal Docker network.

## HTTPS with Nginx and Let's Encrypt

The application uses Nginx as a reverse proxy and TLS termination layer.

Traffic flow:

```
Client
  │
  │ HTTPS :443
  ▼
Nginx
  │
  │ HTTP :8000 (internal Docker network)
  ▼
FastAPI
```

Nginx is responsible for:

* handling HTTPS connections;
* redirecting HTTP traffic to HTTPS;
* serving Let's Encrypt ACME challenges;
* forwarding API requests to FastAPI.

Certificates are managed by Certbot and automatically renewed through the scheduled renewal task created during certificate issuance.

## Instance resources (t3.micro — 1 vCPU, ~911MB RAM)

The instance runs at the edge of the Free Tier's resource limits, which already caused two real incidents during implementation.

### Swap configured (1GB)

The instance had no swap by default. Under memory spikes (like `docker compose pull` plus the old and new containers briefly coexisting), this caused the SSM Agent to hang, requiring a manual reboot to regain access. Fixed with:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

The last line (`/etc/fstab`) ensures swap is re-enabled automatically after reboots.

### Disk full (resolved)

The EBS volume reached 100% usage, causing cascading failures. Cause: old Docker images piling up on every deploy, with no automatic cleanup. Fixed by adding `docker image prune -a -f` at the end of the deployment script.

## Troubleshooting

### `docker: unknown command: docker compose` on the EC2 instance

The Docker Compose plugin (v2) needs to be installed via Docker's official repository (`download.docker.com`) — it doesn't ship by default on AWS's Ubuntu images. See the manual setup section below.

### `Conflict. The container name "/sales-api" is already in use`

Cause: a container with that name already existed without the Docker Compose internal label (for example, created manually with `docker run` or `docker compose up` from a different directory).

Fixed by the deployment script removing both production containers:

```bash
docker rm -f sales-api nginx || true
```

### `TargetNotConnected` / instance "not configured for use with AWS Systems Manager"

Checklist, in order of likelihood:

1. Is the instance `running`?
2. Is the SSM Agent hung — usually from low memory or a full disk?
3. Is `SalesForecastEC2Role` still attached to the instance?
4. Is the Session Manager Plugin installed on the local machine, if testing via CLI?

### Disk full

```bash
df -h
docker system df
docker image prune -a -f
```

If it persists, consider increasing the EBS volume.

### Deployment hangs / EC2 instance becomes unreachable

Fetch the SSM command result manually:

```bash
aws ssm get-command-invocation \
  --command-id "<COMMAND_ID>" \
  --instance-id "<INSTANCE_ID>"
```

## Future improvements (out of current scope)

* Restrict `AmazonS3ReadOnlyAccess` on `SalesForecastEC2Role` to only the necessary prefixes.
* Consider tagging images by commit SHA instead of `latest`, to allow deterministic rollbacks.
* Evaluate upgrading to `t3.small` if memory incidents recur even with swap configured.
