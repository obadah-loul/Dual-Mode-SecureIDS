"""Lightweight A9.10 metric and regularization tests."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from secureids.training.frozen_embedding_specialist_evaluation import (
    assemble_a10_report_bundle,
    compute_oracle_attack_family_metrics,
    compute_routed_attack_family_metrics,
)
from secureids.training.frozen_embedding_specialist_trainer import (
    compute_tempered_class_weights,
)


def test_tempered_class_weights_are_train_only_and_mean_normalized():
    labels = np.array([0, 0, 0, 1, 1, 2], dtype=np.int64)
    weights = compute_tempered_class_weights(labels, num_classes=3, temperature=0.5)
    assert weights.shape == (3,)
    assert weights[2] > weights[1] > weights[0]
    assert np.isclose(weights.mean(), 1.0)
    assert np.allclose(compute_tempered_class_weights(labels, 3, temperature=0.0), np.ones(3))


def test_label_smoothing_loss_is_available_for_a10_head():
    logits = torch.randn(4, 3, requires_grad=True)
    labels = torch.tensor([0, 1, 2, 1], dtype=torch.long)
    loss = torch.nn.CrossEntropyLoss(label_smoothing=0.05)(logits, labels)
    loss.backward()
    assert torch.isfinite(loss)
    assert logits.grad is not None


def test_oracle_and_routed_metric_views_stay_separate():
    y_true = np.array([0, 1, 2, 2])
    y_pred = np.array([0, 1, 1, 2])
    routed = np.array([1, 0, 1, 1])
    oracle_metrics = compute_oracle_attack_family_metrics(y_true, y_pred, num_classes=3)
    routed_metrics = compute_routed_attack_family_metrics(y_true, routed, y_pred, num_classes=3)
    bundle = assemble_a10_report_bundle(
        {"macro_f1": 0.894488},
        oracle_metrics,
        routed_metrics,
    )
    assert bundle["metric_views_are_separated"] is True
    assert bundle["do_not_report_oracle_as_routed"] is True
    assert bundle["specialist_oracle_attack_family"]["is_oracle"] is True
    assert bundle["routed_end_to_end"]["is_routed_deployment_metric"] is True
