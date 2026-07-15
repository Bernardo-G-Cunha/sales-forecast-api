# Sales Forecast API

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20ECR%20%7C%20S3-orange.svg)](https://aws.amazon.com/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF.svg)](https://github.com/features/actions)

A production-oriented Machine Learning API that predicts daily store sales using a Random Forest model.

The project demonstrates an end-to-end ML deployment workflow, including model training, API development, Docker containerization, CI/CD automation, and AWS deployment.

---

# Overview

The application provides a REST API built with FastAPI that receives store information and predicts daily sales using a pre-trained Scikit-Learn pipeline.

ML artifacts are managed separately from the application code. In production, they are stored in Amazon S3 and downloaded during application startup, keeping the Docker image lightweight and allowing independent model updates.

For local execution, the trained model artifact is available through the GitHub Release assets. The model file is not stored in the repository due to its size, while smaller supporting files such as `store.csv` remain versioned with the source code.


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
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── common/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# Features

* FastAPI REST API
* Random Forest regression model
* ML artifact management with Amazon S3
* Docker containerization
* Nginx reverse proxy
* HTTPS with Let's Encrypt
* GitHub Actions CI/CD pipeline
* Amazon ECR image registry
* AWS EC2 deployment
* AWS Systems Manager deployment
* IAM Role authentication
* Automated tests with Pytest
* Health check endpoint

---

# Architecture

```text
GitHub
  |
  v
GitHub Actions
  |
  +--> Tests
  |
  +--> Docker Build
          |
          v
       Amazon ECR
          |
          v
     Deploy via SSM
          |
          v
    EC2 + Docker Compose
          |
          +------------+
          |            |
          v            v
       Nginx        FastAPI
        HTTPS          |
                       v
                    Amazon S3
                (ML artifacts)
```

Request flow:

```text
Client
  |
 HTTPS
  |
Nginx
  |
 HTTP (internal)
  |
FastAPI
```

---

# Machine Learning

Model:

* RandomForestRegressor

Artifacts:

* `sales_forecast_pipeline.joblib` (distributed through GitHub Release assets)
* `store.csv` (versioned with the repository)

The model was optimized to run on a low-resource EC2 instance while maintaining similar predictive performance.

For production deployment, artifacts are stored in Amazon S3 and downloaded automatically by the application.

For local execution, download `sales_forecast_pipeline.joblib` from the latest GitHub Release and place it in the expected directory. The `store.csv` file is already included in the repository.

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
* Nginx
* GitHub Actions

## Cloud

* Amazon EC2
* Amazon ECR
* Amazon S3
* AWS IAM
* AWS Systems Manager

---

# API

Live demo:

https://salesapi.bernardo-cunha.com

Documentation:

https://salesapi.bernardo-cunha.com/docs

## Health Check

```
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Predict Sales

```
POST /predict
```

Example:

```bash
curl -X POST https://salesapi.bernardo-cunha.com/predict \
  -H "Content-Type: application/json" \
  -d '{"store": 1, "date": "2015-07-31", "promo": true, "state_holiday": "0", "school_holiday": false}'
```

Response:

```json
{
  "predicted_sales": 6036
}
```

---

# Running Locally

Install dependencies:

```bash
python -m venv .venv

pip install -r requirements-dev.txt
pip install -e .
```

Download the trained model artifact from the latest GitHub Release:

```
sales_forecast_pipeline.joblib
```

Place it in the directory expected by the application.

```
models/sales_forecast_pipeline.joblib
```

The `store.csv` file is already available after cloning the repository.

Run:

```bash
uvicorn app.main:app --reload
```

---

# Running with Docker

Build:

```bash
docker build -t sales-forecast-api .
```

Run:

```bash
docker compose up -d
```

---

# CI/CD Pipeline

On every push to `main`:

1. Run automated tests
2. Build Docker images
3. Push images to Amazon ECR
4. Upload deployment configuration to Amazon S3
5. Deploy to EC2 using AWS Systems Manager
6. Restart containers with Docker Compose

Authentication uses GitHub Actions OIDC with AWS IAM Roles, avoiding long-lived AWS credentials.


---

# License

MIT License
