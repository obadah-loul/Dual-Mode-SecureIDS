"""CLI gate tests for train-attack-family-specialist (no training)."""

from __future__ import annotations

import pytest

from secureids.cli import (
    PROJECT_ROOT,
    build_parser,
    handle_train_attack_family_specialist,
    handle_train_hierarchical,
)

SEED42_CONFIG = (
    PROJECT_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "unsw_a99_attack_family_specialist_seed42.yaml"
)
SEED42_CHECKPOINT = PROJECT_ROOT / "models" / "experiments" / "unsw_a99_attack_family_specialist_seed42.pt"


def test_subcommand_registered_and_isolated():
    parser = build_parser()
    args = parser.parse_args(
        ["train-attack-family-specialist", "--config", str(SEED42_CONFIG)]
    )
    assert args.func is handle_train_attack_family_specialist
    assert args.execute is False
    assert args.overwrite is False


def test_config_is_required():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["train-attack-family-specialist"])


def test_existing_train_hierarchical_unchanged():
    parser = build_parser()
    args = parser.parse_args(
        ["train-hierarchical", "--config", "configs/training/unsw_nb15_hierarchical.yaml"]
    )
    # Existing subcommand still routes to its own handler and still defaults to no-execute.
    assert args.func is handle_train_hierarchical
    assert args.execute is False


def _sha256(path):
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def test_dry_run_does_not_train_or_modify_checkpoint():
    # The durable guarantee: a dry run creates/modifies NOTHING. (The seed42
    # checkpoint may or may not already exist depending on whether training has
    # been run; either way the dry run must leave it untouched.)
    existed_before = SEED42_CHECKPOINT.exists()
    hash_before = _sha256(SEED42_CHECKPOINT)

    parser = build_parser()
    args = parser.parse_args(
        ["train-attack-family-specialist", "--config", str(SEED42_CONFIG)]
    )
    rc = handle_train_attack_family_specialist(args)
    assert rc == 0

    assert SEED42_CHECKPOINT.exists() == existed_before  # dry run created nothing new
    assert _sha256(SEED42_CHECKPOINT) == hash_before  # and modified nothing
