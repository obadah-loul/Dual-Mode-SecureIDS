"""A9.8 multiseed config path-safety tests.

These tests are torch-free. They load YAML configs only; they do not train,
evaluate, create checkpoints, or write final metrics.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfigError,
    load_hierarchical_training_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs" / "training" / "multiseed"
SEEDS = (42, 123, 999)
VARIANTS = ("a9_linear", "a9_7_branch")


def _config_name(variant: str, seed: int) -> str:
    if variant == "a9_linear":
        return f"unsw_a9_linear_seed{seed}.yaml"
    if variant == "a9_7_branch":
        return f"unsw_a9_7_branch_seed{seed}.yaml"
    raise AssertionError(f"unknown variant {variant}")


def _slug(variant: str, seed: int) -> str:
    if variant == "a9_linear":
        return f"unsw_a9_linear_seed{seed}"
    if variant == "a9_7_branch":
        return f"unsw_a9_7_branch_seed{seed}"
    raise AssertionError(f"unknown variant {variant}")


def _report_path(variant: str, seed: int) -> str:
    if variant == "a9_linear":
        return f"docs/multiseed/HIERARCHICAL_TRAINING_REPORT_UNSW_A9_LINEAR_SEED{seed}.md"
    if variant == "a9_7_branch":
        return f"docs/multiseed/HIERARCHICAL_TRAINING_REPORT_UNSW_A9_7_BRANCH_SEED{seed}.md"
    raise AssertionError(f"unknown variant {variant}")


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("seed", SEEDS)
def test_a9_8_multiseed_configs_load_and_use_seed_scoped_outputs(variant: str, seed: int):
    config = load_hierarchical_training_config(
        CONFIG_DIR / _config_name(variant, seed),
        project_root=REPO_ROOT,
    )

    slug = _slug(variant, seed)
    result_dir = f"results/final/hierarchical/multiseed/{slug}"
    manifest_stem = f"hierarchical_training_manifest_{slug}"

    assert config.dataset == "unsw_nb15"
    assert config.input_dim == 192
    assert config.attack_head_dim == 9
    assert config.raw["training"]["seed"] == seed
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.0
    assert config.outputs["checkpoint"] == f"models/final/multiseed/{slug}.pt"
    assert config.outputs["result_dir"] == result_dir
    assert config.outputs["manifest_json"] == f"results/audits/multiseed/{manifest_stem}.json"
    assert config.outputs["report_md"] == _report_path(variant, seed)

    for filename_key, filename in {
        "training_history_csv": "training_history.csv",
        "test_metrics_json": "test_metrics.json",
        "binary_confusion_matrix_csv": "binary_confusion_matrix.csv",
        "attack_family_confusion_matrix_csv": "attack_family_confusion_matrix.csv",
        "per_class_attack_metrics_csv": "per_class_attack_metrics.csv",
        "rare_class_metrics_csv": "rare_class_metrics.csv",
        "hierarchical_routing_summary_json": "hierarchical_routing_summary.json",
        "training_config_snapshot_yaml": "training_config_snapshot.yaml",
        "class_weight_snapshot_json": "class_weight_snapshot.json",
        "model_summary_json": "model_summary.json",
    }.items():
        assert config.outputs[filename_key] == f"{result_dir}/{filename}"


@pytest.mark.parametrize("seed", SEEDS)
def test_a9_8_branch_configs_keep_mlp_head(seed: int):
    config = load_hierarchical_training_config(
        CONFIG_DIR / f"unsw_a9_7_branch_seed{seed}.yaml",
        project_root=REPO_ROOT,
    )

    assert config.raw["model"]["attack_head_type"] == "mlp"
    assert config.raw["model"]["attack_head_hidden_dim"] == 128
    assert config.raw["model"]["attack_head_norm"] is True
    assert config.raw["model"]["attack_head_dropout"] == 0.20


def _write_modified_config(tmp_path: Path, **updates):
    source = CONFIG_DIR / "unsw_a9_linear_seed42.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for path, value in updates.items():
        current = data
        parts = path.split(".")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    target = tmp_path / "modified.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "checkpoint",
    [
        "models/final/multiseed/unsw_bad_seed42.pt",
        "models/final/multiseed/unsw_a9_linear_seed777.pt",
        "models/final/final_unsw_hierarchical.pt",
        "models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt",
        "models/final/final_unsw_hierarchical_a9_7_head2_branch_capacity.pt",
        "models/final/multiseed/../final_unsw_hierarchical.pt",
        r"C:\temp\unsafe.pt",
        "models/federated/unsafe.pt",
        "models/final/multiseed/fedavg_unsw_seed42.pt",
    ],
)
def test_a9_8_multiseed_rejects_unsafe_checkpoint_paths(tmp_path: Path, checkpoint: str):
    config_path = _write_modified_config(tmp_path, **{"outputs.checkpoint": checkpoint})

    with pytest.raises(HierarchicalTrainingConfigError):
        load_hierarchical_training_config(config_path, project_root=REPO_ROOT)


@pytest.mark.parametrize(
    "field,value",
    [
        ("outputs.result_dir", "results/final/hierarchical/unsw"),
        ("outputs.result_dir", "results/final/hierarchical/multiseed/unsw_bad_seed42"),
        ("outputs.result_dir", "results/final/hierarchical/multiseed/../unsw"),
        ("outputs.manifest_json", "results/audits/hierarchical_training_manifest_unsw_nb15.json"),
        (
            "outputs.manifest_json",
            "results/audits/multiseed/hierarchical_training_manifest_unsw_bad_seed42.json",
        ),
        ("outputs.report_md", "docs/HIERARCHICAL_TRAINING_REPORT.md"),
        (
            "outputs.test_metrics_json",
            "results/final/hierarchical/multiseed/unsw_a9_linear_seed42/../test_metrics.json",
        ),
    ],
)
def test_a9_8_multiseed_rejects_unsafe_result_manifest_and_report_paths(
    tmp_path: Path,
    field: str,
    value: str,
):
    config_path = _write_modified_config(tmp_path, **{field: value})

    with pytest.raises(HierarchicalTrainingConfigError):
        load_hierarchical_training_config(config_path, project_root=REPO_ROOT)


def test_a9_8_multiseed_rejects_unknown_experiment_name(tmp_path: Path):
    config_path = _write_modified_config(tmp_path, experiment="a9_8_multiseed_unknown_seed42")

    with pytest.raises(HierarchicalTrainingConfigError, match="experiment"):
        load_hierarchical_training_config(config_path, project_root=REPO_ROOT)
