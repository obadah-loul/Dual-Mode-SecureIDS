> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW A9.8 Multi-Seed Comparison Plan

Task: A9.8-prep formal multi-seed A9 vs A9.7 comparison preparation

Status: prep only. No training, tests, compileall, aggregation, checkpoints, or final metrics were run.

## Decision Context

A9 remains the current accepted UNSW hierarchical baseline. A9.6 `head2_loss_weight` failed as a replacement experiment because it improved binary metrics while reducing Head 2 and rare-class quality. A9.7 `head2_branch_capacity` also failed as a single-run replacement candidate because attack-family macro-F1 and rare-class macro-F1 were below A9.

A9.7 nevertheless produced mixed signals: DoS and Backdoor F1 improved, attack-family accuracy improved slightly, and wrong-family routing improved slightly. Because single-run differences can be noisy, A9.8 prepares a fresh multi-seed comparison before fully abandoning the Head 2 branch-capacity direction.

## Path-Fix Status

A9.8 manual training was initially blocked before training started because the hierarchical config loader rejected the new safe checkpoint namespace `models/final/multiseed/`. A narrow path-validation fix now allows only the six approved A9.8 multiseed checkpoint patterns, their matching result folders, manifests, reports, and per-seed result files. Original A9, A9.6, and A9.7 checkpoint/result/manifest paths remain protected from A9.8 configs.

## Comparison Design

Compare two model families with fresh multiseed outputs only:

- `a9_linear`: A9 linear Head 2 baseline, based on `configs/training/unsw_nb15_hierarchical.yaml`.
- `a9_7_branch`: A9.7 MLP Head 2 branch-capacity model, based on `configs/training/unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml`.

Historical A9 and A9.7 runs remain context only. They are not counted as multiseed results.

Seeds:

- `42`
- `123`
- `999`

## Prepared Configs

A9 linear configs:

- `configs/training/multiseed/unsw_a9_linear_seed42.yaml`
- `configs/training/multiseed/unsw_a9_linear_seed123.yaml`
- `configs/training/multiseed/unsw_a9_linear_seed999.yaml`

A9.7 branch configs:

- `configs/training/multiseed/unsw_a9_7_branch_seed42.yaml`
- `configs/training/multiseed/unsw_a9_7_branch_seed123.yaml`
- `configs/training/multiseed/unsw_a9_7_branch_seed999.yaml`

## Controls Preserved

Both model families keep:

- corrected UNSW hierarchical protocol
- `input_dim: 192`
- `attack_head_dim: 9`
- `binary_loss_weight: 1.0`
- `attack_loss_weight: 1.0`
- train-only class weights
- class-weight cap `10.0`
- optimizer `adamw`
- learning rate `0.001`
- weight decay `0.0001`
- batch size `1024`
- max epochs `40`
- early stopping on `val_hierarchical_score`
- validation-only checkpoint selection with `0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1`
- final test once after best validation checkpoint selection
- no test-set tuning

The only model-family difference is Head 2 architecture:

- A9 linear keeps the default linear attack-family head.
- A9.7 branch keeps `attack_head_type: mlp`, `attack_head_hidden_dim: 128`, `attack_head_norm: true`, and `attack_head_dropout: 0.20`.

## Output Paths

All multiseed outputs are separate from original A9, A9.6, and A9.7 paths.

A9 linear checkpoints:

- `models/final/multiseed/unsw_a9_linear_seed42.pt`
- `models/final/multiseed/unsw_a9_linear_seed123.pt`
- `models/final/multiseed/unsw_a9_linear_seed999.pt`

A9.7 branch checkpoints:

- `models/final/multiseed/unsw_a9_7_branch_seed42.pt`
- `models/final/multiseed/unsw_a9_7_branch_seed123.pt`
- `models/final/multiseed/unsw_a9_7_branch_seed999.pt`

Result folders:

- `results/final/hierarchical/multiseed/unsw_a9_linear_seed42/`
- `results/final/hierarchical/multiseed/unsw_a9_linear_seed123/`
- `results/final/hierarchical/multiseed/unsw_a9_linear_seed999/`
- `results/final/hierarchical/multiseed/unsw_a9_7_branch_seed42/`
- `results/final/hierarchical/multiseed/unsw_a9_7_branch_seed123/`
- `results/final/hierarchical/multiseed/unsw_a9_7_branch_seed999/`

Each result folder is configured to contain:

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

Reports are configured under `docs/multiseed/`.

## Aggregation Method

After the user manually completes all six seed runs, run the aggregation script:

```powershell
.\.venv\Scripts\python.exe secureids\evaluation\compare_multiseed_hierarchical.py --config results\audits\unsw_a9_8_multiseed_prep.json
```

The script reads completed seed result folders and writes:

- `results/audits/unsw_a9_vs_a9_7_multiseed_summary.json`
- `results/audits/unsw_a9_vs_a9_7_multiseed_summary.csv`
- `docs/UNSW_A9_VS_A9_7_MULTI_SEED_REPORT.md`

It aggregates mean, sample standard deviation, and seed values for:

- binary macro-F1
- binary F1
- attack-family macro-F1
- attack-family accuracy
- rare-class macro-F1
- attack false negatives
- benign false positives
- per-class F1 for Analysis, Backdoor, DoS, Shellcode, Worms, Exploits, Generic, Reconnaissance, and Fuzzers

## Promotion Criteria

A9.7 branch-capacity can be promoted only if all of these hold:

- Mean attack-family macro-F1 is higher than A9 linear mean by at least `+0.015`.
- Mean rare-class macro-F1 is not worse than A9 linear mean by more than `0.010`.
- Mean binary macro-F1 remains at least `0.884`.
- Mean binary F1 remains at least `0.905`.
- Every branch seed keeps attack false negatives at or below `2,450`.
- No branch seed shows severe rare-class collapse.
- Improvement is not only from easy classes.
- No test tuning.
- No overwrite of original A9, A9.6, or A9.7 artifacts.

## Failure Criteria

A9.7 branch-capacity should be formally abandoned for UNSW if:

- Mean attack-family macro-F1 does not beat A9 linear by at least `+0.015`.
- Rare-class macro-F1 drops below the allowed tolerance.
- Binary safety gates fail.
- Attack false negatives exceed the safety gate in any branch seed.
- Rare-class collapse appears in any branch seed.
- Any improvement comes only from easy classes while Analysis, Backdoor, DoS, Shellcode, and Worms do not improve.
- Any configured path overwrites A9, A9.6, or A9.7 final artifacts.
- Any tuning or model selection uses test metrics.

## Manual Commands

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall secureids tests
```

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_hierarchical_multiseed_path_safety.py tests\test_hierarchical_training_config.py tests\test_hierarchical_trainer_safety.py -q
```

Optional full tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Manual training commands:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_linear_seed42.yaml --execute
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_linear_seed123.yaml --execute
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_linear_seed999.yaml --execute
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_7_branch_seed42.yaml --execute
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_7_branch_seed123.yaml --execute
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/multiseed/unsw_a9_7_branch_seed999.yaml --execute
```

Aggregation:

```powershell
.\.venv\Scripts\python.exe secureids\evaluation\compare_multiseed_hierarchical.py --config results\audits\unsw_a9_8_multiseed_prep.json
```

## Stop Condition

Stop after A9.8-prep. Do not run training, tests, compileall, aggregation, preprocessing, FedAvg, security, attacks, Trimmed Mean, XAI, dashboard, Git, or CICIDS until the user manually chooses to run the listed commands.
