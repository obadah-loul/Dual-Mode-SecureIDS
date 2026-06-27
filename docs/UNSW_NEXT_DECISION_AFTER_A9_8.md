# Next Decision After A9.8

Status: `stop_for_main_review`

A9.8 completed successfully. The official multi-seed comparison did not promote the A9.7 MLP Head 2 branch-capacity model over the A9 linear Head 2 baseline.

## Official Decision

- A9.7 branch should not replace A9.
- A9 remains the accepted UNSW baseline.
- Head 2 branch capacity should be abandoned as the next major UNSW improvement direction.
- Stop for main-review.

## Evidence

| Metric | A9 linear Head 2 | A9.7 MLP Head 2 branch | Branch minus linear |
| --- | ---: | ---: | ---: |
| Binary macro-F1 | 0.893974 +/- 0.002360 | 0.899914 +/- 0.001620 | +0.005940 |
| Attack-family macro-F1 | 0.494965 +/- 0.014303 | 0.499489 +/- 0.010440 | +0.004524 |
| Rare-class macro-F1 | 0.360617 +/- 0.056629 | 0.371887 +/- 0.038713 | +0.011270 |

The branch-capacity model made small mean gains, but it did not meet the approved promotion rule. The attack-family macro-F1 gain was only `+0.004524`, below the required promotion margin.

## Next Safest Professional Decision

Do not start another UNSW improvement, CICIDS, focal loss, class-weight changes, FedAvg, security/attack evaluation, XAI, dashboard work, or a next experiment prompt from this task.

Main-review should decide whether to freeze UNSW A9 and proceed, move to CICIDS hierarchical training, or approve a different UNSW strategy only for a clear professor-facing reason.
