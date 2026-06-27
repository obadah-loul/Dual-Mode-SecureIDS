"""Markdown and CSV writers for safe dataset audit outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from secureids.datasets.base import DatasetFileAudit, DatasetSchemaAudit


MISSING_RAW_DATA_NOTE = (
    "Raw data not found yet. Audit framework is ready, but no final dataset "
    "audit has been completed."
)

FILE_AUDIT_FIELDS = [
    "dataset",
    "path",
    "exists",
    "is_csv",
    "size_bytes",
    "size_human",
    "status",
    "error",
]

SCHEMA_AUDIT_FIELDS = [
    "dataset",
    "path",
    "status",
    "column_count",
    "columns",
    "label_column",
    "numeric_columns",
    "categorical_columns",
    "missing_values_sample",
    "sample_rows",
    "notes",
    "error",
]


def write_csv_rows(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_dataset_audit_outputs(
    project_root: Path,
    file_audits: list[DatasetFileAudit],
    schema_audits: dict[str, list[DatasetSchemaAudit]],
) -> None:
    """Write all dataset audit Markdown and CSV artifacts."""

    docs_dir = project_root / "docs"
    audits_dir = project_root / "results" / "audits"
    docs_dir.mkdir(parents=True, exist_ok=True)
    audits_dir.mkdir(parents=True, exist_ok=True)

    write_csv_rows(
        audits_dir / "dataset_file_inventory.csv",
        FILE_AUDIT_FIELDS,
        [audit.to_dict() for audit in file_audits],
    )

    write_csv_rows(
        audits_dir / "cicids_schema_audit.csv",
        SCHEMA_AUDIT_FIELDS,
        [audit.to_flat_dict() for audit in schema_audits.get("cicids2018", [])],
    )
    write_csv_rows(
        audits_dir / "unsw_schema_audit.csv",
        SCHEMA_AUDIT_FIELDS,
        [audit.to_flat_dict() for audit in schema_audits.get("unsw_nb15", [])],
    )

    (docs_dir / "DATASET_SCHEMA_AUDIT.md").write_text(
        build_dataset_schema_audit_markdown(file_audits, schema_audits),
        encoding="utf-8",
    )
    (docs_dir / "UNSW_COMPATIBILITY_DECISION.md").write_text(
        build_unsw_compatibility_decision_markdown(),
        encoding="utf-8",
    )


def build_dataset_schema_audit_markdown(
    file_audits: list[DatasetFileAudit] | None = None,
    schema_audits: dict[str, list[DatasetSchemaAudit]] | None = None,
) -> str:
    file_audits = file_audits or []
    schema_audits = schema_audits or {}
    has_schema_results = any(schema_audits.get(dataset) for dataset in schema_audits)

    lines = [
        "# DATASET_SCHEMA_AUDIT.md",
        "",
        "## Purpose",
        "",
        "The dataset audit framework has been created for the clean V2 rebuild.",
        "It inspects raw CSV inventories, headers, small samples, candidate label",
        "columns, likely numeric/categorical columns, and sample missing values",
        "before any preprocessing or training begins.",
        "",
        "## Expected Raw Data Locations",
        "",
        "- `data/raw/cicids2018`",
        "- `data/raw/unsw_nb15`",
        "",
        "## Audit Policy",
        "",
        "- CICIDS2018 and UNSW-NB15 are audited separately.",
        "- The audit reads CSV headers and small samples only.",
        "- No final audit results exist until raw files are placed in V2",
        "  `data/raw` and the audit command is run.",
        "- No training or preprocessing has been performed.",
        "- No row counts, label counts, or performance metrics are invented.",
        "",
        "## Current Status",
        "",
    ]

    if not has_schema_results:
        lines.extend([
            MISSING_RAW_DATA_NOTE,
            "",
        ])
    else:
        lines.extend([
            "Raw CSV files were found and inspected with header/sample-only",
            "auditing. These are not final preprocessing outputs or model",
            "performance results.",
            "",
        ])

    if file_audits:
        lines.extend([
            "## File Inventory Summary",
            "",
            "| Dataset | Path | Status | Size |",
            "| --- | --- | --- | --- |",
        ])
        for audit in file_audits:
            lines.append(
                f"| {audit.dataset} | `{audit.path}` | {audit.status} | "
                f"{audit.size_human} |"
            )
        lines.append("")

    for dataset_name, audits in schema_audits.items():
        title = "CICIDS2018" if dataset_name == "cicids2018" else "UNSW-NB15"
        lines.extend([
            f"## {title} Schema Audit",
            "",
        ])
        if not audits:
            lines.extend([
                "No CSV schema audit has been completed for this dataset yet.",
                "",
            ])
            continue

        lines.extend([
            "| File | Status | Columns | Label Column | Sample Rows |",
            "| --- | --- | ---: | --- | ---: |",
        ])
        for audit in audits:
            label = audit.label_column or "not detected"
            lines.append(
                f"| `{audit.path}` | {audit.status} | {audit.column_count} | "
                f"{label} | {audit.sample_rows} |"
            )
        lines.append("")

    lines.extend([
        "## Next Step",
        "",
        "Place the official raw CICIDS2018 and UNSW-NB15 files under the expected",
        "V2 raw-data directories, then run:",
        "",
        "```bash",
        "python -m secureids.cli audit-data --dataset all",
        "```",
        "",
    ])
    return "\n".join(lines)


def build_unsw_compatibility_decision_markdown() -> str:
    return "\n".join([
        "# UNSW_COMPATIBILITY_DECISION.md",
        "",
        "## Decision",
        "",
        "Official UNSW-NB15 must not be forced into the old CICIDS2018 feature",
        "pipeline.",
        "",
        "## Rationale",
        "",
        "- The old CICIDS2018 model expected CICIDS-specific numeric features.",
        "- UNSW-NB15 has a different schema and categorical fields such as",
        "  `proto`, `service`, and `state`.",
        "- Binary label mapping is valid.",
        "- Direct frozen CICIDS-to-UNSW feature evaluation is invalid.",
        "",
        "## V2 Solution",
        "",
        "V2 uses dataset-specific adapters and dataset-specific preprocessors for",
        "CICIDS2018 and UNSW-NB15. The project keeps one shared SecureIDSNet",
        "architecture, but uses dataset-specific final checkpoints:",
        "",
        "- `models/final/final_cicids_binary.pt`",
        "- `models/final/final_unsw_binary.pt`",
        "",
        "This keeps the binary IDS task valid without making a fake cross-dataset",
        "generalization claim.",
        "",
    ])
