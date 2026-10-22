> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW A9 vs A9.6 vs A9.7 Comparison

Task: A9.7-review official comparison and next-step decision

Status: complete. A9.7 trained safely into separate artifacts, but it did not beat A9 on the main Head 2 target and must not replace A9.

## Safety Boundary

- This review did not run training, tests, compileall, preprocessing, validation/readiness pipelines, FedAvg, security, attacks, Trimmed Mean, XAI, dashboard, Git, or CICIDS.
- No checkpoints were created.
- No final model metrics were created.
- A9, A9.6, and A9.7 final result artifacts were not modified.
- Only the requested A9/A9.6/A9.7 review outputs were written.

## Recap

A9 remains the accepted UNSW hierarchical baseline: binary macro-F1 0.894488, attack-family macro-F1 0.500429, rare-class macro-F1 0.385669.

A9.6 `head2_loss_weight` improved binary macro-F1 to 0.911474, but attack-family macro-F1 dropped to 0.485478 and rare-class macro-F1 dropped to 0.362125. It proved that more global Head 2 loss pressure is not the right lever.

A9.7 `head2_branch_capacity` added the non-linear Head 2 branch, increasing model parameters from 513,418 to 530,186. It improved binary macro-F1 to 0.898348, but attack-family macro-F1 was 0.493667 and rare-class macro-F1 was 0.354501, both below A9.

## Main Metric Comparison

| Metric | A9 | A9.6 | A9.7 | A9.6 vs A9 | A9.7 vs A9 | A9.7 vs A9.6 |
| --- | --- | --- | --- | --- | --- | --- |
| Binary macro-F1 | 0.894488 | 0.911474 | 0.898348 | +0.016986 | +0.003859 | -0.013126 |
| Binary F1 | 0.910133 | 0.922570 | 0.912501 | +0.012437 | +0.002367 | -0.010070 |
| Attack false negatives | 2,310 | 2,593 | 2,538 | +283 | +228 | -55 |
| Benign false positives | 6,186 | 4,581 | 5,669 | -1,605 | -517 | +1,088 |
| Attack-family accuracy | 0.766478 | 0.761140 | 0.767537 | -0.005338 | +0.001059 | +0.006397 |
| Attack-family macro-F1 | 0.500429 | 0.485478 | 0.493667 | -0.014951 | -0.006762 | +0.008189 |
| Rare-class macro-F1 | 0.385669 | 0.362125 | 0.354501 | -0.023544 | -0.031168 | -0.007624 |

## Best Epoch And Validation Comparison

| Metric | A9 | A9.6 | A9.7 |
| --- | --- | --- | --- |
| Best epoch | 35 | 36 | 17 |
| Epochs run | 40 | 40 | 23 |
| Best validation hierarchical score | 0.762364 | 0.757317 | 0.752137 |
| Validation binary macro-F1 | 0.933090 | 0.925114 | 0.927536 |
| Validation attack-family macro-F1 | 0.591638 | 0.589519 | 0.576739 |

A9.7 stopped after 23 epochs with best epoch 17. Its best validation hierarchical score was lower than A9, so the selected model was not stronger by the approved validation objective.

## A9.7 Success Criteria

| Criterion | A9 reference | A9.7 value | Required | Result |
| --- | --- | --- | --- | --- |
| Attack-family macro-F1 >= 0.530000 | 0.500429 | 0.493667 | >= 0.530000 | FAIL |
| Binary macro-F1 >= 0.884000 | 0.894488 | 0.898348 | >= 0.884000 | PASS |
| Binary F1 >= 0.905000 | 0.910133 | 0.912501 | >= 0.905000 | PASS |
| Attack false negatives <= 2,450 | 2,310 | 2,538 | <= 2,450 | FAIL |
| Benign false positives <= 7,000 | 6,186 | 5,669 | <= 7,000 | PASS |
| Rare-class macro-F1 >= 0.385669 | 0.385669 | 0.354501 | >= 0.385669 | FAIL |
| Shellcode F1 drop <= 0.030 | 0.439909 | 0.428808 | >= 0.409909 | PASS |
| Worms F1 drop <= 0.050 | 0.331429 | 0.280193 | >= 0.281429 | FAIL |
| At least one of Analysis, Backdoor, or DoS improves | weak-class F1 | Analysis -0.012330; Backdoor +0.006516; DoS +0.020798 | any delta > 0 | PASS |
| No A9/A9.6 overwrite | separate baseline paths | separate A9.7 paths | true | PASS |
| No test-set tuning or validation/test labels for weights | clean safety flags | clean safety flags | true | PASS |

A9.7 failed the replacement gates. It passed binary F1 gates, benign false positives, Shellcode F1 margin, weak-class improvement, separate paths, and no-test-tuning checks. It failed attack-family macro-F1, attack false negatives, rare-class macro-F1, and Worms F1 margin.

## Per-Class F1 Comparison

| Class | A9 F1 | A9.6 F1 | A9.7 F1 | A9.6 vs A9 | A9.7 vs A9 | A9.7 vs A9.6 |
| --- | --- | --- | --- | --- | --- | --- |
| Generic | 0.980808 | 0.981135 | 0.979605 | +0.000327 | -0.001203 | -0.001530 |
| Exploits | 0.690720 | 0.699625 | 0.684826 | +0.008905 | -0.005894 | -0.014799 |
| Fuzzers | 0.767899 | 0.742470 | 0.771375 | -0.025429 | +0.003476 | +0.028905 |
| DoS | 0.387737 | 0.337537 | 0.408535 | -0.050200 | +0.020798 | +0.070998 |
| Reconnaissance | 0.822659 | 0.828571 | 0.812773 | +0.005912 | -0.009886 | -0.015798 |
| Analysis | 0.012330 | 0.007576 | 0.000000 | -0.004754 | -0.012330 | -0.007576 |
| Backdoor | 0.070370 | 0.048140 | 0.076886 | -0.022230 | +0.006516 | +0.028746 |
| Shellcode | 0.439909 | 0.368421 | 0.428808 | -0.071488 | -0.011101 | +0.060387 |
| Worms | 0.331429 | 0.355828 | 0.280193 | +0.024399 | -0.051236 | -0.075635 |

