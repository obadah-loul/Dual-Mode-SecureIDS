# CICIDS Hierarchical EXP02 3-Seed Prep Plan

Generated on: `2026-06-25`

Status: `prepared_only_not_run`

Experiment ID: `cicids_hierarchical_exp02_attack_loss_weight`

## Purpose

Prepare EXP02 as a controlled 3-seed CICIDS improvement experiment. The user
will run the three training commands manually after main-control approval.

This preparation does not run training, preprocessing, long evaluation, XAI,
Streamlit, Git, checkpoint writes, final metric creation, or result deletion.

## Baseline To Beat

Accepted CICIDS baseline:

- Checkpoint: `models/final/final_cicids_hierarchical.pt`
- Binary Head 1 macro-F1: `0.972167`
- Attack-family Head 2 macro-F1: `0.849111`
- Rare-class macro-F1: `0.716987`
- End-to-end correct attribution rate: `0.909008`
- Attack missed as benign rate: `0.053807`
- Benign false alarm rate: `0.010008`

## EXP01 Rejection Summary

EXP01, `cicids_hierarchical_exp01_head2_mlp_capacity`, is classified as
`REJECT_AS_IMPROVEMENT` and kept only as diagnostic experiment evidence.

EXP01 showed that simply increasing Head 2 capacity did not improve the main
CICIDS bottleneck. The reliable issue remained the large Head 2 confusion pair:

`DoS-SlowHTTPTest -> FTP-BruteForce: 11,796 / 20,941`

EXP01 improved binary false alarms but worsened attack-family macro-F1,
rare-class macro-F1, correct attribution, and missed attacks. EXP02 therefore
returns to the accepted baseline linear Head 2 and changes training signal
instead of architecture capacity.

## Why EXP02 Uses Attack Loss Weight 1.5

EXP02 tests the loss-balance hypothesis:

- Baseline `attack_loss_weight`: `1.0`
- EXP02 `attack_loss_weight`: `1.5`
- Binary loss weight remains `1.0`

The goal is to give attack-family classification more gradient pressure in the
shared encoder while preserving the baseline architecture. This is a single,
config-only controlled factor.

## Why EXP02 Returns To Baseline Linear Head 2

EXP01 already tested the MLP Head 2 capacity idea and rejected it as an
improvement. EXP02 should not combine failed capacity changes with loss pressure.
Returning to the baseline linear Head 2 keeps the comparison clean and tests
only whether stronger attack-family loss pressure helps.

## Why Three Seeds Are Used

Single-seed CICIDS deltas can be within noise, especially for rare classes. EXP02
uses seeds `42`, `123`, and `999` so the decision can compare mean and standard
deviation against the accepted baseline. Do not promote based on one lucky seed.

## Exact Config Paths

- `configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed42.yaml`
- `configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed123.yaml`
- `configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed999.yaml`

## Exact Checkpoint Paths

- `models/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed42.pt`
- `models/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed123.pt`
- `models/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed999.pt`

## Exact Result Folders

- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed42/`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed123/`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed999/`

## Exact Report Paths

- `docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_SEED42_REPORT.md`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_SEED123_REPORT.md`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_SEED999_REPORT.md`

## Manual Commands

Run manually only after main-control approval. Do not add `--overwrite`.

Seed 42:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed42.yaml --execute
```

Seed 123:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed123.yaml --execute
```

Seed 999:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed999.yaml --execute
```

## Expected Outputs Per Seed

Each seed should produce:

- `models/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>.pt`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/training_history.csv`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/test_metrics.json`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/binary_confusion_matrix.csv`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/attack_family_confusion_matrix.csv`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/per_class_attack_metrics.csv`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/rare_class_metrics.csv`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/hierarchical_routing_summary.json`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/training_config_snapshot.yaml`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/class_weight_snapshot.json`
- `results/experiments/cicids_hierarchical_exp02_attack_loss_weight_seed<seed>/model_summary.json`
- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp02_attack_loss_weight_seed<seed>.json`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_SEED<seed>_REPORT.md`

## What To Paste Back After Each Seed

After each manual seed run, paste:

- first 30-50 console lines
- final 80-120 console lines
- output file existence checks
- `test_metrics.json`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- training manifest JSON

## What To Paste Back After All Three Seeds

After all three seeds are complete, paste enough artifacts to compare mean and
standard deviation across:

- binary macro-F1
- attack-family macro-F1
- rare-class macro-F1
- end-to-end correct attribution
- attack missed as benign
- benign false alarm rate

Then classify EXP02 as one of:

- `PROMOTE`
- `REJECT_AS_IMPROVEMENT`
- `DIAGNOSTIC_ONLY`
- `NEEDS_ADDITIONAL_SEEDS_OR_ANALYSIS`

## Promotion Criteria

Promote EXP02 only if:

- Mean attack-family macro-F1 improves meaningfully over `0.849111`.
- Rare-class macro-F1 improves over `0.716987` or at least does not collapse.
- Mean binary Head 1 macro-F1 remains strong, preferably `>= 0.965`.
- Mean end-to-end correct attribution does not drop badly from `0.909008`.
- Mean attack missed-as-benign does not materially worsen from `0.053807`.
- Mean benign false alarm rate stays acceptable versus `0.010008`.
- No leakage, overwrite, path contamination, or fake metric issue appears.
- The result is stable enough across seeds; do not promote one lucky seed.

## Rejection Criteria

Reject or mark diagnostic only if:

- Mean Head 2 macro-F1 does not improve meaningfully.
- Rare-class macro-F1 collapses.
- Missed attacks materially worsen.
- Head 1 drops badly.
- Results are unstable across seeds.
- Any leakage, fake metric, overwrite, or path contamination issue appears.

## Safety Rules

- Do not run training until main-control approval.
- Do not add `--overwrite`.
- Do not tune on test data.
- Do not modify preprocessing, taxonomy, or dataset split.
- Do not overwrite the accepted baseline checkpoint or result folder.
- Do not overwrite EXP01 artifacts.
- Do not hide weak classes or fake improved metrics.

## Next Decision Needed

Main control must approve the user running EXP02 seed training manually.
