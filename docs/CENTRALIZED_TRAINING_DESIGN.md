> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CENTRALIZED_TRAINING_DESIGN.md

## 1. Purpose

This document defines the centralized training plan **before** any training
implementation begins. It exists to keep the next phase disciplined and
reproducible.

It prevents:

- messy, ad-hoc model experiments,
- hardcoded input dimensions baked into model code,
- fake or placeholder metrics presented as real results,
- checkpoint confusion between datasets and between draft and final weights.

This is a design-only document. No training is run, no checkpoints are created,
and no metrics are produced as part of this task. Implementation starts only
after this design is reviewed and approved (see Section 15).

## 2. Current Input Artifacts

Both datasets have completed leakage-safe preprocessing, and both passed their
final preprocessing safety check.

CICIDS2018:

- Processed path: `data/processed/cicids2018/binary`
- Input features: **77**
- Labels: binary `0` = Benign / Normal, `1` = Attack
- Preprocessing safety check: **PASS**
- Note: `Dst Port` and port-identifier variants were removed before training
  design.

UNSW-NB15:

- Processed path: `data/processed/unsw_nb15/binary`
- Input features: **190**
- Labels: binary `0` = Benign / Normal, `1` = Attack
- Preprocessing safety check: **PASS**
- Note: `id`, `label`, and `attack_cat` were removed from the final feature set.

Important:

The two datasets use **different feature spaces** (77 vs 190). Therefore the
model architecture is **shared**, but `input_dim` is **dataset-specific** and is
always loaded from dataset metadata/config - never hardcoded.

## 3. Training Scope

The next implementation phase covers **centralized training only**. Everything
else remains out of scope until centralized training produces real, reproducible
results.

In scope now:

- centralized (single-node) supervised training on each dataset separately.

Not in scope yet:

- no federated training yet,
- no secure communication yet,
- no Byzantine attacks yet,
- no robust aggregation yet,
- no XAI yet,
- no dashboard model demo yet,
- no final performance claims until real training results exist.

## 4. Model Strategy

There is exactly **one architecture name**: `SecureIDSNet`.

Rules:

- one architecture class, shared across both datasets,
- binary classifier,
- `input_dim` is loaded from dataset metadata/config (never hardcoded),
- `output_dim = 1` logit for binary classification,
- loss is `BCEWithLogitsLoss` (or an equivalent that operates on a single
  logit),
- no hardcoded `77` or `190` anywhere inside the model,
- dataset-specific final checkpoints are produced later:
  - `models/final/final_cicids_binary.pt`
  - `models/final/final_unsw_binary.pt`

Explanation:

Same architecture design, different `input_dim`, and a different trained
checkpoint per dataset. The architecture is the shared network blueprint; a
checkpoint is the dataset-specific trained weight set.

## 5. Proposed SecureIDSNet Architecture

A lightweight tabular neural network suitable for both datasets.

Suggested architecture:

- input layer: `input_dim` (77 for CICIDS2018, 190 for UNSW-NB15, from config)
- dense block 1: `Linear(input_dim, 256)` -> `BatchNorm1d(256)` -> `ReLU` ->
  `Dropout(p)`
- dense block 2: `Linear(256, 128)` -> `BatchNorm1d(128)` -> `ReLU` -> `Dropout(p)`
- dense block 3: `Linear(128, 64)` -> `ReLU` -> `Dropout(p)`
- output layer: `Linear(64, 1)` (raw logit; sigmoid applied only at evaluation /
  inference, never inside the loss path)

Why this design:

- lightweight enough to later run inside federated training rounds,
- simple enough for reproducibility and deterministic re-runs,
- stable for binary tabular intrusion detection,
- compatible with later XAI (permutation importance, gradient-based methods),
- intentionally **not** a heavy experimental model.

The hidden dimensions `[256, 128, 64]` and dropout are config-driven so the same
class serves both datasets without code changes.

Do not add extra model variants unless they are clearly marked as **future
optional** and kept out of the core training path.

## 6. Dataset Loading Design

Future training code loads, per dataset, from the processed directory:

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

`feature_names.json` is stored as an object and must be loaded as:

```python
feature_names = json.load(open(path))["feature_names"]
```

not as a direct top-level list.

Loading rules:

- use NumPy `mmap_mode` when useful for the large CICIDS2018 arrays
  (`X_train` is ~6.7M rows x 77), to avoid loading everything into memory at
  once,
- wrap arrays in a PyTorch `Dataset` and feed a `DataLoader`,
- CICIDS2018 batch size should be large enough for efficiency but memory-safe
  (default `4096`),
- UNSW-NB15 is small and can use normal in-memory loading (default batch size
  `1024`),
- `input_dim` is validated against `X_train.shape[1]` and against the config
  value at load time; a mismatch is a hard error.

