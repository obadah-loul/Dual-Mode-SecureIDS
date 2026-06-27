# PREPROCESSING_DESIGN.md

## 1. Purpose

This document defines the approved preprocessing plan before implementation. It
exists to prevent data leakage, misleading compatibility claims, inconsistent feature
handling, and messy outputs. It also records exactly how CICIDS2018 and
UNSW-NB15 will be prepared for the shared binary IDS objective without pretending
that the two datasets have one raw feature schema.

## 2. Current Dataset Status

CICIDS2018:

- raw folder: `data/raw/cicids2018`
- 14 CSV files found and audited
- label column detected: `Label`
- no preprocessing has been run

UNSW-NB15:

- raw folder: `data/raw/unsw_nb15`
- files found:
  - `UNSW_NB15_training-set.csv`
  - `UNSW_NB15_testing-set.csv`
- 45 columns detected
- label column detected: `label`
- categorical columns detected from audit/design:
  - `proto`
  - `service`
  - `state`
  - `attack_cat`
- no preprocessing has been run

## 3. Core Preprocessing Principles

- Dataset-specific preprocessing is required.
- CICIDS2018 and UNSW-NB15 must not be forced into one raw feature schema.
- Both datasets use the same binary objective: Benign vs Attack.
- Scalers, imputers, and encoders must be fitted only on training data.
- Validation and test data must only be transformed with train-fitted artifacts.
- Test data must not be used for fitting or tuning.
- No invented numbers should be reported as real preprocessing results.
- All preprocessing outputs must be reproducible from config and CLI commands.

## 4. CICIDS2018 Preprocessing Design

Input:

`data/raw/cicids2018/*.csv`

Plan:

- Load the 14 raw CICIDS2018 CSV files.
- Strip whitespace from column names.
- Validate that all CSV files use compatible schemas before merging.
- Use `Label` as the target column.
- Binary label mapping:
  - `BENIGN` / `Benign` / `benign` -> `0`
  - all other labels -> `1`
- Drop the target column from features.
- Drop non-feature or leakage-risk columns if present:
  - `Flow ID`
  - `Src IP`
  - `Dst IP`
  - `Dst Port`
  - `Destination Port`
  - `Dest Port`
  - `Src Port`
  - `Source Port`
  - `Sport`
  - `Dport`
  - `Timestamp`
  - `Label`
- CICIDS2018 port identifier fields are excluded from the final feature set to
  reduce leakage and endpoint/service identifier risk before training.
- Keep numeric traffic-flow features.
- Coerce numeric columns safely.
- Replace `inf` and `-inf` with `NaN`.
- Fit numeric imputer only on training data.
- Impute validation/test using train-fitted imputer only.
- Fit scaler only on training data.
- Scale validation/test using train-fitted scaler only.
- Save feature names after preprocessing.
- Save label mapping.

Split:

- Stratified split by binary label.
- 70% train, 15% validation, 15% test.
- Fixed random seed: `42`.
- Test set is final holdout.

## 5. UNSW-NB15 Preprocessing Design

Input:

`data/raw/unsw_nb15/UNSW_NB15_training-set.csv`

`data/raw/unsw_nb15/UNSW_NB15_testing-set.csv`

Plan:

- Use the official training file as the source for train/validation.
- Use the official testing file as the final test set.
- Use `label` as the target column.
- Binary label mapping:
  - label `0` -> `0` Benign / Normal
  - label `1` -> `1` Attack
- Drop `label` from features.
- Drop `id` because it is only an identifier.
- Drop `attack_cat` from features because it is target-related and can leak
  attack-type information into the binary objective.
- Treat `proto`, `service`, and `state` as categorical input features.
- Encode `proto`, `service`, and `state` using
  `OneHotEncoder(handle_unknown="ignore")`.
- Fit encoder only on training data.
- Transform validation/test with train-fitted encoder only.
- Clean numeric columns.
- Replace `inf` and `-inf` with `NaN`.
- Fit numeric imputer only on training data.
- Impute validation/test using train-fitted imputer only.
- Fit scaler only on training data.
- Scale validation/test using train-fitted scaler only.
- Save final encoded feature names.
- Save label mapping.

