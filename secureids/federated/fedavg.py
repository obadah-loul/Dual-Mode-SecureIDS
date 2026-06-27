"""FedAvg contracts and aggregation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


FEDAVG_ALGORITHM = "FedAvg"
FEDAVG_WEIGHTING = "sample_count"


class FedAvgExecutionNotImplemented(RuntimeError):
    """Raised if real FedAvg execution is attempted before approval."""


@dataclass(frozen=True)
class FedAvgPlan:
    dataset: str
    input_dim: int
    num_clients: int
    rounds: int
    local_epochs: int
    aggregation_weighting: str = FEDAVG_WEIGHTING


def describe_fedavg_plan(
    dataset: str,
    input_dim: int,
    num_clients: int,
    rounds: int,
    local_epochs: int,
) -> FedAvgPlan:
    """Return a lightweight future execution plan description."""

    return FedAvgPlan(
        dataset=dataset,
        input_dim=input_dim,
        num_clients=num_clients,
        rounds=rounds,
        local_epochs=local_epochs,
    )


def aggregate_state_dicts_weighted(
    state_dicts: list[Mapping[str, object]],
    sample_counts: list[int],
) -> dict[str, object]:
    """Return weighted FedAvg state dict using client sample counts.

    The function imports torch lazily so dry-run config validation remains
    torch-free. It performs only aggregation math; it does not train, evaluate,
    or write artifacts.
    """

    if not state_dicts:
        raise ValueError("At least one client state_dict is required.")
    if len(state_dicts) != len(sample_counts):
        raise ValueError("state_dicts and sample_counts must have the same length.")
    if any(count <= 0 for count in sample_counts):
        raise ValueError("All sample counts must be positive.")

    total_samples = float(sum(sample_counts))
    reference_keys = list(state_dicts[0].keys())
    for state in state_dicts[1:]:
        if list(state.keys()) != reference_keys:
            raise ValueError("All client state_dicts must have identical keys/order.")

    import torch

    aggregated: dict[str, object] = {}
    for key in reference_keys:
        first_value = state_dicts[0][key]
        if not torch.is_tensor(first_value):
            aggregated[key] = first_value
            continue
        if not torch.is_floating_point(first_value):
            aggregated[key] = first_value.detach().clone()
            continue

        accumulator = torch.zeros_like(first_value, dtype=torch.float32)
        for state, count in zip(state_dicts, sample_counts):
            value = state[key]
            if not torch.is_tensor(value):
                raise ValueError(f"State value for key {key!r} is not a tensor.")
            accumulator = accumulator + value.detach().to(dtype=torch.float32) * (
                float(count) / total_samples
            )
        aggregated[key] = accumulator.to(dtype=first_value.dtype)
    return aggregated


def run_fedavg_training(*args: object, **kwargs: object) -> None:
    """Compatibility placeholder; use ``secureids.federated.training``."""

    raise FedAvgExecutionNotImplemented(
        "Call secureids.federated.training.run_unsw_fedavg_training for the "
        "approved UNSW-only FedAvg execution path."
    )
