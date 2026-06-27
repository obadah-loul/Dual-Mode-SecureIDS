# UNSW Hierarchical Controlled Improvement Plan

Task: A9.5 planning output for one controlled A9.6 experiment

Status: plan only. Do not run A9.6 until main-review approval.

## Decision

A9 is a valid corrected-protocol UNSW hierarchical baseline. It should not be accepted as the final UNSW hierarchical result yet because the attack-family head remains too weak.

The next experiment should be exactly one controlled change:

`A9.6 head2_loss_weight`

## Why A9 Needs One More Controlled Experiment

A9 Head 1 binary detection is strong:

- Binary F1: 0.910133
- Binary macro-F1: 0.894488
- Attack recall: 0.949043
- Attack false negatives: 2,310

A9 Head 2 attack-family attribution is the limiting component:

- Attack-family accuracy: 0.766478
- Attack-family macro-F1: 0.500429
- Rare-class macro-F1: 0.385669

Weak Head 2 classes:

- `Analysis`: F1 0.012330
- `Backdoor`: F1 0.070370
- `Worms`: F1 0.331429
- `DoS`: F1 0.387737
- `Shellcode`: F1 0.439909

The routing summary confirms that the main problem is wrong-family attribution, not missed attack detection:

- Attack missed as benign: 2,310 / 45,332 = 0.0510
- Attack detected but wrong family: 10,348 / 45,332 = 0.2283

## Controlled Experiment Choice

Recommended experiment: increase Head 2 attack-family loss pressure.

Short name: `head2_loss_weight`

Hypothesis: A moderate increase in attack-family loss weight will give the shared encoder and Head 2 more pressure to learn minority and overlapping family boundaries, improving attack-family macro-F1 without materially weakening Head 1 binary detection.

## Exact A9.6 Planned Changes

Create a new config file only after approval:

`configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml`

Start from the A9 config:

`configs/training/unsw_nb15_hierarchical.yaml`

Change only these values:

```yaml
binary_loss_weight: 1.0
attack_loss_weight: 1.5
```

If the current config nests loss weights under a section, preserve the existing structure and change only the corresponding values. For example:

```yaml
loss:
  binary_loss_weight: 1.0
  attack_loss_weight: 1.5
```

or:

```yaml
loss_weights:
  binary: 1.0
  attack: 1.5
```

The value change is exact: binary stays at `1.0`; attack-family becomes `1.5`.

## Values That Must Stay Unchanged

A9.6 must keep these unchanged:

- Corrected UNSW train/validation/test protocol.
- Input dimension: 192.
- Attack head dimension: 9.
- Model family: `SecureIDSHierarchicalAdvancedNet`.
- Binary threshold.
- Attack class-weight cap.
- Class-weight generation method.
- Focal loss disabled.
- Shared encoder architecture.
- Head architecture.
- Optimizer family.
- Learning-rate schedule.
- Max epochs.
- Early stopping policy.
- Validation split.
- Final test source.

The experiment must be one-factor: Head 2 loss pressure only.

## Required Separate A9.6 Outputs

A9.6 must write to separate paths:

- Checkpoint: `models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt`
- Result folder: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/`
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`

A9.6 must not write into:

- `models/final/final_unsw_hierarchical.pt`
- `results/final/hierarchical/unsw/`
- `results/audits/hierarchical_training_manifest_unsw_nb15.json`

## Manual Command For Later

Do not run this during A9.5. After main-review approval, run the same training entrypoint used for A9 and replace only the config path with:

```powershell
configs\training\unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml
```

Planned command shape:

```powershell
python -m secureids.training.train_hierarchical --config configs\training\unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml
```

If the existing A9 command uses a project script instead of `python -m secureids.training.train_hierarchical`, keep the existing entrypoint and change only the config path.

## Success Criteria

A9.6 can be promoted over A9 only if all required criteria pass:

| Criterion | A9 baseline | A9.6 required |
| --- | ---: | ---: |
| Attack-family macro-F1 | 0.500429 | >= 0.535000 |
| Attack-family accuracy | 0.766478 | >= 0.760000 |
| Binary macro-F1 | 0.894488 | >= 0.884000 |
| Binary F1 | 0.910133 | >= 0.905000 |
| Attack false negatives | 2,310 | <= 2,450 |
| Benign false positives | 6,186 | <= 7,000 |
| Rare-class macro-F1 | 0.385669 | >= 0.385669 |
| Shellcode F1 | 0.439909 | >= 0.409909 |
| Worms F1 | 0.331429 | >= 0.281429 |

