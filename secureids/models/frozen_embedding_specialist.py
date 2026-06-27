"""A9.10 frozen-A9-embedding attack-family specialist.

A9.10 keeps the accepted A9 hierarchical model frozen and trains only a small
attack-family head on the fixed 128-dimensional A9 embedding. The extraction
point is the existing ``SecureIDSHierarchicalAdvancedNet`` forward output key
``"embedding"`` (encoder + gate), so Head 1 binary routing stays A9-based and
unchanged.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch
from torch import nn

from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
)


HEAD_TYPES: tuple[str, ...] = ("linear", "shallow_mlp")
DEFAULT_EMBEDDING_DIM = 128
DEFAULT_NUM_ATTACK_FAMILIES = 9
DEFAULT_DROPOUT = 0.35


def _validate_positive_int(name: str, value: int) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")
    return parsed


class FrozenEmbeddingSpecialistHead(nn.Module):
    """Small trainable attack-family head over frozen A9 embeddings."""

    def __init__(
        self,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        num_attack_families: int = DEFAULT_NUM_ATTACK_FAMILIES,
        head_type: str = "linear",
        hidden_dim: int = 64,
        dropout: float = DEFAULT_DROPOUT,
    ) -> None:
        super().__init__()
        self.embedding_dim = _validate_positive_int("embedding_dim", embedding_dim)
        self.num_attack_families = _validate_positive_int(
            "num_attack_families", num_attack_families
        )
        self.head_type = str(head_type).lower()
        if self.head_type not in HEAD_TYPES:
            raise ValueError(f"head_type must be one of {HEAD_TYPES}, got {head_type!r}.")
        if not 0.0 <= float(dropout) < 1.0:
            raise ValueError(f"dropout must be in [0.0, 1.0), got {dropout!r}.")
        self.dropout = float(dropout)
        self.hidden_dim = _validate_positive_int("hidden_dim", hidden_dim)

        if self.head_type == "linear":
            self.net = nn.Sequential(
                nn.Dropout(self.dropout),
                nn.Linear(self.embedding_dim, self.num_attack_families),
            )
        else:
            self.net = nn.Sequential(
                nn.LayerNorm(self.embedding_dim),
                nn.Dropout(self.dropout),
                nn.Linear(self.embedding_dim, self.hidden_dim),
                nn.GELU(),
                nn.Dropout(self.dropout),
                nn.Linear(self.hidden_dim, self.num_attack_families),
            )

    def forward(self, embedding: torch.Tensor) -> torch.Tensor:
        """Return attack-family logits of shape ``(batch, num_attack_families)``."""

        return self.net(embedding)

    @property
    def architecture_metadata(self) -> dict[str, Any]:
        return {
            "architecture": "FrozenEmbeddingSpecialistHead",
            "role": "a10_attack_family_head_on_frozen_a9_embedding",
            "embedding_dim": self.embedding_dim,
            "num_attack_families": self.num_attack_families,
            "head_type": self.head_type,
            "hidden_dim": self.hidden_dim if self.head_type == "shallow_mlp" else None,
            "dropout": self.dropout,
            "trainable_component": "specialist_head_only",
            "frozen_embedding_source": "A9 SecureIDSHierarchicalAdvancedNet forward()['embedding']",
            "has_binary_head": False,
        }


def freeze_a9_model(a9_model: nn.Module) -> nn.Module:
    """Freeze all A9 parameters and switch to eval mode."""

    for parameter in a9_model.parameters():
        parameter.requires_grad_(False)
    a9_model.eval()
    return a9_model


class FrozenA9EmbeddingExtractor(nn.Module):
    """Read-only extractor for A9 embeddings and Head 1 routing decisions."""

    def __init__(self, a9_model: nn.Module, binary_threshold: float = 0.5) -> None:
        super().__init__()
        self.a9_model = freeze_a9_model(a9_model)
        self.binary_threshold = float(binary_threshold)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            output = self.a9_model(x)
            if not isinstance(output, dict) or "embedding" not in output:
                raise KeyError("frozen A9 model must return an 'embedding' output.")
            return output["embedding"].detach()

    def route_attack(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            output = self.a9_model(x)
            if not isinstance(output, dict) or "binary_logit" not in output:
                raise KeyError("frozen A9 model must return a 'binary_logit' output.")
            probs = torch.sigmoid(output["binary_logit"].reshape(-1))
            return (probs >= self.binary_threshold).to(dtype=torch.long)


def _torch_load_checkpoint(path: Path, map_location: str = "cpu") -> dict[str, Any]:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:  # pragma: no cover - older torch
        return torch.load(path, map_location=map_location)


def build_a9_model_from_checkpoint_payload(payload: dict[str, Any]) -> SecureIDSHierarchicalAdvancedNet:
    """Reconstruct the A9 architecture from checkpoint metadata and freeze it."""

    metadata = dict(payload.get("architecture_metadata") or {})
    attack_meta = dict(metadata.get("attack_head") or {})
    model = SecureIDSHierarchicalAdvancedNet(
        input_dim=int(payload.get("input_dim", metadata.get("input_dim", 192))),
        attack_head_dim=int(payload.get("attack_head_dim", metadata.get("attack_head_dim", 9))),
        hidden_dims=metadata.get("hidden_dims") or (256, 128, 128),
        dropout=float(metadata.get("dropout", 0.2)),
        normalization=str(metadata.get("normalization", "layernorm")),
        residual_expansion=int(metadata.get("residual_expansion", 2)),
        attack_head_type=str(attack_meta.get("type", "linear")),
        attack_head_hidden_dim=attack_meta.get("hidden_dim"),
        attack_head_norm=bool(attack_meta.get("norm", False)),
        attack_head_dropout=attack_meta.get("dropout"),
    )
    model.load_state_dict(payload["model_state_dict"])
    freeze_a9_model(model)
    return model


def load_frozen_a9_model(
    checkpoint_path: Path | str,
    map_location: str = "cpu",
) -> SecureIDSHierarchicalAdvancedNet:
    """Load the accepted A9 checkpoint and return a frozen model."""

    payload = _torch_load_checkpoint(Path(checkpoint_path), map_location=map_location)
    return build_a9_model_from_checkpoint_payload(payload)


def extract_fixed_embeddings(
    extractor: FrozenA9EmbeddingExtractor,
    features: Any,
    batch_size: int = 8192,
    return_router: bool = False,
) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
    """Extract fixed A9 embeddings without enabling gradients."""

    x = torch.as_tensor(features, dtype=torch.float32)
    embeddings: list[torch.Tensor] = []
    routes: list[torch.Tensor] = []
    extractor.eval()
    for start in range(0, x.shape[0], int(batch_size)):
        batch = x[start : start + int(batch_size)]
        embeddings.append(extractor(batch).cpu())
        if return_router:
            routes.append(extractor.route_attack(batch).cpu())
    joined = torch.cat(embeddings, dim=0) if embeddings else torch.empty((0, DEFAULT_EMBEDDING_DIM))
    if not return_router:
        return joined
    route_joined = torch.cat(routes, dim=0) if routes else torch.empty((0,), dtype=torch.long)
    return joined, route_joined
