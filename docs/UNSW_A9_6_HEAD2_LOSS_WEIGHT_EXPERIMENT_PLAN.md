> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW A9.6 Head2 Loss Weight Experiment Plan

Task: A9.6-prep controlled UNSW `head2_loss_weight` experiment

Status: prepared only. A9.6 has not been run yet.

## Safety Boundary

- This document is a prep artifact only.
- No A9.6 training has been run.
- No A9.6 checkpoint has been created.
- No A9.6 final metrics have been created.
- A9 remains the preserved corrected-protocol UNSW hierarchical baseline.
- A9.6 must not overwrite A9 checkpoint, A9 result files, or the A9 manifest.
- CICIDS, FedAvg, security, attacks, Trimmed Mean, XAI, dashboard, and V1 are out of scope.

## A9 Baseline Result

A9 is a valid corrected-protocol UNSW hierarchical baseline using `SecureIDSHierarchicalAdvancedNet`.

- A9 checkpoint: `models/final/final_unsw_hierarchical.pt`
- A9 result folder: `results/final/hierarchical/unsw/`
- A9 manifest: `results/audits/hierarchical_training_manifest_unsw_nb15.json`
- Corrected train rows: 149,039
- Corrected validation rows: 26,302
- Corrected test rows: 82,332
- `input_dim`: 192
- `attack_head_dim`: 9

Training summary:

- Device: CUDA, NVIDIA GeForce RTX 4070 Ti
- Epochs run: 40
- Best validation epoch: 35
- Best validation hierarchical score: 0.762364
- Validation binary macro-F1: 0.933090
- Validation attack-family macro-F1: 0.591638

Final test Head 1 binary result:

- Accuracy: 0.896808
- Precision: 0.874289
- Recall: 0.949043
- F1: 0.910133
- Macro-F1: 0.894488
- TN: 30,814
- FP: 6,186
- FN: 2,310
- TP: 43,022

Final test Head 2 attack-family result:

- Attack rows evaluated: 45,332
- Attack-family accuracy: 0.766478
- Attack-family macro-F1: 0.500429
- Rare-class macro-F1: 0.385669

Weakest attack-family classes:

- `Analysis`: F1 0.012330
- `Backdoor`: F1 0.070370
- `Worms`: F1 0.331429
- `DoS`: F1 0.387737
- `Shellcode`: F1 0.439909

## A9.5 Diagnosis

A9.5 concluded that A9 is valid but not strong enough as the final UNSW hierarchical result. Head 1 binary detection is strong and should be preserved. Head 2 attack-family attribution is the blocker.

The routing profile supports this diagnosis:

- Benign correctly stopped: 30,814 / 37,000 = 0.8328
- Benign flagged as attack: 6,186 / 37,000 = 0.1672
- Attack detected and correctly attributed: 32,674 / 45,332 = 0.7208
- Attack detected but wrong family: 10,348 / 45,332 = 0.2283
- Attack missed as benign: 2,310 / 45,332 = 0.0510

The largest hierarchical error source is detected attacks being assigned to the wrong family, not attacks missed by Head 1.

## Why Head 2 Needs More Training Pressure

Head 1 solves a binary benign-versus-attack problem and is already strong. Head 2 must separate nine attack families with severe imbalance and feature overlap. A moderate increase in attack-family loss pressure gives the shared encoder and Head 2 more incentive to learn family boundaries while keeping the architecture, data protocol, class weights, optimizer, and checkpoint selection unchanged.

This is a controlled one-factor experiment, not random retraining.

## Exact One-Factor Change

New config:

`configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml`

Only approved training-objective change:

```yaml
loss:
  binary_loss_weight: 1.0
  attack_loss_weight: 1.5
```

The baseline A9 value for `attack_loss_weight` is `1.0`; A9.6 changes it to `1.5`.

## Values That Stay Unchanged

- Corrected UNSW train/validation/test protocol.
- Train/validation source: `data/raw/unsw_nb15/UNSW_NB15_testing-set.csv`.
- Final test source: `data/raw/unsw_nb15/UNSW_NB15_training-set.csv`.
- `input_dim: 192`.
- `attack_head_dim: 9`.
- Model family and architecture: `SecureIDSHierarchicalAdvancedNet`.
- Hidden dimensions, dropout, and normalization.
- Optimizer: AdamW.
- Learning rate: 0.001.
- Weight decay: 0.0001.
- Batch size: 1024.
- Max epochs: 40.
- Early stopping metric and patience.
- Validation-only checkpoint selection.
- Final test evaluated once after best validation checkpoint selection.
- Train-only class-weight strategy.
- Attack class-weight cap: 10.0.
- No validation/test labels for class weights.
- No oversampling.
- No test-set tuning.

## A9.6 Output Paths

- Checkpoint: `models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt`
- Result folder: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/`
- Training history: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/training_history.csv`
- Test metrics: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/test_metrics.json`
- Binary confusion matrix: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/binary_confusion_matrix.csv`
- Attack-family confusion matrix: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/attack_family_confusion_matrix.csv`
- Per-class attack metrics: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/per_class_attack_metrics.csv`
- Rare-class metrics: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/rare_class_metrics.csv`
- Routing summary: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/hierarchical_routing_summary.json`
- Config snapshot: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/training_config_snapshot.yaml`
- Class-weight snapshot: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/class_weight_snapshot.json`
- Model summary: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/model_summary.json`
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`
- Training report: `docs/HIERARCHICAL_TRAINING_REPORT_A9_6_HEAD2_LOSS_WEIGHT.md`

## Trainer And CLI Path Support