Additional qualitative success requirement:

At least one of `Analysis`, `Backdoor`, or `DoS` must improve without causing rare-class collapse.

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
- Any data protocol, model, class dimension, or output path differs from the approved plan.
- Any required metric file, confusion matrix, per-class report, rare-class report, routing summary, or manifest is missing.
- Training is unstable, incomplete, or produces NaN metrics.

## Candidate Comparison

| Option | Description | Benefit | Risk | A9.5 decision |
| --- | --- | --- | --- | --- |
| A | Increase `attack_loss_weight` | Direct Head 2 pressure with minimal code/config change | Can slightly hurt Head 1 if too aggressive | Recommended at 1.5 |
| B | Reweight checkpoint selection toward Head 2 | May choose a better Head 2 epoch | Does not change learned boundaries | Backup |
| C | Head 2 focal loss only | Focuses hard Head 2 examples | Can destabilize rare precision with weights | Backup |
| D | Adjust attack class-weight cap | Tunes rare precision/recall | Current rare recall is already high and precision is low | Not first |
| E | Scheduler/training schedule | May improve convergence | Does not directly address Head 2 objective pressure | Not first |
| F | Longer training | Simple continuation | Risks spending time for plateau-level gains | Not first |
| G | Capacity/regularization | May improve boundaries | Higher overfit and random-tuning risk | Not first |

## Comparison Method Against A9

Compare A9.6 only against the corrected A9 baseline:

- A9 checkpoint: `models/final/final_unsw_hierarchical.pt`
- A9 result folder: `results/final/hierarchical/unsw/`
- A9 manifest: `results/audits/hierarchical_training_manifest_unsw_nb15.json`

Required comparison files:

- `test_metrics.json`
- `binary_confusion_matrix.csv`
- `attack_family_confusion_matrix.csv`
- `per_class_attack_metrics.csv`
- `rare_class_metrics.csv`
- `hierarchical_routing_summary.json`
- `training_history.csv`
- A9.6 manifest

Old UNSW binary centralized and FedAvg baselines are legacy pre-correction results and must not be used as final UNSW comparisons.

## Rollback And Safety Rule

A9 remains the preserved baseline regardless of A9.6 outcome.

If A9.6 fails any safety criterion, do not overwrite A9 reports. Keep A9.6 as an experimental result only and document the failure. The next backup experiment, if approved later, should be checkpoint-selection reweighting or Head 2 focal loss, but not both at once.

## Manual Verification Commands

The user can run these after A9.5 to verify that the audit files exist and no A9.6 artifacts were created by this planning step:

```powershell
Write-Host "`n=== A9.5 result-quality audit outputs ==="
Get-Item docs\UNSW_HIERARCHICAL_RESULT_QUALITY_AUDIT.md
Get-Item docs\UNSW_HIERARCHICAL_IMPROVEMENT_PLAN.md
Get-Item results\audits\unsw_hierarchical_result_quality_audit.json
Get-Item results\audits\unsw_hierarchical_improvement_candidates.csv -ErrorAction SilentlyContinue
Get-Item results\audits\unsw_hierarchical_error_profile.csv -ErrorAction SilentlyContinue

Write-Host "`n=== A9.5 JSON summary ==="
$a = Get-Content results\audits\unsw_hierarchical_result_quality_audit.json -Raw | ConvertFrom-Json
$a | Select-Object status,a9_valid_baseline,a9_acceptable_as_final,recommended_a9_6_experiment,a9_6_should_train_now,training_was_run,checkpoints_created,final_metrics_created,a9_artifacts_modified,cicids_started,fedavg_security_xai_dashboard_started,git_operations_run | Format-List

Write-Host "`n=== A9.5 audit doc ==="
Get-Content docs\UNSW_HIERARCHICAL_RESULT_QUALITY_AUDIT.md -Raw

Write-Host "`n=== A9.5 improvement plan ==="
Get-Content docs\UNSW_HIERARCHICAL_IMPROVEMENT_PLAN.md -Raw

Write-Host "`n=== Confirm A9 checkpoint still exists and unchanged by A9.5 ==="
Get-Item models\final\final_unsw_hierarchical.pt

Write-Host "`n=== Confirm no A9.6 checkpoint was created ==="
Get-ChildItem models\final -Filter "*a9_6*" -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime

Write-Host "`n=== Confirm no A9.6 result folder was created ==="
Get-ChildItem results\final\hierarchical -Directory -Filter "*a9_6*" -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime
```
