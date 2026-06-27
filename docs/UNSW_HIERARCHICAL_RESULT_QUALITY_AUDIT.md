# UNSW Hierarchical Result-Quality Audit

Task: A9.5 UNSW hierarchical result-quality audit and controlled improvement plan

Status: audit complete as a documentation-only A9.5 planning artifact. No A9.6 training is authorized or performed by this task.

## Safety Boundary

A9.5 is an audit/planning step only.

- No training was intentionally run for A9.5.
- No A9.6 checkpoint was created.
- No A9.6 final metrics were created.
- The A9 checkpoint `models/final/final_unsw_hierarchical.pt` must remain preserved.
- The A9 result folder `results/final/hierarchical/unsw/` must remain preserved.
- CICIDS, FedAvg, security, attacks, Trimmed Mean, XAI, and dashboard work remain out of scope.
- A9.6 must not overwrite A9 artifacts.

## A9 Artifact Identity

- Final model family: `SecureIDSHierarchicalAdvancedNet`
- A9 checkpoint: `models/final/final_unsw_hierarchical.pt`
- A9 result folder: `results/final/hierarchical/unsw/`
- A9 manifest: `results/audits/hierarchical_training_manifest_unsw_nb15.json`

## Corrected UNSW Protocol

A9 follows the approved corrected UNSW protocol:

- Train/validation source: `data/raw/unsw_nb15/UNSW_NB15_testing-set.csv`
- Final test source: `data/raw/unsw_nb15/UNSW_NB15_training-set.csv`
- Corrected train rows: 149,039
- Corrected validation rows: 26,302
- Corrected test rows: 82,332
- Corrected input dimension: 192
- UNSW attack head dimension: 9

Conclusion: A9 is a valid corrected-protocol UNSW hierarchical baseline.

## Executive Decision

A9 should be accepted as a valid baseline, but it should not be treated as the final UNSW hierarchical result yet.

The binary head is strong and useful. The attack-family head is scientifically meaningful but not strong enough for a final advanced hierarchical IDS claim because macro-F1 is pulled down by very weak minority and overlapping families, especially `Analysis`, `Backdoor`, `DoS`, `Shellcode`, and `Worms`.

Recommended next step: one controlled A9.6 experiment named `head2_loss_weight`.

## A9 Training Summary

- Device: CUDA
- GPU: NVIDIA GeForce RTX 4070 Ti
- Epochs run: 40
- Best validation epoch: 35
- Best validation hierarchical score: 0.762364
- Validation binary macro-F1: 0.933090
- Validation attack-family macro-F1: 0.591638

The selected epoch is reasonable because the best validation score occurred late in training, close to the 40-epoch limit. The summary does not indicate an early collapse. It suggests late convergence or a plateau rather than a clear need for random longer training.

## Head 1 Binary Result

Final test binary metrics:

| Metric | Value |
| --- | ---: |
| Accuracy | 0.896808 |
| Precision | 0.874289 |
| Recall | 0.949043 |
| F1 | 0.910133 |
| Macro-F1 | 0.894488 |
| TN | 30,814 |
| FP | 6,186 |
| FN | 2,310 |
| TP | 43,022 |

Head 1 is strong enough to preserve as the safety anchor for A9.6. Attack recall is high at 0.949043, and only 5.10 percent of attack rows are missed as benign. The false-positive burden is visible: 6,186 benign rows are flagged as attacks, or 16.72 percent of benign test rows. That is not trivial, but in an IDS setting the current operating point favors attack capture over benign convenience, which is acceptable for a baseline.

Binary threshold conclusion: do not tune the binary threshold in A9.6. The safest next experiment should target Head 2 while keeping Head 1 behavior protected.

## Head 2 Attack-Family Result

Final test attack-family metrics:

| Metric | Value |
| --- | ---: |
| Attack rows evaluated | 45,332 |
| Attack-family accuracy | 0.766478 |
| Attack-family macro-F1 | 0.500429 |

Per-class attack-family F1:

| Attack family | F1 |
| --- | ---: |
| Generic | 0.980808 |
| Exploits | 0.690720 |
| Fuzzers | 0.767899 |
| DoS | 0.387737 |
| Reconnaissance | 0.822659 |
| Analysis | 0.012330 |
| Backdoor | 0.070370 |
| Shellcode | 0.439909 |
| Worms | 0.331429 |

Head 2 is the limiting component. Accuracy looks acceptable because large and easier families such as `Generic`, `Reconnaissance`, `Fuzzers`, and partially `Exploits` are handled well. Macro-F1 exposes the real quality issue: several families remain near-failing or unstable.

## Rare-Class Result

Rare-class macro-F1: 0.385669

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| Shellcode | 0.307937 | 0.769841 | 0.439909 | 378 |
| Worms | 0.221374 | 0.659091 | 0.331429 | 44 |

The rare-class profile shows a classic weighted-training tradeoff. Recall is relatively high for very small classes, especially `Shellcode` and `Worms`, but precision is low. This suggests class weighting helped the model notice rare attacks, but it also caused over-assignment into rare labels. That is better than total rare-class blindness, but it is not yet a polished final result.

