# Sales Forecast API

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20ECR%20%7C%20S3-orange.svg)](https://aws.amazon.com/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF.svg)](https://github.com/features/actions)

A production-oriented Machine Learning API that predicts daily store sales using a Random Forest model. The project demonstrates an end-to-end ML workflow, including model training, API development, containerization, automated CI/CD, and deployment on AWS.

---

# Overview

This project was designed to simulate a real-world Machine Learning service rather than a notebook-based experiment. The focus is less on squeezing out maximum predictive accuracy and more on building the full pipeline a model like this would actually need to reach production: training, packaging, testing, CI/CD, and cloud infrastructure. The Random Forest model itself was deliberately kept small and simple, so the engineering side of the project could take center stage.

The application exposes a REST API built with FastAPI that receives store information and predicts daily sales using a pre-trained Scikit-Learn pipeline.

Instead of packaging the trained model inside the Docker image, ML artifacts are stored separately in Amazon S3 and downloaded automatically during application startup. This keeps the application image lightweight while allowing independent model updates.

---

# Features

* REST API built with FastAPI
* Random Forest regression model
* Automatic artifact download from Amazon S3
* Docker containerization
* Docker Compose support
* Automated CI/CD with GitHub Actions
* Amazon ECR image publishing
* AWS EC2 deployment
* IAM Roles (no AWS Access Keys required)
* Automated testing with Pytest

---

# Architecture

```text
                 GitHub
                    │
                    ▼
            GitHub Actions
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   Run Tests              Build Docker Image
                                │
                                ▼
                         Push Image to ECR
                                │
                                ▼
                  Upload docker-compose.yml to S3
                                │
                                ▼
                       Deploy to EC2 (SSM)
                                │
                                ▼
                         Docker Compose
                                │
                                ▼
                           FastAPI Service
                                │
                Downloads artifacts from S3
                                │
                                ▼
                    Random Forest Pipeline
```

---

# Machine Learning

The prediction model is implemented using Scikit-Learn.

Model:

* RandomForestRegressor

Artifacts:

* `sales_forecast_pipeline.joblib`
* `store.csv`

To improve deployment on low-resource instances (`t3.micro`), the model was optimized by reducing its size while maintaining similar predictive performance.

The Docker image contains only the application code.

Model artifacts are downloaded from Amazon S3 during application startup.

---

# Tech Stack

## Backend

* Python
* FastAPI
* Pydantic

## Machine Learning

* Scikit-Learn
* Pandas
* NumPy

## DevOps

* Docker
* Docker Compose
* GitHub Actions

## Cloud

* Amazon EC2
* Amazon ECR
* Amazon S3
* AWS IAM
* AWS Systems Manager (SSM)

## Testing

* Pytest

---

# Project Structure

```text
.
├── app/
│   ├── api/
│   ├── core/
│   ├── exceptions/
│   ├── handlers/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── models/
├── data/
├── tests/
├── notebooks/
├── ml_utils/
├── common/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# API

**Live demo:** `http://3.220.32.87`

## Predict sales

**POST** `/predict`

Example request:

```bash
curl -X POST http://3.220.32.87/predict \
  -H "Content-Type: application/json" \
  -d '{"store": 1, "date": "2015-07-31", "promo": true, "state_holiday": "0", "school_holiday": false}'
```

Example response:

```json
{
  "predicted_sales": 6036
}
```

---

# Running Locally

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

Run the API:

```bash
uvicorn app.main:app --reload
```

---

# Running with Docker

Build the image:

```bash
docker build -t sales-forecast-api .
```

Run with Docker Compose:

```bash
docker compose up -d
```

---

# AWS Deployment

The application is deployed using the following AWS services:

* Amazon S3 stores ML artifacts
* Amazon ECR stores Docker images
* Amazon EC2 hosts the application
* IAM Roles provide secure AWS authentication
* Systems Manager (SSM) enables remote deployment without SSH keys

---

# CI/CD

The deployment pipeline is implemented with GitHub Actions.

On every push to the `main` branch, the workflow:

1. Checks out the repository
2. Assumes an AWS IAM Role using OpenID Connect (OIDC)
3. Installs project dependencies
4. Executes automated tests
5. Builds the Docker image
6. Pushes the image to Amazon ECR
7. Uploads the updated `docker-compose.yml` to Amazon S3
8. Triggers deployment on EC2 via AWS Systems Manager (SSM Run Command), which pulls the new image, recreates the container, and prunes old images

---

# Testing

The project includes automated API tests using Pytest.

Tests validate:

* Successful predictions
* Invalid payload handling
* Missing store detection
* Request schema validation

---

# Design Decisions

Some architectural decisions were made to better reflect production environments:

* ML artifacts are separated from the application image.
* IAM Roles are used instead of AWS Access Keys.
* Docker images remain independent from trained models.
* Artifacts are downloaded during application startup.
* CI/CD uses GitHub Actions with OpenID Connect authentication.
* Docker Compose manages the production container.
* No `git clone` or SSH access on the EC2 instance — the `docker-compose.yml` is treated as a deployment artifact and distributed via S3, following the same pattern used for ML artifacts. All instance access is via AWS Systems Manager, with no open SSH port and no long-lived credentials.

---

# Future Improvements

* HTTPS with Nginx and Let's Encrypt
* Custom domain
* Blue/Green deployments
* Monitoring and metrics
* Model versioning
* Automated retraining pipeline
* Infrastructure as Code (Terraform)

---

# License

This project is available under the MIT License.
