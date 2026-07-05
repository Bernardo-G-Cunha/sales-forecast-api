from collections.abc import Mapping

import pandas as pd
from pandas import DataFrame, Series
from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
)


def evaluate_regression(
    y_true: Series,
    y_pred,
) -> dict[str, float]:
    """
    Compute standard regression evaluation metrics.

    Parameters
    ----------
    y_true : pandas.Series
        Ground-truth target values.

    y_pred : array-like
        Predicted target values.

    Returns
    -------
    dict[str, float]
        Dictionary containing the following metrics:

        - MAE
        - RMSE
        - R2
    """

    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": root_mean_squared_error(y_true, y_pred),
        "R2": r2_score(y_true, y_pred),
    }


def print_metrics(
    metrics: Mapping[str, float],
) -> None:
    """
    Print regression metrics in a human-readable format.

    Parameters
    ----------
    metrics : Mapping[str, float]
        Dictionary returned by ``evaluate_regression()``.
    """

    print(f"MAE : {metrics['MAE']:.2f}")
    print(f"RMSE: {metrics['RMSE']:.2f}")
    print(f"R²  : {metrics['R2']:.4f}")


def compare_models(
    metrics: Mapping[str, Mapping[str, float]],
) -> DataFrame:
    """
    Create a comparison table from multiple regression models.

    Parameters
    ----------
    metrics : Mapping[str, Mapping[str, float]]
        Dictionary mapping model names to the metric dictionaries
        returned by ``evaluate_regression()``.

        Example
        -------
        {
            "Baseline": {"MAE": ..., "RMSE": ..., "R2": ...},
            "Random Forest": {...},
            "XGBoost": {...},
        }

    Returns
    -------
    pandas.DataFrame
        DataFrame containing one row per model and one column per metric.
    """

    rows = []

    for model_name, model_metrics in metrics.items():
        rows.append(
            {
                "Model": model_name,
                **model_metrics,
            }
        )

    return pd.DataFrame(rows)