## Hierarchical Routing Result

| Routing outcome | Count / total | Rate |
| --- | ---: | ---: |
| Benign correctly stopped | 30,814 / 37,000 | 0.8328 |
| Benign flagged as attack | 6,186 / 37,000 | 0.1672 |
| Attack detected and correctly attributed | 32,674 / 45,332 | 0.7208 |
| Attack detected but wrong family | 10,348 / 45,332 | 0.2283 |
| Attack missed as benign | 2,310 / 45,332 | 0.0510 |

The largest hierarchical error source is not missed attacks; it is detected attacks being assigned to the wrong family. This strongly points toward Head 2 class-boundary quality rather than Head 1 being the main blocker.

## Validation-To-Test Gap

| Metric | Validation | Test | Gap |
| --- | ---: | ---: | ---: |
| Binary macro-F1 | 0.933090 | 0.894488 | -0.038602 |
| Attack-family macro-F1 | 0.591638 | 0.500429 | -0.091209 |

The corrected UNSW protocol intentionally trains/validates from one original split and tests on the other. A validation-to-test drop is therefore expected. The binary gap is reasonable. The attack-family gap is larger and worth respecting: Head 2 generalizes less robustly than Head 1 under the corrected protocol.

This does not invalidate A9. It means A9 is a valid baseline with a clear improvement target.

## Weakest Classes And Likely Causes

Weakest classes by F1:

- `Analysis`: 0.012330
- `Backdoor`: 0.070370
- `Worms`: 0.331429
- `DoS`: 0.387737
- `Shellcode`: 0.439909

Likely causes:

- Severe class imbalance, especially for the rarest families.
- Feature overlap among UNSW families. `Analysis`, `Backdoor`, `DoS`, and portions of `Exploits` can share traffic patterns, which weakens clean family separation.
- Class weighting appears to improve rare-class recall while hurting precision.
- The shared encoder and validation objective may still be too dominated by binary detection, because Head 1 has a much easier and more separable objective.
- Model capacity is not the first suspected cause. The model already separates several families well, so the immediate issue is more likely objective pressure and minority-boundary calibration than gross undercapacity.
- Routing is not the main cause of weak Head 2 macro-F1, because only 5.10 percent of attacks are missed as benign while 22.83 percent are detected but attributed to the wrong family.

## Audit Questions

1. Is A9 a valid corrected-protocol UNSW hierarchical baseline?
   Yes. It uses the approved corrected train/validation/test sources, row counts, input dimension, attack-head dimension, and final hierarchical model family.

2. Is A9 good enough to accept as final UNSW hierarchical result?
   Not yet. It is a good baseline, but Head 2 macro-F1 of 0.500429 and near-failing `Analysis` and `Backdoor` results are too weak for the final advanced hierarchical claim.

3. What is strong in A9?
   Head 1 binary detection, attack recall, Generic classification, Reconnaissance classification, Fuzzers classification, and the low attack-missed-as-benign routing rate.

4. What is weak in A9?
   Attack-family macro-F1, minority-family precision, and family attribution for detected attacks.

5. Is Head 1 strong enough?
   Yes. Head 1 is strong enough to preserve, not the primary target for change.

6. Why is Head 2 weaker than Head 1?
   Head 2 must separate nine attack families with imbalance and semantic overlap, while Head 1 solves the easier benign-versus-attack split.

7. Which classes damage Head 2 macro-F1 most?
   `Analysis`, `Backdoor`, `Worms`, `DoS`, and `Shellcode`.

8. Are Analysis and Backdoor failing because of extreme overlap, class imbalance, weighting, routing, or model design?
   Most likely because of class imbalance and overlap, with weighting and routing as secondary effects. Routing cannot be the main explanation because the larger problem is wrong-family attribution among detected attacks.

9. Did class weighting improve rare-class recall at the cost of precision?
   Yes. Shellcode recall is 0.769841 with precision 0.307937, and Worms recall is 0.659091 with precision 0.221374.

10. Is the binary threshold causing too many false positives or acceptable attack recall?
    It causes a meaningful false-positive burden, but the attack recall is acceptable for an IDS baseline. A9.6 should not change the binary threshold.

11. Is the validation-to-test gap reasonable under corrected UNSW protocol?
    Yes for Head 1, and concerning but explainable for Head 2. The Head 2 gap confirms the improvement target.

12. Was the selected best validation epoch reasonable?
    Yes. Best epoch 35 of 40 is reasonable and does not suggest an obviously bad checkpoint choice.

13. Did training continue too long or not long enough?
    The summary suggests neither obvious overtraining nor obvious undertraining. Longer training alone is not the cleanest next experiment.

14. Does training history suggest underfitting, overfitting, or plateau?
    The available summary suggests late convergence or plateau near epoch 35. It does not justify random longer training as the first improvement.

15. Is the validation objective too balanced toward Head 1 instead of Head 2?
    It may be. The much stronger Head 1 can dominate model selection, but the more direct first test is to increase Head 2 training pressure moderately.

16. Does Head 2 need a stronger loss weight?
    Yes, as a controlled single-factor A9.6 experiment.

