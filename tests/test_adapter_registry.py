from __future__ import annotations

import subprocess
import sys

import pytest

from secureids.datasets.adapter_registry import (
    artifact_status_report,
    get_adapter_metadata,
    list_supported_adapters,
    resolve_metadata_from_columns,
)
from secureids.datasets.router import UnsupportedSchemaError


CICIDS_COLUMNS = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Fwd Packet Length Max",
    "Bwd Packet Length Max",
    "Protocol",
    "Label",
]

UNSW_COLUMNS = [
    "dur",
    "proto",
    "service",
    "state",
    "spkts",
    "dpkts",
    "sbytes",
    "dbytes",
    "attack_cat",
    "label",
]


def test_list_supported_adapters_includes_expected_schemas():
    assert list_supported_adapters() == ["cicids2018", "unsw_nb15"]


def test_get_cicids_metadata_contains_registered_paths():
    metadata = get_adapter_metadata("cicids2018")

    assert metadata.schema_id == "cicids2018"
    assert metadata.adapter_id == "secureids.datasets.cicids2018.CICIDS2018Adapter"
    assert metadata.preprocessing_artifacts.binary_config == "configs/preprocessing/cicids2018_binary.yaml"
    assert metadata.preprocessing_artifacts.hierarchical_config == "configs/preprocessing/cicids2018_hierarchical.yaml"
    assert metadata.taxonomy_config == "configs/taxonomy/cicids2018_attack_taxonomy.yaml"
    assert metadata.supports_hierarchical is True


def test_get_unsw_metadata_contains_registered_paths():
    metadata = get_adapter_metadata("unsw_nb15")

    assert metadata.schema_id == "unsw_nb15"
    assert metadata.adapter_id == "secureids.datasets.unsw_nb15.UNSWNB15Adapter"
    assert metadata.preprocessing_artifacts.binary_config == "configs/preprocessing/unsw_nb15_binary.yaml"
    assert metadata.preprocessing_artifacts.hierarchical_config == "configs/preprocessing/unsw_nb15_hierarchical.yaml"
    assert metadata.taxonomy_config == "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml"
    assert metadata.supports_hierarchical is True


def test_unknown_schema_raises_clear_error():
    with pytest.raises(UnsupportedSchemaError, match="Unsupported adapter schema"):
        get_adapter_metadata("made_up_schema")


def test_resolve_metadata_from_columns_returns_cicids_metadata():
    metadata = resolve_metadata_from_columns(CICIDS_COLUMNS)

    assert metadata.schema_id == "cicids2018"
    assert metadata.dashboard_label == "CICIDS2018 adapter/pipeline"


def test_resolve_metadata_from_columns_returns_unsw_metadata():
    metadata = resolve_metadata_from_columns(UNSW_COLUMNS)

    assert metadata.schema_id == "unsw_nb15"
    assert metadata.dashboard_label == "UNSW-NB15 adapter/pipeline"


def test_artifact_statuses_expose_exists_booleans_without_fake_success():
    metadata = get_adapter_metadata("cicids2018")
    statuses = metadata.preprocessing_artifacts.artifact_statuses

    assert statuses
    assert all(isinstance(status.exists, bool) for status in statuses)
    assert all(status.note for status in statuses)


def test_checkpoint_references_include_existence_and_no_final_claims():
    metadata = get_adapter_metadata("unsw_nb15")

    assert metadata.checkpoint_references
    assert all(isinstance(checkpoint.exists, bool) for checkpoint in metadata.checkpoint_references)
    assert all(checkpoint.is_final_claim is False for checkpoint in metadata.checkpoint_references)


def test_artifact_status_report_is_metadata_only():
    report = artifact_status_report("unsw_nb15")

    assert report["schema_id"] == "unsw_nb15"
    assert "preprocessing_artifacts" in report
    assert "checkpoint_references" in report


def test_registry_does_not_import_torch():
    # Run in a fresh process so the check is not contaminated by sibling test
    # modules (which legitimately import torch) populating sys.modules. This still
    # proves that importing the adapter registry alone never pulls in torch.
    code = (
        "import sys; "
        "import secureids.datasets.adapter_registry; "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, (
        "importing secureids.datasets.adapter_registry pulled in torch.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
