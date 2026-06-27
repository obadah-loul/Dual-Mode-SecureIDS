from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
import subprocess
import sys

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = PROJECT_ROOT / "configs/preprocessing/experiments/unsw_a11_enhanced_feature_protocol.yaml"


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "secureids.cli", *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_prepare_unsw_a11_requires_config() -> None:
    result = run_cli(["prepare-unsw-a11"])

    assert result.returncode != 0
    assert "--config" in (result.stderr + result.stdout)


def test_prepare_unsw_a11_dry_run_writes_nothing() -> None:
    guarded_paths = [
        PROJECT_ROOT / "data/processed/unsw_a11_enhanced",
        PROJECT_ROOT / "models/experiments/preprocessors/unsw_a11_enhanced/unsw_a11_enhanced_preprocessor.joblib",
        PROJECT_ROOT / "results/audits/unsw_a11_enhanced_feature_protocol_preprocessing_audit.json",
    ]
    before = {path: path.exists() for path in guarded_paths}

    result = run_cli(["prepare-unsw-a11", "--config", str(ACTIVE_CONFIG)])

    after = {path: path.exists() for path in guarded_paths}
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout
    assert "writes nothing" in result.stdout
    assert before == after


def test_prepare_unsw_a11_rejects_unsafe_paths(tmp_path: Path) -> None:
    raw = yaml.safe_load(ACTIVE_CONFIG.read_text(encoding="utf-8"))
    raw = deepcopy(raw)
    raw["planned_outputs"]["processed_data_dir"] = "results/final/bad"
    bad_config = tmp_path / "bad_unsw_a11.yaml"
    bad_config.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    result = run_cli(["prepare-unsw-a11", "--config", str(bad_config)])

    assert result.returncode != 0
    assert "request rejected" in result.stdout
    assert "No preprocessing, training, evaluation" in result.stdout
