from pandas import DataFrame, Series
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline

def split_feature_types(
    df: DataFrame,
) -> tuple[list[str], list[str]]:
    
    """
    Split a DataFrame into numerical and categorical feature lists.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame containing the features.

    Returns
    -------
    tuple[list[str], list[str]]
        A tuple containing:

        - numerical_features
        - categorical_features

        in this exact order.
    """

    categorical = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    numerical = df.select_dtypes(
        exclude=["object", "category"]
    ).columns.tolist()
    
    return numerical, categorical


def chronological_split(
    split_date: str,
    X: DataFrame,
    y: Series,
) -> tuple[DataFrame, DataFrame, Series, Series]:
    
    """
    Split features and target into chronological training and test sets.

    Samples with dates earlier than ``split_date`` are assigned to the
    training set, while samples on or after ``split_date`` are assigned
    to the test set.

    Parameters
    ----------
    split_date : str or pandas.Timestamp
        Date used to separate the training and test periods.

    X : pandas.DataFrame
        Feature matrix. Must contain a ``Date`` column.

    y : pandas.Series
        Target variable aligned with ``X``.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame, pandas.Series, pandas.Series]
        A tuple containing, in this exact order:

        - X_train
        - X_test
        - y_train
        - y_test
    """

    train_mask = X["Date"] < split_date
    test_mask = X["Date"] >= split_date

    X_train = X.loc[train_mask].copy()
    X_test = X.loc[test_mask].copy()

    y_train = y.loc[train_mask].copy()
    y_test = y.loc[test_mask].copy()

    return X_train, X_test, y_train, y_test


def get_feature_importance(
    pipeline: Pipeline,
) -> pd.DataFrame:
    """
    Extract feature importances from a fitted tree-based pipeline.

    Parameters
    ----------
    pipeline : sklearn.pipeline.Pipeline
        A fitted Scikit-Learn pipeline containing a ``preprocessor`` step
        and a tree-based model exposing the ``feature_importances_`` attribute.

    Returns
    -------
    pandas.DataFrame
        DataFrame sorted by descending importance with the following columns:

        - Feature
        - Importance
    """

    model = pipeline.named_steps["model"]

    preprocessor = pipeline.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()

    feature_importance = pd.DataFrame(
        {
            "Feature": feature_names,
            "Importance": model.feature_importances_,
        }
    )

    return feature_importance.sort_values(
        by="Importance",
        ascending=False,
        ignore_index=True,
    )


def plot_feature_importance(
    feature_importance: pd.DataFrame,
    top_n: int = 15,
) -> None:
    """
    Plot the top feature importances.

    Parameters
    ----------
    feature_importance : pandas.DataFrame
        DataFrame produced by ``get_feature_importance()``.

    top_n : int, default=15
        Number of most important features to display.
    """

    top_features = feature_importance.head(top_n)

    plt.figure(figsize=(10, 6))

    plt.barh(
        top_features["Feature"][::-1],
        top_features["Importance"][::-1],
    )

    plt.xlabel("Importance")
    plt.title(f"Top {top_n} Feature Importances")

    plt.tight_layout()
    plt.show()