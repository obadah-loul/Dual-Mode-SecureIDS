"""SecureIDS-HierarchicalAdvancedNet architecture skeleton.

Task A5 introduces the model and masked loss interface only. This module does
not load datasets, train, evaluate, save checkpoints, or create metrics.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import torch
from torch import nn
from torch.nn import functional as F


DEFAULT_HIDDEN_DIMS: tuple[int, ...] = (256, 128, 128)
DEFAULT_DROPOUT: float = 0.20
DEFAULT_NORMALIZATION: str = "layernorm"
ATTACK_HEAD_TYPES: tuple[str, ...] = ("linear", "mlp")
DEFAULT_ATTACK_HEAD_TYPE: str = "linear"
DEFAULT_ATTACK_HEAD_HIDDEN_DIM: int = 128


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


def _build_attack_head(
    embedding_dim: int,
    attack_head_dim: int,
    head_type: str,
    hidden_dim: int,
    use_norm: bool,
    dropout: float,
    normalization: str,
) -> nn.Module:
    """Build the Head 2 (attack-family) classifier.

    ``"linear"`` (default) reproduces the A9 baseline exactly:
    ``Linear(embedding_dim, attack_head_dim)``. ``"mlp"`` (A9.7
    ``head2_branch_capacity``) inserts one non-linear branch
    ``Linear -> [norm] -> GELU -> Dropout -> Linear`` for more attack-family
    capacity. Either way the output shape is ``(batch, attack_head_dim)`` so the
    forward contract and the masked loss are unchanged.
    """

    normalized = str(head_type).lower()
    if normalized == "linear":
        return nn.Linear(embedding_dim, attack_head_dim)
    if normalized == "mlp":
        layers: list[nn.Module] = [nn.Linear(embedding_dim, hidden_dim)]
        if use_norm:
            layers.append(_make_normalization(normalization, hidden_dim))
        layers.append(nn.GELU())
        layers.append(nn.Dropout(dropout))
        layers.append(nn.Linear(hidden_dim, attack_head_dim))
        return nn.Sequential(*layers)
    raise ValueError(
        "attack_head_type must be one of {'linear', 'mlp'}, "
        f"got {head_type!r}."
    )


class TransitionBlock(nn.Module):
    """Project between representation widths before residual processing."""

    def __init__(self, in_dim: int, out_dim: int, dropout: float, normalization: str) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(in_dim, out_dim),
            _make_normalization(normalization, out_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class ResidualMLPBlock(nn.Module):
    """Pre-norm residual MLP block for tabular representations."""

    def __init__(
        self,
        dim: int,
        dropout: float,
        normalization: str,
        expansion: int = 2,
    ) -> None:
        super().__init__()
        hidden_dim = _validate_positive_int("expansion", expansion) * dim
        self.norm = _make_normalization(normalization, dim)
        self.mlp = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.mlp(self.norm(x))


class GatedRepresentationBlock(nn.Module):
    """Lightweight gated channel block over the shared embedding."""

    def __init__(self, dim: int, normalization: str) -> None:
        super().__init__()
        self.value = nn.Linear(dim, dim)
        self.gate = nn.Linear(dim, dim)
        self.norm = _make_normalization(normalization, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gated = self.value(x) * torch.sigmoid(self.gate(x))
        return self.norm(x + gated)


class SecureIDSHierarchicalAdvancedNet(nn.Module):
    """Advanced tabular encoder with binary and dataset-aware attack heads.

    Parameters
    ----------
    input_dim:
        Dataset-specific feature dimension, for example 77 for CICIDS2018 or
        192 for UNSW-NB15 (A8.8 corrected protocol; the pre-correction binary
        baseline used 190).
    attack_head_dim:
        Dataset-specific Head 2 output dimension, for example 14 for CICIDS2018
        after Task A4.5 or 9 for UNSW-NB15.
    hidden_dims:
        Encoder widths. The first width is the input projection size; later
        widths are reached by transition blocks and refined by residual blocks.
    dropout:
        Dropout probability in ``[0.0, 1.0)``.
    normalization:
        ``"layernorm"`` by default because it is stable for tiny synthetic
        smoke batches. ``"batchnorm"`` and ``"none"`` are also supported.
    attack_head_type:
        ``"linear"`` (default) reproduces the A9 baseline Head 2
        ``Linear(embedding_dim, attack_head_dim)`` exactly, so existing A9
        checkpoints stay loadable. ``"mlp"`` (A9.7 ``head2_branch_capacity``)
        inserts one non-linear branch
        ``Linear -> [norm] -> GELU -> Dropout -> Linear`` for more attack-family
        capacity. The forward output keys/shapes are unchanged either way.
    attack_head_hidden_dim:
        Hidden width of the ``"mlp"`` branch (default 128). Ignored for
        ``"linear"``.
    attack_head_norm:
        Whether the ``"mlp"`` branch applies ``normalization`` after the first
        linear layer (default ``True``).
    attack_head_dropout:
        Dropout for the ``"mlp"`` branch. Defaults to the model ``dropout``.
    """

    def __init__(
        self,
        input_dim: int,
        attack_head_dim: int,
        hidden_dims: Sequence[int] | None = None,
        dropout: float = DEFAULT_DROPOUT,
        normalization: str = DEFAULT_NORMALIZATION,
        residual_expansion: int = 2,
        attack_head_type: str = DEFAULT_ATTACK_HEAD_TYPE,
        attack_head_hidden_dim: int | None = None,
        attack_head_norm: bool = True,
        attack_head_dropout: float | None = None,
    ) -> None:
        super().__init__()

        self.input_dim = _validate_positive_int("input_dim", input_dim)
        self.attack_head_dim = _validate_positive_int("attack_head_dim", attack_head_dim)
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
        self.residual_expansion = _validate_positive_int(
            "residual_expansion",
            residual_expansion,
        )
        self.embedding_dim = self.hidden_dims[-1]

        layers: list[nn.Module] = [
            TransitionBlock(
                self.input_dim,
                self.hidden_dims[0],
                self.dropout,
                self.normalization,
            ),
            ResidualMLPBlock(
                self.hidden_dims[0],
                self.dropout,
                self.normalization,
                self.residual_expansion,
            ),
        ]
        current_dim = self.hidden_dims[0]
        for width in self.hidden_dims[1:]:
            if width != current_dim:
                layers.append(TransitionBlock(current_dim, width, self.dropout, self.normalization))
                current_dim = width
            layers.append(
                ResidualMLPBlock(
                    current_dim,
                    self.dropout,
                    self.normalization,
                    self.residual_expansion,
                )
            )

        self.encoder = nn.Sequential(*layers)
        self.gate = GatedRepresentationBlock(self.embedding_dim, self.normalization)
        self.binary_head = nn.Linear(self.embedding_dim, 1)

        # Head 2 (attack-family) is configurable. "linear" (default) is the A9
        # baseline; "mlp" (A9.7 head2_branch_capacity) adds one non-linear branch
        # for more capacity. The forward output keys/shapes stay identical.
        self.attack_head_type = str(attack_head_type).lower()
        if self.attack_head_type not in ATTACK_HEAD_TYPES:
            raise ValueError(
                "attack_head_type must be one of "
                f"{set(ATTACK_HEAD_TYPES)}, got {attack_head_type!r}."
            )
        self.attack_head_hidden_dim = _validate_positive_int(
            "attack_head_hidden_dim",
            DEFAULT_ATTACK_HEAD_HIDDEN_DIM
            if attack_head_hidden_dim is None
            else attack_head_hidden_dim,
        )
        self.attack_head_norm = bool(attack_head_norm)
        resolved_attack_dropout = (
            self.dropout if attack_head_dropout is None else float(attack_head_dropout)
        )
        if not 0.0 <= resolved_attack_dropout < 1.0:
            raise ValueError(
                f"attack_head_dropout must be in [0.0, 1.0), got {attack_head_dropout!r}."
            )
        self.attack_head_dropout = resolved_attack_dropout
        self.attack_head = _build_attack_head(
            embedding_dim=self.embedding_dim,
            attack_head_dim=self.attack_head_dim,
            head_type=self.attack_head_type,
            hidden_dim=self.attack_head_hidden_dim,
            use_norm=self.attack_head_norm,
            dropout=self.attack_head_dropout,
            normalization=self.normalization,
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Return binary logits, attack logits, and shared embeddings."""

        embedding = self.gate(self.encoder(x))
        binary_logit = self.binary_head(embedding).squeeze(-1)
        attack_logits = self.attack_head(embedding)
        return {
            "binary_logit": binary_logit,
            "attack_logits": attack_logits,
            "embedding": embedding,
        }

    @property
    def architecture_metadata(self) -> dict[str, Any]:
        """Return a serializable description for future manifests."""

        return {
            "architecture": "SecureIDSHierarchicalAdvancedNet",
            "input_dim": self.input_dim,
            "attack_head_dim": self.attack_head_dim,
            "hidden_dims": list(self.hidden_dims),
            "embedding_dim": self.embedding_dim,
            "dropout": self.dropout,
            "normalization": self.normalization,
            "residual_expansion": self.residual_expansion,
            "attack_head": {
                "type": self.attack_head_type,
                "hidden_dim": (
                    self.attack_head_hidden_dim
                    if self.attack_head_type == "mlp"
                    else None
                ),
                "norm": (
                    self.attack_head_norm if self.attack_head_type == "mlp" else False
                ),
                "dropout": (
                    self.attack_head_dropout if self.attack_head_type == "mlp" else 0.0
                ),
            },
            "heads": {
                "binary": "single raw logit for Benign/Normal vs Attack",
                "attack_family": "dataset-aware attack-family logits",
            },
        }


