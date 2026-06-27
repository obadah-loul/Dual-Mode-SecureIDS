"""Focused tests for hierarchical class-weight wiring (A8.8 HIGH finding F2).

These tests prove that ``compute_hierarchical_loss`` can apply the A8.5-locked
Head 1 (binary ``pos_weight``) and Head 2 (``attack_class_weights``) class
weights, that wrong shapes fail clearly, that all-benign/all-attack/mixed and
empty-mask batches stay finite, and that the train-only weight builder never
reads validation/test labels. They use tiny synthetic tensors and never train a
full model, save checkpoints, or write final metrics.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


torch = pytest.importorskip("torch")

from secureids.models.secureids_hierarchical_advanced_net import (  # noqa: E402
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ATTACK_HEAD_DIM = 5
INPUT_DIM = 8
DEVICES = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])


def _model(seed: int = 0) -> SecureIDSHierarchicalAdvancedNet:
    torch.manual_seed(seed)
    model = SecureIDSHierarchicalAdvancedNet(
        input_dim=INPUT_DIM,
        attack_head_dim=ATTACK_HEAD_DIM,
        hidden_dims=(16, 8),
        dropout=0.0,
    )
    model.eval()
    return model


def _outputs(model: SecureIDSHierarchicalAdvancedNet, n: int, seed: int = 1) -> dict[str, torch.Tensor]:
    torch.manual_seed(seed)
    return model(torch.randn(n, INPUT_DIM))


def _mixed_batch() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    y_binary = torch.tensor([0, 1, 1, 0, 1, 1], dtype=torch.float32)
    y_attack = torch.tensor([-1, 0, 4, -1, 1, 4], dtype=torch.long)
    mask = torch.tensor([0, 1, 1, 0, 1, 1], dtype=torch.long)
    return y_binary, y_attack, mask


# --- Head 2 (attack-family) class weights -----------------------------------

def test_attack_class_weights_change_attack_loss():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()

    unweighted = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)
    # Up-weight rare class id 4 (present twice in this batch) heavily.
    weights = torch.tensor([1.0, 1.0, 1.0, 1.0, 6.0], dtype=torch.float32)
    weighted = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, attack_class_weights=weights
    )

    assert weighted["attack_class_weights_applied"] is True
    assert unweighted["attack_class_weights_applied"] is False
    assert torch.isfinite(weighted["attack_loss"])
    assert not torch.isclose(
        weighted["attack_loss"], unweighted["attack_loss"], atol=1e-6
    ), "non-uniform attack class weights must change the attack loss"


def test_uniform_attack_weights_match_unweighted():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()

    unweighted = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)
    weights = torch.ones(ATTACK_HEAD_DIM, dtype=torch.float32)
    weighted = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, attack_class_weights=weights
    )
    assert torch.isclose(weighted["attack_loss"], unweighted["attack_loss"], atol=1e-6)


def test_attack_class_weights_accept_list_and_align_to_class_ids():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()

    # A plain Python list aligned to class ids 0..4 must be accepted.
    weighted = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, attack_class_weights=[1.0, 2.0, 3.0, 4.0, 5.0]
    )
    assert torch.isfinite(weighted["attack_loss"])
    assert weighted["attack_class_weights_applied"] is True


# --- Head 1 (binary) class weight -------------------------------------------

def test_binary_pos_weight_changes_binary_loss():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()

    unweighted = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)
    weighted = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, pos_weight=5.0
    )

    assert weighted["binary_pos_weight_applied"] is True
    assert unweighted["binary_pos_weight_applied"] is False
    assert torch.isfinite(weighted["binary_loss"])
    assert not torch.isclose(
        weighted["binary_loss"], unweighted["binary_loss"], atol=1e-6
    ), "a non-unit binary pos_weight must change the binary loss"


# --- Device handling ---------------------------------------------------------

@pytest.mark.parametrize("device", DEVICES)
def test_weights_moved_to_logits_device(device):
    model = _model().to(device)
    torch.manual_seed(2)
    features = torch.randn(6, INPUT_DIM, device=device)
    outputs = model(features)
    y_binary, y_attack, mask = _mixed_batch()
    # Pass CPU weights deliberately; the loss must move them to the logits device.
    weights = torch.tensor([1.0, 1.0, 1.0, 1.0, 6.0], dtype=torch.float32)

    loss = compute_hierarchical_loss(
        outputs,
        y_binary,
        y_attack,
        mask,
        pos_weight=2.0,
        attack_class_weights=weights,
    )
    assert loss["attack_loss"].device.type == torch.device(device).type
    assert loss["binary_loss"].device.type == torch.device(device).type
    assert torch.isfinite(loss["total_loss"])


# --- Batch-composition safety with weights ----------------------------------

def test_all_benign_batch_safe_with_weights():
    model = _model()
    outputs = _outputs(model, 4)
    y_binary = torch.zeros(4, dtype=torch.float32)
    y_attack = torch.full((4,), -1, dtype=torch.long)
    mask = torch.zeros(4, dtype=torch.long)
    weights = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0], dtype=torch.float32)

    loss = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, pos_weight=3.0, attack_class_weights=weights
    )
    assert int(loss["attack_rows"]) == 0
    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["binary_loss"])
    # Empty attack mask => zero attack loss, never NaN, even with weights supplied.
    assert torch.equal(loss["attack_loss"], loss["binary_loss"].new_zeros(()))
    assert not torch.isnan(loss["attack_loss"]).any()


def test_all_attack_batch_safe_with_weights():
    model = _model()
    outputs = _outputs(model, 5)
    y_binary = torch.ones(5, dtype=torch.float32)
    y_attack = torch.tensor([0, 1, 2, 3, 4], dtype=torch.long)
    mask = torch.ones(5, dtype=torch.long)
    weights = torch.tensor([1.0, 1.0, 1.0, 1.0, 6.0], dtype=torch.float32)

    loss = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, pos_weight=2.0, attack_class_weights=weights
    )
    assert int(loss["attack_rows"]) == 5
    assert torch.isfinite(loss["total_loss"])
    assert float(loss["attack_loss"].detach()) > 0.0


def test_mixed_batch_safe_with_weights():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()
    weights = torch.tensor([1.0, 1.5, 2.0, 2.5, 6.0], dtype=torch.float32)

    loss = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask, pos_weight=2.0, attack_class_weights=weights
    )
    assert int(loss["attack_rows"]) == 4
    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["attack_loss"])


# --- Shape validation --------------------------------------------------------

def test_attack_class_weights_too_short_raises():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()
    with pytest.raises(ValueError, match="attack_class_weights length must equal"):
        compute_hierarchical_loss(
            outputs, y_binary, y_attack, mask,
            attack_class_weights=torch.ones(ATTACK_HEAD_DIM - 1),
        )


def test_attack_class_weights_too_long_raises():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()
    with pytest.raises(ValueError, match="attack_class_weights length must equal"):
        compute_hierarchical_loss(
            outputs, y_binary, y_attack, mask,
            attack_class_weights=torch.ones(ATTACK_HEAD_DIM + 3),
        )


def test_wrong_weight_shape_fails_even_on_all_benign_batch():
    """Shape is validated up front, so it fails clearly with no attack rows."""
    model = _model()
    outputs = _outputs(model, 4)
    y_binary = torch.zeros(4, dtype=torch.float32)
    y_attack = torch.full((4,), -1, dtype=torch.long)
    mask = torch.zeros(4, dtype=torch.long)
    with pytest.raises(ValueError, match="attack_class_weights length must equal"):
        compute_hierarchical_loss(
            outputs, y_binary, y_attack, mask,
            attack_class_weights=torch.ones(ATTACK_HEAD_DIM + 1),
        )


def test_exact_length_weights_pass():
    model = _model()
    outputs = _outputs(model, 6)
    y_binary, y_attack, mask = _mixed_batch()
    loss = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask,
        attack_class_weights=torch.ones(ATTACK_HEAD_DIM),
    )
    assert torch.isfinite(loss["total_loss"])


# --- Train-only weight builder ----------------------------------------------

def _unsw_train_labels_exist() -> bool:
    base = PROJECT_ROOT / "data" / "processed" / "unsw_nb15" / "hierarchical"
    needed = [
        "y_binary_train.npy",
        "y_attack_family_train.npy",
        "attack_family_mask_train.npy",
    ]
    return base.is_dir() and all((base / name).exists() for name in needed)


@pytest.mark.skipif(
    not _unsw_train_labels_exist(),
    reason="UNSW hierarchical train labels are not present",
)
def test_build_train_only_class_weights_does_not_read_val_or_test(monkeypatch):
    from secureids.training import hierarchical_class_weights as hcw

    real_load = np.load

    def guarded_load(path, *args, **kwargs):
        text = str(path).replace("\\", "/")
        if "_val.npy" in text or "_test.npy" in text:
            raise AssertionError(f"weight builder read a non-train label file: {path}")
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(hcw.np, "load", guarded_load)
    result = hcw.build_train_only_class_weights("unsw_nb15", project_root=PROJECT_ROOT)

    assert result["computed_from_train_only"] is True
    assert result["validation_labels_used"] is False
    assert result["test_labels_used"] is False
    assert result["train_only_read_diagnostics"]["validation_files_read"] == []
    assert result["train_only_read_diagnostics"]["test_files_read"] == []


@pytest.mark.skipif(
    not _unsw_train_labels_exist(),
    reason="UNSW hierarchical train labels are not present",
)
def test_build_train_only_class_weights_align_and_within_cap():
    from secureids.training.hierarchical_class_weights import (
        build_train_only_class_weights,
    )

    result = build_train_only_class_weights("unsw_nb15", project_root=PROJECT_ROOT)
    weights = result["attack_class_weights"]

    assert len(weights) == int(result["attack_head_dim"])
    assert all(np.isfinite(weights))
    assert all(w > 0.0 for w in weights)
    assert max(weights) <= float(result["weight_cap"]) + 1e-9
    assert result["binary_pos_weight"] > 0.0

    # The returned vector must be usable directly by the loss for this dataset.
    model = SecureIDSHierarchicalAdvancedNet(
        input_dim=INPUT_DIM, attack_head_dim=int(result["attack_head_dim"]), dropout=0.0
    )
    outputs = model(torch.randn(4, INPUT_DIM))
    y_binary = torch.tensor([0.0, 1.0, 1.0, 0.0])
    y_attack = torch.tensor([-1, 0, 1, -1], dtype=torch.long)
    mask = torch.tensor([0, 1, 1, 0], dtype=torch.long)
    loss = compute_hierarchical_loss(
        outputs, y_binary, y_attack, mask,
        pos_weight=float(result["binary_pos_weight"]),
        attack_class_weights=weights,
    )
    assert torch.isfinite(loss["total_loss"])
