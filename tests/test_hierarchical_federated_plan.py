from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from secureids.federated.hierarchical_plan import (
    HierarchicalFederatedPlanError,
    load_hierarchical_federated_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIGS = [
    "configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml",
    "configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml",
    "configs/federated/experiments/cicids_hierarchical_byzantine_signflip.yaml",
    "configs/federated/experiments/unsw_hierarchical_byzantine_signflip.yaml",
    "configs/federated/experiments/cicids_hierarchical_robust_trimmed_mean.yaml",
    "configs/federated/experiments/unsw_hierarchical_robust_trimmed_mean.yaml",
]


@pytest.mark.parametrize("config_path", CONFIGS)
def test_future_hierarchical_federated_configs_validate(config_path):
    plan = load_hierarchical_federated_plan(config_path, project_root=PROJECT_ROOT)

    assert plan.raw["status"] == "not_run_yet"
    assert plan.raw["safety"]["dry_run_writes_outputs"] is False
    assert plan.raw["centralized_reference"]["use"] == "reference_only"


def test_final_output_path_rejected(tmp_path):
    config_path = PROJECT_ROOT / CONFIGS[0]
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["outputs"]["checkpoint"] = "models/final/unsafe.pt"
    unsafe_path = tmp_path / "unsafe.yaml"
    unsafe_path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(HierarchicalFederatedPlanError, match="models/final"):
        load_hierarchical_federated_plan(unsafe_path, project_root=PROJECT_ROOT)


def test_a11_reference_rejected(tmp_path):
    config_path = PROJECT_ROOT / CONFIGS[1]
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["centralized_reference"]["checkpoint"] = (
        "models/experiments/unsw_a11_enhanced_feature_protocol_seed42.pt"
    )
    unsafe_path = tmp_path / "a11.yaml"
    unsafe_path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(HierarchicalFederatedPlanError, match="final reference|A11"):
        load_hierarchical_federated_plan(unsafe_path, project_root=PROJECT_ROOT)
