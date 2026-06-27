from __future__ import annotations

from pathlib import Path

from secureids.cli import build_parser, main
from secureids.federated.hierarchical_plan import load_hierarchical_federated_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml"


def test_federated_plan_command_parser_exists():
    parser = build_parser()

    args = parser.parse_args(["federated-plan", "--config", CONFIG])

    assert args.command == "federated-plan"
    assert args.config.as_posix() == CONFIG
    assert args.execute is False


def test_federated_plan_dry_run_writes_nothing():
    plan = load_hierarchical_federated_plan(CONFIG, project_root=PROJECT_ROOT)
    planned_paths = [
        PROJECT_ROOT / plan.raw["outputs"]["checkpoint"],
        PROJECT_ROOT / plan.raw["outputs"]["test_metrics"],
        PROJECT_ROOT / plan.raw["outputs"]["audit_json"],
    ]
    before = {path: path.exists() for path in planned_paths}

    result = main(["federated-plan", "--config", CONFIG])

    after = {path: path.exists() for path in planned_paths}
    assert result == 0
    assert after == before
    assert not any(after.values())


def test_federated_plan_execute_is_refused():
    result = main(["federated-plan", "--config", CONFIG, "--execute"])

    assert result == 1
