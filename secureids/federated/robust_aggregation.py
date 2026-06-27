"""Deterministic aggregation utilities for future federated/security runs.

The helpers operate on client update tensors or dictionaries of tensors. They
perform only in-memory aggregation math: no training, evaluation, checkpoint
writes, or result writes happen here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


class AggregationValidationError(ValueError):
    """Raised when client updates cannot be safely aggregated."""


def _torch():
    try:
        import torch
    except ModuleNotFoundError as error:  # pragma: no cover - environment specific
        raise AggregationValidationError("PyTorch is required for aggregation.") from error
    return torch


def _is_tensor(value: Any) -> bool:
    torch = _torch()
    return torch.is_tensor(value)


def _clone_value(value: Any) -> Any:
    if _is_tensor(value):
        return value.detach().clone()
    return value


def _clone_update(update: Any) -> Any:
    if _is_tensor(update):
        return update.detach().clone()
    if isinstance(update, Mapping):
        return {key: _clone_value(value) for key, value in update.items()}
    raise AggregationValidationError("Each update must be a tensor or mapping.")


def _validate_tensor_list(updates: Sequence[Any]) -> None:
    if not updates:
        raise AggregationValidationError("At least one client update is required.")
    if not all(_is_tensor(update) for update in updates):
        raise AggregationValidationError(
            "Client updates must be all tensors or all mappings."
        )
    reference = updates[0]
    for index, update in enumerate(updates[1:], start=1):
        if tuple(update.shape) != tuple(reference.shape):
            raise AggregationValidationError(
                f"Tensor update {index} shape {tuple(update.shape)} does not match "
                f"reference shape {tuple(reference.shape)}."
            )


def _validate_mapping_list(updates: Sequence[Any]) -> None:
    if not updates:
        raise AggregationValidationError("At least one client update is required.")
    if not all(isinstance(update, Mapping) for update in updates):
        raise AggregationValidationError(
            "Client updates must be all tensors or all mappings."
        )

    reference_keys = list(updates[0].keys())
    if not reference_keys:
        raise AggregationValidationError("Client update mappings must not be empty.")
    for index, update in enumerate(updates):
        if list(update.keys()) != reference_keys:
            raise AggregationValidationError(
                f"Update {index} keys/order do not match the reference update."
            )
        for key in reference_keys:
            value = update[key]
            reference_value = updates[0][key]
            if _is_tensor(reference_value):
                if not _is_tensor(value):
                    raise AggregationValidationError(
                        f"Update {index} value for {key!r} is not a tensor."
                    )
                if tuple(value.shape) != tuple(reference_value.shape):
                    raise AggregationValidationError(
                        f"Update {index} value for {key!r} has shape "
                        f"{tuple(value.shape)}; expected {tuple(reference_value.shape)}."
                    )
            elif _is_tensor(value):
                raise AggregationValidationError(
                    f"Update {index} value for {key!r} mixes tensor and non-tensor."
                )


def validate_client_updates(updates: Sequence[Any]) -> str:
    """Validate client updates and return ``tensor`` or ``mapping``.

    All updates must have the same container type and compatible tensor shapes.
    Non-tensor mapping values are allowed but preserved from the first client
    instead of being averaged.
    """

    if not isinstance(updates, Sequence) or isinstance(updates, (str, bytes)):
        raise AggregationValidationError("updates must be a non-empty sequence.")
    if len(updates) == 0:
        raise AggregationValidationError("At least one client update is required.")
    if _is_tensor(updates[0]):
        _validate_tensor_list(updates)
        return "tensor"
    if isinstance(updates[0], Mapping):
        _validate_mapping_list(updates)
        return "mapping"
    raise AggregationValidationError("Each update must be a tensor or mapping.")


def _validate_weights(weights: Sequence[float] | None, num_updates: int) -> list[float]:
    if weights is None:
        return [1.0 / float(num_updates)] * num_updates
    if len(weights) != num_updates:
        raise AggregationValidationError("weights must match the number of updates.")
    if any(isinstance(weight, bool) for weight in weights):
        raise AggregationValidationError("weights must be numeric and positive.")
    normalized = [float(weight) for weight in weights]
    if any(not math.isfinite(weight) or weight <= 0.0 for weight in normalized):
        raise AggregationValidationError("weights must be finite positive values.")
    total = sum(normalized)
    if total <= 0.0:
        raise AggregationValidationError("weights must sum to a positive value.")
    return [weight / total for weight in normalized]


def _weighted_tensor_mean(values: Sequence[Any], weights: Sequence[float]) -> Any:
    torch = _torch()
    reference = values[0]
    if not torch.is_floating_point(reference):
        return reference.detach().clone()
    accumulator = torch.zeros_like(reference, dtype=torch.float32)
    for value, weight in zip(values, weights):
        accumulator = accumulator + value.detach().to(dtype=torch.float32) * float(weight)
    return accumulator.to(dtype=reference.dtype)


def aggregate_fedavg(updates: Sequence[Any], weights: Sequence[float] | None = None) -> Any:
    """Aggregate client updates with weighted FedAvg."""

    update_kind = validate_client_updates(updates)
    normalized_weights = _validate_weights(weights, len(updates))
    if update_kind == "tensor":
        return _weighted_tensor_mean(updates, normalized_weights)

    aggregated: dict[str, Any] = {}
    for key in updates[0].keys():
        values = [update[key] for update in updates]
        if _is_tensor(values[0]):
            aggregated[key] = _weighted_tensor_mean(values, normalized_weights)
        else:
            aggregated[key] = values[0]
    return aggregated


def _stack_floating_tensors(values: Sequence[Any], context: str) -> Any:
    torch = _torch()
    if not torch.is_floating_point(values[0]):
        return None
    return torch.stack([value.detach().to(dtype=torch.float32) for value in values], dim=0)


def _trimmed_mean(values: Sequence[Any], trim_ratio: float) -> Any:
    torch = _torch()
    stacked = _stack_floating_tensors(values, "trimmed_mean")
    if stacked is None:
        return values[0].detach().clone()
    sorted_values, _ = torch.sort(stacked, dim=0)
    trim_k = int(math.floor(float(trim_ratio) * len(values)))
    if trim_k:
        sorted_values = sorted_values[trim_k : len(values) - trim_k]
    return sorted_values.mean(dim=0).to(dtype=values[0].dtype)


def aggregate_trimmed_mean(updates: Sequence[Any], trim_ratio: float) -> Any:
    """Aggregate updates by coordinate-wise trimmed mean."""

    if isinstance(trim_ratio, bool) or not math.isfinite(float(trim_ratio)):
        raise AggregationValidationError("trim_ratio must be a finite float.")
    ratio = float(trim_ratio)
    if ratio < 0.0 or ratio >= 0.5:
        raise AggregationValidationError("trim_ratio must satisfy 0 <= ratio < 0.5.")
    update_kind = validate_client_updates(updates)
    trim_k = int(math.floor(ratio * len(updates)))
    if len(updates) - 2 * trim_k <= 0:
        raise AggregationValidationError("trim_ratio removes all client updates.")

    if update_kind == "tensor":
        return _trimmed_mean(updates, ratio)

    aggregated: dict[str, Any] = {}
    for key in updates[0].keys():
        values = [update[key] for update in updates]
        aggregated[key] = _trimmed_mean(values, ratio) if _is_tensor(values[0]) else values[0]
    return aggregated


def _median(values: Sequence[Any]) -> Any:
    torch = _torch()
    stacked = _stack_floating_tensors(values, "median")
    if stacked is None:
        return values[0].detach().clone()
    return torch.median(stacked, dim=0).values.to(dtype=values[0].dtype)


def aggregate_median(updates: Sequence[Any]) -> Any:
    """Aggregate updates by coordinate-wise median."""

    update_kind = validate_client_updates(updates)
    if update_kind == "tensor":
        return _median(updates)

    aggregated: dict[str, Any] = {}
    for key in updates[0].keys():
        values = [update[key] for update in updates]
        aggregated[key] = _median(values) if _is_tensor(values[0]) else values[0]
    return aggregated


def _flatten_floating_update(update: Any) -> Any:
    torch = _torch()
    if _is_tensor(update):
        return update.detach().to(dtype=torch.float32).reshape(-1)
    pieces = []
    for key in update.keys():
        value = update[key]
        if _is_tensor(value) and torch.is_floating_point(value):
            pieces.append(value.detach().to(dtype=torch.float32).reshape(-1))
    if not pieces:
        raise AggregationValidationError("Krum requires at least one floating tensor.")
    return torch.cat(pieces)


def aggregate_krum(updates: Sequence[Any], num_malicious: int) -> Any:
    """Select one update using the Krum score.

    This lightweight implementation is intended for small deterministic tests and
    future guarded experiments. It returns a clone of the selected client update.
    """

    if isinstance(num_malicious, bool) or not isinstance(num_malicious, int):
        raise AggregationValidationError("num_malicious must be an integer.")
    if num_malicious < 0:
        raise AggregationValidationError("num_malicious must be non-negative.")
    validate_client_updates(updates)
    n_clients = len(updates)
    if n_clients <= 2 * num_malicious + 2:
        raise AggregationValidationError(
            "Krum requires n_clients > 2 * num_malicious + 2."
        )

    torch = _torch()
    flattened = [_flatten_floating_update(update) for update in updates]
    neighbor_count = n_clients - num_malicious - 2
    scores: list[float] = []
    for index, vector in enumerate(flattened):
        distances = []
        for other_index, other in enumerate(flattened):
            if index == other_index:
                continue
            distances.append(float(torch.sum((vector - other) ** 2).item()))
        distances.sort()
        scores.append(sum(distances[:neighbor_count]))
    selected_index = min(range(n_clients), key=lambda index: (scores[index], index))
    return _clone_update(updates[selected_index])
