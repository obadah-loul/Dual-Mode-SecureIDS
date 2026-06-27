from __future__ import annotations

from pathlib import Path

import numpy as np

from secureids.preprocessing.pipeline import run_preprocessing_execute


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_unsw_execute_creates_expected_outputs_for_tiny_csvs(tmp_path):
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
binary_mapping:
  normal_value: 0
  attack_value: 1
split:
  strategy: official_train_test_with_validation_from_train
  val_size_from_train: 0.5
  random_seed: 42
cleaning:
  strip_column_whitespace: true
  replace_inf_with_nan: true
  numeric_coerce: true
encoding:
  categorical_encoder: onehot
  handle_unknown: ignore
  fit_on: train_only
imputation:
  numeric_strategy: median
  fit_on: train_only
scaling:
  type: standard
  fit_on: train_only
""",
    )
    sample = (
        "id,dur,proto,service,state,attack_cat,label\n"
        "1,0.1,tcp,http,FIN,Normal,0\n"
        "2,0.2,udp,dns,CON,Generic,1\n"
        "3,0.3,tcp,http,FIN,Normal,0\n"
        "4,0.4,udp,dns,CON,Generic,1\n"
    )
    write_text(tmp_path / "data/raw/unsw_nb15/UNSW_NB15_training-set.csv", sample)
    write_text(tmp_path / "data/raw/unsw_nb15/UNSW_NB15_testing-set.csv", sample)

    report = run_preprocessing_execute("unsw", tmp_path)[0]
    output_dir = Path(report["output_dir"])

    assert (output_dir / "X_train.npy").exists()
    assert (output_dir / "feature_names.json").exists()
    assert Path(report["artifact_path"]).exists()

    x_train = np.load(output_dir / "X_train.npy")
    y_train = np.load(output_dir / "y_train.npy")

    assert x_train.ndim == 2
    assert y_train.ndim == 1
    assert set(np.unique(y_train)).issubset({0, 1})
    assert np.isfinite(x_train).all()
