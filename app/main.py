from fastapi import FastAPI

from app.api import router
from app.core import logging_config
from app.handlers import (
    register_exception_handlers
)

app = FastAPI(
    title="Sales Forecast API",
    description="API for predicting daily sales using Machine Learning.",
    version="1.0.0",
)

app.include_router(router)

register_exception_handlers(app)