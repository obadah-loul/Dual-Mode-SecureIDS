"""Encoding helpers for preprocessing."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder


def validate_categorical_columns(
    columns: list[str],
    categorical_columns: list[str],
) -> dict[str, str]:
    """Report whether configured categorical columns are present."""

    available = {column.strip(): column for column in columns}
    return {
        column: "present" if column in available else "missing"
        for column in categorical_columns
    }


def build_onehot_encoder(handle_unknown: str = "ignore") -> OneHotEncoder:
    """Create a dense one-hot encoder for stable feature arrays."""

    return OneHotEncoder(handle_unknown=handle_unknown, sparse_output=False)


def prepare_categorical_frame(
    frame: pd.DataFrame,
    categorical_columns: list[str],
) -> pd.DataFrame:
    """Normalize categorical values before fitting or transforming."""

    prepared = frame.loc[:, categorical_columns].copy()
    for column in categorical_columns:
        prepared[column] = prepared[column].fillna("__missing__").astype(str)
    return prepared


def encode_categorical_frame(
    encoder: OneHotEncoder,
    frame: pd.DataFrame,
    categorical_columns: list[str],
) -> np.ndarray:
    """Transform categorical columns into a float32 dense matrix."""

    prepared = prepare_categorical_frame(frame, categorical_columns)
    return encoder.transform(prepared).astype(np.float32, copy=False)
