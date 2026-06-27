"""Base configuration and CSV helpers for preprocessing dry runs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None


CSV_ENCODINGS = ("utf-8-sig", "utf-8", "latin1")

CICIDS_REQUIRED_KEYS = {
    "dataset",
    "task",
    "raw_dir",
    "output_dir",
    "artifact_path",
    "target_column",
    "drop_columns",
    "binary_mapping",
    "split",
    "cleaning",
    "imputation",
    "scaling",
}

UNSW_REQUIRED_KEYS = {
    "dataset",
    "task",
    "train_file",
    "test_file",
    "output_dir",
    "artifact_path",
    "target_column",
    "drop_columns",
    "categorical_columns",
    "encoding",
    "split",
    "cleaning",
    "imputation",
    "scaling",
}


@dataclass(slots=True)
class PreprocessingConfig:
    """Loaded preprocessing config plus its source path."""

    path: Path
    values: dict[str, Any]

    @property
    def dataset(self) -> str:
        return str(self.values.get("dataset", ""))


@dataclass(slots=True)
class DryRunFileCheck:
    """Header/sample inspection result for one raw CSV file."""

    path: str
    exists: bool
    status: str
    columns: list[str] = field(default_factory=list)
    column_count: int = 0
    sample_rows_inspected: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "status": self.status,
            "columns": self.columns,
            "column_count": self.column_count,
            "sample_rows_inspected": self.sample_rows_inspected,
            "error": self.error,
        }


def project_path(project_root: Path, raw_path: str | Path) -> Path:
    """Resolve a possibly relative project path."""

    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def load_preprocessing_config(config_path: Path) -> PreprocessingConfig:
    """Load a preprocessing YAML config safely.

    PyYAML is used when installed. A small local parser handles the simple YAML
    subset used by the project configs so dry-run validation still works in a
    bare Python environment.
    """

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
    else:
        loaded = parse_simple_yaml(text)

    if not isinstance(loaded, dict):
        raise ValueError(f"Config must load to a mapping: {config_path}")

    return PreprocessingConfig(path=config_path, values=loaded)


def validate_preprocessing_config(config: PreprocessingConfig) -> list[str]:
    """Return validation errors for required config keys."""

    dataset = config.dataset
    required = UNSW_REQUIRED_KEYS if dataset == "unsw_nb15" else CICIDS_REQUIRED_KEYS
    missing = sorted(key for key in required if key not in config.values)

    errors = [f"missing required key: {key}" for key in missing]
    if config.values.get("task") != "binary":
        errors.append("task must be binary")
    if dataset not in {"cicids2018", "unsw_nb15"}:
        errors.append(f"unsupported dataset: {dataset}")
    return errors


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the limited YAML subset used by V2 config skeletons."""

    lines = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        if lines[index][1].startswith("- "):
            return parse_list(index, indent)
        return parse_dict(index, indent)

    def parse_dict(index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(lines):
            current_indent, stripped = lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                break
            if stripped.startswith("- "):
                break

            key, separator, value = stripped.partition(":")
            if not separator:
                raise ValueError(f"Invalid YAML line: {stripped}")
            key = key.strip()
            value = value.strip()
            index += 1

            if value:
                result[key] = parse_scalar(value)
            elif index < len(lines) and lines[index][0] > current_indent:
                result[key], index = parse_block(index, lines[index][0])
            else:
                result[key] = {}
        return result, index

    def parse_list(index: int, indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(lines):
            current_indent, stripped = lines[index]
            if current_indent != indent or not stripped.startswith("- "):
                break
            value = stripped[2:].strip()
            result.append(parse_scalar(value))
            index += 1
        return result, index

    parsed, final_index = parse_block(0, 0)
    if final_index != len(lines):
        raise ValueError("Unsupported YAML structure in preprocessing config")
    if not isinstance(parsed, dict):
        raise ValueError("Top-level YAML value must be a mapping")
    return parsed


def parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    try:
        if "." not in value:
            return int(value)
        return float(value)
    except ValueError:
        return value.strip("\"'")


def discover_csv_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists() or not raw_dir.is_dir():
        return []
    return sorted(path for path in raw_dir.glob("*.csv") if path.is_file())


def read_csv_header_and_sample_count(
    csv_path: Path,
    sample_rows: int = 5,
) -> DryRunFileCheck:
    """Read only the header and a few rows from a CSV file."""

    if not csv_path.exists():
        return DryRunFileCheck(
            path=str(csv_path),
            exists=False,
            status="missing",
        )

    last_error = ""
    for encoding in CSV_ENCODINGS:
        try:
            with csv_path.open("r", newline="", encoding=encoding) as handle:
                reader = csv.reader(handle)
                columns = [str(column) for column in next(reader, [])]
                inspected = 0
                for inspected, _row in enumerate(reader, start=1):
                    if inspected >= sample_rows:
                        break
                return DryRunFileCheck(
                    path=str(csv_path),
                    exists=True,
                    status="ok",
                    columns=columns,
                    column_count=len(columns),
                    sample_rows_inspected=inspected,
                )
        except Exception as exc:  # pragma: no cover - input dependent
            last_error = f"{type(exc).__name__}: {exc}"

    return DryRunFileCheck(
        path=str(csv_path),
        exists=True,
        status="read_error",
        error=last_error,
    )
