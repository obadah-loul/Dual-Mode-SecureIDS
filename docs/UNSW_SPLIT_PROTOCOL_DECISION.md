> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW-NB15 Split Protocol Decision (Task A8.8 — resolves HIGH F1)

Status: `RESOLVED — standard protocol restored; UNSW artifacts regenerated`
Generated UTC: `2026-06-24`
Related: [PRE_TRAINING_CODE_AUDIT_REPORT.md](PRE_TRAINING_CODE_AUDIT_REPORT.md) (F1),
`results/audits/unsw_split_protocol_audit.json`

---

## 1. What A8.75 found

The A8.75 pre-training audit flagged HIGH finding **F1**: the UNSW-NB15 train/test
protocol was non-standard / swapped. The model was training on the **smaller**
partition and evaluating on the **larger** one — the reverse of the published
benchmark protocol.

## 2. Why it matters

- Training on the smaller partition discards roughly half of the available labeled
  training data, which is exactly the data rare classes need.
- It inverts the standard UNSW-NB15 protocol, so results are **not comparable** to
  published benchmarks.
- It shrank rare-class **training** support (Worms had only 40 train rows) and
  rare-class **validation** support (Worms had only 4 val rows), which also
  destabilizes validation macro-F1 used for checkpoint selection (A8.75 finding F3).

It is **not** a leakage bug — the partitions are disjoint — but it is a
result-quality and comparability bug, and the first real training is UNSW, so it
would have been baked into the headline model.

## 3. Verification (do not guess — verified from the raw files)

Row counts and label/`attack_cat` distributions were read directly from the local
raw CSVs:

| Local file | Data rows | Normal (0) | Attack (1) | Canonical role by row count |
| --- | ---: | ---: | ---: | --- |
| `UNSW_NB15_training-set.csv` | 82,332 | 37,000 | 45,332 | canonical **TEST** set (82,332) |
| `UNSW_NB15_testing-set.csv` | 175,341 | 56,000 | 119,341 | canonical **TRAIN** set (175,341) |

`attack_cat` distributions (attack rows):

| attack_cat | local training-set.csv (82,332) | local testing-set.csv (175,341) |
| --- | ---: | ---: |
| Generic | 18,871 | 40,000 |
| Exploits | 11,132 | 33,393 |
| Fuzzers | 6,062 | 18,184 |
| DoS | 4,089 | 12,264 |
| Reconnaissance | 3,496 | 10,491 |
| Analysis | 677 | 2,000 |
| Backdoor | 583 | 1,746 |
| Shellcode | 378 | 1,133 |
| Worms | 44 | 130 |

**Canonical reference.** The official UNSW-NB15 partition (Moustafa & Slay) is
`UNSW_NB15_training-set.csv` = 175,341 records and `UNSW_NB15_testing-set.csv` =
82,332 records. In this local copy the file **names are swapped** relative to the
canonical row counts. By canonical row count, the **175,341-row** partition is the
benchmark training set and the **82,332-row** partition is the benchmark test set.

## 4. Decision

Adopt the **standard UNSW-NB15 benchmark protocol**:

- **Train/val source:** the 175,341-row partition (local file
  `data/raw/unsw_nb15/UNSW_NB15_testing-set.csv`), split 85/15 into train/val,
  stratified on the binary label, `random_seed = 42`.
- **Final test source:** the 82,332-row partition (local file
  `data/raw/unsw_nb15/UNSW_NB15_training-set.csv`).

Files are assigned by **canonical row count**, not by their (misleading) local
file names. The raw files were **not** renamed, moved, or modified.

## 5. Which local file is used for what

| Role | Local file | Rows | Reason |
| --- | --- | ---: | --- |
| Train + Val | `UNSW_NB15_testing-set.csv` | 175,341 | canonical training partition (largest, benchmark train) |
| Final Test | `UNSW_NB15_training-set.csv` | 82,332 | canonical testing partition (benchmark test) |

Implemented by swapping `train_file`/`test_file` in
[configs/preprocessing/unsw_nb15_binary.yaml](../configs/preprocessing/unsw_nb15_binary.yaml),
with comments explaining the name/size mismatch.

