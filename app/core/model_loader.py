from src.config import MODEL_DIR
import joblib
import logging

logger = logging.getLogger(__name__)

pipeline = joblib.load(MODEL_DIR / "sales_forecast_pipeline.joblib")

logger.info("Model loaded successfully")