The CLI accepts a user-supplied hierarchical config path through:

```powershell
--config configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml
```

The trainer reads these config-defined output paths:

- `outputs.checkpoint`
- `outputs.result_dir`
- `outputs.training_history_csv`
- `outputs.test_metrics_json`
- `outputs.binary_confusion_matrix_csv`
- `outputs.attack_family_confusion_matrix_csv`
- `outputs.per_class_attack_metrics_csv`
- `outputs.rare_class_metrics_csv`
- `outputs.manifest_json`
- `outputs.report_md`
- `outputs.hierarchical_routing_summary_json`
- `outputs.training_config_snapshot_yaml`
- `outputs.class_weight_snapshot_json`
- `outputs.model_summary_json`

Prep change made: the trainer was adjusted to honor config-defined report and snapshot-style output paths, and the config loader was adjusted to accept controlled experiment checkpoint names such as `final_unsw_hierarchical_a9_6_head2_loss_weight.pt`.

The trainer still refuses to overwrite existing planned final output files unless `--overwrite` is supplied.

## Success Criteria

A9.6 may replace A9 as the preferred UNSW hierarchical result only if all safety gates pass:

- Attack-family macro-F1 improves from 0.500429 to at least 0.535000.
- Attack-family accuracy remains at least 0.760000.
- Binary macro-F1 remains at least 0.884000.
- Binary F1 remains at least 0.905000.
- Attack false negatives remain <= 2,450.
- Benign false positives remain <= 7,000.
- Rare-class macro-F1 remains at least 0.385669.
- Shellcode F1 does not drop by more than 0.030.
- Worms F1 does not drop by more than 0.050.
- At least one of `Analysis`, `Backdoor`, or `DoS` improves without rare-class collapse.

## Failure Criteria

A9.6 fails even if one metric improves if any of these occur:

- Binary macro-F1 drops below 0.884000.
- Binary F1 drops below 0.905000.
- Attack false negatives exceed 2,450.
- Benign false positives exceed 7,000.
- Attack-family macro-F1 improves by less than 0.020 absolute.
- Attack-family macro-F1 improves only through already-strong classes while weak classes degrade.
- Rare-class macro-F1 drops below 0.385669.
- Shellcode precision drops below 0.250000.
- Worms precision drops below 0.180000.
- `Analysis` and `Backdoor` remain near zero while other classes absorb the improvement.
- Data protocol changes.
- `input_dim` changes.
- `attack_head_dim` changes.
- Model family changes.
- A9 output paths are overwritten.
- Any required metric file, confusion matrix, per-class report, rare-class report, routing summary, or manifest is missing.
- Training is unstable, incomplete, or produces NaN metrics.

## No-Overwrite Rules

A9.6 must not overwrite:

- `models/final/final_unsw_hierarchical.pt`
- `results/final/hierarchical/unsw/`
- `results/audits/hierarchical_training_manifest_unsw_nb15.json`
- `docs/HIERARCHICAL_TRAINING_REPORT.md`

The A9.6 config uses separate paths for every planned output.

## No-Test-Tuning Rules

- Test metrics must not affect checkpoint selection.
- Class weights must be computed from train labels only.
- Validation/test labels must not be used for class weights.
- The final test split must be evaluated once after the best validation checkpoint has been selected.
- Do not tune thresholds or hyperparameters from A9.6 test results.

## Manual Commands For Later

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall secureids tests
```

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_hierarchical_weighted_loss.py tests\test_hierarchical_trainer_safety.py tests\test_hierarchical_metrics.py -q
```

Optional full tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

A9.6 training command after approval:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml --execute
```

## Manual Verification Commands After Training

```powershell
Write-Host "`n=== A9.6 checkpoint ==="
Get-Item models\final\final_unsw_hierarchical_a9_6_head2_loss_weight.pt

Write-Host "`n=== A9.6 result files ==="
Get-ChildItem results\final\hierarchical\unsw_a9_6_head2_loss_weight -Force | Select-Object Name,Length,LastWriteTime

Write-Host "`n=== A9.6 manifest ==="
Get-Item results\audits\hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json
Get-Content results\audits\hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json -Raw

Write-Host "`n=== A9.6 test metrics ==="
Get-Content results\final\hierarchical\unsw_a9_6_head2_loss_weight\test_metrics.json -Raw

Write-Host "`n=== A9.6 rare-class metrics ==="
Import-Csv results\final\hierarchical\unsw_a9_6_head2_loss_weight\rare_class_metrics.csv | Format-Table -AutoSize

Write-Host "`n=== A9.6 per-class attack metrics ==="
Import-Csv results\final\hierarchical\unsw_a9_6_head2_loss_weight\per_class_attack_metrics.csv | Format-Table -AutoSize

Write-Host "`n=== Confirm A9 baseline checkpoint still exists ==="
Get-Item models\final\final_unsw_hierarchical.pt

Write-Host "`n=== Confirm A9 baseline result folder still exists ==="
Get-ChildItem results\final\hierarchical\unsw -Force | Select-Object Name,Length,LastWriteTime

Write-Host "`n=== Confirm no CICIDS hierarchical checkpoint ==="
Test-Path models\final\final_cicids_hierarchical.pt

Write-Host "`n=== Confirm no hierarchical FedAvg checkpoints ==="
Test-Path models\federated\fedavg_cicids_hierarchical.pt
Test-Path models\federated\fedavg_unsw_hierarchical.pt
```

## Stop Condition

Stop after A9.6-prep and wait for main-review/user approval. Do not run A9.6 during prep.

