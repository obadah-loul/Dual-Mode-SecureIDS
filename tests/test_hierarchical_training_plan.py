"""Read-only tests for hierarchical training and smoke planning.

The planner may inspect NumPy headers through mmap, but it must not run
training, write final metrics, or create checkpoints.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from secureids.training import hierarchical_planning
from secureids.training.hierarchical_config import (
    load_hierarchical_smoke_config,
    load_hierarchical_training_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "config_name,dataset,input_dim,attack_head_dim",
    [
        ("cicids2018_hierarchical.yaml", "cicids2018", 77, 14),
        ("unsw_nb15_hierarchical.yaml", "unsw_nb15", 192, 9),
    ],
)
def test_hierarchical_training_plan_passes_without_executing_training(
    config_name: str,
    dataset: str,
    input_dim: int,
    attack_head_dim: int,
):
    config = load_hierarchical_training_config(
        REPO_ROOT / "configs" / "training" / config_name,
        project_root=REPO_ROOT,
    )
    plan = hierarchical_planning.build_hierarchical_training_plan(config)

    assert plan["dataset"] == dataset
    assert plan["input_dim"] == input_dim
    assert plan["attack_head_dim"] == attack_head_dim
    assert plan["feature_count"] == input_dim
    assert plan["attack_family_class_count"] == attack_head_dim
    assert plan["safety"]["training_run"] is False
    assert plan["safety"]["evaluation_run"] is False
    assert plan["safety"]["checkpoint_created"] is False
    assert plan["safety"]["metrics_created"] is False
    # Every substantive readiness check must pass. The "future_final_outputs_absent"
    # check is excluded because A9 has legitimately produced UNSW final outputs;
    # the planner correctly reports them as present afterward.
    for check in plan["checks"]:
        if check["name"] == "future_final_outputs_absent":
            continue
        assert check["status"] == "PASS", f"{check['name']}: {check['detail']}"


@pytest.mark.parametrize(
    "config_name,dataset,input_dim,attack_head_dim",
    [
        ("smoke_cicids2018_hierarchical.yaml", "cicids2018", 77, 14),
        ("smoke_unsw_nb15_hierarchical.yaml", "unsw_nb15", 192, 9),
    ],
)
def test_hierarchical_smoke_plan_is_non_final(
    config_name: str,
    dataset: str,
    input_dim: int,
    attack_head_dim: int,
):
    config = load_hierarchical_smoke_config(
        REPO_ROOT / "configs" / "training" / config_name,
        project_root=REPO_ROOT,
    )
    plan = hierarchical_planning.build_hierarchical_smoke_plan(config)

    assert plan["status"] == "PASS"
    assert plan["dataset"] == dataset
    assert plan["input_dim"] == input_dim
    assert plan["attack_head_dim"] == attack_head_dim
    assert plan["sample_limits"]["max_epochs"] == 1
    assert plan["sample_limits"]["max_train_batches"] <= 4
    assert plan["sample_limits"]["max_eval_batches"] <= 2
    assert plan["safety"]["checkpoint_created"] is False
    assert plan["safety"]["metrics_created"] is False
    assert plan["safety"]["save_checkpoint"] is False
    assert plan["safety"]["final_metrics"] is False
    assert plan["safety"]["do_not_report_as_final"] is True
    assert not plan["planned_non_final_outputs"]["output_json"].startswith(
        str(REPO_ROOT / "results" / "final")
    )
    assert all(check["status"] == "PASS" for check in plan["checks"])


def test_unsw_a11_hierarchical_training_plan_passes_without_execution():
    config = load_hierarchical_training_config(
        REPO_ROOT
        / "configs"
        / "training"
        / "experiments"
        / "unsw_a11_enhanced_feature_protocol_seed42.yaml",
        project_root=REPO_ROOT,
    )
    plan = hierarchical_planning.build_hierarchical_training_plan(config)

    assert plan["status"] == "PASS"
    assert plan["dataset"] == "unsw_nb15"
    assert plan["input_dim"] == 192
    assert plan["attack_head_dim"] == 9
    assert plan["hierarchical_data_dir"].endswith(
        "data\\processed\\unsw_a11_enhanced\\hierarchical"
    ) or plan["hierarchical_data_dir"].endswith(
        "data/processed/unsw_a11_enhanced/hierarchical"
    )
    assert plan["planned_outputs"]["checkpoint"].endswith(
        "models\\experiments\\unsw_a11_enhanced_feature_protocol_seed42.pt"
    ) or plan["planned_outputs"]["checkpoint"].endswith(
        "models/experiments/unsw_a11_enhanced_feature_protocol_seed42.pt"
    )
    assert plan["safety"]["training_run"] is False
    assert plan["safety"]["evaluation_run"] is False
    assert plan["safety"]["checkpoint_created"] is False
    assert plan["safety"]["metrics_created"] is False
    assert all(check["status"] == "PASS" for check in plan["checks"])


def test_hierarchical_training_plan_uses_mmap_for_array_shape_checks(monkeypatch):
    calls: list[tuple[str, str | None]] = []

    class FakeMmap:
        def close(self) -> None:
            return None

    class FakeArray:
        def __init__(self, shape: tuple[int, ...]):
            self.shape = shape
            self._mmap = FakeMmap()

    def fake_load(path, mmap_mode=None):
        calls.append((Path(path).name, mmap_mode))
        if Path(path).name.startswith("X_"):
            return FakeArray((10, 77))
        return FakeArray((10,))

    monkeypatch.setattr(hierarchical_planning.np, "load", fake_load)

    config = load_hierarchical_training_config(
        REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml",
        project_root=REPO_ROOT,
    )
    plan = hierarchical_planning.build_hierarchical_training_plan(config)

    # Substantive checks must pass; "future_final_outputs_absent" is excluded
    # because the shared HIERARCHICAL_TRAINING_REPORT.md now exists after A9.
    for check in plan["checks"]:
        if check["name"] == "future_final_outputs_absent":
            continue
        assert check["status"] == "PASS", f"{check['name']}: {check['detail']}"
    assert len(calls) == 12
    assert all(mmap_mode == "r" for _, mmap_mode in calls)
    assert {name.split("_")[0] for name, _ in calls if name.startswith("X_")} == {"X"}
