"""Model-level tests for A9.10 frozen embedding behavior."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from secureids.models.frozen_embedding_specialist import (
    FrozenA9EmbeddingExtractor,
    FrozenEmbeddingSpecialistHead,
)
from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
)


def test_linear_and_mlp_heads_return_family_logits():
    x = torch.randn(4, 128)
    linear = FrozenEmbeddingSpecialistHead(head_type="linear", dropout=0.1)
    mlp = FrozenEmbeddingSpecialistHead(head_type="shallow_mlp", hidden_dim=32, dropout=0.2)
    assert linear(x).shape == (4, 9)
    assert mlp(x).shape == (4, 9)
    assert linear.architecture_metadata["has_binary_head"] is False


def test_frozen_a9_extractor_shape_and_no_a9_gradients():
    a9 = SecureIDSHierarchicalAdvancedNet(
        input_dim=6,
        attack_head_dim=9,
        hidden_dims=(8, 128),
        dropout=0.1,
    )
    extractor = FrozenA9EmbeddingExtractor(a9)
    head = FrozenEmbeddingSpecialistHead(head_type="linear", dropout=0.1)
    x = torch.randn(5, 6)
    y = torch.tensor([0, 1, 2, 3, 4], dtype=torch.long)

    embedding = extractor(x)
    assert embedding.shape == (5, 128)
    assert embedding.requires_grad is False
    assert all(parameter.requires_grad is False for parameter in a9.parameters())

    loss = torch.nn.CrossEntropyLoss()(head(embedding), y)
    loss.backward()
    assert all(parameter.grad is None for parameter in a9.parameters())
    assert any(parameter.grad is not None for parameter in head.parameters())


def test_routing_uses_binary_head_separately_from_oracle_embedding():
    a9 = SecureIDSHierarchicalAdvancedNet(input_dim=6, attack_head_dim=9, hidden_dims=(8, 128))
    extractor = FrozenA9EmbeddingExtractor(a9)
    x = torch.randn(3, 6)
    routed = extractor.route_attack(x)
    assert routed.shape == (3,)
    assert set(routed.tolist()).issubset({0, 1})
