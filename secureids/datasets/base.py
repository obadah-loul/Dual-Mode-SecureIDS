"""Shared dataset audit utilities for the SecureIDS V2 rebuild.

The helpers in this module intentionally avoid full-dataset loading. They read
CSV headers and small samples only, so they are safe to run before preprocessing
or training has been approved.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import pandas as pd
    from pandas.api.types import is_bool_dtype, is_numeric_dtype
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    pd = None

    def is_bool_dtype(_series: object) -> bool:
        return False

    def is_numeric_dtype(_series: object) -> bool:
        return False


DEFAULT_SAMPLE_ROWS = 50
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "latin1")


@dataclass(slots=True)
class DatasetFileAudit:
    """Small inventory record for a raw dataset path."""

    dataset: str
    path: str
    exists: bool
    is_csv: bool
    size_bytes: int | None
    size_human: str
    status: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "path": self.path,
            "exists": self.exists,
            "is_csv": self.is_csv,
            "size_bytes": self.size_bytes if self.size_bytes is not None else "",
            "size_human": self.size_human,
            "status": self.status,
            "error": self.error,
        }


@dataclass(slots=True)
class DatasetSchemaAudit:
    """Header and sample-based schema record for a CSV file."""

    dataset: str
    path: str
    status: str
    column_count: int
    columns: list[str] = field(default_factory=list)
    label_column: str | None = None
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    missing_values_sample: dict[str, int] = field(default_factory=dict)
    sample_rows: int = 0
    notes: str = ""
    error: str = ""

    def to_flat_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "path": self.path,
            "status": self.status,
            "column_count": self.column_count,
            "columns": "|".join(self.columns),
            "label_column": self.label_column or "",
            "numeric_columns": "|".join(self.numeric_columns),
            "categorical_columns": "|".join(self.categorical_columns),
            "missing_values_sample": ";".join(
                f"{column}={count}"
                for column, count in sorted(self.missing_values_sample.items())
            ),
            "sample_rows": self.sample_rows,
            "notes": self.notes,
            "error": self.error,
        }


def format_file_size(size_bytes: int | None) -> str:
    """Format a file size without reading file contents."""

    if size_bytes is None:
        return "unknown"

    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024

    return f"{size_bytes} B"


def normalize_column_name(column: object) -> str:
    """Normalize a column name for matching while preserving original headers."""

    normalized = str(column).replace("\ufeff", "").strip().lower()
    normalized = "_".join(normalized.replace("-", "_").split())
    return normalized


def build_file_audit(dataset: str, path: Path, status: str = "found") -> DatasetFileAudit:
    """Create a file or directory inventory record without opening data files."""

    try:
        exists = path.exists()
        is_csv = path.is_file() and path.suffix.lower() == ".csv"
        size_bytes = path.stat().st_size if path.is_file() else None
        return DatasetFileAudit(
            dataset=dataset,
            path=str(path),
            exists=exists,
            is_csv=is_csv,
            size_bytes=size_bytes,
            size_human=format_file_size(size_bytes),
            status=status,
        )
    except OSError as exc:
        return DatasetFileAudit(
            dataset=dataset,
            path=str(path),
            exists=False,
            is_csv=False,
            size_bytes=None,
            size_human="unknown",
            status="error",
            error=str(exc),
        )


def discover_csv_files(raw_dir: Path) -> list[Path]:
    """Discover CSV files under a raw directory without loading them."""

    if not raw_dir.exists() or not raw_dir.is_dir():
        return []
    return sorted(path for path in raw_dir.rglob("*.csv") if path.is_file())


def read_csv_header_safe(csv_path: Path) -> tuple[list[str], str]:
    """Read a CSV header using pandas without loading rows."""

    if pd is None:
        return read_csv_header_with_stdlib(csv_path)

    last_error = ""
    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(csv_path, nrows=0, encoding=encoding)
            return [str(column) for column in frame.columns], ""
        except Exception as exc:  # pragma: no cover - depends on input encoding/parser
            last_error = f"{type(exc).__name__}: {exc}"
    return [], last_error


def read_csv_header_with_stdlib(csv_path: Path) -> tuple[list[str], str]:
    """Fallback header reader used when pandas is not installed."""

    last_error = ""
    for encoding in CSV_ENCODINGS:
        try:
            with csv_path.open("r", newline="", encoding=encoding) as handle:
                reader = csv.reader(handle)
                return [str(column) for column in next(reader, [])], ""
        except Exception as exc:  # pragma: no cover - depends on input encoding/parser
            last_error = f"{type(exc).__name__}: {exc}"
    return [], last_error


def read_csv_sample_safe(
    csv_path: Path,
    nrows: int = DEFAULT_SAMPLE_ROWS,
) -> tuple[Any | None, str]:
    """Read a small CSV sample using pandas nrows only."""

    if pd is None:
        return read_csv_sample_with_stdlib(csv_path, nrows=nrows)

    last_error = ""
    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(csv_path, nrows=nrows, encoding=encoding)
            return frame, ""
        except Exception as exc:  # pragma: no cover - depends on input encoding/parser
            last_error = f"{type(exc).__name__}: {exc}"
    return None, last_error


def read_csv_sample_with_stdlib(
    csv_path: Path,
    nrows: int = DEFAULT_SAMPLE_ROWS,
) -> tuple[list[dict[str, str]] | None, str]:
    """Fallback sample reader used when pandas is not installed."""

    last_error = ""
    for encoding in CSV_ENCODINGS:
        try:
            with csv_path.open("r", newline="", encoding=encoding) as handle:
                reader = csv.DictReader(handle)
                rows: list[dict[str, str]] = []
                for index, row in enumerate(reader):
                    if index >= nrows:
                        break
                    rows.append(dict(row))
                return rows, ""
        except Exception as exc:  # pragma: no cover - depends on input encoding/parser
            last_error = f"{type(exc).__name__}: {exc}"
    return None, last_error


def detect_label_column(
    columns: list[str],
    possible_label_columns: list[str],
) -> str | None:
    """Find a label column using normalized candidate matching."""

    normalized_columns = {
        normalize_column_name(column): column
        for column in columns
    }
    for candidate in possible_label_columns:
        column = normalized_columns.get(normalize_column_name(candidate))
        if column:
            return column
    return None


def detect_numeric_categorical_columns(
    sample: Any | None,
    known_categorical_columns: list[str] | None = None,
    label_column: str | None = None,
) -> tuple[list[str], list[str]]:
    """Detect numeric and categorical columns from a small sample only."""

    if sample is None:
        return [], []

    known_categorical = {
        normalize_column_name(column)
        for column in (known_categorical_columns or [])
    }
    label_normalized = normalize_column_name(label_column) if label_column else None

    numeric_columns: list[str] = []
    categorical_columns: list[str] = []

    for column in sample_columns(sample):
        column_name = str(column)
        normalized = normalize_column_name(column_name)

        if label_normalized and normalized == label_normalized:
            continue

        if normalized in known_categorical:
            categorical_columns.append(column_name)
        elif sample_column_is_numeric(sample, column_name):
            numeric_columns.append(column_name)
        else:
            categorical_columns.append(column_name)

    return numeric_columns, categorical_columns


def sample_columns(sample: Any) -> list[str]:
    if pd is not None and hasattr(sample, "columns"):
        return [str(column) for column in sample.columns]
    if isinstance(sample, list) and sample:
        return [str(column) for column in sample[0].keys()]
    return []


def sample_column_is_numeric(sample: Any, column: str) -> bool:
    if pd is not None and hasattr(sample, "columns"):
        series = sample[column]
        return not is_bool_dtype(series) and is_numeric_dtype(series)

    if not isinstance(sample, list):
        return False

    saw_value = False
    for row in sample:
        value = row.get(column, "")
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        saw_value = True
        try:
            float(text)
        except ValueError:
            return False
    return saw_value


def audit_missing_values_sample(sample: Any | None) -> dict[str, int]:
    """Count missing values in a small sample without inferring full-dataset rates."""

    if sample is None:
        return {}

    if pd is None or not hasattr(sample, "columns"):
        missing: dict[str, int] = {}
        for column in sample_columns(sample):
            count = sum(
                1
                for row in sample
                if row.get(column) is None or str(row.get(column)).strip() == ""
            )
            if count:
                missing[column] = count
        return missing

    missing: dict[str, int] = {}
    for column in sample.columns:
        series = sample[column]
        missing_count = int(series.isna().sum())

        if not is_numeric_dtype(series):
            blank_count = int(series.fillna("").astype(str).str.strip().eq("").sum())
            missing_count = max(missing_count, blank_count)

        if missing_count:
            missing[str(column)] = missing_count

    return missing


def audit_csv_schema(
    dataset: str,
    csv_path: Path,
    possible_label_columns: list[str],
    known_categorical_columns: list[str] | None = None,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> DatasetSchemaAudit:
    """Create a safe schema audit for one CSV file."""

    columns, header_error = read_csv_header_safe(csv_path)
    if header_error:
        return DatasetSchemaAudit(
            dataset=dataset,
            path=str(csv_path),
            status="header_error",
            column_count=0,
            error=header_error,
        )

    label_column = detect_label_column(columns, possible_label_columns)
    sample, sample_error = read_csv_sample_safe(csv_path, nrows=sample_rows)
    numeric_columns, categorical_columns = detect_numeric_categorical_columns(
        sample=sample,
        known_categorical_columns=known_categorical_columns,
        label_column=label_column,
    )
    missing_values = audit_missing_values_sample(sample)

    notes = "Header and small sample inspected only; no preprocessing was run."
    status = "ok"
    if not label_column:
        status = "label_missing"
        notes = f"{notes} No known label column was detected."
    if sample_error:
        status = "sample_error" if status == "ok" else status
        notes = f"{notes} Sample read failed."

    return DatasetSchemaAudit(
        dataset=dataset,
        path=str(csv_path),
        status=status,
        column_count=len(columns),
        columns=columns,
        label_column=label_column,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        missing_values_sample=missing_values,
        sample_rows=0 if sample is None else len(sample),
        notes=notes,
        error=sample_error,
    )
