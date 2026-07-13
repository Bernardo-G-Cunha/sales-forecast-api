# Automated Deployment — Sales Forecast API

This document describes the continuous deployment architecture implemented for the project, the execution flow, the decisions behind it, and how to diagnose the most common issues. It's aimed at whoever operates or debugs the infrastructure — for a project overview, see `README.md`.

## Architecture overview

Deployment is triggered automatically on every push to the `main` branch (except pushes that only touch `.md` files — see the CI/CD section below). There is no `git clone` and no SSH involved in production — the EC2 instance is managed exclusively via **AWS Systems Manager (SSM)**, and configuration syncing is done via **S3**, following the same pattern already used for the Machine Learning artifacts (trained model and `store.csv`).

```
GitHub Actions (OIDC, no Access Keys)
   │
   ├── 1. Tests (pytest)
   ├── 2. Build Docker image
   ├── 3. Push image → Amazon ECR
   ├── 4. Upload docker-compose.yml → S3 (deploy/ prefix)
   └── 5. SSM SendCommand → EC2
              │
              ├── downloads docker-compose.yml from S3
              ├── logs in to ECR
              ├── docker compose pull (new image)
              ├── removes the old container (if any)
              ├── docker compose up -d
              └── docker image prune -a -f (cleans up old images)
```

## Why this architecture (and not `git clone` on the EC2 instance)

The decision was to stay consistent with the pattern already established in the project: **no static credentials anywhere**, everything goes through an IAM Role (Instance Profile on the EC2 instance, OIDC on GitHub Actions). A `git clone` would require a GitHub deploy key or PAT stored on the instance, plus keeping a full copy of the repository in production. Treating `docker-compose.yml` as a deployment artifact in S3 — the same way the model and `store.csv` are already treated — avoids that extra credential and keeps the instance's access surface smaller.

## Authentication: two separate identities

It's important to understand there are **two completely independent IAM roles**, each acting in its own moment — GitHub never talks directly to the EC2 instance, and vice versa. The only bridge between them is the SSM API.

### `SalesForecastGitHubRole` (assumed via OIDC by GitHub Actions)

Exists only during the workflow run. GitHub Actions generates a signed OIDC token (enabled by `permissions: id-token: write` in the YAML), AWS checks that token against a previously configured Identity Provider and against the role's *trust policy* (which restricts who can assume it to this specific repository), and returns temporary credentials valid only for that run.

| Policy | Purpose |
|---|---|
| `AmazonEC2ContainerRegistryPowerUser` | Pushing the image to ECR |
| `SalesForecastS3ReadPolicy` (inline) | Reading ML artifacts during tests |
| `SalesForecastDeployPolicy` (customer-managed) | Uploading `docker-compose.yml` to S3 + `ssm:SendCommand` + `ssm:GetCommandInvocation` |

### `SalesForecastEC2Role` (Instance Profile, permanently attached to the EC2 instance)

Different mechanism: it isn't assumed on demand, it's always "worn" by the instance. Any process running inside it can request temporary credentials automatically via the Instance Metadata Service, with no manual configuration.

| Policy | Purpose |
|---|---|
| `AmazonS3ReadOnlyAccess` | Reading ML artifacts and the `docker-compose.yml` (`deploy/` prefix) |
| `AmazonEC2ContainerRegistryReadOnly` | Pulling the Docker image from ECR |
| `AmazonSSMManagedInstanceCore` | Allows the instance to receive commands via SSM |

> Note: `AmazonS3ReadOnlyAccess` is more permissive than strictly necessary (grants read access to every bucket in the account, not just ours). It works correctly, but is a candidate for tightening later — see Future Improvements.

## Workflow flow (`ci-cd.yml`)

