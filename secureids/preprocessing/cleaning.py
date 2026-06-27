"""Reusable cleaning helpers for preprocessing."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def strip_column_whitespace(columns: list[str]) -> list[str]:
    """Return column names with surrounding whitespace removed."""

    return [str(column).strip() for column in columns]


def replace_inf_with_nan(value: Any) -> Any:
    """Replace positive/negative infinity values with NaN."""

    if isinstance(value, float) and math.isinf(value):
        return math.nan
    if isinstance(value, str) and value.strip().lower() in {"inf", "+inf", "-inf"}:
        return math.nan
    return value


def safe_numeric_coerce(value: Any) -> float:
    """Coerce a value to float, returning NaN when conversion is unsafe."""

    value = replace_inf_with_nan(value)
    if value is None:
        return math.nan
    if isinstance(value, str) and not value.strip():
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def clean_numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce selected columns to numeric values and replace infinities with NaN."""

    cleaned = frame.loc[:, columns].copy()
    for column in columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned.replace([np.inf, -np.inf], np.nan, inplace=True)
    return cleaned


def replace_nonfinite_with_values(
    array: np.ndarray,
    replacement_values: np.ndarray,
) -> None:
    """Replace NaN/inf values in-place using per-column replacement values."""

    mask = ~np.isfinite(array)
    if mask.any():
        _row_indices, column_indices = np.where(mask)
        array[mask] = replacement_values[column_indices]
