"""Byzantine client update transformations for federated-security scaffolds."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from secureids.federated.robust_aggregation import (
    AggregationValidationError,
    validate_client_updates,
)


class ByzantineAttackError(ValueError):
    """Raised when an attack setting or update payload is invalid."""


def _torch():
    try:
        import torch
    except ModuleNotFoundError as error:  # pragma: no cover - environment specific
        raise ByzantineAttackError("PyTorch is required for attack transforms.") from error
    return torch


def _is_tensor(value: Any) -> bool:
    torch = _torch()
    return torch.is_tensor(value)


def _validate_malicious_clients(
    malicious_clients: Sequence[int],
    num_clients: int,
) -> list[int]:
    normalized = sorted({int(client) for client in malicious_clients})
    if any(client < 0 or client >= num_clients for client in normalized):
        raise ByzantineAttackError("malicious client id is out of range.")
    return normalized


def select_malicious_clients(
    num_clients: int,
    malicious_fraction: float,
    seed: int,
) -> list[int]:
    """Select deterministic malicious client ids from ``0..num_clients-1``."""

    if isinstance(num_clients, bool) or not isinstance(num_clients, int) or num_clients <= 0:
        raise ByzantineAttackError("num_clients must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ByzantineAttackError("seed must be an integer.")
    if isinstance(malicious_fraction, bool) or not math.isfinite(float(malicious_fraction)):
        raise ByzantineAttackError("malicious_fraction must be finite.")
    fraction = float(malicious_fraction)
    if fraction < 0.0 or fraction > 1.0:
        raise ByzantineAttackError("malicious_fraction must satisfy 0 <= fraction <= 1.")

    count = int(math.floor(num_clients * fraction))
    if count == 0:
        return []
    rng = random.Random(seed)
    return sorted(rng.sample(range(num_clients), count))


def _clone_value(value: Any) -> Any:
    if _is_tensor(value):
        return value.detach().clone()
    return value


def _clone_update(update: Any) -> Any:
    if _is_tensor(update):
        return update.detach().clone()
    if isinstance(update, Mapping):
        return {key: _clone_value(value) for key, value in update.items()}
    raise ByzantineAttackError("Each update must be a tensor or mapping.")


def _map_floating_tensors(update: Any, transform: Any) -> Any:
    torch = _torch()
    if _is_tensor(update):
        if torch.is_floating_point(update):
            return transform(update.detach().clone())
        return update.detach().clone()
    if isinstance(update, Mapping):
        attacked: dict[str, Any] = {}
        for key, value in update.items():
            if _is_tensor(value) and torch.is_floating_point(value):
                attacked[key] = transform(value.detach().clone())
            else:
                attacked[key] = _clone_value(value)
        return attacked
    raise ByzantineAttackError("Each update must be a tensor or mapping.")


def _prepare_updates(updates: Sequence[Any]) -> tuple[list[Any], str]:
    try:
        update_kind = validate_client_updates(updates)
    except AggregationValidationError as error:
        raise ByzantineAttackError(str(error)) from error
    return [_clone_update(update) for update in updates], update_kind


def apply_sign_flip(
    updates: Sequence[Any],
    malicious_clients: Sequence[int],
    scale: float = -1.0,
) -> list[Any]:
    """Apply sign-flip style scaling to malicious client updates."""

    if isinstance(scale, bool) or not math.isfinite(float(scale)):
        raise ByzantineAttackError("scale must be a finite float.")
    attacked, _ = _prepare_updates(updates)
    malicious = _validate_malicious_clients(malicious_clients, len(attacked))
    malicious_set = set(malicious)
    for index in malicious_set:
        attacked[index] = _map_floating_tensors(
            attacked[index],
            lambda tensor: tensor * float(scale),
        )
    return attacked


def apply_gaussian_noise(
    updates: Sequence[Any],
    malicious_clients: Sequence[int],
    std: float,
    seed: int,
) -> list[Any]:
    """Add deterministic Gaussian noise to malicious client updates."""

    if isinstance(std, bool) or not math.isfinite(float(std)) or float(std) < 0.0:
        raise ByzantineAttackError("std must be a finite non-negative float.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ByzantineAttackError("seed must be an integer.")
    attacked, _ = _prepare_updates(updates)
    malicious = _validate_malicious_clients(malicious_clients, len(attacked))
    torch = _torch()
    generator = torch.Generator()
    generator.manual_seed(int(seed))

    def add_noise(tensor: Any) -> Any:
        noise = torch.randn(
            tuple(tensor.shape),
            generator=generator,
            dtype=tensor.dtype,
            device=tensor.device,
        )
        return tensor + noise * float(std)

    for index in malicious:
        attacked[index] = _map_floating_tensors(attacked[index], add_noise)
    return attacked


def apply_scaling_attack(
    updates: Sequence[Any],
    malicious_clients: Sequence[int],
    scale: float,
) -> list[Any]:
    """Multiply malicious client updates by ``scale``."""

    if isinstance(scale, bool) or not math.isfinite(float(scale)):
        raise ByzantineAttackError("scale must be a finite float.")
    attacked, _ = _prepare_updates(updates)
    malicious = _validate_malicious_clients(malicious_clients, len(attacked))
    for index in malicious:
        attacked[index] = _map_floating_tensors(
            attacked[index],
            lambda tensor: tensor * float(scale),
        )
    return attacked


def _update_norm(update: Any) -> float:
    torch = _torch()
    pieces = []
    if _is_tensor(update):
        if torch.is_floating_point(update):
            pieces.append(update.detach().to(dtype=torch.float32).reshape(-1))
    elif isinstance(update, Mapping):
        for value in update.values():
            if _is_tensor(value) and torch.is_floating_point(value):
                pieces.append(value.detach().to(dtype=torch.float32).reshape(-1))
    if not pieces:
        return 0.0
    return float(torch.linalg.vector_norm(torch.cat(pieces)).item())


def summarize_attack_effect(
    clean_updates: Sequence[Any],
    attacked_updates: Sequence[Any],
    malicious_clients: Sequence[int],
) -> dict[str, Any]:
    """Return lightweight norm metadata for attacked client updates."""

    validate_client_updates(clean_updates)
    validate_client_updates(attacked_updates)
    if len(clean_updates) != len(attacked_updates):
        raise ByzantineAttackError("clean and attacked updates must have equal length.")
    malicious = _validate_malicious_clients(malicious_clients, len(clean_updates))
    rows = []
    for client_id in malicious:
        before = _update_norm(clean_updates[client_id])
        after = _update_norm(attacked_updates[client_id])
        rows.append(
            {
                "client_id": int(client_id),
                "norm_before": before,
                "norm_after": after,
                "norm_ratio": after / before if before else None,
            }
        )
    return {
        "malicious_client_ids": malicious,
        "malicious_client_count": len(malicious),
        "client_effects": rows,
    }
