"""Adapter and pipeline metadata contracts for SecureIDS V2.

These dataclasses describe supported adapter/pipeline metadata only. They do not
load datasets, preprocessing artifacts, checkpoints, or model frameworks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class ArtifactStatus:
    """Existence status for a metadata or artifact path."""

    path: str
    exists: bool
    kind: str
    required_for: str
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreprocessingArtifactSet:
    """Registered preprocessing/taxonomy metadata for one adapter route."""

    binary_config: str
    hierarchical_config: str
    taxonomy_config: str
    expected_processed_dir: str | None
    expected_audit_files: list[str] = field(default_factory=list)
    artifact_statuses: list[ArtifactStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CheckpointReference:
    """Checkpoint-family reference without claiming final validity."""

    checkpoint_family: str
    expected_path: str | None
    exists: bool
    checkpoint_type: str
    is_final_claim: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdapterPipelineMetadata:
    """Complete metadata returned for a supported adapter/pipeline."""

    schema_id: str
    adapter_id: str
    adapter_class: str
    dataset_display_name: str
    raw_label_column: str
    binary_label_mapping: dict[str, object]
    attack_family_source: str
    taxonomy_config: str
    preprocessing_artifacts: PreprocessingArtifactSet
    model_input_dim: int | None
    checkpoint_references: list[CheckpointReference]
    prediction_sample_format: str
    dashboard_label: str
    supports_hierarchical: bool
    notes: list[str] = field(default_factory=list)
    training_configs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


__all__ = [
    "AdapterPipelineMetadata",
    "ArtifactStatus",
    "CheckpointReference",
    "PreprocessingArtifactSet",
]
