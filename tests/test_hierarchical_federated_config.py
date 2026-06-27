from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from secureids.federated.hierarchical_plan import (
    HierarchicalFederatedPlanError,
    load_hierarchical_federated_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNSW_CONFIG = "configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml"
CICIDS_CONFIG = "configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml"


@pytest.mark.parametrize("config_path", [UNSW_CONFIG, CICIDS_CONFIG])
def test_clean_hierarchical_fedavg_configs_use_real_runner_contract(config_path):
    plan = load_hierarchical_federated_plan(config_path, project_root=PROJECT_ROOT)

    assert plan.raw["status"] == "not_run_yet"
    assert plan.raw["initialization"] == "from_scratch"
    assert plan.raw["federation"]["client_split"] == "attack_family_aware_iid"
    assert plan.raw["centralized_reference"]["use"] == "reference_only"
    assert plan.raw["centralized_reference"]["warm_start_from_centralized"] is False
    assert "metrics" in plan.raw["centralized_reference"]
    assert plan.raw["aggregation"]["strategy"] == "fedavg"
    assert plan.raw["attack"]["type"] == "none"


def test_warm_start_from_centralized_reference_is_rejected(tmp_path):
    raw = yaml.safe_load((PROJECT_ROOT / UNSW_CONFIG).read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["centralized_reference"]["warm_start_from_centralized"] = True
    path = tmp_path / "warm_start.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(HierarchicalFederatedPlanError, match="warm_start"):
        load_hierarchical_federated_plan(path, project_root=PROJECT_ROOT)


def test_clean_fedavg_requires_attack_family_aware_split(tmp_path):
    raw = yaml.safe_load((PROJECT_ROOT / CICIDS_CONFIG).read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["federation"]["client_split"] = "stratified_iid"
    path = tmp_path / "binary_only_split.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(HierarchicalFederatedPlanError, match="attack_family_aware_iid"):
        load_hierarchical_federated_plan(path, project_root=PROJECT_ROOT)
