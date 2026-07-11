import logging

import joblib
import pandas as pd

from common import MODEL_DIR, RAW_DATA_DIR

logger = logging.getLogger(__name__)

pipeline = None
stores = None


def load_pipeline() -> None:
    global pipeline

    logger.info("Loading model...")

    model_path = MODEL_DIR / "sales_forecast_pipeline.joblib"

    pipeline = joblib.load(model_path)

    logger.info("Model loaded successfully")


def load_stores() -> None:
    global stores

    logger.info("Loading store metadata...")

    store_path = RAW_DATA_DIR / "store.csv"

    stores = pd.read_csv(store_path)

    logger.info("Store metadata loaded successfully")