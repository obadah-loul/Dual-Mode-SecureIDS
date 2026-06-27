# Secure, Robust, and Explainable Federated Intrusion Detection System

## Overview

This repository contains the V2 implementation workspace for the Dual-Mode
SecureIDS Framework. The project combines centralized reference baselines,
hierarchical federated intrusion detection, robustness evidence, integrity
verification, explainability, and a live demonstration dashboard.

The current detection objectives are:

- Binary detection: Benign / Attack.
- Attack-family classification for detected attack traffic.

CICIDS2018 and UNSW-NB15 are intentionally handled through separate dataset
adapters and preprocessors. UNSW-NB15 is not forced into the CICIDS2018 feature
schema, and no direct frozen CICIDS-to-UNSW evaluation is claimed.

## Current Implementation Status

Current finalized scope:

- Dual-mode SecureIDS framing: centralized reference mode and federated IDS mode.
- Dataset-specific CICIDS2018 and UNSW-NB15 preprocessing and evaluation paths.
- Hierarchical IDS models with binary and attack-family outputs.
- Selected clean hierarchical federated baselines for CICIDS2018 and UNSW-NB15.
- Phase A SignFlip 25% federated robustness evidence comparing FedAvg and
  Trimmed Mean.
- SHA-256 integrity/tamper-evidence for selected samples, prediction records,
  and federated update manifests.
- Streamlit live demonstration dashboard with saved benchmark attack scenarios.
- Gradient x Input local feature attribution for one-sample live inference.

Final evidence index:

- `docs/experiments/FINAL_EVIDENCE_REPORT_INDEX.md`
- `docs/experiments/CENTRALIZED_VS_FEDERATED_COMPARISON.md`
- `docs/experiments/PHASE_A_SIGNFLIP25_ATTACK_DEFENSE_SUMMARY.md`

Created preprocessing artifacts:

- Train/validation/test NumPy outputs under `data/processed/`
- Dataset-specific preprocessor artifacts under `models/final/preprocessors/`
- CICIDS2018 preprocessing safety fix applied: port identifier fields are
  removed before centralized training design.

Not final claims:

- TLS secure transport is a future deployment hardening extension.
- Gaussian Noise and Scaling are optional future Byzantine attack extensions.
- Phase B / 50% malicious-client work is archive-only stress-test evidence.
- Standalone binary FedAvg artifacts are archive/baseline evidence, not the
  final hierarchical target.
- SHA-256 supports integrity/tamper-evidence; it is not the Byzantine defense.
- Trimmed Mean is the robust aggregation defense evaluated in the final Phase A
  matrix.

## Dataset Status

CICIDS2018:

- Raw folder: `data/raw/cicids2018`
- Current files: 14 CSV files
- Audit status: headers and tiny samples inspected
- Detected label column: `Label`

UNSW-NB15:

- Raw folder: `data/raw/unsw_nb15`
- Current files:
  - `UNSW_NB15_training-set.csv`
  - `UNSW_NB15_testing-set.csv`
- Audit status: headers and tiny samples inspected
- Detected label column: `label`
- Categorical columns tracked for preprocessing: `proto`, `service`, `state`

## Architecture

The V2 architecture is organized into these layers:

- Dataset adapters: `secureids/datasets/`
- Reusable preprocessing utilities: `secureids/preprocessing/`
- Reporting and audit writers: `secureids/reporting/`
- Model, training, federated, security, evaluation, inference, and XAI modules
  under `secureids/`
- Streamlit live demonstration entry point: `dashboard/app.py`
- Configuration files: `configs/`
- Design and audit documentation: `docs/`

## Current Safe Commands

PowerShell commands should be run from the V2 project root:

```powershell
C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
```

Correct virtual-environment activation from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Do not use parent-directory or bare environment paths such as
`..venv\Scripts\Activate.ps1`, `..\venv\Scripts\Activate.ps1`, or
`venv\Scripts\Activate.ps1`.

Dataset audit:

```bash
python -m secureids.cli audit-data --dataset all
```

Preprocessing dry-run validation:

```bash
python -m secureids.cli preprocess --dataset all --dry-run
```

Preprocessing execution:

```bash
python -m secureids.cli preprocess --dataset all --execute
```

The preprocessing safety check must pass before centralized training design.

Centralized baseline validation:

```bash
python -m secureids.cli validate-centralized-baselines
```

This validation command reads existing finalized centralized baseline artifacts
only. It does not train, retrain, evaluate models, load full arrays, or modify
checkpoints, metrics, histories, confusion matrices, manifests, preprocessing,
datasets, splits, thresholds, or model architecture.

FedAvg dry-run validation:

```bash
python -m secureids.cli federated-dry-run --dataset unsw --config configs/federated/unsw_nb15_fedavg.yaml
python -m secureids.cli federated-dry-run --dataset cicids --config configs/federated/cicids2018_fedavg.yaml
```

The FedAvg dry-run validates configuration, artifact references, feature counts,
and deterministic client distribution planning only. It does not run federated
training, evaluate on the test set, create federated checkpoints, or create
final federated metrics.

Live dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

The dashboard performs one-sample inference against saved selected hierarchical
federated checkpoints. It does not run training, preprocessing, full evaluation,
federated experiments, or attack/defense experiments.

Phase A evidence files:

- `results/experiments/federated_security/phase_a_signflip25_attack_defense_matrix.csv`
- `docs/experiments/PHASE_A_SIGNFLIP25_ATTACK_DEFENSE_SUMMARY.md`

## Reproducibility And Safety Rules

- Fit scalers, encoders, and imputers only on training data.
- Transform validation and test data only with train-fitted artifacts.
- Keep raw data under `data/raw/`.
- Keep generated processed data out of version control.
- Do not report invented values as real results.
- Do not claim final metrics until they are reproducible from scripts and configs.
- Keep failed or blocked experiments documented honestly.

## GitHub Policy

Do not push, create pull requests, create branches, or commit generated artifacts
without explicit approval. Raw datasets, processed arrays, private keys,
certificates, caches, checkpoints, model artifacts, and local scratch files must
not be committed.
