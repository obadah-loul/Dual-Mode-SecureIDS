"""Adapter/pipeline registry for supported SecureIDS V2 schemas.

The registry resolves schema detection results to metadata and artifact
existence statuses only. It does not load checkpoints, run preprocessing,
train, evaluate, or make predictions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from secureids.datasets.adapter_contracts import (
    AdapterPipelineMetadata,
    ArtifactStatus,
    CheckpointReference,
    PreprocessingArtifactSet,
)
from secureids.datasets.router import UnsupportedSchemaError, route_schema
from secureids.datasets.schema_detector import SupportedSchema


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def list_supported_adapters() -> list[str]:
    """Return supported adapter schema IDs."""

    return [SupportedSchema.CICIDS2018.value, SupportedSchema.UNSW_NB15.value]


def get_adapter_metadata(schema_id: str) -> AdapterPipelineMetadata:
    """Return metadata for a supported schema ID."""

    normalized = _normalize_schema_id(schema_id)
    if normalized == SupportedSchema.CICIDS2018.value:
        return _build_cicids_metadata()
    if normalized == SupportedSchema.UNSW_NB15.value:
        return _build_unsw_metadata()
    raise UnsupportedSchemaError(
        f"Unsupported adapter schema: {schema_id!r}. Supported schemas are: "
        f"{', '.join(list_supported_adapters())}."
    )


def get_all_adapter_metadata() -> dict[str, AdapterPipelineMetadata]:
    """Return fresh metadata for every supported adapter route."""

    return {
        schema_id: get_adapter_metadata(schema_id)
        for schema_id in list_supported_adapters()
    }


def resolve_metadata_from_columns(
    columns_or_dataframe: Any,
    require_supported: bool = True,
) -> AdapterPipelineMetadata:
    """Detect schema from columns and return adapter/pipeline metadata."""

    route = route_schema(columns_or_dataframe, require_supported=require_supported)
    if route.schema_id == SupportedSchema.UNKNOWN.value:
        return _build_unknown_metadata(route.reason)
    return get_adapter_metadata(route.schema_id)


def artifact_status_report(schema_id: str) -> dict[str, object]:
    """Return artifact and checkpoint existence statuses for one schema."""

    metadata = get_adapter_metadata(schema_id)
    return {
        "schema_id": metadata.schema_id,
        "preprocessing_artifacts": [
            status.to_dict()
            for status in metadata.preprocessing_artifacts.artifact_statuses
        ],
        "checkpoint_references": [
            checkpoint.to_dict()
            for checkpoint in metadata.checkpoint_references
        ],
    }


def _build_cicids_metadata() -> AdapterPipelineMetadata:
    preprocessing = _build_preprocessing_artifacts(
        binary_config="configs/preprocessing/cicids2018_binary.yaml",
        hierarchical_config="configs/preprocessing/cicids2018_hierarchical.yaml",
        taxonomy_config="configs/taxonomy/cicids2018_attack_taxonomy.yaml",
        expected_processed_dir="data/processed/cicids2018/hierarchical",
        expected_audit_files=[
            "results/audits/preprocessing_manifest_cicids2018.json",
            "results/audits/hierarchical_preprocessing_audit_cicids2018.json",
        ],
        extra_artifacts=[
            (
                "models/final/preprocessors/cicids2018_binary_preprocessor.joblib",
                "preprocessor_artifact",
                "future_transform",
                "Binary preprocessor artifact; existence is reported only.",
            ),
            (
                "data/processed/cicids2018/binary",
                "processed_directory",
                "future_binary_features",
                "Expected binary processed feature directory.",
            ),
        ],
    )
    return AdapterPipelineMetadata(
        schema_id=SupportedSchema.CICIDS2018.value,
        adapter_id="secureids.datasets.cicids2018.CICIDS2018Adapter",
        adapter_class="CICIDS2018Adapter",
        dataset_display_name="CICIDS2018-like supported schema",
        raw_label_column="Label",
        binary_label_mapping={
            "BENIGN": 0,
            "Benign": 0,
            "benign": 0,
            "all_other_labels": 1,
        },
        attack_family_source="Label",
        taxonomy_config=preprocessing.taxonomy_config,
        preprocessing_artifacts=preprocessing,
        model_input_dim=77,
        checkpoint_references=[
            _checkpoint(
                "cicids2018_hierarchical_final",
                "models/final/final_cicids_hierarchical.pt",
                "centralized_hierarchical",
            ),
            _checkpoint(
                "cicids2018_binary_final",
                "models/final/final_cicids_binary.pt",
                "centralized_binary",
            ),
            _checkpoint(
                "cicids2018_hierarchical_fedavg",
                "models/federated/fedavg_cicids_hierarchical.pt",
                "fedavg_hierarchical",
            ),
            _checkpoint(
                "cicids2018_binary_fedavg",
                "models/federated/fedavg_cicids_binary.pt",
                "fedavg_binary",
            ),
        ],
        prediction_sample_format=(
            "One CICIDS2018-like row or file with supported flow-feature columns; "
            "later pipeline must apply saved CICIDS preprocessing artifacts."
        ),
        dashboard_label="CICIDS2018 adapter/pipeline",
        supports_hierarchical=True,
        training_configs=[
            "configs/training/cicids2018_binary.yaml",
            "configs/training/cicids2018_hierarchical.yaml",
        ],
        notes=[
            "Input schema matches a supported adapter/pipeline; this is not a traffic-origin claim.",
            "Model input dimension 77 comes from the CICIDS hierarchical preprocessing config metadata.",
            "Checkpoint references report file existence only and do not claim final acceptance.",
        ],
    )


def _build_unsw_metadata() -> AdapterPipelineMetadata:
    preprocessing = _build_preprocessing_artifacts(
        binary_config="configs/preprocessing/unsw_nb15_binary.yaml",
        hierarchical_config="configs/preprocessing/unsw_nb15_hierarchical.yaml",
        taxonomy_config="configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        expected_processed_dir="data/processed/unsw_nb15/hierarchical",
        expected_audit_files=[
            "results/audits/preprocessing_manifest_unsw_nb15.json",
            "results/audits/hierarchical_preprocessing_audit_unsw_nb15.json",
        ],
        extra_artifacts=[
            (
                "models/final/preprocessors/unsw_nb15_binary_preprocessor.joblib",
                "preprocessor_artifact",
                "future_transform",
                "Binary preprocessor artifact; existence is reported only.",
            ),
            (
                "data/processed/unsw_nb15/binary",
                "processed_directory",
                "future_binary_features",
                "Expected binary processed feature directory.",
            ),
        ],
    )
    return AdapterPipelineMetadata(
        schema_id=SupportedSchema.UNSW_NB15.value,
        adapter_id="secureids.datasets.unsw_nb15.UNSWNB15Adapter",
        adapter_class="UNSWNB15Adapter",
        dataset_display_name="UNSW-NB15-like supported schema",
        raw_label_column="label",
        binary_label_mapping={
            "label_0": "Benign / Normal",
            "label_1": "Attack",
        },
        attack_family_source="attack_cat",
        taxonomy_config=preprocessing.taxonomy_config,
        preprocessing_artifacts=preprocessing,
        model_input_dim=192,
        checkpoint_references=[
            _checkpoint(
                "unsw_nb15_hierarchical_final",
                "models/final/final_unsw_hierarchical.pt",
                "centralized_hierarchical",
            ),
            _checkpoint(
                "unsw_nb15_binary_final",
                "models/final/final_unsw_binary.pt",
                "centralized_binary",
            ),
            _checkpoint(
                "unsw_nb15_hierarchical_fedavg",
                "models/federated/fedavg_unsw_hierarchical.pt",
                "fedavg_hierarchical",
            ),
            _checkpoint(
                "unsw_nb15_binary_fedavg",
                "models/federated/fedavg_unsw_binary.pt",
                "fedavg_binary",
            ),
        ],
        prediction_sample_format=(
            "One UNSW-NB15-like row or file with supported tabular columns; "
            "later pipeline must apply saved UNSW preprocessing artifacts."
        ),
        dashboard_label="UNSW-NB15 adapter/pipeline",
        supports_hierarchical=True,
        training_configs=[
            "configs/training/unsw_nb15_binary.yaml",
            "configs/training/unsw_nb15_hierarchical.yaml",
            "configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml",
            "configs/training/unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml",
        ],
        notes=[
            "Input schema matches a supported adapter/pipeline; this is not a traffic-origin claim.",
            "Model input dimension 192 comes from corrected UNSW hierarchical preprocessing config metadata.",
            "A9 remains accepted baseline context; A9.6/A9.7/A9.8 are evidence, not automatic replacements.",
            "Checkpoint references report file existence only and do not claim final acceptance.",
        ],
    )


def _build_unknown_metadata(reason: str) -> AdapterPipelineMetadata:
    empty_artifacts = PreprocessingArtifactSet(
        binary_config="",
        hierarchical_config="",
        taxonomy_config="",
        expected_processed_dir=None,
        expected_audit_files=[],
        artifact_statuses=[],
    )
    return AdapterPipelineMetadata(
        schema_id=SupportedSchema.UNKNOWN.value,
        adapter_id="",
        adapter_class="",
        dataset_display_name="Unknown / unsupported schema",
        raw_label_column="",
        binary_label_mapping={},
        attack_family_source="",
        taxonomy_config="",
        preprocessing_artifacts=empty_artifacts,
        model_input_dim=None,
        checkpoint_references=[],
        prediction_sample_format="Unsupported schema; no prediction pipeline metadata is available.",
        dashboard_label="Unknown / unsupported schema",
        supports_hierarchical=False,
        notes=[reason],
    )


def _build_preprocessing_artifacts(
    *,
    binary_config: str,
    hierarchical_config: str,
    taxonomy_config: str,
    expected_processed_dir: str,
    expected_audit_files: list[str],
    extra_artifacts: list[tuple[str, str, str, str]],
) -> PreprocessingArtifactSet:
    statuses = [
        _artifact(binary_config, "preprocessing_config", "binary_preprocessing", "Registered binary preprocessing config."),
        _artifact(hierarchical_config, "preprocessing_config", "hierarchical_preprocessing", "Registered hierarchical preprocessing config."),
        _artifact(taxonomy_config, "taxonomy_config", "attack_family_mapping", "Registered dataset-aware attack taxonomy config."),
        _artifact(expected_processed_dir, "processed_directory", "future_hierarchical_features", "Expected hierarchical processed feature directory."),
    ]
    statuses.extend(
        _artifact(path, "audit_file", "evidence_review", "Expected preprocessing/hierarchical audit evidence.")
        for path in expected_audit_files
    )
    statuses.extend(
        _artifact(path, kind, required_for, note)
        for path, kind, required_for, note in extra_artifacts
    )
    return PreprocessingArtifactSet(
        binary_config=binary_config,
        hierarchical_config=hierarchical_config,
        taxonomy_config=taxonomy_config,
        expected_processed_dir=expected_processed_dir,
        expected_audit_files=expected_audit_files,
        artifact_statuses=statuses,
    )


def _artifact(path: str, kind: str, required_for: str, note: str) -> ArtifactStatus:
    return ArtifactStatus(
        path=path,
        exists=_path_exists(path),
        kind=kind,
        required_for=required_for,
        note=note,
    )


def _checkpoint(
    checkpoint_family: str,
    expected_path: str,
    checkpoint_type: str,
) -> CheckpointReference:
    exists = _path_exists(expected_path)
    if exists:
        note = (
            "File exists; registry records existence only and does not claim "
            "this checkpoint is final accepted evidence."
        )
    else:
        note = "Missing or unconfirmed; future training/artifact review is required."
    return CheckpointReference(
        checkpoint_family=checkpoint_family,
        expected_path=expected_path,
        exists=exists,
        checkpoint_type=checkpoint_type,
        is_final_claim=False,
        note=note,
    )


def _path_exists(path: str) -> bool:
    return (PROJECT_ROOT / path).exists()


def _normalize_schema_id(schema_id: str) -> str:
    normalized = schema_id.strip().lower().replace("-", "_")
    aliases = {
        "cicids": SupportedSchema.CICIDS2018.value,
        "cicids2018": SupportedSchema.CICIDS2018.value,
        "unsw": SupportedSchema.UNSW_NB15.value,
        "unsw_nb15": SupportedSchema.UNSW_NB15.value,
    }
    return aliases.get(normalized, normalized)


__all__ = [
    "artifact_status_report",
    "get_adapter_metadata",
    "get_all_adapter_metadata",
    "list_supported_adapters",
    "resolve_metadata_from_columns",
]