A9.7 honestly shows mixed Head 2 behavior: `DoS` and `Backdoor` improved over A9, and `Fuzzers` improved slightly. But `Analysis` fell to zero, `Exploits`, `Generic`, `Reconnaissance`, `Shellcode`, and `Worms` declined, so total attack-family macro-F1 did not improve.

## Rare-Class Precision Recall F1

| Class | A9 P | A9.6 P | A9.7 P | A9.7 P vs A9 | A9 R | A9.6 R | A9.7 R | A9.7 R vs A9 | A9 F1 | A9.6 F1 | A9.7 F1 | A9.7 F1 vs A9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shellcode | 0.307937 | 0.236486 | 0.312048 | +0.004111 | 0.769841 | 0.833333 | 0.685185 | -0.084656 | 0.439909 | 0.368421 | 0.428808 | -0.011101 |
| Worms | 0.221374 | 0.243697 | 0.177914 | -0.043460 | 0.659091 | 0.659091 | 0.659091 | +0.000000 | 0.331429 | 0.355828 | 0.280193 | -0.051236 |

Rare-class macro-F1 declined from 0.385669 to 0.354501. Shellcode stayed inside the allowed F1 drop, but Worms narrowly failed its F1 floor and precision dropped below A9.

## Routing Comparison

| Routing metric | A9 | A9.6 | A9.7 | A9.7 vs A9 |
| --- | --- | --- | --- | --- |
| attack_detected_and_correctly_attributed | 32,674 | 32,237 | 32,593 | -81 |
| attack_detected_wrong_family | 10,348 | 10,502 | 10,201 | -147 |
| attack_missed_as_benign | 2,310 | 2,593 | 2,538 | +228 |
| benign_correctly_stopped | 30,814 | 32,419 | 31,331 | +517 |
| benign_flagged_as_attack | 6,186 | 4,581 | 5,669 | -517 |
| attack_detected_and_correctly_attributed_rate | 0.720771 | 0.711131 | 0.718984 | -0.001787 |
| attack_detected_wrong_family_rate | 0.228271 | 0.231669 | 0.225029 | -0.003243 |
| attack_missed_as_benign_rate | 0.050957 | 0.057200 | 0.055987 | +0.005030 |
| benign_correctly_stopped_rate | 0.832811 | 0.876189 | 0.846784 | +0.013973 |
| benign_flagged_as_attack_rate | 0.167189 | 0.123811 | 0.153216 | -0.013973 |

A9.7 slightly reduced wrong-family routing versus A9 and slightly improved attack-family accuracy, but it also increased missed attacks and reduced correctly attributed attacks. The routing gains were too small to overcome the macro-F1 and rare-class failures.

## Direct Answers

1. Did A9.7 beat A9? No. It improved binary macro-F1, but failed the main Head 2 target.
2. Did A9.7 pass success criteria? No.
3. Should A9.7 replace A9? No.
4. What did A9.6 prove? More global Head 2 loss pressure can improve binary behavior while hurting Head 2 and rare classes.
5. What did A9.7 prove? Extra Head 2 branch capacity alone did not beat A9 in this single run, though it produced a few weak-class/routing signals worth interpreting carefully.
6. Is the current best still A9? Yes.
7. What is the next safest professional step? Stop and ask main-review to decide on a formal multi-seed comparison plan before declaring the architecture direction failed or moving to another lever.

## Diagnosis

- A9.6 proved that increasing global Head 2 loss pressure was too blunt: binary improved, but attack-family and rare-class macro-F1 declined.
- A9.7 proved that adding a small non-linear Head 2 branch is not sufficient in a single seed to beat A9 on the main Head 2 target.
- The Head 2 branch did produce mixed signals: attack-family accuracy was slightly higher than A9, wrong-family routing was slightly lower, and DoS/Backdoor F1 improved.
- Those gains were outweighed by Analysis falling to zero, lower rare-class macro-F1, more attack false negatives, and a lower validation score.
- UNSW family overlap, especially among Analysis, Backdoor, DoS, and Exploits, likely dominates simple capacity changes.
- Head 2 capacity alone does not repair rare precision or weak-class boundaries; branch capacity may need multi-seed evaluation before a final architecture conclusion, but this A9.7 single run failed the gates.

## Official Decision

- A9 remains the current accepted UNSW hierarchical baseline.
- A9.6 remains a completed failed controlled experiment.
- A9.7 remains a completed failed controlled experiment.
- Do not replace A9 with A9.7.
- Do not start CICIDS.
- Do not start another experiment without main-review approval.

## Next Professional Direction

Recommended next direction: `formal_multi_seed_a9_vs_a9_7_branch_capacity_comparison_before_any_new_strategy`.

Do not prepare a new training prompt yet. The evidence is mixed enough that a formal multi-seed decision is more professional than immediately jumping to class-weight caps, focal loss, selection reweighting, feature changes, or two-stage fine-tuning. A9.7 did not pass gates, but it slightly improved DoS/Backdoor and wrong-family routing; a multi-seed review would determine whether that is signal or single-run noise.