1. **Checkout + tests**: installs dependencies, runs `pytest` (tests download artifacts from S3 using the already-active OIDC credentials).
2. **Build and push**: builds the Docker image and publishes it to ECR with the `latest` tag.
3. **Upload the compose file**: sends the `docker-compose.yml` versioned in the repo to `s3://<bucket>/deploy/docker-compose.yml`.
4. **Deploy via SSM**: fires a `send-command` (`AWS-RunShellScript` document) on the EC2 instance, which runs the following in sequence, as root:
   - downloads the latest `docker-compose.yml` from S3;
   - authenticates with ECR (`aws ecr get-login-password`);
   - `docker compose pull` (downloads the new image);
   - `docker rm -f sales-api || true` (removes any existing container with that name — `|| true` prevents the script from failing if the container doesn't exist);
   - `docker compose up -d` (recreates the container with the updated image);
   - `docker image prune -a -f` (removes unused old images, **after** `up -d` — never before, or Docker would delete the freshly pulled image before it's actually in use by a container).
5. **Wait for the result**: `aws ssm wait command-executed` waits for the run to finish; if the script fails on the instance, this step fails the GitHub Actions job.
6. **Detailed log**: `aws ssm get-command-invocation` prints the full result (stdout/stderr/status) to the Actions log.

### Known limitation of steps 5/6

If `wait command-executed` detects `Status: Failed`, it returns an error and stops the step's execution — since commands within the same `run: |` block in GitHub Actions stop at the first failure, `get-command-invocation` **doesn't run** in that case. In other words: when the deployment fails, the Actions log only shows the `wait` error, without the detail of what actually failed inside the EC2 instance — it has to be fetched manually via `aws ssm get-command-invocation` from the local CLI. Pending improvement: use `if: always()` on a separate step to guarantee the detailed log always shows up, even on failure.

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

- **Port 22 (SSH) is not the automated management path** — every workflow action happens via SSM, with no need for an open inbound port (the SSM Agent initiates communication from the inside out, polling the SSM API). Manual SSH (`ssh -i ~/.ssh/sales-forecast-key.pem ubuntu@<ip>`) is still available for ad-hoc use, with port 22 open in the Security Group.
- **Elastic IP attached to the instance** — the EC2 instance's public IP is fixed (Elastic IP), and doesn't change across stop/start cycles. This replaced the original auto-assigned public IP, which would change on every `Stop`/`Start` (a plain reboot doesn't change the IP, but a full stop does).
- **Port 80 open in the Security Group**, mapped to the Uvicorn's port 8000 inside the container (`80:8000` in `docker-compose.yml`).

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

The last line (`/etc/fstab`) ensures swap is re-enabled automatically after reboots — without it, `swapon` alone doesn't persist.

### Disk full (resolved)

The EBS volume (6.8GB effective) reached 100% usage, causing cascading failures (including temporarily blocking swap creation, since `fallocate` needs free space). Cause: old Docker images piling up on every deploy, with no automatic cleanup. Fixed by adding `docker image prune -a -f` at the end of the deployment script (see Workflow flow above).

## Troubleshooting

### `docker: unknown command: docker compose` on the EC2 instance

The Docker Compose plugin (v2) needs to be installed via Docker's official repository (`download.docker.com`) — it doesn't ship by default on AWS's Ubuntu images. See the manual setup section below.

### `Conflict. The container name "/sales-api" is already in use`

Cause: a container with that name already existed without the Docker Compose internal label (for example, created manually with `docker run` or `docker compose up` from a different directory). Permanently fixed by the `docker rm -f sales-api || true` line in the deployment script.

### `TargetNotConnected` / instance "not configured for use with AWS Systems Manager"

Checklist, in order of likelihood:
1. Is the instance `running`? (A stopped instance responds to neither SSM nor the application.)
2. Is the SSM Agent hung — usually from low memory (see swap section above) or a full disk? A **reboot** usually restores access; the root cause is fixed by the swap + disk cleanup above.
3. Is `SalesForecastEC2Role` still attached to the instance (EC2 → Security → IAM Role)?
4. Is the **Session Manager Plugin** installed on the local machine, if testing via CLI (`aws ssm start-session`)? Without it, the error is `SessionManagerPlugin is not found` — a local problem, not an instance problem. Alternative without installing anything: Console → Systems Manager → Session Manager → Start session.

### Disk full (`fallocate: No space left on device`, or any operation failing due to space)

```bash
df -h                        # confirms usage %
docker system df             # shows what Docker is using
docker image prune -a -f     # removes unused images
```
If it persists even with few images, consider increasing the EBS volume (Console → EC2 → Volumes → Modify Volume — up to 30GB within the Free Tier) and expanding the partition with `growpart` + `resize2fs`.

### Deployment hangs / EC2 instance becomes unreachable with no clear error in the Actions log

Due to the limitation described in the "Workflow flow" section above, the Actions log may not show the detailed error when `wait` fails. Fetch it manually:
```bash
aws ssm get-command-invocation \
  --command-id "<COMMAND_ID>" \
  --instance-id "<INSTANCE_ID>"
```
The `CommandId` can be found in Systems Manager → Run Command → History, in the console.

### Manual Docker Compose plugin setup (reference, in case the instance ever needs to be recreated)

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-compose-plugin -y
```

## Future improvements (out of current scope)

- Restrict `AmazonS3ReadOnlyAccess` on `SalesForecastEC2Role` to only the necessary prefixes (artifacts bucket + `deploy/`), instead of read access to every bucket in the account.
- Add `if: always()` to the deployment log step, so the detailed result shows up in Actions even when `wait` fails.
- Consider tagging images by commit SHA instead of `latest`, to allow deterministic rollbacks.
- Evaluate upgrading to `t3.small` if memory incidents recur even with swap configured (check `CPUCreditBalance` in CloudWatch before deciding).
- HTTPS via Nginx + Let's Encrypt — the API currently runs over plain HTTP on port 80.
