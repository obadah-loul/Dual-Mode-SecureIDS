"""Config loading/validation tests for the UNSW A9.9 attack-family specialist."""

from __future__ import annotations

import copy

import pytest

yaml = pytest.importorskip("yaml")

from secureids.training.attack_family_specialist_config import (
    PROJECT_ROOT,
    AttackFamilySpecialistConfigError,
    load_attack_family_specialist_config,
)

SEED42_CONFIG = (
    PROJECT_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "unsw_a99_attack_family_specialist_seed42.yaml"
)


def test_seed42_config_loads_and_validates():
    config = load_attack_family_specialist_config(SEED42_CONFIG, project_root=PROJECT_ROOT)
    assert config.dataset == "unsw_nb15"
    assert config.task == "attack_family_specialist"
    assert config.status == "not_run_yet"
    assert config.seed == 42
    assert config.input_dim == 192
    assert config.num_attack_families == 9
    assert config.frozen_a9_router["trainable"] is False
    assert config.frozen_a9_router["checkpoint"].replace("\\", "/") == (
        "models/final/final_unsw_hierarchical.pt"
    )
    assert config.training_data["attack_rows_only"] is True
    assert config.checkpoint_selection["use_validation_only"] is True
    assert config.checkpoint_selection["select_by_test_metrics"] is False
    assert config.safety["training_executed"] is False
    # outputs isolated under experiments / docs experiments
    assert config.outputs["checkpoint"].startswith("models/experiments/")
    assert config.outputs["result_dir"].startswith("results/experiments/")
    assert config.outputs["report_md"].startswith("docs/experiments/")
    for weak in ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms"):
        assert weak in config.weak_classes_must_remain_visible


def _write_tmp(raw, tmp_path):
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


@pytest.fixture()
def base_raw():
    return yaml.safe_load(SEED42_CONFIG.read_text(encoding="utf-8"))


def test_rejects_final_checkpoint_path(base_raw, tmp_path):
    raw = copy.deepcopy(base_raw)
    raw["outputs"]["checkpoint"] = "models/final/final_unsw_hierarchical.pt"
    with pytest.raises(AttackFamilySpecialistConfigError):
        load_attack_family_specialist_config(_write_tmp(raw, tmp_path), project_root=PROJECT_ROOT)


def test_rejects_test_based_weights(base_raw, tmp_path):
    raw = copy.deepcopy(base_raw)
    raw["class_imbalance"]["allow_test_based_weights"] = True
    with pytest.raises(AttackFamilySpecialistConfigError):
        load_attack_family_specialist_config(_write_tmp(raw, tmp_path), project_root=PROJECT_ROOT)


def test_rejects_test_based_selection(base_raw, tmp_path):
    raw = copy.deepcopy(base_raw)
    raw["checkpoint_selection"]["select_by_test_metrics"] = True
    with pytest.raises(AttackFamilySpecialistConfigError):
        load_attack_family_specialist_config(_write_tmp(raw, tmp_path), project_root=PROJECT_ROOT)


def test_rejects_trainable_router(base_raw, tmp_path):
    raw = copy.deepcopy(base_raw)
    raw["frozen_a9_router"]["trainable"] = True
    with pytest.raises(AttackFamilySpecialistConfigError):
        load_attack_family_specialist_config(_write_tmp(raw, tmp_path), project_root=PROJECT_ROOT)


def test_rejects_training_executed_true_in_prep(base_raw, tmp_path):
    raw = copy.deepcopy(base_raw)
    raw["safety"]["training_executed"] = True
    with pytest.raises(AttackFamilySpecialistConfigError):
        load_attack_family_specialist_config(_write_tmp(raw, tmp_path), project_root=PROJECT_ROOT)
