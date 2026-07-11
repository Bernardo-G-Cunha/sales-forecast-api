import pandas as pd
import logging

from app.core import artifacts
from app.schemas import PredictionRequest
from app.exceptions import StoreNotFoundError

logger = logging.getLogger(__name__)

def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "store": "Store",
            "date": "Date",
            "promo": "Promo",
            "state_holiday": "StateHoliday",
            "school_holiday": "SchoolHoliday",
        }
    )

def _create_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df["Date"] = pd.to_datetime(df["Date"])

    df["DayOfWeek"] = df["Date"].dt.isocalendar().day
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Day"] = df["Date"].dt.day
    df["Week"] = df["Date"].dt.isocalendar().week
    df["Quarter"] = df["Date"].dt.quarter

    df["IsWeekend"] = df["DayOfWeek"].isin([6, 7])
    df["IsMonthStart"] = df["Date"].dt.is_month_start
    df["IsMonthEnd"] = df["Date"].dt.is_month_end

    return df.drop(columns="Date")


def _merge_store_metadata(df: pd.DataFrame) -> pd.DataFrame:

    merged = df.merge(
        artifacts.stores,
        on="Store",
        how="left",
    )

    if merged["StoreType"].isna().any():
        store_id = int(df.iloc[0]["Store"])
        raise StoreNotFoundError(store_id)
    
    return merged


def predict(request: PredictionRequest) -> float:

    logger.info(
        "Prediction requested for store=%s on %s",
        request.store,
        request.date,
    )

    df = pd.DataFrame([request.model_dump()])

    df = _rename_columns(df)
    df = _merge_store_metadata(df)
    df = _create_calendar_features(df)
    
    prediction = artifacts.pipeline.predict(df)
    
    logger.info(
        "Prediction completed for store=%s with predicted_sales=%.2f",
        request.store,
        prediction[0],
    )

    return int(prediction[0])