17. Should the attack-class weight cap be adjusted?
    Not first. The current rare-class profile already shows recall is being pushed; changing the cap first risks confusing precision/recall effects.

18. Should focal loss be tested for Head 2 only?
    It is a credible backup, but not the first A9.6 experiment. Focal loss plus existing class weights may destabilize rare precision.

19. Should learning rate, scheduler, or early stopping be adjusted?
    Not first. Those are lower-priority unless the loss-weight experiment shows plateau without Head 2 improvement.

20. Should model capacity or regularization be adjusted?
    Not first. Capacity changes have a higher risk of looking like broad tuning and may overfit minority families.

21. What is the safest single next experiment?
    Increase Head 2 loss pressure moderately with `attack_loss_weight = 1.5` while keeping Head 1, architecture, class weights, thresholding, and training schedule unchanged.

22. What exact success criteria should A9.6 use?
    See the A9.6 success section below.

23. What exact files/configs should A9.6 create or modify?
    A9.6 should create a separate config and separate outputs only. It should not overwrite A9 config, checkpoint, result directory, or manifest.

24. What should A9.6 not touch?
    It must not touch `models/final/final_unsw_hierarchical.pt`, `results/final/hierarchical/unsw/`, or the A9 manifest.

25. What would make A9.6 a failure even if one metric improves?
    Any material Head 1 safety regression, an increase in missed attacks beyond the safety threshold, rare-class precision collapse, or a result that improves only accuracy while macro-F1 and minority classes remain weak.

## Improvement Candidate Comparison

| ID | Option | Benefit | Risk | Decision |
| --- | --- | --- | --- | --- |
| A | Increase `attack_loss_weight` | Directly increases Head 2 pressure while keeping the architecture stable | Can hurt Head 1 if too large | Recommended at 1.5 |
| B | Reweight checkpoint selection toward Head 2 | May choose a better family-classification checkpoint | May not help if training objective never learned better Head 2 boundaries | Backup |
| C | Head 2 focal loss only | Targets hard attack-family examples | Can amplify instability when combined with class weights | Backup after A |
| D | Adjust attack class-weight cap | May tune rare precision/recall | Current evidence already shows recall-heavy rare behavior | Not first |
| E | Scheduler/training schedule change | May improve convergence without objective changes | Adds complexity and may not address Head 2 pressure | Not first |
| F | Longer training | Simple to run | Best epoch was already late but not clearly improving enough; risks small, noisy gain | Not first |
| G | Capacity/regularization change | Could improve hard boundaries | Higher overfit and tuning risk | Not first |

## Recommended A9.6 Experiment

Experiment name: `head2_loss_weight`

Hypothesis: A moderate increase in attack-family loss weight will improve Head 2 macro-F1 and weak-family attribution without materially degrading Head 1 binary safety.

Exact planned change:

- `binary_loss_weight: 1.0`
- `attack_loss_weight: 1.5`
- Keep attack class-weight cap unchanged.
- Keep focal loss disabled.
- Keep architecture unchanged.
- Keep binary threshold unchanged.
- Keep train/validation/test sources unchanged.
- Keep max epochs and early stopping policy unchanged unless the existing A9 config requires only output-path updates.
- Keep A9 result selection policy unchanged for this first controlled test.

Planned separate A9.6 artifacts:

- Config draft: `configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml`
- Checkpoint: `models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt`
- Result folder: `results/final/hierarchical/unsw_a9_6_head2_loss_weight/`
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`

A9.6 should not be implemented or trained until main-review approval.

## A9.6 Success Criteria

A9.6 may replace A9 as the preferred UNSW hierarchical result only if all safety gates pass:

- Attack-family macro-F1 improves from 0.500429 to at least 0.535000.
- Attack-family accuracy remains at least 0.760000.
- Binary macro-F1 remains at least 0.884000.
- Binary F1 remains at least 0.905000.
- Attack false negatives remain no worse than 2,450.
- Benign false positives remain no worse than 7,000.
- Rare-class macro-F1 remains at least 0.385669, or improves.
- `Shellcode` F1 does not drop by more than 0.030 absolute.
- `Worms` F1 does not drop by more than 0.050 absolute.
- At least one of `Analysis`, `Backdoor`, or `DoS` improves without causing rare-class collapse.

## A9.6 Failure Criteria

A9.6 is a failure even if one headline metric improves if any of the following happen:

- Binary macro-F1 drops below 0.884000.
- Binary F1 drops below 0.905000.
- Attack false negatives exceed 2,450.
- Benign false positives exceed 7,000.
- Attack-family macro-F1 improves only because strong classes improve while `Analysis`, `Backdoor`, `DoS`, `Shellcode`, and `Worms` collectively degrade.
- Rare-class recall improves but precision collapses further enough to lower rare-class macro-F1.
- `Shellcode` precision drops below 0.250000.
- `Worms` precision drops below 0.180000.
- The run changes data protocol, input dimension, attack-head dimension, model family, or A9 artifact paths.
- Any NaN, failed run, incomplete manifest, missing confusion matrix, or missing per-class metrics occur.

## Manual Verification Commands

The user can run these PowerShell commands later to verify the A9.5 files and safety state:

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
