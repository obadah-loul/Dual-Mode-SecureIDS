"""One-sample local feature attribution for SecureIDS live demos.

This module intentionally implements a small dependency-free Gradient x Input
method. It does not run dataset evaluation, save files, or require SHAP/LIME.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import torch


BinaryAndFamily = tuple[torch.Tensor, torch.Tensor | None]


def _as_one_sample_tensor(input_tensor: torch.Tensor) -> torch.Tensor:
    if not isinstance(input_tensor, torch.Tensor):
        raise TypeError("input_tensor must be a torch.Tensor.")

    tensor = input_tensor.detach().clone().to(dtype=torch.float32)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    if tensor.ndim != 2 or int(tensor.shape[0]) != 1:
        raise ValueError("Gradient x Input expects exactly one sample.")
    return tensor


def extract_hierarchical_outputs(outputs: Any) -> BinaryAndFamily:
    """Extract binary and attack-family logits from supported model outputs."""

    if isinstance(outputs, dict):
        binary_logit = None
        for key in ("binary_logit", "binary_logits", "binary", "logit", "logits"):
            if key in outputs:
                binary_logit = outputs[key]
                break
        if binary_logit is None:
            raise KeyError("Model output dict does not contain a binary logit key.")

        attack_logits = None
        for key in ("attack_logits", "attack_family_logits", "family_logits"):
            if key in outputs:
                attack_logits = outputs[key]
                break
        return torch.as_tensor(binary_logit), (
            None if attack_logits is None else torch.as_tensor(attack_logits)
        )

    if isinstance(outputs, (tuple, list)):
        if len(outputs) == 0:
            raise ValueError("Model output tuple/list is empty.")
        binary_logit = torch.as_tensor(outputs[0])
        attack_logits = torch.as_tensor(outputs[1]) if len(outputs) > 1 else None
        return binary_logit, attack_logits

    if isinstance(outputs, torch.Tensor):
        return outputs, None

    raise TypeError(f"Unsupported model output type: {type(outputs)!r}.")


def _score_from_outputs(
    outputs: Any,
    score_name: str,
    family_index: int | None = None,
) -> torch.Tensor:
    binary_logit, attack_logits = extract_hierarchical_outputs(outputs)
    if score_name == "binary_attack_logit":
        return binary_logit.reshape(-1)[0]
    if score_name == "attack_family_logit":
        if attack_logits is None:
            raise ValueError("Attack-family logits are not available.")
        if family_index is None:
            raise ValueError("family_index is required for attack-family attribution.")
        if attack_logits.ndim != 2 or int(attack_logits.shape[0]) != 1:
            raise ValueError("Attack-family logits must have shape [1, num_classes].")
        return attack_logits[0, int(family_index)]
    raise ValueError(f"Unsupported attribution score: {score_name!r}.")


def _compute_gradient_x_input(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    score_selector: Callable[[Any], torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    model.zero_grad(set_to_none=True)

    x = input_tensor.detach().clone().requires_grad_(True)
    outputs = model(x)
    score = score_selector(outputs).reshape(())
    score.backward()

    if x.grad is None:
        raise RuntimeError("Input gradients were not computed.")

    attributions = (x.grad.detach()[0] * x.detach()[0]).cpu()
    input_values = x.detach()[0].cpu()
    model.zero_grad(set_to_none=True)
    return attributions, input_values


def _rank_features(
    attributions: torch.Tensor,
    input_values: torch.Tensor,
    feature_names: Sequence[str],
    *,
    top_k: int,
    positive: bool,
    direction: str,
) -> list[dict[str, int | float | str]]:
    if int(attributions.numel()) != len(feature_names):
        raise ValueError(
            "feature_names length must match attribution dimension: "
            f"{len(feature_names)} names for {int(attributions.numel())} features."
        )

    values = attributions.numpy()
    if positive:
        indices = [idx for idx, value in enumerate(values) if value > 0.0]
        indices.sort(key=lambda idx: float(values[idx]), reverse=True)
    else:
        indices = [idx for idx, value in enumerate(values) if value < 0.0]
        indices.sort(key=lambda idx: float(values[idx]))

    ranked: list[dict[str, int | float | str]] = []
    for rank, idx in enumerate(indices[: max(0, int(top_k))], start=1):
        ranked.append(
            {
                "rank": rank,
                "feature_index": int(idx),
                "feature_name": str(feature_names[idx]),
                "attribution": float(values[idx]),
                "input_value": float(input_values[idx].item()),
                "direction": direction,
            }
        )
    return ranked


def gradient_x_input_attribution(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    feature_names: Sequence[str],
    *,
    top_k: int = 8,
    binary_threshold: float = 0.5,
    include_family: bool = True,
    family_index: int | None = None,
) -> dict[str, Any]:
    """Compute real Gradient x Input attribution for one SecureIDS sample.

    The binary attribution targets the attack logit. Positive attributions push
    the model toward Attack, while negative attributions push it toward Benign.
    If the binary prediction is Attack and attack-family logits are available,
    the predicted family logit is also attributed.
    """

    if len(feature_names) == 0:
        raise ValueError("feature_names must not be empty.")

    sample = _as_one_sample_tensor(input_tensor).cpu()
    model = model.cpu()
    model.eval()

    with torch.no_grad():
        raw_outputs = model(sample)
        binary_logit, attack_logits = extract_hierarchical_outputs(raw_outputs)
        binary_score = binary_logit.reshape(-1)[0]
        binary_probability = float(torch.sigmoid(binary_score).item())
        predicted_binary = "Attack" if binary_probability >= float(binary_threshold) else "Benign"
        predicted_family_index = None
        predicted_family_probability = None
        if attack_logits is not None and attack_logits.ndim == 2:
            family_probs = torch.softmax(attack_logits, dim=1)
            predicted_family_index = int(torch.argmax(family_probs, dim=1).item())
            predicted_family_probability = float(family_probs[0, predicted_family_index].item())

    binary_attr, binary_inputs = _compute_gradient_x_input(
        model,
        sample,
        lambda outputs: _score_from_outputs(outputs, "binary_attack_logit"),
    )

    result: dict[str, Any] = {
        "method": "Gradient x Input",
        "binary": {
            "target": "binary_attack_logit",
            "prediction": predicted_binary,
            "probability": binary_probability,
            "top_positive": _rank_features(
                binary_attr,
                binary_inputs,
                feature_names,
                top_k=top_k,
                positive=True,
                direction="supports Attack",
            ),
            "top_negative": _rank_features(
                binary_attr,
                binary_inputs,
                feature_names,
                top_k=top_k,
                positive=False,
                direction="supports Benign",
            ),
        },
        "family": None,
        "limitations": [
            "Local gradient-based attribution for one processed sample.",
            "Not SHAP/LIME and not a causal proof.",
            "Processed feature values may be normalized or encoded.",
        ],
    }

    family_target = family_index if family_index is not None else predicted_family_index
    if include_family and predicted_binary == "Attack" and family_target is not None:
        family_attr, family_inputs = _compute_gradient_x_input(
            model,
            sample,
            lambda outputs: _score_from_outputs(
                outputs,
                "attack_family_logit",
                family_index=int(family_target),
            ),
        )
        result["family"] = {
            "target": "predicted_attack_family_logit",
            "family_index": int(family_target),
            "probability": predicted_family_probability,
            "top_positive": _rank_features(
                family_attr,
                family_inputs,
                feature_names,
                top_k=top_k,
                positive=True,
                direction="supports predicted attack family",
            ),
            "top_negative": _rank_features(
                family_attr,
                family_inputs,
                feature_names,
                top_k=top_k,
                positive=False,
                direction="opposes predicted attack family",
            ),
        }

    return result


def format_attribution_rows(
    items: list[dict[str, object]],
    *,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Format attribution dictionaries for compact dashboard tables."""

    selected = items if limit is None else items[: max(0, int(limit))]
    return [
        {
            "rank": item["rank"],
            "feature": item["feature_name"],
            "score": f"{float(item['attribution']):.6g}",
            "processed value": f"{float(item['input_value']):.6g}",
            "direction": item["direction"],
        }
        for item in selected
    ]


__all__ = [
    "extract_hierarchical_outputs",
    "format_attribution_rows",
    "gradient_x_input_attribution",
]
