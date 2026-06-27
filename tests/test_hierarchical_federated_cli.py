from __future__ import annotations

from pathlib import Path

from secureids.cli import build_parser, main
from secureids.federated.hierarchical_plan import load_hierarchical_federated_plan
from secureids.federated.hierarchical_training import planned_output_paths


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNSW_CONFIG = "configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml"
CICIDS_CONFIG = "configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml"


def test_federated_train_hierarchical_parser_exists():
    parser = build_parser()

    args = parser.parse_args(
        ["federated-train-hierarchical", "--config", UNSW_CONFIG]
    )

    assert args.command == "federated-train-hierarchical"
    assert args.config.as_posix() == UNSW_CONFIG
    assert args.execute is False


def test_federated_train_hierarchical_dry_run_writes_nothing():
    plan = load_hierarchical_federated_plan(UNSW_CONFIG, project_root=PROJECT_ROOT)
    paths = planned_output_paths(plan, PROJECT_ROOT)
    before = {name: path.exists() for name, path in paths.items()}

    result = main(["federated-train-hierarchical", "--config", UNSW_CONFIG])

    after = {name: path.exists() for name, path in paths.items()}
    assert result == 0
    assert after == before


def test_federated_train_hierarchical_dry_run_accepts_cicids_config():
    result = main(["federated-train-hierarchical", "--config", CICIDS_CONFIG])

    assert result == 0