def compute_hierarchical_loss(
    outputs: dict[str, torch.Tensor],
    y_binary: torch.Tensor,
    y_attack_family: torch.Tensor,
    attack_family_mask: torch.Tensor,
    binary_loss_weight: float = 1.0,
    attack_loss_weight: float = 1.0,
    ignore_index: int = -1,
    pos_weight: torch.Tensor | float | None = None,
    attack_class_weights: torch.Tensor | Sequence[float] | None = None,
) -> dict[str, torch.Tensor | int | float | bool]:
    """Compute masked multi-task loss for the hierarchical IDS skeleton.

    Binary loss is computed for every row with optional ``pos_weight`` applied to
    ``BCEWithLogits`` (Head 1 class weighting per the A8.5 strategy). Attack-family
    loss is computed only for rows where ``attack_family_mask == 1`` and
    ``y_attack_family`` is not the ignore index, with optional
    ``attack_class_weights`` applied to the attack-family ``CrossEntropy`` (Head 2
    class weighting per the A8.5 strategy).

    Parameters
    ----------
    pos_weight:
        Optional scalar BCE positive-class weight for Head 1.
    attack_class_weights:
        Optional Head 2 per-class weight vector. Its length must equal
        ``attack_head_dim`` (``attack_logits.shape[1]``); index ``i`` weights
        attack-family class id ``i``, so it must align with the
        ``id_to_class`` mapping. A wrong length raises ``ValueError``. Both
        weight tensors are moved to the logits' device/dtype.

    Safety
    ------
    If a batch has no attack rows, the attack loss is a zero tensor on the same
    device/dtype as the binary loss, so an empty attack mask never produces NaN.
    Weight shapes are validated up front, so a wrong ``attack_class_weights``
    length fails clearly even on an all-benign batch.
    """

    if "binary_logit" not in outputs or "attack_logits" not in outputs:
        raise KeyError("outputs must contain 'binary_logit' and 'attack_logits'.")

    binary_logit = outputs["binary_logit"].reshape(-1)
    attack_logits = outputs["attack_logits"]
    device = binary_logit.device
    y_binary = y_binary.to(device=device, dtype=binary_logit.dtype).reshape(-1)
    y_attack_family = y_attack_family.to(device=device, dtype=torch.long).reshape(-1)
    attack_family_mask = attack_family_mask.to(device=device).reshape(-1)

    batch_size = binary_logit.shape[0]
    if y_binary.shape[0] != batch_size:
        raise ValueError("y_binary length must match binary_logit batch size.")
    if y_attack_family.shape[0] != batch_size:
        raise ValueError("y_attack_family length must match binary_logit batch size.")
    if attack_family_mask.shape[0] != batch_size:
        raise ValueError("attack_family_mask length must match binary_logit batch size.")
    if attack_logits.ndim != 2 or attack_logits.shape[0] != batch_size:
        raise ValueError("attack_logits must have shape [batch, attack_head_dim].")

    # Validate/move the Head 2 class-weight vector up front so a wrong shape
    # fails clearly regardless of whether this batch contains any attack rows.
    attack_weight_tensor = None
    if attack_class_weights is not None:
        attack_weight_tensor = torch.as_tensor(
            attack_class_weights,
            dtype=attack_logits.dtype,
            device=device,
        ).reshape(-1)
        num_attack_classes = int(attack_logits.shape[1])
        if attack_weight_tensor.numel() != num_attack_classes:
            raise ValueError(
                "attack_class_weights length must equal attack_head_dim "
                f"({num_attack_classes}), got {attack_weight_tensor.numel()}."
            )

    bce_pos_weight = None
    if pos_weight is not None:
        bce_pos_weight = torch.as_tensor(
            pos_weight,
            dtype=binary_logit.dtype,
            device=device,
        ).reshape(1)
    binary_loss = F.binary_cross_entropy_with_logits(
        binary_logit,
        y_binary,
        pos_weight=bce_pos_weight,
    )

    mask_bool = attack_family_mask == 1
    attack_rows = int(mask_bool.sum().item())
    valid_attack_mask = mask_bool & (y_attack_family != int(ignore_index))
    if bool(valid_attack_mask.any().item()):
        attack_loss = F.cross_entropy(
            attack_logits[valid_attack_mask],
            y_attack_family[valid_attack_mask],
            weight=attack_weight_tensor,
        )
    else:
        attack_loss = binary_loss.new_zeros(())

    total_loss = (
        float(binary_loss_weight) * binary_loss
        + float(attack_loss_weight) * attack_loss
    )
    return {
        "total_loss": total_loss,
        "binary_loss": binary_loss,
        "attack_loss": attack_loss,
        "attack_rows": attack_rows,
        "binary_loss_weight": float(binary_loss_weight),
        "attack_loss_weight": float(attack_loss_weight),
        "binary_pos_weight_applied": bool(pos_weight is not None),
        "attack_class_weights_applied": bool(attack_weight_tensor is not None),
    }
