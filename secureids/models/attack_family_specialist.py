"""UNSW A9.9 attack-family specialist model.

An isolated, attack-only multiclass classifier used *behind* the frozen A9
Head 1 binary router. It is intentionally separate from
``SecureIDSHierarchicalAdvancedNet`` so it cannot change existing hierarchical
or CICIDS behaviour. It has no binary head: it only predicts the attack family
of rows that the (frozen) A9 router has already decided are attacks.

This module defines the architecture only. It does not load data, train,
evaluate, or save checkpoints.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import torch
from torch import nn


DEFAULT_HIDDEN_DIMS: tuple[int, ...] = (256, 128)
DEFAULT_DROPOUT: float = 0.20
DEFAULT_NORMALIZATION: str = "layernorm"


def _validate_positive_int(name: str, value: int) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {value!r}.")
    return parsed


def _make_normalization(kind: str, dim: int) -> nn.Module:
    normalized = str(kind).lower()
    if normalized == "layernorm":
        return nn.LayerNorm(dim)
    if normalized == "batchnorm":
        return nn.BatchNorm1d(dim)
    if normalized in {"none", "identity"}:
        return nn.Identity()
    raise ValueError(
        "normalization must be one of {'layernorm', 'batchnorm', 'none'}, "
        f"got {kind!r}."
    )


class AttackFamilySpecialistNet(nn.Module):
    """Dedicated attack-only family classifier.

    Parameters
    ----------
    input_dim:
        Feature dimension (192 for UNSW-NB15 corrected protocol).
    num_attack_families:
        Number of attack-family classes (9 for UNSW-NB15).
    hidden_dims:
        Encoder widths. A dedicated encoder (not shared with the A9 binary
        detector) so all capacity is spent on attack-family separation.
    dropout:
        Dropout probability in ``[0.0, 1.0)``.
    normalization:
        ``"layernorm"`` (default), ``"batchnorm"``, or ``"none"``.
    """

    def __init__(
        self,
        input_dim: int,
        num_attack_families: int,
        hidden_dims: Sequence[int] | None = None,
        dropout: float = DEFAULT_DROPOUT,
        normalization: str = DEFAULT_NORMALIZATION,
    ) -> None:
        super().__init__()

        self.input_dim = _validate_positive_int("input_dim", input_dim)
        self.num_attack_families = _validate_positive_int(
            "num_attack_families", num_attack_families
        )
        if not 0.0 <= float(dropout) < 1.0:
            raise ValueError(f"dropout must be in [0.0, 1.0), got {dropout!r}.")

        hidden = tuple(DEFAULT_HIDDEN_DIMS if hidden_dims is None else hidden_dims)
        if len(hidden) == 0:
            raise ValueError("hidden_dims must contain at least one layer.")
        if any(int(width) <= 0 for width in hidden):
            raise ValueError(f"hidden_dims must all be > 0, got {hidden!r}.")

        self.hidden_dims = tuple(int(width) for width in hidden)
        self.dropout = float(dropout)
        self.normalization = str(normalization).lower()

        layers: list[nn.Module] = []
        current_dim = self.input_dim
        for width in self.hidden_dims:
            layers.append(nn.Linear(current_dim, width))
            layers.append(_make_normalization(self.normalization, width))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(self.dropout))
            current_dim = width
        self.encoder = nn.Sequential(*layers)
        self.embedding_dim = current_dim
        self.attack_family_head = nn.Linear(self.embedding_dim, self.num_attack_families)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return attack-family logits of shape ``(batch, num_attack_families)``."""

        return self.attack_family_head(self.encoder(x))

    @property
    def architecture_metadata(self) -> dict[str, Any]:
        """Serializable description for future manifests/snapshots."""

        return {
            "architecture": "AttackFamilySpecialistNet",
            "role": "attack_only_family_classifier_behind_frozen_a9_router",
            "input_dim": self.input_dim,
            "num_attack_families": self.num_attack_families,
            "hidden_dims": list(self.hidden_dims),
            "embedding_dim": self.embedding_dim,
            "dropout": self.dropout,
            "normalization": self.normalization,
            "has_binary_head": False,
        }
