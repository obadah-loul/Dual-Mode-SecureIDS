"""Safety tests: output-path validation, attack-row selection, model build."""

from __future__ import annotations

import numpy as np
import pytest

from secureids.training.attack_family_specialist_config import (
    is_final_path,
    is_safe_experiment_output_path,
)
from secureids.training.attack_family_specialist_trainer import select_attack_rows


def test_experiment_paths_accepted():
    assert is_safe_experiment_output_path("models/experiments/unsw_a99_x_seed42.pt")
    assert is_safe_experiment_output_path("results/experiments/unsw_a99_x_seed42/metrics.json")
    assert is_safe_experiment_output_path("docs/experiments/UNSW_A99_REPORT.md")


def test_final_and_unsafe_paths_rejected():
    assert not is_safe_experiment_output_path("models/final/final_unsw_hierarchical.pt")
    assert not is_safe_experiment_output_path("results/final/hierarchical/unsw/test_metrics.json")
    assert not is_safe_experiment_output_path("../escape.pt")
    assert not is_safe_experiment_output_path("C:/abs/escape.pt")
    assert not is_safe_experiment_output_path("/abs/escape.pt")


def test_is_final_path_flags_protected_trees():
    assert is_final_path("models/final/final_unsw_hierarchical.pt")
    assert is_final_path("results/final/hierarchical/unsw/test_metrics.json")
    assert not is_final_path("models/experiments/unsw_a99_x.pt")


def test_select_attack_rows_only_attack_rows():
    y = np.array([-1, 0, 3, -1, 8])
    mask = np.array([0, 1, 1, 0, 1])
    selected = select_attack_rows(y, mask)
    assert selected.tolist() == [False, True, True, False, True]
    # benign rows (mask 0 or label -1) are never selected
    assert not selected[0] and not selected[3]


def test_select_attack_rows_excludes_ignore_label_even_if_masked():
    y = np.array([-1, 1])
    mask = np.array([1, 1])  # first row masked-attack but ignore label -> excluded
    selected = select_attack_rows(y, mask)
    assert selected.tolist() == [False, True]


def test_specialist_model_builds_and_forwards():
    torch = pytest.importorskip("torch")
    from secureids.models.attack_family_specialist import AttackFamilySpecialistNet

    model = AttackFamilySpecialistNet(input_dim=192, num_attack_families=9)
    out = model(torch.zeros((4, 192), dtype=torch.float32))
    assert tuple(out.shape) == (4, 9)
    assert model.architecture_metadata["has_binary_head"] is False
