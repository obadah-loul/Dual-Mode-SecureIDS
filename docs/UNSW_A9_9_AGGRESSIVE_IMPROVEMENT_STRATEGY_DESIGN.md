# UNSW A9.9 Aggressive Improvement Strategy Design

Status: `design_only_not_implemented`

This document designs the next professional UNSW improvement strategy after A9.6, A9.7, and A9.8 showed that simple attack-loss scaling and simple Head 2 branch capacity are not enough.

No experiment is implemented by this document. No training, testing, checkpoint creation, final metric creation, CICIDS work, FedAvg/security/attack/XAI/dashboard work, or Git operation is part of A9.9-design.

## Current Accepted State

A9 remains the accepted UNSW hierarchical baseline.

| Model | Binary macro-F1 | Attack-family macro-F1 | Rare-class macro-F1 |
| --- | ---: | ---: | ---: |
| A9 accepted baseline, seed 42 | 0.894488 | 0.500429 | 0.385669 |
| A9 linear multi-seed mean | 0.893974 +/- 0.002360 | 0.494965 +/- 0.014303 | 0.360617 +/- 0.056629 |
| A9.7 branch multi-seed mean | 0.899914 +/- 0.001620 | 0.499489 +/- 0.010440 | 0.371887 +/- 0.038713 |
| A9.7 branch minus A9 linear mean | +0.005940 | +0.004524 | +0.011270 |

A9.8 completed successfully and did not promote A9.7. The attack-family macro-F1 gain was only `+0.004524`, below the approved promotion requirement.

## Lessons So Far

A9.6 increased global attack loss pressure from 1.0 to 1.5. It failed replacement because simply pushing Head 2 harder improved binary behavior but hurt attack-family and rare-class quality.

A9.7 changed Head 2 from a linear classifier to a small MLP branch. It failed single-run replacement because extra branch capacity alone did not move the hard attack-family boundary enough.

A9.8 ran the formal multi-seed comparison. A9.7 was slightly better on average, but the improvement was too small to promote. This suggests branch capacity is stable and not useless, but not strong enough as the next major direction.

## Strategy Evaluation

| Strategy | Expected impact | Complexity | Main risk | Recommendation |
| --- | --- | --- | --- | --- |
| Attack-family specialist | High | Medium | Overfitting on fewer attack rows if not controlled | Recommended next controlled experiment |
| Two-stage attack-only fine-tuning | Medium-high | Medium-high | Fine-tuning instability and harder attribution | Backup, not first |
| Attack-row sampling | Medium | Low-medium | Calibration/prior distortion if used alone | Useful inside specialist protocol, not standalone |
| Head 2 focal loss | Low-medium | Low | Overfocusing noisy or rare examples; precision loss | Later ablation, not next |
| Hard-class specialist | Medium | High | Too many moving pieces and professor-facing complexity | Diagnostic only for now |
| Feature/preprocessing enhancement | Uncertain | Medium-high | Reproducibility and leakage burden late in project | Not next |

## Recommended Next Strategy

The recommended A9.9 strategy is an attack-family specialist.

The core idea is to keep A9 Head 1 as the accepted binary detector and train a separate attack-only classifier for attack-family prediction. The hierarchical story becomes:

`A9 binary detector routes detected attacks into a dedicated attack-family specialist.`

This is stronger than another small Head 2 tweak because it changes the task decomposition. The attack-family learner no longer spends capacity on benign-vs-attack separation. It learns only the boundaries among attack families.

## Scientific Design

The specialist must be trained only on UNSW training attack rows. Validation must use only validation attack rows. Test labels must be used only once for final evaluation after validation-based selection is frozen.

The A9 binary detector should remain fixed if the A9.9 experiment is specialist-only. This protects the accepted binary performance and gives a clean comparison:

- A9 Head 1 predicts benign or attack.
- If Head 1 predicts attack, the sample is routed to the attack-family specialist.
- If Head 1 predicts benign, the routed system does not assign an attack family.
- Report routed end-to-end metrics and oracle attack-row specialist metrics separately.

