from src import MODEL_DIR
import joblib
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = MODEL_DIR / "sales_forecast_pipeline.joblib"

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

pipeline = joblib.load(MODEL_PATH)

logger.info("Model loaded successfully")