## 7. Class Imbalance Handling

- compute the class distribution from `y_train` **only**,
- if imbalance is meaningful, use `pos_weight` for `BCEWithLogitsLoss`
  (`pos_weight = negatives / positives` from the training split),
- never compute class weighting from the validation or test splits,
- record the computed class distribution and the applied `pos_weight` in the
  training manifest.

## 8. Training Policy

- optimizer: `AdamW`
- learning rate: config-driven, default `1e-3`
- weight decay: config-driven, default `1e-4`
- max epochs: config-driven
- early stopping: based on validation macro-F1 (primary) or validation loss,
  with config-driven patience
- fixed seed: `42` (Python, NumPy, and PyTorch), set before model init and data
  shuffling
- save the **best** checkpoint based on the validation metric only,
- the test set is evaluated **exactly once**, after the final best checkpoint is
  selected,
- no tuning, threshold selection, or early-stopping decisions on the test set.

## 9. Metrics Policy

Allowed metrics, computed only after real training:

- accuracy
- precision
- recall
- F1
- macro-F1
- confusion matrix
- ROC-AUC (if stable)
- PR-AUC (if stable)

Rules:

- training metrics may be recorded during training (per-epoch history),
- validation metrics may guide early stopping and checkpoint selection,
- test metrics are computed only after the final best checkpoint is selected,
- **no placeholder or invented metrics are created in this design task.**

## 10. Output Structure For Future Training

Future centralized training writes to the following locations.

Final checkpoints - `models/final/`:

- `final_cicids_binary.pt`
- `final_unsw_binary.pt`

Centralized results - `results/final/centralized/`:

- `cicids_training_history.csv`
- `unsw_training_history.csv`
- `cicids_test_metrics.json`
- `unsw_test_metrics.json`
- `cicids_confusion_matrix.csv`
- `unsw_confusion_matrix.csv`
- `centralized_summary.md`

Training audits - `results/audits/`:

- `training_manifest_cicids2018.json`
- `training_manifest_unsw_nb15.json`

Documentation - `docs/`:

- `CENTRALIZED_TRAINING_REPORT.md`

Important:

**None** of these final result files are created during this design task. They
are listed here only to fix the future output contract.

## 11. Downstream Compatibility

The centralized training outputs are designed to feed every later stage cleanly:

- **Federated training baseline:** the same `SecureIDSNet` class and config-driven
  `input_dim` are reused as the per-client model; centralized test metrics become
  the comparison baseline for FedAvg.
- **Secure aggregation experiments:** the shared model definition and checkpoint
  format allow gradient/weight exchange and integrity hashing without redefining
  the model.
- **Byzantine attack experiments:** a clean, reproducible baseline checkpoint
  makes attack impact measurable against a known-good reference.
- **Robust aggregation (Trimmed Mean):** baseline metrics let robustness gains and
  losses be quantified honestly.
- **XAI:** the lightweight, single-logit architecture supports permutation
  importance and gradient-based local explanations; `feature_names.json` provides
  human-readable feature labels.
- **Streamlit dashboard:** the dashboard loads saved checkpoints, preprocessors,
  metrics JSON, history CSVs, and confusion matrices without running training.
- **Reproducibility reports:** training manifests record seed, config, class
  weights, and data shapes so every result is reproducible from scripts and
  configs.

## 12. CLI Plan

Future CLI commands (not implemented in this task):

```bash
python -m secureids.cli train-centralized --dataset cicids --config configs/training/cicids2018_binary.yaml
python -m secureids.cli train-centralized --dataset unsw --config configs/training/unsw_nb15_binary.yaml
python -m secureids.cli evaluate-centralized --dataset cicids
python -m secureids.cli evaluate-centralized --dataset unsw
```

These commands are **not** implemented during this design task. They define the
intended interface so implementation stays consistent with the existing
`audit-data` and `preprocess` subcommand style.

## 13. Safety Rules

- no training in this design task,
- no checkpoint creation in this design task,
- no metrics in this design task,
- no GitHub push,
- no direct CICIDS-to-UNSW frozen-model evaluation claim,
- no hardcoded input dimensions,
- no test-set tuning.

## 14. Manual Verification Plan

The user runs these manually later. **Do not run them as part of this task.**

Compile check:

```bash
python -m compileall -q secureids dashboard tests
```

Manual checks:

- confirm `docs/CENTRALIZED_TRAINING_DESIGN.md` exists,
- confirm `configs/training/cicids2018_binary.yaml` exists,
- confirm `configs/training/unsw_nb15_binary.yaml` exists,
- confirm no `.pt` / `.pth` / `.ckpt` files were created by this task,
- confirm no metrics files were created by this task.

## 15. Approval Gate

Centralized training implementation must **not** start until this design is
reviewed and approved by the user.
