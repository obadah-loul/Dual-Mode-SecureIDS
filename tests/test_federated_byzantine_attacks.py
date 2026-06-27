from __future__ import annotations

import pytest

from secureids.federated.byzantine_attacks import (
    apply_gaussian_noise,
    apply_scaling_attack,
    apply_sign_flip,
    select_malicious_clients,
    summarize_attack_effect,
)


torch = pytest.importorskip("torch")


def _updates():
    return [
        {"w": torch.tensor([1.0, 2.0])},
        {"w": torch.tensor([3.0, 4.0])},
        {"w": torch.tensor([5.0, 6.0])},
        {"w": torch.tensor([7.0, 8.0])},
    ]


def test_malicious_client_selection_is_deterministic():
    first = select_malicious_clients(num_clients=5, malicious_fraction=0.4, seed=123)
    second = select_malicious_clients(num_clients=5, malicious_fraction=0.4, seed=123)

    assert first == second
    assert len(first) == 2


def test_sign_flip_attack_does_not_mutate_clean_updates():
    clean = _updates()

    attacked = apply_sign_flip(clean, malicious_clients=[1], scale=-1.0)

    assert torch.allclose(clean[1]["w"], torch.tensor([3.0, 4.0]))
    assert torch.allclose(attacked[1]["w"], torch.tensor([-3.0, -4.0]))
    assert torch.allclose(attacked[0]["w"], clean[0]["w"])


def test_gaussian_noise_attack_is_deterministic_with_seed():
    clean = _updates()

    first = apply_gaussian_noise(clean, malicious_clients=[0, 2], std=0.1, seed=42)
    second = apply_gaussian_noise(clean, malicious_clients=[0, 2], std=0.1, seed=42)

    assert torch.allclose(first[0]["w"], second[0]["w"])
    assert torch.allclose(first[2]["w"], second[2]["w"])
    assert not torch.allclose(first[0]["w"], clean[0]["w"])


def test_scaling_attack_multiplies_malicious_updates():
    clean = _updates()

    attacked = apply_scaling_attack(clean, malicious_clients=[3], scale=10.0)

    assert torch.allclose(attacked[3]["w"], torch.tensor([70.0, 80.0]))
    assert torch.allclose(attacked[2]["w"], clean[2]["w"])


def test_attack_summary_reports_norm_change():
    clean = _updates()
    attacked = apply_scaling_attack(clean, malicious_clients=[0], scale=2.0)

    summary = summarize_attack_effect(clean, attacked, malicious_clients=[0])

    assert summary["malicious_client_ids"] == [0]
    assert summary["client_effects"][0]["norm_ratio"] == pytest.approx(2.0)