## 6. Corrected split (regenerated artifacts)

| Split | Rows | Normal (0) | Attack (1) |
| --- | ---: | ---: | ---: |
| train | 149,039 | 47,600 | 101,439 |
| val | 26,302 | 8,400 | 17,902 |
| test | 82,332 | 37,000 | 45,332 |

Feature dimension changed **190 → 192** (the one-hot encoder, now fit on the larger
training partition, sees 2 additional categorical values; the dimension is
data-derived, not hardcoded). All hierarchical-path configs/code were updated to 192.

Rare-class support after correction (hierarchical Head 2):

| Class | train | val | test | before (train/val) |
| --- | ---: | ---: | ---: | --- |
| Shellcode | 965 | 168 | 378 | 316 / 62 |
| Worms | 109 | 21 | 44 | 40 / 4 |

Worms train support is now above the very-low (<50) threshold, and Worms validation
support rose from 4 to 21 — directly mitigating the A8.75 F3 selection-stability risk.

## 7. Old UNSW binary baselines are now legacy / pre-correction

The previous UNSW **binary** centralized and FedAvg results were trained on the old
(swapped, 190-feature) protocol. They are therefore **legacy / pre-correction and
not final**:

- `models/final/final_unsw_binary.pt` — legacy (190-dim, swapped protocol)
- `models/federated/fedavg_unsw_binary.pt` — legacy (190-dim, swapped protocol)
- `results/final/centralized/unsw_*.{json,csv}` — legacy binary metrics
- `results/federated/unsw/*` — legacy FedAvg binary metrics

These files were **preserved on disk** (not deleted). They describe a superseded
protocol and must not be presented as final V2 results. The corresponding legacy
preprocessor and metadata snapshots were archived under
`results/audits/legacy_pre_a8_8_unsw/` and
`models/final/preprocessors/legacy_pre_a8_8/`.

> Note: the legacy UNSW binary/FedAvg **configs and code constants** (e.g.
> `configs/training/unsw_nb15_binary.yaml`, `configs/federated/unsw_nb15_fedavg.yaml`,
> `secureids/federated/config.py`, `secureids/training/baseline_validation.py`)
> intentionally still reference `input_dim: 190` because they describe the legacy
> baseline. The corrected hierarchical pipeline uses `input_dim: 192`. CICIDS2018 is
> unchanged.

## 8. Which artifacts were regenerated

UNSW only (CICIDS2018 untouched):

- `data/processed/unsw_nb15/binary/*` (corrected protocol, 192 features) + preprocessor joblib
- `data/processed/unsw_nb15/hierarchical/*` (X copied from corrected binary, labels/masks rebuilt)
- `results/audits/preprocessing_manifest_unsw_nb15.json`, `preprocessing_audit_unsw_nb15.csv`
- `results/audits/hierarchical_preprocessing_audit_unsw_nb15.json`
- `results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json`
- `results/audits/hierarchical_class_weight_strategy_unsw_nb15.json`
- `results/audits/hierarchical_full_training_readiness_unsw_nb15.json`
- `results/audits/hierarchical_smoke_training_unsw_nb15.json` (non-final)

## 9. No-fake-results statement

- The partitions are disjoint; there is **no leakage**.
- Scaler, imputer, and one-hot encoder are fit on the **train split only**; validation
  and test are transformed with train-fitted artifacts (no refit on val/test).
- Class weights are computed from the **train split only**; no validation/test labels
  are used.
- No test-set tuning: checkpoint selection remains validation-only with a single
  final test (config `use_validation_only: true`, `select_by_test_metrics: false`).
- Old legacy binary results are explicitly marked legacy and are **not** presented as
  final hierarchical results.
- No full training, final checkpoints, or final metrics were created by A8.8.

## 10. This is the final UNSW protocol

This standard benchmark protocol (train on 175,341, test on 82,332) is the locked
protocol for all final V2 UNSW hierarchical training, evaluation, and federated work.
