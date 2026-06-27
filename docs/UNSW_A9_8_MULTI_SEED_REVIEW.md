# UNSW A9.8 Multi-Seed Review

Status: `complete`

Task A9.8 completed the official multi-seed comparison between the accepted A9 linear Head 2 baseline and the A9.7 MLP Head 2 branch-capacity candidate.

## Review Answers

1. Did A9.8 complete? Yes. The A9.8 multi-seed aggregation status is `complete`.
2. Did A9.7 branch beat A9 linear by the approved promotion rule? No. `promote_a9_7_branch` is `False`.
3. Should A9.7 replace A9? No.
4. Current accepted UNSW baseline: A9 linear Head 2.
5. Should Head 2 branch capacity remain the next major UNSW improvement direction? No. It should be abandoned as the next major UNSW improvement direction.
6. Next safest professional decision: stop for main-review.

## Seed Results

| Model | Seed | Binary macro-F1 | Attack-family macro-F1 | Rare-class macro-F1 |
| --- | ---: | ---: | ---: | ---: |
| A9 linear Head 2 | 42 | 0.894488 | 0.500429 | 0.385669 |
| A9 linear Head 2 | 123 | 0.891399 | 0.478736 | 0.295782 |
| A9 linear Head 2 | 999 | 0.896035 | 0.505731 | 0.400399 |
| A9.7 MLP Head 2 branch | 42 | 0.898348 | 0.493667 | 0.354501 |
| A9.7 MLP Head 2 branch | 123 | 0.899810 | 0.511542 | 0.416245 |
| A9.7 MLP Head 2 branch | 999 | 0.901583 | 0.493259 | 0.344914 |

## Mean +/- Std

| Metric | A9 linear Head 2 | A9.7 MLP Head 2 branch | Branch minus linear |
| --- | ---: | ---: | ---: |
| Binary macro-F1 | 0.893974 +/- 0.002360 | 0.899914 +/- 0.001620 | +0.005940 |
| Attack-family macro-F1 | 0.494965 +/- 0.014303 | 0.499489 +/- 0.010440 | +0.004524 |
| Rare-class macro-F1 | 0.360617 +/- 0.056629 | 0.371887 +/- 0.038713 | +0.011270 |

## Promotion Rule Result

A9.7 branch does not pass the approved promotion rule. Although it slightly improves the three reviewed means, the attack-family macro-F1 mean gain is only `+0.004524`, which is below the required promotion margin. Therefore the branch-capacity model is not promoted.

## Lessons

A9.6 showed that increasing attack loss weight was not a reliable UNSW improvement path. It improved binary behavior but hurt attack-family and rare-class quality, so it remains a failed single-factor experiment.

A9.7 showed that adding MLP branch capacity to Head 2 can improve some signals, but the single-run result was not strong enough to replace A9.

A9.8 showed that the A9.7 branch is stable and not useless, but its average gains are too small for promotion. The formal multi-seed result confirms that branch capacity should not be the next major UNSW improvement direction.

## Official Decision

- A9.8 completed successfully.
- A9.7 branch does not pass the approved promotion rule.
- A9.7 branch should not replace A9.
- A9 remains the accepted UNSW baseline.
- Head 2 branch capacity should be abandoned as the next major UNSW improvement direction.
- Stop for main-review.
