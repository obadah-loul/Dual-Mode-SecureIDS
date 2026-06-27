# UNSW A10 Frozen Embedding Specialist Seed42 Report

Status: `FAIL_SCREEN`

A9.10 seed42 is rejected as diagnostic only. It does not proceed to 3-seed confirmation, and A9 remains the accepted UNSW baseline. No single-seed promotion is allowed.

## Safety

- A9 final checkpoint SHA256 stayed unchanged: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- A9.10 checkpoint SHA256 stayed unchanged: `AC790FD0FBD67FAD9702DBBE29F12ED8A817FE3C076C9E2D91027187111C81D6`
- No training rerun occurred.
- No test tuning occurred.
- No checkpoint was promoted or replaced.
- `models/final/` and `results/final/` were not modified.

## Metric Views

- Oracle metrics are teacher-forced on true attack rows. They are not routed/deployed metrics.
- Routed metrics are deployment-style because the frozen A9 Head 1 routes rows into the A9.10 head.
- Routed performance is bounded by frozen A9 Head 1 misses.

## Screen Metrics

| Metric | A9 baseline | A9.10 seed42 | Delta | Gate | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Oracle attack-family macro-F1 | 0.500429 | 0.501155 | +0.000726 | >= 0.515429 | FAIL |
| Oracle rare-class macro-F1 | 0.385669 | 0.374971 | -0.010698 | >= 0.385669 | FAIL |
| Routed attack-family macro-F1 | 0.500429 | 0.490005 | -0.010424 | deployment-style context | FAIL |
| Routed rare-class macro-F1 | 0.385669 | 0.382772 | -0.002897 | diagnostic | WARN |
| Binary macro-F1 | 0.894488 | A9 router unchanged | 0.000000 | frozen A9 Head 1 | PASS |

## Screen Gates

| Gate | Result |
| --- | --- |
| Oracle attack-family macro-F1 >= 0.515429 | FAIL |
| Rare-class macro-F1 >= 0.385669 | FAIL |
| Oracle/routed separated | PASS |
| Binary router remains A9-based | PASS |
| Overall | FAIL_SCREEN |

## Weak Classes Remain Visible

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| Analysis | 0.06666666666666667 | 0.0103397341211226 | 0.017902813299232736 | 677 |
| Backdoor | 0.03903243540406817 | 0.12178387650085763 | 0.05911740216486262 | 583 |
| DoS | 0.3221046355641675 | 0.5284910736121301 | 0.40025930727912573 | 4089 |
| Shellcode | 0.2731239092495637 | 0.828042328042328 | 0.410761154855643 | 378 |
| Worms | 0.2283464566929134 | 0.6590909090909091 | 0.3391812865497076 | 44 |

## Generated Repair Artifacts

- Per-class CSV: `results/experiments/unsw_a10_frozen_embedding_specialist_seed42/per_class_attack_metrics.csv`
- Rare-class CSV: `results/experiments/unsw_a10_frozen_embedding_specialist_seed42/rare_class_metrics.csv`
- Oracle confusion matrix CSV: `results/experiments/unsw_a10_frozen_embedding_specialist_seed42/attack_family_confusion_matrix.csv`

## Recommendation

Reject A9.10 seed42 as diagnostic only. Do not proceed to 3-seed confirmation. Stop UNSW specialist work unless main control requests further deep analysis. Keep A9 as the accepted UNSW baseline.
