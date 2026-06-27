from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from secureids.preprocessing.pipeline import run_preprocessing_dry_run
from secureids.preprocessing.validation import map_binary_label


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_cicids_dry_run_detects_label(tmp_path):
    write_text(
        tmp_path / "configs/preprocessing/cicids2018_binary.yaml",
        """
dataset: cicids2018
task: binary
raw_dir: data/raw/cicids2018
output_dir: data/processed/cicids2018/binary
artifact_path: models/final/preprocessors/cicids2018_binary_preprocessor.joblib
target_column: Label
drop_columns:
  - Flow ID
  - Src IP
  - Dst IP
  - Timestamp
  - Label
binary_mapping:
  benign_values:
    - BENIGN
  attack_rule: all_non_benign_are_attack
split:
  strategy: stratified_random
  random_seed: 42
cleaning:
  strip_column_whitespace: true
imputation:
  numeric_strategy: median
scaling:
  type: standard
""",
    )
    write_text(
        tmp_path / "data/raw/cicids2018/sample.csv",
        "Flow Duration,Label\n1,BENIGN\n2,DoS\n",
    )

    reports = run_preprocessing_dry_run("cicids", tmp_path)

    assert reports[0]["target_column_status"]["present"] is True
    assert reports[0]["processed_outputs_created"] is False
    assert not (tmp_path / "data/processed/cicids2018/binary").exists()


def test_cicids_binary_mapping_helper():
    mapping = {
        "benign_values": ["BENIGN", "Benign", "benign"],
        "attack_rule": "all_non_benign_are_attack",
    }

    assert map_binary_label("BENIGN", mapping) == 0
    assert map_binary_label("Bot", mapping) == 1


def test_unsw_dry_run_detects_required_columns(tmp_path):
    write_text(
        tmp_path / "configs/preprocessing/unsw_nb15_binary.yaml",
        """
dataset: unsw_nb15
task: binary
train_file: data/raw/unsw_nb15/UNSW_NB15_training-set.csv
test_file: data/raw/unsw_nb15/UNSW_NB15_testing-set.csv
output_dir: data/processed/unsw_nb15/binary
artifact_path: models/final/preprocessors/unsw_nb15_binary_preprocessor.joblib
target_column: label
drop_columns:
  - id
  - label
  - attack_cat
categorical_columns:
  - proto
  - service
  - state
split:
  strategy: official_train_test_with_validation_from_train
  random_seed: 42
cleaning:
  strip_column_whitespace: true
encoding:
  categorical_encoder: onehot
imputation:
  numeric_strategy: median
scaling:
  type: standard
""",
    )
    csv_text = (
        "id,dur,proto,service,state,attack_cat,label\n"
        "1,0.1,tcp,http,FIN,Normal,0\n"
        "2,0.2,udp,dns,CON,Generic,1\n"
    )
    write_text(tmp_path / "data/raw/unsw_nb15/UNSW_NB15_training-set.csv", csv_text)
    write_text(tmp_path / "data/raw/unsw_nb15/UNSW_NB15_testing-set.csv", csv_text)

    reports = run_preprocessing_dry_run("unsw", tmp_path)
    report = reports[0]

    assert report["target_column_status"]["present"] is True
    assert report["configured_drop_column_status"]["id"] == "present"
    assert report["configured_drop_column_status"]["attack_cat"] == "present"
    assert report["categorical_column_status"] == {
        "proto": "present",
        "service": "present",
        "state": "present",
    }


def test_preprocess_without_dry_run_refuses_safely():
    result = subprocess.run(
        [sys.executable, "-m", "secureids.cli", "preprocess", "--dataset", "cicids"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Full preprocessing requires --execute. Use --dry-run for validation only." in (
        result.stdout + result.stderr
    )
