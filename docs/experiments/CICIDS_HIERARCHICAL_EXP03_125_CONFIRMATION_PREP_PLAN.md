# CICIDS Hierarchical EXP03 1.25 Confirmation Prep Plan

Generated: `2026-06-25`

Status: `confirmation config preparation only - NOT trained`

Experiment ID: `cicids_hierarchical_exp03_attack_loss_weight_125_confirmation`

Parent experiment ID: `cicids_hierarchical_exp03_attack_loss_weight_conservative_sweep`

## Purpose

Prepare the remaining EXP03 `attack_loss_weight = 1.25` confirmation configs for seeds `123` and `999`.
Seed42 was already trained during the EXP03 screening step, so these two configs complete the planned
three-seed confirmation set without overwriting the seed42 run.

## Current Baseline Status

The accepted CICIDS baseline remains unchanged:

- Checkpoint: `models/final/final_cicids_hierarchical.pt`
- Binary macro-F1: `0.972167`
- Attack-family macro-F1: `0.849111`
- Rare-class macro-F1: `0.716987`
- Correct attribution rate: `0.909008`
- Missed-as-benign rate: `0.053807`
- Benign false alarm rate: `0.010008`

The accepted baseline checkpoint and final result paths must not be overwritten.

## EXP01 Status

EXP01, `cicids_hierarchical_exp01_head2_mlp_capacity`, remains diagnostic only. It tested Head 2 MLP
capacity and was not promoted. EXP03 confirmation keeps the baseline linear Head 2 and does not reuse
the EXP01 MLP branch.

## EXP02 Status

EXP02 used `attack_loss_weight = 1.5` with baseline linear Head 2 across seeds `42`, `123`, and `999`.
It improved Head 2 / rare-class metrics but slightly worsened correct attribution and missed-as-benign,
so it is not the accepted CICIDS baseline.

EXP02 3-seed mean:

- Binary macro-F1: `0.973222`
- Attack-family macro-F1: `0.859641`
- Rare-class macro-F1: `0.751845`
- Correct attribution rate: `0.905235`
- Missed-as-benign rate: `0.056220`
- Benign false alarm rate: `0.007776`

## EXP03 Screening Result

EXP03 screening compared `attack_loss_weight = 1.25` against `1.35` using seed42.

The winner was selected using validation metrics only:

- `1.25` best validation hierarchical score: `0.909871`
- `1.35` best validation hierarchical score: `0.901976`
- `1.25` validation attack-family macro-F1: `0.847569`
- `1.35` validation attack-family macro-F1: `0.828328`

Test metrics were recorded for audit only and were not used to select the screening winner.

## Seed42 Already Completed

Do not overwrite seed42:

- Config: `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.yaml`
- Checkpoint: `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.pt`
- Results: `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42/`
- Report: `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED42_REPORT.md`
- Manifest: `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed42.json`

Seed42 test metrics, recorded for audit only:

- Binary macro-F1: `0.972019`
- Attack-family macro-F1: `0.867881`
- Rare-class macro-F1: `0.765155`
- Correct attribution: `0.909144`
- Missed as benign: `0.053081`
- Benign false alarm: `0.010484`

## Why Seed123 And Seed999 Are Needed

Seed42 is promising, but one seed is not enough to promote a CICIDS final model. Seeds `123` and `999`
are needed so EXP03 1.25 can be judged on the same three-seed basis used for EXP02:

- Seed42 already trained
- Seed123 to be trained manually later
- Seed999 to be trained manually later

The promotion decision must use the aggregate of seeds `42`, `123`, and `999`.

## Confirmation Configs

| Seed | Config | Checkpoint | Results |
| --- | --- | --- | --- |
| 123 | `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed123.yaml` | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed123.pt` | `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed123/` |
| 999 | `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.yaml` | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` | `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999/` |

Reports:

- `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED123_REPORT.md`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED999_REPORT.md`

Manifests:

- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed123.json`
- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed999.json`

## Manual PowerShell Commands

Seed123 confirmation:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed123.yaml --execute
```

Seed999 confirmation:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.yaml --execute
```

Do not add `--overwrite`.

## Expected Outputs After Each Confirmation Run

Each confirmation run should produce only its isolated experiment files:

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

No final checkpoint, seed42 artifact, EXP01 artifact, or EXP02 artifact should be overwritten.

## What To Paste Back After Seed123

Please paste:

- First 30-50 console lines
- Final 80-120 console lines
- File existence checks
- `test_metrics.json`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- Training manifest JSON

## What To Paste Back After Seed999

Please paste:

- First 30-50 console lines
- Final 80-120 console lines
- File existence checks
- `test_metrics.json`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- Training manifest JSON

## Post-Run Aggregation Plan

After seed123 and seed999 finish, aggregate seed42 + seed123 + seed999.

Report mean and sample standard deviation for:

- Binary macro-F1
- Attack-family macro-F1
- Rare-class macro-F1
- Correct attribution rate
- Missed-as-benign rate
- Benign false alarm rate

Compare against:

- Accepted CICIDS baseline
- EXP02 3-seed mean

Classify EXP03 1.25 as one of:

- `PROMOTE`
- `REJECT_AS_IMPROVEMENT`
- `DIAGNOSTIC_ONLY`
- `NEEDS_ADDITIONAL_ANALYSIS`

Do not promote automatically. Main control must decide after aggregate review.

## Promotion Criteria

Promote EXP03 1.25 only if:

- Mean attack-family macro-F1 improves meaningfully over baseline `0.849111`.
- Mean rare-class macro-F1 improves meaningfully over baseline `0.716987`.
- Mean correct attribution stays close to or above baseline `0.909008`.
- Mean missed-as-benign does not materially worsen from baseline `0.053807`.
- Binary macro-F1 stays strong.
- Benign false alarm rate stays acceptable.
- Results are reasonably stable across seeds.
- No leakage, fake metrics, path contamination, or overwrite issue appears.

## Rejection Criteria

Reject EXP03 1.25 as an improvement if:

- The three-seed mean Head 2 improvement disappears.
- Rare-class improvement collapses.
- Correct attribution drops materially below baseline.
- Missed-as-benign worsens materially.
- Results are unstable across seeds.
- Any leakage, fake metric, overwrite, or path contamination issue appears.

## No-Test-Tuning Rules

- Seed42 screening winner was selected by validation metrics only.
- Seed123 and seed999 checkpoints must be selected by validation only.
- Test metrics are recorded for audit and final comparison only.
- No preprocessing, taxonomy, split, threshold, or class weights may be tuned on test data.

## Next Decision Needed

Main control must approve manually running the seed123 and seed999 confirmation commands. After both
finish, main control must review the three-seed aggregate before any promotion decision.
