"""Tests for the dataset-aware hierarchical precondition gate.

These exercise `_dataset_precondition_errors` in isolation with synthetic temp
paths, so they prove the UNSW/A8.8 dependency is required ONLY for UNSW and that
CICIDS no longer depends on UNSW files -- without loading the multi-million-row
CICIDS arrays or running any training.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from secureids.training.hierarchical_config import (  # noqa: E402
    load_hierarchical_training_config,
)

torch = pytest.importorskip("torch")

from secureids.training.hierarchical_trainer import (  # noqa: E402
    _dataset_precondition_errors,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CICIDS_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
UNSW_CONFIG = REPO_ROOT / "configs" / "training" / "unsw_nb15_hierarchical.yaml"


def _cfg(dataset: str):
    # _dataset_precondition_errors only reads config.dataset.
    return SimpleNamespace(dataset=dataset)


def _write_unsw_evidence(root: Path, ready: bool) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "results" / "audits").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "UNSW_SPLIT_PROTOCOL_DECISION.md").write_text("decision", encoding="utf-8")
    (root / "results" / "audits" / "pre_training_high_findings_resolution.json").write_text(
        json.dumps({"ready_for_unsw_training": ready}), encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# CICIDS: no UNSW/A8.8 dependency
# --------------------------------------------------------------------------- #
def test_cicids_preconditions_do_not_require_unsw_files(tmp_path):
    # Empty project root (no UNSW files at all) must still produce no errors.
    assert _dataset_precondition_errors(_cfg("cicids2018"), tmp_path) == []


def test_cicids_unaffected_even_if_unsw_not_ready(tmp_path):
    _write_unsw_evidence(tmp_path, ready=False)
    assert _dataset_precondition_errors(_cfg("cicids2018"), tmp_path) == []


def test_real_cicids_config_canonical_dataset_has_no_unsw_dependency(tmp_path):
    config = load_hierarchical_training_config(CICIDS_CONFIG, project_root=REPO_ROOT)
    assert config.dataset == "cicids2018"
    # Use a tmp project_root with NO UNSW files to prove the dependency is gone.
    assert _dataset_precondition_errors(config, tmp_path) == []


# --------------------------------------------------------------------------- #
# UNSW: still requires its A8.8 evidence
# --------------------------------------------------------------------------- #
def test_unsw_preconditions_require_unsw_files_when_absent(tmp_path):
    errors = _dataset_precondition_errors(_cfg("unsw_nb15"), tmp_path)
    assert any("UNSW split protocol decision doc" in e for e in errors)
    assert any("A8.8 high-findings resolution json" in e for e in errors)


def test_unsw_preconditions_fail_when_not_ready(tmp_path):
    _write_unsw_evidence(tmp_path, ready=False)
    errors = _dataset_precondition_errors(_cfg("unsw_nb15"), tmp_path)
    assert any("ready_for_unsw_training is not true" in e for e in errors)


def test_unsw_preconditions_pass_when_evidence_present_and_ready(tmp_path):
    _write_unsw_evidence(tmp_path, ready=True)
    assert _dataset_precondition_errors(_cfg("unsw_nb15"), tmp_path) == []


def test_real_unsw_config_uses_unsw_branch(tmp_path):
    config = load_hierarchical_training_config(UNSW_CONFIG, project_root=REPO_ROOT)
    assert config.dataset == "unsw_nb15"
    # Without UNSW evidence it must still fail (UNSW safety preserved).
    assert _dataset_precondition_errors(config, tmp_path) != []
    # With evidence present and ready, it passes.
    _write_unsw_evidence(tmp_path, ready=True)
    assert _dataset_precondition_errors(config, tmp_path) == []


# --------------------------------------------------------------------------- #
# Unsupported dataset fails clearly
# --------------------------------------------------------------------------- #
def test_unsupported_dataset_fails_clearly(tmp_path):
    errors = _dataset_precondition_errors(_cfg("made_up_dataset"), tmp_path)
    assert len(errors) == 1
    assert "unsupported dataset for hierarchical training preconditions" in errors[0]
    assert "made_up_dataset" in errors[0]
