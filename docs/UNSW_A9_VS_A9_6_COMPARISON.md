# UNSW A9 vs A9.6 Comparison

Task: A9.6-review controlled experiment comparison

Status: complete. A9.6 trained safely into separate artifacts, but failed the main Head 2 improvement goal.

## Safety Boundary

- This review did not run training, preprocessing, validation/readiness pipelines, FedAvg, security, attacks, Trimmed Mean, XAI, dashboard, or Git commands.
- No checkpoints were created.
- No final model metrics were created.
- A9 final artifacts were not modified.
- A9.6 final artifacts were not modified.
- Only the A9 vs A9.6 comparison/audit outputs were written.

## Source Artifacts

A9 baseline:

- `results/final/hierarchical/unsw/test_metrics.json`
- `results/final/hierarchical/unsw/per_class_attack_metrics.csv`
- `results/final/hierarchical/unsw/rare_class_metrics.csv`
- `results/final/hierarchical/unsw/hierarchical_routing_summary.json`
- `results/final/hierarchical/unsw/training_history.csv`
- `results/audits/hierarchical_training_manifest_unsw_nb15.json`
- `docs/HIERARCHICAL_TRAINING_REPORT.md`

A9.6 experiment:

- `results/final/hierarchical/unsw_a9_6_head2_loss_weight/test_metrics.json`
- `results/final/hierarchical/unsw_a9_6_head2_loss_weight/per_class_attack_metrics.csv`
- `results/final/hierarchical/unsw_a9_6_head2_loss_weight/rare_class_metrics.csv`
- `results/final/hierarchical/unsw_a9_6_head2_loss_weight/hierarchical_routing_summary.json`
- `results/final/hierarchical/unsw_a9_6_head2_loss_weight/training_history.csv`
- `results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`
- `docs/HIERARCHICAL_TRAINING_REPORT_A9_6_HEAD2_LOSS_WEIGHT.md`

Planning inputs reviewed:

- `docs/UNSW_HIERARCHICAL_RESULT_QUALITY_AUDIT.md`
- `docs/UNSW_HIERARCHICAL_IMPROVEMENT_PLAN.md`
- `docs/UNSW_A9_6_HEAD2_LOSS_WEIGHT_EXPERIMENT_PLAN.md`
- `results/audits/unsw_hierarchical_result_quality_audit.json`
- `results/audits/unsw_a9_6_head2_loss_weight_prep.json`

## Final Decision

A9.6 must not replace A9.

A9 remains the current accepted UNSW hierarchical baseline. A9.6 should be retained as a completed controlled experiment showing that increasing `attack_loss_weight` from 1.0 to 1.5 did not improve Head 2.

## Headline Metric Deltas

| Metric | A9 | A9.6 | Delta | Result |
| --- | --- | --- | --- | --- |
| Binary macro-F1 | 0.894488 | 0.911474 | +0.016986 | Improved |
| Binary F1 | 0.910133 | 0.922570 | +0.012437 | Improved |
| Attack false negatives | 2,310 | 2,593 | +283 | Worse |
| Benign false positives | 6,186 | 4,581 | -1,605 | Improved |
| Attack-family accuracy | 0.766478 | 0.761140 | -0.005338 | Slightly worse |
| Attack-family macro-F1 | 0.500429 | 0.485478 | -0.014951 | Worse |
| Rare-class macro-F1 | 0.385669 | 0.362125 | -0.023544 | Worse |

## Validation And Best Epoch Comparison

| Metric | A9 | A9.6 | Delta |
| --- | --- | --- | --- |
| Best epoch | 35 | 36 | +1 |
| Best validation hierarchical score | 0.762364 | 0.757317 | -0.005047 |
| Validation binary macro-F1 | 0.933090 | 0.925114 | -0.007976 |
| Validation attack-family macro-F1 | 0.591638 | 0.589519 | -0.002119 |

A9.6 selected one epoch later than A9, but its validation hierarchical score, validation binary macro-F1, and validation attack-family macro-F1 were all lower. The test-set Head 2 decline is therefore consistent with validation behavior rather than a surprise test-only reversal.

## Success Criteria Results

| Criterion | A9 baseline | A9.6 value | Required | Result | Detail |
| --- | --- | --- | --- | --- | --- |
| Attack-family macro-F1 improves to at least 0.535000 | 0.500429 | 0.485478 | >= 0.535000 | FAIL | delta -0.014951 |
| Attack-family accuracy remains at least 0.760000 | 0.766478 | 0.761140 | >= 0.760000 | PASS | delta -0.005338 |
| Binary macro-F1 remains at least 0.884000 | 0.894488 | 0.911474 | >= 0.884000 | PASS | delta +0.016986 |
| Binary F1 remains at least 0.905000 | 0.910133 | 0.922570 | >= 0.905000 | PASS | delta +0.012437 |
| Attack false negatives remain <= 2,450 | 2,310 | 2,593 | <= 2,450 | FAIL | delta +283 |
| Benign false positives remain <= 7,000 | 6,186 | 4,581 | <= 7,000 | PASS | delta -1,605 |
| Rare-class macro-F1 remains at least 0.385669 | 0.385669 | 0.362125 | >= 0.385669 | FAIL | delta -0.023544 |
| Shellcode F1 does not drop by more than 0.030 | 0.439909 | 0.368421 | >= 0.409909 | FAIL | delta -0.071488 |
| Worms F1 does not drop by more than 0.050 | 0.331429 | 0.355828 | >= 0.281429 | PASS | delta +0.024399 |
| At least one of Analysis, Backdoor, or DoS improves without rare-class collapse | Analysis/Backdoor/DoS and rare macro-F1 | Analysis -0.004754; Backdoor -0.022230; DoS -0.050200; rare macro -0.023544 | one weak class F1 delta > 0 and rare macro-F1 not lower than A9 | FAIL | none of the three weak classes improved, and rare macro-F1 decreased |

