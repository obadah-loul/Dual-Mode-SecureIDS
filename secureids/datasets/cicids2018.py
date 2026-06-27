"""CICIDS2018 adapter skeleton and audit logic."""

from __future__ import annotations

from pathlib import Path

from secureids.datasets.base import (
    DatasetFileAudit,
    DatasetSchemaAudit,
    audit_csv_schema,
    build_file_audit,
    discover_csv_files,
)


class CICIDS2018Adapter:
    """Safe CICIDS2018 adapter skeleton for schema audits only."""

    dataset_name = "cicids2018"
    label_columns = ["Label", "label", "attack_label"]
    binary_label_mapping_plan = {
        "BENIGN": 0,
        "Benign": 0,
        "benign": 0,
        "all_other_labels": 1,
    }

    def __init__(self, raw_dir: str | Path = "data/raw/cicids2018") -> None:
        self.raw_dir = Path(raw_dir)

    def discover_files(self) -> list[Path]:
        """Discover CICIDS2018 CSV files without loading data."""

        return discover_csv_files(self.raw_dir)

    def audit_schema(self) -> tuple[list[DatasetFileAudit], list[DatasetSchemaAudit]]:
        """Audit CICIDS2018 files using headers and small samples only."""

        if not self.raw_dir.exists():
            return [
                build_file_audit(
                    self.dataset_name,
                    self.raw_dir,
                    status="missing_raw_dir",
                )
            ], []

        csv_files = self.discover_files()
        if not csv_files:
            return [
                build_file_audit(
                    self.dataset_name,
                    self.raw_dir,
                    status="no_csv_files",
                )
            ], []

        file_audits = [
            build_file_audit(self.dataset_name, csv_path)
            for csv_path in csv_files
        ]
        schema_audits = [
            audit_csv_schema(
                dataset=self.dataset_name,
                csv_path=csv_path,
                possible_label_columns=self.label_columns,
            )
            for csv_path in csv_files
        ]
        return file_audits, schema_audits
