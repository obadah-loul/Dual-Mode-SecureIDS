# CICIDS Hierarchical EXP03 Screening Prep Plan

Generated: `2026-06-25`

Status: `config preparation only - NOT trained`

Experiment ID: `cicids_hierarchical_exp03_attack_loss_weight_conservative_sweep`

## Purpose

EXP03 screens two conservative attack-family loss weights to search for a better balance than EXP02.
EXP02 showed that `attack_loss_weight = 1.5` improved Head 2 and rare-class metrics, but slightly
worsened correct attribution and missed-as-benign behavior. EXP03 tests whether smaller weights can keep
most of the Head 2 / rare-class signal while recovering routing behavior.

## Current Baseline Status

The accepted CICIDS baseline remains:

- Checkpoint: `models/final/final_cicids_hierarchical.pt`
- Binary macro-F1: `0.972167`
- Attack-family macro-F1: `0.849111`
- Rare-class macro-F1: `0.716987`
- Correct attribution rate: `0.909008`
- Missed-as-benign rate: `0.053807`
- Benign false alarm rate: `0.010008`

The baseline checkpoint must not be overwritten.

## EXP02 Status

EXP02 used baseline linear Head 2 with `binary_loss_weight = 1.0` and
`attack_loss_weight = 1.5` over seeds `42`, `123`, and `999`.

EXP02 aggregate:

- Binary macro-F1 mean: `0.973222`
- Attack-family macro-F1 mean: `0.859641`
- Rare-class macro-F1 mean: `0.751845`
- Correct attribution rate mean: `0.905235`
- Missed-as-benign rate mean: `0.056220`
- Benign false alarm rate mean: `0.007776`

EXP02 is evidence that attack-loss weighting can improve Head 2 / rare-class behavior, but it is not
promoted because routing became weaker: correct attribution moved below baseline and missed-as-benign
moved above baseline.

## Why 1.25 And 1.35

The controlled factor is only `attack_loss_weight`.

- `1.25` brackets the low side of the likely useful range. It has the best chance of recovering routing
  while retaining some rare-class gain.
- `1.35` brackets the high side. It stays closer to EXP02 and may retain more Head 2 / rare-class
  improvement while easing the routing regression.

Both screening configs keep:

- Baseline linear Head 2
- `binary_loss_weight = 1.0`
- `seed = 42`
- CICIDS preprocessing, taxonomy, split, and processed artifact paths unchanged
- Train-only class weights
- Validation-only checkpoint selection
- Final test once after best validation checkpoint
- Fixed threshold behavior at `0.5`
- No test tuning
- No `--overwrite`

## Why 1.15 Is Not Screened Now

`1.15` is too close to the baseline weight of `1.0`. It is more likely to give back the EXP02 rare-class
signal before proving whether a useful knee exists between baseline and `1.5`. If both `1.25` and `1.35`
fail by losing the Head 2 / rare-class signal, main control can decide whether a lower value is worth a
separate run.

## Why 1.75 Is Not Screened Now

`1.75` moves in the wrong direction for EXP03's goal. At `1.5`, missed-as-benign already worsened and the
hard pair did not improve reliably across seeds. A more aggressive attack loss is more likely to worsen
routing without providing a dependable Head 2 payoff.

## Prepared Screening Runs

| Weight | Seed | Config | Checkpoint | Results |
| --- | --- | --- | --- | --- |
| 1.25 | 42 | `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.yaml` | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.pt` | `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42/` |
| 1.35 | 42 | `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_135_seed42.yaml` | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_135_seed42.pt` | `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_135_seed42/` |

Reports:

- `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED42_REPORT.md`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_135_SEED42_REPORT.md`

Manifests:

- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed42.json`
- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_135_seed42.json`

## Manual PowerShell Commands

EXP03 `1.25` seed42 screen:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.yaml --execute
```

EXP03 `1.35` seed42 screen:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_135_seed42.yaml --execute
```

Do not add `--overwrite`.

## Expected Outputs After Each Run

Each run should produce only its isolated experiment files:

- Checkpoint under `models/experiments/`
- `training_history.csv`
- `test_metrics.json`
- `binary_confusion_matrix.csv`
- `attack_family_confusion_matrix.csv`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- `training_config_snapshot.yaml`
- `class_weight_snapshot.json`
- `model_summary.json`
- Manifest under `results/audits/`
- Report under `docs/experiments/`

No final checkpoint, final results folder, EXP01 artifact, or EXP02 artifact should be overwritten.

## What To Paste Back After Each Screening Run

Please paste:

- First 30-50 console lines
- Final 80-120 console lines
- Output file existence checks
- `test_metrics.json`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- Training manifest JSON
- `training_history.csv` summary if useful

## Validation-Only Winner Selection Rule

The screening winner must be chosen using validation metrics only.

Primary selection metric:

`best_val_hierarchical_score = 0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1`

Secondary validation guardrails:

- Validation attack-family macro-F1 should preserve most of the EXP02 Head 2 signal.
- Validation binary macro-F1 should stay strong.
- If one value clearly improves validation score while not hurting validation binary behavior, choose it.
- If validation metrics are close, prefer `1.25` because the EXP03 goal is routing recovery.

Do not choose the screening winner using test metrics.

## Recording Test Metrics Without Test Tuning

The trainer may produce test metrics after each screening run. Record those metrics in the audit and later
final review, but do not use them to choose between `1.25` and `1.35`. The test split remains a final
reporting split, not a selection split.

## Winner Outcomes

If `1.25` wins:

- Stop and request main-control approval to prepare `1.25` confirmation configs for seeds `123` and `999`.
- Reuse the seed42 screening run only because the winner was selected by validation.

If `1.35` wins:

- Stop and request main-control approval to prepare `1.35` confirmation configs for seeds `123` and `999`.
- Reuse the seed42 screening run only because the winner was selected by validation.

If neither is better:

- Do not continue the loss sweep automatically.
- Keep the accepted baseline as the CICIDS final model.
- Ask main control whether to stop the loss-weight line or move to a separate validation-only threshold
  calibration experiment.

## No-Test-Tuning Rules

- Checkpoints are selected by validation only.
- The `1.25` vs `1.35` screening decision is selected by validation only.
- Test metrics may be recorded but must not choose the screening winner.
- Class weights remain train-only.
- No preprocessing, taxonomy, threshold, or split is tuned against test data.

## Next Decision Needed

Main control must approve running the two EXP03 screening training commands manually. After both runs,
main control must approve any seed123/seed999 confirmation configs for the validation-selected winner.
