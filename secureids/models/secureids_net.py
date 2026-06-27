"""SecureIDSNet: the shared lightweight tabular binary IDS network for V2.

This single architecture is reused across both datasets (CICIDS2018 and
UNSW-NB15) and, later, across federated clients. The input dimension is always
supplied by the caller from dataset metadata/config and is never hardcoded, so
the same class serves the 77-feature CICIDS2018 space and the 190-feature
UNSW-NB15 space without modification.

The network emits a single raw logit per sample (``output_dim == 1``). A sigmoid
is applied only at evaluation/inference time, never inside the model, so the
output pairs directly with :class:`torch.nn.BCEWithLogitsLoss`.
"""

from __future__ import annotations

from typing import Sequence

import torch
from torch import nn

DEFAULT_HIDDEN_DIMS: tuple[int, ...] = (256, 128, 64)
DEFAULT_DROPOUT: float = 0.20


class SecureIDSNet(nn.Module):
    """Lightweight feed-forward network for binary tabular intrusion detection.

    Architecture for the default hidden dims ``[256, 128, 64]``::

        Linear(input_dim, 256) -> BatchNorm1d(256) -> ReLU -> Dropout
        Linear(256, 128)       -> BatchNorm1d(128) -> ReLU -> Dropout
        Linear(128, 64)        ->                     ReLU -> Dropout
        Linear(64, 1)          -> raw logit

    Notes
    -----
    * ``input_dim`` is dataset-specific and supplied by the caller; nothing in
      this module assumes 77 or 190 features.
    * The final layer emits a single raw logit. Use ``BCEWithLogitsLoss`` for
      training and apply a sigmoid only when converting logits to probabilities
      for evaluation/inference.
    * BatchNorm is applied to every hidden block except the last one, matching
      the locked design (blocks 1 and 2 use BatchNorm; block 3 does not). This
      keeps the model lightweight and reusable later for federated training.

    Parameters
    ----------
    input_dim:
        Number of input features. Must be > 0.
    hidden_dims:
        Width of each hidden block. Defaults to ``[256, 128, 64]``.
    dropout:
        Dropout probability applied after each hidden block. In ``[0.0, 1.0)``.
    output_dim:
        Number of output logits. Must be ``1`` for the current binary task.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] | None = None,
        dropout: float = DEFAULT_DROPOUT,
        output_dim: int = 1,
    ) -> None:
        super().__init__()

        if int(input_dim) <= 0:
            raise ValueError(f"input_dim must be > 0, got {input_dim!r}.")
        if int(output_dim) != 1:
            raise ValueError(
                "SecureIDSNet currently supports the binary task only; "
                f"output_dim must be 1, got {output_dim!r}."
            )

        hidden = tuple(DEFAULT_HIDDEN_DIMS if hidden_dims is None else hidden_dims)
        if len(hidden) == 0:
            raise ValueError("hidden_dims must contain at least one layer.")
        if any(int(width) <= 0 for width in hidden):
            raise ValueError(f"hidden_dims must all be > 0, got {hidden!r}.")
        if not 0.0 <= float(dropout) < 1.0:
            raise ValueError(f"dropout must be in [0.0, 1.0), got {dropout!r}.")

        self.input_dim = int(input_dim)
        self.hidden_dims = tuple(int(width) for width in hidden)
        self.dropout = float(dropout)
        self.output_dim = int(output_dim)

        layers: list[nn.Module] = []
        in_features = self.input_dim
        last_hidden_index = len(self.hidden_dims) - 1
        for index, width in enumerate(self.hidden_dims):
            layers.append(nn.Linear(in_features, width))
            # BatchNorm on every hidden block except the last, per the design.
            if index < last_hidden_index:
                layers.append(nn.BatchNorm1d(width))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(self.dropout))
            in_features = width

        self.feature_extractor = nn.Sequential(*layers)
        self.classifier = nn.Linear(in_features, self.output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return raw logits of shape ``[batch, output_dim]`` (no sigmoid)."""

        features = self.feature_extractor(x)
        return self.classifier(features)

    @property
    def architecture_metadata(self) -> dict[str, object]:
        """Return a small, serializable description of the architecture.

        Useful for checkpoints and training manifests so the saved metadata
        always reflects the actual constructed network.
        """

        return {
            "architecture": "SecureIDSNet",
            "input_dim": self.input_dim,
            "hidden_dims": list(self.hidden_dims),
            "dropout": self.dropout,
            "output_dim": self.output_dim,
        }
