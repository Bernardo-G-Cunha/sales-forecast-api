from src import RAW_DATA_DIR
import logging
import pandas as pd

logger = logging.getLogger(__name__)

STORE_PATH = RAW_DATA_DIR / "store.csv"

if not RAW_DATA_DIR.exists():
    raise FileNotFoundError(
        f"Model not found: {RAW_DATA_DIR}"
    )

stores = pd.read_csv(RAW_DATA_DIR / "store.csv")

logger.info("Store metadata loaded successfully")