A9.6 passed binary safety and benign false-positive gates, but failed the main replacement criteria. In particular, Head 2 macro-F1 decreased, attack false negatives exceeded the safety limit, rare-class macro-F1 decreased, Shellcode F1 dropped too much, and none of `Analysis`, `Backdoor`, or `DoS` improved.

## Per-Class Attack-Family Deltas

| Class | Support | A9 precision | A9 recall | A9 F1 | A9.6 precision | A9.6 recall | A9.6 F1 | F1 delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Generic | 18,871 | 0.998135 | 0.964072 | 0.980808 | 0.999725 | 0.963224 | 0.981135 | +0.000327 |
| Exploits | 11,132 | 0.778353 | 0.620823 | 0.690720 | 0.722419 | 0.678225 | 0.699625 | +0.008905 |
| Fuzzers | 6,062 | 0.836770 | 0.709502 | 0.767899 | 0.864533 | 0.650610 | 0.742470 | -0.025429 |
| DoS | 4,089 | 0.324080 | 0.482514 | 0.387737 | 0.305964 | 0.376376 | 0.337537 | -0.050200 |
| Reconnaissance | 3,496 | 0.803051 | 0.843249 | 0.822659 | 0.827626 | 0.829519 | 0.828571 | +0.005912 |
| Analysis | 677 | 0.037313 | 0.007386 | 0.012330 | 0.006615 | 0.008863 | 0.007576 | -0.004754 |
| Backdoor | 583 | 0.044875 | 0.162950 | 0.070370 | 0.035341 | 0.075472 | 0.048140 | -0.022230 |
| Shellcode | 378 | 0.307937 | 0.769841 | 0.439909 | 0.236486 | 0.833333 | 0.368421 | -0.071488 |
| Worms | 44 | 0.221374 | 0.659091 | 0.331429 | 0.243697 | 0.659091 | 0.355828 | +0.024399 |

The improvements were limited to `Generic`, `Exploits`, `Reconnaissance`, and `Worms`. The weaker families that motivated the experiment did not improve: `Analysis`, `Backdoor`, and `DoS` all declined. `Shellcode` also declined sharply.

## Rare-Class Deltas

| Class | Support | A9 precision | A9.6 precision | Precision delta | A9 recall | A9.6 recall | Recall delta | A9 F1 | A9.6 F1 | F1 delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shellcode | 378 | 0.307937 | 0.236486 | -0.071451 | 0.769841 | 0.833333 | +0.063492 | 0.439909 | 0.368421 | -0.071488 |
| Worms | 44 | 0.221374 | 0.243697 | +0.022323 | 0.659091 | 0.659091 | +0.000000 | 0.331429 | 0.355828 | +0.024399 |

Rare-class macro-F1 moved from 0.385669 to 0.362125, a delta of -0.023544. Shellcode recall improved, but Shellcode precision fell enough to cause a large F1 drop. Worms improved slightly, but not enough to offset Shellcode.

## Routing Deltas

| Routing metric | A9 | A9.6 | Delta |
| --- | --- | --- | --- |
| attack_detected_and_correctly_attributed | 32,674 | 32,237 | -437 |
| attack_detected_wrong_family | 10,348 | 10,502 | +154 |
| attack_missed_as_benign | 2,310 | 2,593 | +283 |
| benign_correctly_stopped | 30,814 | 32,419 | +1,605 |
| benign_flagged_as_attack | 6,186 | 4,581 | -1,605 |
| attack_detected_and_correctly_attributed_rate | 0.720771 | 0.711131 | -0.009640 |
| attack_detected_wrong_family_rate | 0.228271 | 0.231669 | +0.003397 |
| attack_missed_as_benign_rate | 0.050957 | 0.057200 | +0.006243 |
| benign_correctly_stopped_rate | 0.832811 | 0.876189 | +0.043378 |
| benign_flagged_as_attack_rate | 0.167189 | 0.123811 | -0.043378 |

A9.6 reduced benign false positives by 1,605, which explains much of the improved binary precision and binary macro-F1. However, it also increased attack misses by 283, reduced correctly attributed attacks by 437, and increased wrong-family attribution among detected attacks by 154. That is the wrong trade for replacing A9.

## Diagnosis

- Global Head 2 loss scaling was too blunt. More attack-family loss pressure did not create better family boundaries.
- The problem is not simply undertraining the shared encoder. A9.6 improved binary macro-F1 and binary F1, while Head 2 macro-F1 and rare-class macro-F1 declined.
- Weak and overlapping UNSW families need a more targeted Head 2 objective. `Analysis`, `Backdoor`, `DoS`, `Exploits`, and `Shellcode` remain boundary-sensitive.
- Rare-class precision/recall balance worsened for `Shellcode`: recall increased, but precision fell below the A9.6 failure threshold and F1 dropped by more than the allowed limit.
- Increasing `attack_loss_weight` further is not justified by this evidence.

## Next Experiment Recommendation

Recommend exactly one next controlled experiment: `head2_focal_loss`.

The recommended next change is to return `attack_loss_weight` to 1.0 and replace the Head 2 attack-row cross-entropy loss with focal loss only for attack-family classification, starting with `gamma = 1.5`. Binary loss, architecture, data protocol, train-only class weights, class-weight cap, thresholding, and separate output paths should remain unchanged.

This is safer than random retraining because it changes one mechanism that directly targets hard Head 2 examples, while preserving the A9 baseline and keeping the comparison interpretable.

Do not implement this next experiment until main-review/user approval.