The routed metric answers whether the final system improves. The oracle attack-row metric diagnoses whether the specialist itself learned better attack-family boundaries when routing errors are removed.

## Why This Is Stronger Than Focal Loss Alone

Focal loss alone changes the loss shape but leaves the same mixed hierarchical training problem in place. A9.6 already showed that more Head 2 loss pressure can improve one part of the system while damaging attack-family or rare-class behavior.

The specialist strategy is stronger because it removes benign-vs-attack pressure from the attack-family learner, isolates attack-family boundaries, allows train-only attack-row sampling without changing the binary detector, and protects A9 Head 1 by keeping it unchanged.

Focal loss may still be useful later inside the specialist, but it should not be the next major controlled experiment by itself.

## Why This Is Stronger Than Simple Head 2 Branch Capacity

A9.7 and A9.8 already tested simple Head 2 branch capacity. It was stable and slightly positive, but the attack-family macro-F1 mean gain was only `+0.004524`.

The specialist strategy is stronger because it does more than increase branch size. It gives the attack-family model a cleaner training distribution, attack-only batches, validation-only selection, and a professor-facing hierarchical interpretation. It also avoids disturbing the accepted A9 binary detector.

## Rare-Class Protection

Rare-class macro-F1 should be protected by attack-only training and train-only class-balanced sampling or class-aware batching inside the specialist. Any weights or sampling probabilities must be computed from training attack labels only.

Rare-class gains should be treated cautiously. The immediate safety requirement should be no meaningful rare-class regression versus A9, with modest improvement as a desired outcome.

## Realistic Target

Attack-family macro-F1 above 0.9 is not realistic for the corrected UNSW setup. The dataset has difficult minority families, limited rare-class support, and routing errors from the binary detector in the end-to-end system.

A realistic short-term target is attack-family macro-F1 around `0.52-0.58`. A strong but still realistic result would be around `0.60` if the specialist and train-only sampling work well. Rare-class macro-F1 should be protected near the A9/A9.8 range and ideally modestly improved. Binary macro-F1 should remain close to A9 because Head 1 stays unchanged.

## A9.9-Prep Task If Approved

If main-review approves A9.9-prep, prepare an attack-family specialist experiment only. Do not train it during prep.

Exact proposed A9.9-prep task:

1. Create a controlled attack-family specialist experiment plan and config.
2. Keep A9 as the accepted binary router.
3. Prepare a separate attack-only specialist classifier trained on UNSW training attack rows only.
4. Prepare validation-only model selection and optional calibration using validation attack rows only.
5. Prepare routed evaluation: A9 Head 1 routes predicted attacks to the specialist.
6. Prepare oracle attack-row evaluation for diagnosis.
7. Predefine promotion criteria before any test evaluation.
8. Record leakage controls and artifact paths.
9. Stop before training.

Expected files if approved later may include:

- `configs/training/unsw_nb15_attack_family_specialist_a9_9.yaml`
- `secureids/models/attack_family_specialist.py`
- `secureids/training/attack_family_specialist_trainer.py`
- `secureids/evaluation/evaluate_attack_family_specialist.py`
- `docs/UNSW_A9_9_ATTACK_FAMILY_SPECIALIST_PLAN.md`
- `results/audits/unsw_a9_9_specialist_prep.json`

These files are not created by A9.9-design.

## Risks

The specialist can overfit because it sees fewer rows than the full hierarchical model. Class-balanced sampling can distort real class priors if it is not paired with careful validation and calibration. End-to-end routed metrics can still be limited by A9 Head 1 false negatives. Maintaining an extra specialist model adds evaluation and reporting complexity.

These risks are acceptable for a controlled A9.9 experiment because the strategy is scientifically clean, directly aligned with hierarchical IDS, and more likely to move attack-family macro-F1 than another minor Head 2 tweak.

## Main-Review Decision Needed

Main-review should decide whether to approve A9.9-prep for the attack-family specialist strategy. Approval should be for preparation only first, not immediate training.
