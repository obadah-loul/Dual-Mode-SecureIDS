"""CLI gate tests for train-frozen-embedding-specialist (no training)."""

from __future__ import annotations

import hashlib

import pytest

from secureids.cli import (
    PROJECT_ROOT,
    build_parser,
    handle_train_frozen_embedding_specialist,
    handle_train_hierarchical,
)


SEED42_CONFIG = (
    PROJECT_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "unsw_a10_frozen_embedding_specialist_seed42.yaml"
)
SEED42_CHECKPOINT = PROJECT_ROOT / "models" / "experiments" / "unsw_a10_frozen_embedding_specialist_seed42.pt"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def test_subcommand_registered_and_isolated():
    parser = build_parser()
    args = parser.parse_args(
        ["train-frozen-embedding-specialist", "--config", str(SEED42_CONFIG)]
    )
    assert args.func is handle_train_frozen_embedding_specialist
    assert args.execute is False
    assert args.overwrite is False


def test_config_is_required():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["train-frozen-embedding-specialist"])


def test_existing_train_hierarchical_unchanged():
    parser = build_parser()
    args = parser.parse_args(
        ["train-hierarchical", "--config", "configs/training/unsw_nb15_hierarchical.yaml"]
    )
    assert args.func is handle_train_hierarchical
    assert args.execute is False


def test_dry_run_does_not_train_or_modify_checkpoint():
    existed_before = SEED42_CHECKPOINT.exists()
    hash_before = _sha256(SEED42_CHECKPOINT)

    parser = build_parser()
    args = parser.parse_args(
        ["train-frozen-embedding-specialist", "--config", str(SEED42_CONFIG)]
    )
    rc = handle_train_frozen_embedding_specialist(args)
    assert rc == 0

    assert SEED42_CHECKPOINT.exists() == existed_before
    assert _sha256(SEED42_CHECKPOINT) == hash_before
