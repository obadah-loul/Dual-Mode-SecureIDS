"""Tests for the configurable Head 2 (attack-family) branch (Task A9.7-prep).

These tests use tiny synthetic tensors and the real A9 / A9.7 configs. They do
NOT train, evaluate real data, save checkpoints, or write metrics. They verify:

* the default attack head stays the A9 linear layer (backward compatible),
* the A9.7 "mlp" branch builds the expected non-linear stack,
* forward output keys/shapes and the masked loss are unchanged,
* invalid attack-head options fail clearly,
* the A9.7 config selects the mlp head and writes to separate output paths that
  never collide with A9 or A9.6.
"""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
from torch import nn  # noqa: E402

from secureids.models.secureids_hierarchical_advanced_net import (  # noqa: E402
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)
from secureids.training.hierarchical_config import (  # noqa: E402
    load_hierarchical_training_config,
)
from secureids.training.hierarchical_trainer import build_model  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
A9_CONFIG = REPO_ROOT / "configs" / "training" / "unsw_nb15_hierarchical.yaml"
A9_7_CONFIG = (
    REPO_ROOT
    / "configs"
    / "training"
    / "unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml"
)
INPUT_DIM = 192
ATTACK_HEAD_DIM = 9


def _model(attack_head_type: str = "linear", **kwargs) -> SecureIDSHierarchicalAdvancedNet:
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=INPUT_DIM,
        attack_head_dim=ATTACK_HEAD_DIM,
        hidden_dims=(256, 128, 128),
        dropout=0.20,
        normalization="layernorm",
        attack_head_type=attack_head_type,
        **kwargs,
    )


def test_default_attack_head_is_linear_a9_behavior():
    model = SecureIDSHierarchicalAdvancedNet(input_dim=INPUT_DIM, attack_head_dim=ATTACK_HEAD_DIM)
    assert model.attack_head_type == "linear"
    assert isinstance(model.attack_head, nn.Linear)
    assert model.attack_head.in_features == model.embedding_dim
    assert model.attack_head.out_features == ATTACK_HEAD_DIM


def test_mlp_attack_head_builds_expected_branch():
    model = _model("mlp", attack_head_hidden_dim=128, attack_head_norm=True, attack_head_dropout=0.20)
    head = model.attack_head
    assert isinstance(head, nn.Sequential)
    kinds = [type(layer) for layer in head]
    assert kinds == [nn.Linear, nn.LayerNorm, nn.GELU, nn.Dropout, nn.Linear]
    assert head[0].in_features == model.embedding_dim
    assert head[0].out_features == 128
    assert head[-1].out_features == ATTACK_HEAD_DIM


def test_mlp_attack_head_without_norm_drops_layernorm():
    model = _model("mlp", attack_head_norm=False)
    kinds = [type(layer) for layer in model.attack_head]
    assert kinds == [nn.Linear, nn.GELU, nn.Dropout, nn.Linear]


def test_forward_keys_and_shapes_unchanged_for_mlp_head():
    batch = 7
    model = _model("mlp")
    outputs = model(torch.randn(batch, INPUT_DIM))
    assert set(outputs) == {"binary_logit", "attack_logits", "embedding"}
    assert outputs["binary_logit"].shape == (batch,)
    assert outputs["attack_logits"].shape == (batch, ATTACK_HEAD_DIM)
    assert outputs["embedding"].shape == (batch, model.embedding_dim)


def test_masked_loss_and_class_weights_work_with_mlp_head():
    model = _model("mlp")
    outputs = model(torch.randn(6, INPUT_DIM))
    y_binary = torch.tensor([0, 1, 1, 0, 1, 0], dtype=torch.float32)
    y_attack = torch.tensor([-1, 0, 8, -1, 3, -1], dtype=torch.long)
    mask = torch.tensor([0, 1, 1, 0, 1, 0], dtype=torch.long)
    weights = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8]

    loss = compute_hierarchical_loss(
        outputs,
        y_binary,
        y_attack,
        mask,
        pos_weight=0.5,
        attack_class_weights=weights,
    )
    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["attack_loss"])
    assert int(loss["attack_rows"]) == 3
    assert loss["attack_class_weights_applied"] is True


