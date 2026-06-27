# Hierarchical Smoke Training Plan

Status: `Task A6 non-final smoke-training plan only - smoke run not executed`

## 1. Purpose

The future hierarchical smoke-training pass is a tiny non-final execution check
for the `SecureIDS-HierarchicalAdvancedNet` training path. Its purpose is to
catch wiring problems before any approved full training task:

- dataset-specific dimensions,
- Head 1 and Head 2 tensor shapes,
- masked multi-task loss,
- one backward pass path,
- small validation/test batch metric plumbing,
- safety gates that prevent final artifact creation.

Smoke outputs must never be reported as final model results.

## 2. Smoke Configs

Created configs:

- `configs/training/smoke_cicids2018_hierarchical.yaml`
- `configs/training/smoke_unsw_nb15_hierarchical.yaml`

Both smoke configs point back to their full design configs:

- `configs/training/cicids2018_hierarchical.yaml`
- `configs/training/unsw_nb15_hierarchical.yaml`

## 3. Dataset-Specific Smoke Dimensions

| Dataset | Input dimension | Head 2 dimension |
| --- | ---: | ---: |
| CICIDS2018 | 77 | 14 |
| UNSW-NB15 | 190 | 9 |

The smoke pass must use the same `SecureIDSHierarchicalAdvancedNet` class as the
future full training path.

## 4. Sample And Batch Limits

Each smoke config is limited to:

- `train_samples: 4096`
- `val_samples: 2048`
- `test_samples: 2048`
- `batch_size: 512`
- `max_epochs: 1`
- `max_train_batches: 4`
- `max_eval_batches: 2`

These limits are intentionally small. The smoke pass is not a performance run.

## 5. Non-Final Output Policy

Smoke configs disable final artifacts:

- `save_checkpoint: false`
- `final_metrics: false`
- no `models/final` outputs
- no `results/final` outputs

Planned non-final smoke-plan locations:

- `results/audits/hierarchical_smoke_plan_cicids2018.json`
- `results/audits/hierarchical_smoke_plan_unsw_nb15.json`
- `docs/HIERARCHICAL_SMOKE_TRAINING_CHECK.md`

Task A6 does not create those smoke execution outputs. It only creates the plan
and validators.

## 6. Required Smoke Safety Checks

A future smoke runner must verify:

- The base full-training config loads.
- Smoke dataset, input dimension, and Head 2 dimension match the base config.
- Hierarchical processed artifacts exist.
- `max_epochs` is exactly `1`.
- Train and eval batch limits remain tiny.
- Checkpoint saving remains disabled.
- Final metrics remain disabled.
- Output paths are non-final.
- Smoke results are labeled non-final in every report.

## 7. Future Command Suggestions

These are future commands only. They were not executed in Task A6, and the
corresponding hierarchical smoke CLI is not implemented by A6.

```powershell
python -m secureids.cli smoke-train-hierarchical --dataset cicids --config configs/training/smoke_cicids2018_hierarchical.yaml --execute
python -m secureids.cli smoke-train-hierarchical --dataset unsw --config configs/training/smoke_unsw_nb15_hierarchical.yaml --execute
```

Future full training should remain separate from smoke training:

```powershell
python -m secureids.cli train-hierarchical --dataset cicids --config configs/training/cicids2018_hierarchical.yaml --execute
python -m secureids.cli train-hierarchical --dataset unsw --config configs/training/unsw_nb15_hierarchical.yaml --execute
```

Do not run these until a later task explicitly implements and approves the
hierarchical training or smoke-training CLI.

## 8. A6 Boundary

Task A6 did not:

- Run smoke training.
- Run full training.
- Run final evaluation.
- Create checkpoints.
- Create final metrics.
- Create smoke execution JSON/report outputs.
- Start hierarchical FedAvg.
- Start security, attacks, robust aggregation, XAI, or dashboard work.
- Modify V1.
- Modify existing centralized or federated binary artifacts.