Split:

- Official `UNSW_NB15_training-set.csv` -> train + validation.
- Official `UNSW_NB15_testing-set.csv` -> final test.
- Validation split from official training only.
- Suggested validation size: 15% or 20% of official training.
- Stratify validation split by binary label.
- Fixed random seed: `42`.
- Official testing file is final holdout.

## 6. Output Structure

Future processed outputs must be saved under:

- `data/processed/cicids2018/binary/`
- `data/processed/unsw_nb15/binary/`

Future files per dataset:

- `X_train.npy`
- `y_train.npy`
- `X_val.npy`
- `y_val.npy`
- `X_test.npy`
- `y_test.npy`
- `feature_names.json`
- `label_mapping.json`
- `split_summary.json`
- `preprocessing_manifest.json`

Future preprocessor artifacts must be saved under:

- `models/final/preprocessors/`

Future artifacts:

- `cicids2018_binary_preprocessor.joblib`
- `unsw_nb15_binary_preprocessor.joblib`

## 7. Audit and Report Outputs

Future preprocessing audit outputs must be saved under:

- `results/audits/`

Expected future files:

- `preprocessing_audit_cicids2018.csv`
- `preprocessing_audit_unsw_nb15.csv`
- `preprocessing_manifest_cicids2018.json`
- `preprocessing_manifest_unsw_nb15.json`

Expected documentation output:

- `docs/PREPROCESSING_REPORT.md`

## 8. Verification Requirements

After preprocessing is implemented later, the pipeline must verify:

- processed train/val/test files exist
- labels contain only `0` and `1`
- no `NaN` values remain
- no `inf` or `-inf` values remain
- no target column appears inside features
- no `attack_cat` appears inside UNSW features
- no `id` column appears inside UNSW features
- feature count is consistent across train/val/test within each dataset
- train/val/test label distributions are recorded
- feature names are saved
- label mapping is saved
- preprocessing artifacts are saved
- scalers/encoders/imputers are fitted only on training data
- validation/test use train-fitted artifacts only
- config path, input files, output files, random seed, and timestamp are recorded

## 9. Clean Architecture Plan

Preprocessing code should be organized later as:

`secureids/preprocessing/`

- `base.py`
- `cleaning.py`
- `encoding.py`
- `splitting.py`
- `artifacts.py`
- `validation.py`

Dataset-specific logic should remain in:

- `secureids/datasets/cicids2018.py`
- `secureids/datasets/unsw_nb15.py`

CLI commands later should be:

```bash
python -m secureids.cli preprocess --dataset cicids
python -m secureids.cli preprocess --dataset unsw
python -m secureids.cli preprocess --dataset all
```

Active preprocessing commands are not part of this design document. Any command
added before implementation approval must be dry-run/design-only.

## 10. Reproducibility Plan

Preprocessing must be config-driven.

Future configs:

- `configs/preprocessing/cicids2018_binary.yaml`
- `configs/preprocessing/unsw_nb15_binary.yaml`

Each config should define:

- dataset name
- task: binary
- raw input paths
- output paths
- artifact paths
- target column
- drop columns
- categorical columns
- numeric cleaning policy
- split policy
- validation size
- random seed
- scaler type
- encoder type
- imputer type

## 11. Compatibility Integrity Policy

- CICIDS2018 and UNSW-NB15 have different raw feature spaces.
- The project may share one architecture, SecureIDSNet.
- The project must use dataset-specific preprocessors.
- The project must use dataset-specific final checkpoints.
- A frozen CICIDS2018 checkpoint must not be presented as directly valid on raw
  official UNSW-NB15.
- No direct CICIDS-to-UNSW frozen-feature evaluation should be claimed.
- Any cross-dataset comparison must be explained carefully as separate binary
  IDS experiments, not one shared raw-feature model.

## 12. Approval Gate

No real preprocessing should run until this preprocessing design is reviewed and
approved by the user.
