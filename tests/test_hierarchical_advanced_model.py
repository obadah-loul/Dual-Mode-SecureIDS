"""Smoke-only tests for SecureIDS-HierarchicalAdvancedNet.

These tests use tiny synthetic tensors only. They do not load real processed
arrays, train a model, evaluate real performance, save checkpoints, or write
metrics.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")

from secureids.models.secureids_hierarchical_advanced_net import (  # noqa: E402
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HIERARCHICAL_CHECKPOINTS = [
    PROJECT_ROOT / "models" / "final" / "final_cicids_hierarchical.pt",
    PROJECT_ROOT / "models" / "final" / "final_unsw_hierarchical.pt",
    PROJECT_ROOT / "models" / "federated" / "fedavg_cicids_hierarchical.pt",
    PROJECT_ROOT / "models" / "federated" / "fedavg_unsw_hierarchical.pt",
]


def _tiny_model(input_dim: int, attack_head_dim: int) -> SecureIDSHierarchicalAdvancedNet:
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=input_dim,
        attack_head_dim=attack_head_dim,
        hidden_dims=(32, 16),
        dropout=0.0,
    )


def _assert_forward_shapes(
    outputs: dict[str, torch.Tensor],
    batch_size: int,
    attack_head_dim: int,
) -> None:
    assert outputs["binary_logit"].shape == (batch_size,)
    assert outputs["attack_logits"].shape == (batch_size, attack_head_dim)
    assert outputs["embedding"].ndim == 2
    assert outputs["embedding"].shape[0] == batch_size


def test_cicids_forward_smoke_shape():
    batch_size = 5
    model = _tiny_model(input_dim=77, attack_head_dim=14)
    outputs = model(torch.randn(batch_size, 77))

    _assert_forward_shapes(outputs, batch_size=batch_size, attack_head_dim=14)


def test_unsw_forward_smoke_shape():
    batch_size = 6
    model = _tiny_model(input_dim=190, attack_head_dim=9)
    outputs = model(torch.randn(batch_size, 190))

    _assert_forward_shapes(outputs, batch_size=batch_size, attack_head_dim=9)


def test_cicids_mixed_batch_loss_uses_attack_rows_only():
    model = _tiny_model(input_dim=77, attack_head_dim=14)
    outputs = model(torch.randn(5, 77))
    y_binary = torch.tensor([0, 1, 0, 1, 1], dtype=torch.float32)
    y_attack = torch.tensor([-1, 0, -1, 13, 6], dtype=torch.long)
    mask = torch.tensor([0, 1, 0, 1, 1], dtype=torch.long)

    loss = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)

    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["binary_loss"])
    assert torch.isfinite(loss["attack_loss"])
    assert int(loss["attack_rows"]) == 3
    assert float(loss["attack_loss"].detach()) > 0.0


def test_cicids_all_benign_batch_loss_has_zero_attack_loss():
    model = _tiny_model(input_dim=77, attack_head_dim=14)
    outputs = model(torch.randn(4, 77))
    y_binary = torch.zeros(4, dtype=torch.float32)
    y_attack = torch.full((4,), -1, dtype=torch.long)
    mask = torch.zeros(4, dtype=torch.long)

    loss = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)

    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["binary_loss"])
    assert torch.isfinite(loss["attack_loss"])
    assert int(loss["attack_rows"]) == 0
    assert torch.equal(loss["attack_loss"], loss["binary_loss"].new_zeros(()))


def test_cicids_all_attack_batch_loss_uses_every_row_for_head2():
    model = _tiny_model(input_dim=77, attack_head_dim=14)
    outputs = model(torch.randn(4, 77))
    y_binary = torch.ones(4, dtype=torch.float32)
    y_attack = torch.tensor([0, 3, 6, 13], dtype=torch.long)
    mask = torch.ones(4, dtype=torch.long)

    loss = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)

    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["binary_loss"])
    assert torch.isfinite(loss["attack_loss"])
    assert int(loss["attack_rows"]) == 4
    assert float(loss["attack_loss"].detach()) > 0.0


def test_unsw_mixed_batch_loss_works():
    model = _tiny_model(input_dim=190, attack_head_dim=9)
    outputs = model(torch.randn(6, 190))
    y_binary = torch.tensor([0, 1, 1, 0, 1, 0], dtype=torch.float32)
    y_attack = torch.tensor([-1, 0, 8, -1, 3, -1], dtype=torch.long)
    mask = torch.tensor([0, 1, 1, 0, 1, 0], dtype=torch.long)

    loss = compute_hierarchical_loss(outputs, y_binary, y_attack, mask)

    assert torch.isfinite(loss["total_loss"])
    assert torch.isfinite(loss["binary_loss"])
    assert torch.isfinite(loss["attack_loss"])
    assert int(loss["attack_rows"]) == 3


def test_safety_model_forward_does_not_read_artifacts_or_write_files(monkeypatch):
    original_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        path_text = str(file).replace("\\", "/")
        mode = args[0] if args else kwargs.get("mode", "r")
        if "data/processed" in path_text or any(c in mode for c in "wax+"):
            raise AssertionError(f"Model forward attempted artifact IO: {file}")
        return original_open(file, *args, **kwargs)

    def reject_save(*args, **kwargs):
        raise AssertionError("Model forward attempted to save an artifact")

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(torch, "save", reject_save)
    monkeypatch.setattr(Path, "write_text", reject_save)
    monkeypatch.setattr(Path, "write_bytes", reject_save)
    model = _tiny_model(input_dim=77, attack_head_dim=14)
    _assert_forward_shapes(model(torch.randn(2, 77)), batch_size=2, attack_head_dim=14)
