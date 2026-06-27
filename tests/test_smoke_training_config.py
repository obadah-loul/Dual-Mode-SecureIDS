"""Torch-free tests for smoke-training config parsing and safety rules.

These tests validate only the smoke *config* layer (``load_smoke_config`` in
``secureids.training.config``), which is intentionally torch-free. They do not
import torch, do not load datasets, and do not run any smoke training. The smoke
*execution* module (``secureids.training.smoke``) requires PyTorch and is not
exercised here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from secureids.training.config import SmokeConfigError, load_smoke_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def _base_smoke_dict() -> dict:
    return {
        "dataset": "unsw_nb15",
        "base_config": "configs/training/unsw_nb15_binary.yaml",
        "processed_dir": "data/processed/unsw_nb15/binary",
        "input_dim": 190,
        "smoke": {
            "enabled": True,
            "non_final": True,
            "max_train_samples": 4096,
            "max_val_samples": 2048,
            "max_test_samples": 2048,
            "batch_size": 512,
            "max_epochs": 1,
            "max_batches_per_epoch": 4,
            "evaluation_batches": 2,
            "save_checkpoint": False,
            "output_json": "results/audits/centralized_smoke_check.json",
            "report_md": "docs/CENTRALIZED_TRAINING_SMOKE_CHECK.md",
        },
    }


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "smoke.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "config_name,expected_dim",
    [
        ("smoke_cicids2018_binary.yaml", 77),
        ("smoke_unsw_nb15_binary.yaml", 190),
    ],
)
def test_repo_smoke_configs_are_non_final_and_safe(config_name, expected_dim):
    config_path = REPO_ROOT / "configs" / "training" / config_name
    smoke = load_smoke_config(config_path, project_root=REPO_ROOT)

    assert smoke.non_final is True
    assert smoke.enabled is True
    assert smoke.save_checkpoint is False
    assert smoke.input_dim == expected_dim
    assert smoke.output_json == "results/audits/centralized_smoke_check.json"
    assert smoke.report_md == "docs/CENTRALIZED_TRAINING_SMOKE_CHECK.md"
    # Outputs must never be final result paths.
    assert not smoke.output_json.startswith("results/final")
    assert not smoke.report_md.startswith("results/final")


def test_smoke_config_parses_without_torch(tmp_path):
    path = _write(tmp_path, _base_smoke_dict())
    smoke = load_smoke_config(path, project_root=tmp_path)

    assert smoke.dataset == "unsw_nb15"
    assert smoke.base_config == "configs/training/unsw_nb15_binary.yaml"
    assert smoke.batch_size == 512
    assert smoke.max_epochs == 1
    assert smoke.max_batches_per_epoch == 4


def test_smoke_config_requires_non_final_true(tmp_path):
    data = _base_smoke_dict()
    data["smoke"]["non_final"] = False
    path = _write(tmp_path, data)
    with pytest.raises(SmokeConfigError):
        load_smoke_config(path, project_root=tmp_path)


def test_smoke_config_requires_enabled_true(tmp_path):
    data = _base_smoke_dict()
    data["smoke"]["enabled"] = False
    path = _write(tmp_path, data)
    with pytest.raises(SmokeConfigError):
        load_smoke_config(path, project_root=tmp_path)


def test_smoke_save_checkpoint_defaults_false(tmp_path):
    data = _base_smoke_dict()
    del data["smoke"]["save_checkpoint"]
    path = _write(tmp_path, data)
    smoke = load_smoke_config(path, project_root=tmp_path)
    assert smoke.save_checkpoint is False


def test_smoke_output_paths_must_not_be_final(tmp_path):
    data = _base_smoke_dict()
    data["smoke"]["output_json"] = "results/final/centralized/smoke.json"
    path = _write(tmp_path, data)
    with pytest.raises(SmokeConfigError):
        load_smoke_config(path, project_root=tmp_path)


def test_smoke_missing_required_key_raises(tmp_path):
    data = _base_smoke_dict()
    del data["base_config"]
    path = _write(tmp_path, data)
    with pytest.raises(SmokeConfigError):
        load_smoke_config(path, project_root=tmp_path)
