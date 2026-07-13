from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api import router
from app.handlers import register_exception_handlers
from app.services import ArtifactService
from app.core import logging_config, load_pipeline, load_stores
from common import MODEL_DIR, RAW_DATA_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):

    artifact_service = ArtifactService()

    artifact_service.download_if_missing(
        "metadata/store.csv",
        RAW_DATA_DIR / "store.csv",
    )

    artifact_service.download_if_missing(
        "models/sales_forecast_pipeline.joblib",
        MODEL_DIR / "sales_forecast_pipeline.joblib",
    )

    load_pipeline()
    load_stores()

    yield


app = FastAPI(
    title="Sales Forecast API",
    description="API for predicting daily sales using Machine Learning.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

register_exception_handlers(app)