def test_mlp_head_adds_capacity_over_linear_head():
    linear = _model("linear")
    mlp = _model("mlp", attack_head_hidden_dim=128)
    linear_params = sum(p.numel() for p in linear.attack_head.parameters())
    mlp_params = sum(p.numel() for p in mlp.attack_head.parameters())
    assert linear_params == model_linear_head_params()
    assert mlp_params > linear_params
    # 128*128+128 (linear1) + 2*128 (LayerNorm) + 128*9+9 (linear2)
    assert mlp_params == 16512 + 256 + 1161


def model_linear_head_params() -> int:
    # Linear(128, 9): 128*9 + 9
    return 128 * ATTACK_HEAD_DIM + ATTACK_HEAD_DIM


def test_invalid_attack_head_type_raises_clearly():
    with pytest.raises(ValueError, match="attack_head_type"):
        _model("conv")


def test_invalid_attack_head_dropout_raises_clearly():
    with pytest.raises(ValueError, match="attack_head_dropout"):
        _model("mlp", attack_head_dropout=1.5)


def test_architecture_metadata_reports_attack_head():
    mlp = _model("mlp", attack_head_hidden_dim=128, attack_head_norm=True, attack_head_dropout=0.20)
    meta = mlp.architecture_metadata["attack_head"]
    assert meta == {"type": "mlp", "hidden_dim": 128, "norm": True, "dropout": 0.20}

    linear = _model("linear")
    lmeta = linear.architecture_metadata["attack_head"]
    assert lmeta["type"] == "linear"
    assert lmeta["hidden_dim"] is None


def test_a9_config_build_model_is_linear_backward_compatible():
    config = load_hierarchical_training_config(A9_CONFIG, project_root=REPO_ROOT)
    model = build_model(config)
    assert model.attack_head_type == "linear"
    assert isinstance(model.attack_head, nn.Linear)


def test_a9_7_config_selects_mlp_head_via_build_model():
    config = load_hierarchical_training_config(A9_7_CONFIG, project_root=REPO_ROOT)
    assert config.dataset == "unsw_nb15"
    assert config.input_dim == 192
    assert config.attack_head_dim == 9
    assert config.raw["model"]["attack_head_type"] == "mlp"
    assert config.raw["model"]["attack_head_hidden_dim"] == 128
    assert config.raw["model"]["attack_head_norm"] is True
    assert config.raw["model"]["attack_head_dropout"] == 0.20
    # A9.7 changes exactly one factor vs A9: loss/class weights stay at A9 values.
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.0
    assert config.raw["class_imbalance"]["class_weight_max_clip"] == 10.0

    model = build_model(config)
    assert isinstance(model.attack_head, nn.Sequential)
    outputs = model(torch.randn(4, 192))
    assert outputs["attack_logits"].shape == (4, 9)


def test_a9_7_config_uses_separate_output_paths():
    a9_7 = load_hierarchical_training_config(A9_7_CONFIG, project_root=REPO_ROOT).outputs
    a9 = load_hierarchical_training_config(A9_CONFIG, project_root=REPO_ROOT).outputs

    # Every A9.7 output path is namespaced (case-insensitive: the report file uses
    # an uppercase A9_7_HEAD2_BRANCH_CAPACITY suffix) and never equals the A9 path.
    for key in ("checkpoint", "result_dir", "manifest_json", "report_md"):
        assert "a9_7_head2_branch_capacity" in a9_7[key].lower()
        assert a9_7[key] != a9[key]

    # And never collides with A9 or A9.6 final artifacts.
    forbidden = {
        "models/final/final_unsw_hierarchical.pt",
        "results/final/hierarchical/unsw",
        "results/audits/hierarchical_training_manifest_unsw_nb15.json",
        "docs/HIERARCHICAL_TRAINING_REPORT.md",
        "models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt",
        "results/final/hierarchical/unsw_a9_6_head2_loss_weight",
        "results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json",
    }
    normalized = {str(value).replace("\\", "/").rstrip("/") for value in a9_7.values()}
    assert normalized.isdisjoint(forbidden)
