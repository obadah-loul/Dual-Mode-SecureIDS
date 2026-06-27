"""Torch-free train-hierarchical CLI gate tests.

These tests exercise only the private CLI safety helper. They do not invoke
training, preprocessing, model loading, checkpoint writing, or metric creation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from secureids.cli import (
    _validate_train_hierarchical_cli_gate,
    normalized_dataset_name,
)


@pytest.mark.parametrize("alias", ["unsw", "unsw_nb15", "unsw-nb15"])
def test_unsw_aliases_accept_unsw_hierarchical_config(alias: str) -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection=alias,
        config_path=Path("configs/training/unsw_nb15_hierarchical.yaml"),
        config_dataset="unsw_nb15",
        config_input_dim=192,
        config_task="hierarchical",
    )

    assert normalized_dataset_name(alias) == "unsw_nb15"
    assert label == "UNSW-NB15"


@pytest.mark.parametrize("alias", ["cicids", "cicids2018", "cicids-2018"])
def test_cicids_aliases_accept_cicids_hierarchical_config(alias: str) -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection=alias,
        config_path=Path("configs/training/cicids2018_hierarchical.yaml"),
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )

    assert normalized_dataset_name(alias) == "cicids2018"
    assert label == "CICIDS2018"


def test_cicids_experiment_config_name_is_accepted_when_scoped_and_hierarchical() -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="cicids",
        config_path=Path(
            "configs/training/experiments/"
            "cicids_hierarchical_exp01_head2_mlp_capacity.yaml"
        ),
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )

    assert label == "CICIDS2018"


def test_unsw_a9_variant_config_name_is_accepted_when_config_is_hierarchical() -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="unsw",
        config_path=Path("configs/training/multiseed/unsw_a9_linear_seed42.yaml"),
        config_dataset="unsw_nb15",
        config_input_dim=192,
        config_task="hierarchical",
    )

    assert label == "UNSW-NB15"


def test_unsw_a11_enhanced_feature_protocol_config_name_is_accepted() -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="unsw",
        config_path=Path(
            "configs/training/experiments/"
            "unsw_a11_enhanced_feature_protocol_seed42.yaml"
        ),
        config_dataset="unsw_nb15",
        config_input_dim=192,
        config_attack_head_dim=9,
        config_task="hierarchical",
    )

    assert label == "UNSW-NB15"


@pytest.mark.parametrize(
    "dataset,config_path,config_dataset,input_dim",
    [
        (
            "cicids",
            "configs/training/unsw_nb15_hierarchical.yaml",
            "unsw_nb15",
            192,
        ),
        (
            "unsw",
            "configs/training/cicids2018_hierarchical.yaml",
            "cicids2018",
            77,
        ),
    ],
)
def test_dataset_config_cross_pairs_are_rejected(
    dataset: str,
    config_path: str,
    config_dataset: str,
    input_dim: int,
) -> None:
    with pytest.raises(ValueError, match="does not match"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection=dataset,
            config_path=Path(config_path),
            config_dataset=config_dataset,
            config_input_dim=input_dim,
            config_task="hierarchical",
        )


def test_unsupported_dataset_alias_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported dataset alias"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="kdd",
            config_path=Path("configs/training/unsw_nb15_hierarchical.yaml"),
            config_dataset="unsw_nb15",
            config_input_dim=192,
            config_task="hierarchical",
        )


@pytest.mark.parametrize(
    "config_path,config_task,expected_message",
    [
        ("configs/training/unsw_nb15_binary.yaml", "binary", "requires task"),
        ("configs/training/unsw_notes.yaml", "hierarchical", "requires a UNSW"),
    ],
)
def test_binary_or_unrelated_configs_are_rejected(
    config_path: str,
    config_task: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="unsw",
            config_path=Path(config_path),
            config_dataset="unsw_nb15",
            config_input_dim=192,
            config_task=config_task,
        )


def test_cicids_rejects_unapproved_experiment_config_name() -> None:
    with pytest.raises(ValueError, match="approved"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="cicids",
            config_path=Path("configs/training/cicids2018_hierarchical_experiment.yaml"),
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=14,
            config_task="hierarchical",
        )


def test_cicids_experiment_rejects_wrong_attack_head_dim() -> None:
    with pytest.raises(ValueError, match="attack_head_dim"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="cicids",
            config_path=Path(
                "configs/training/experiments/"
                "cicids_hierarchical_exp01_head2_mlp_capacity.yaml"
            ),
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=9,
            config_task="hierarchical",
        )
