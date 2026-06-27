# UNSW Optimization Closure Report

Generated on: 2026-06-25

This report records the formal main-control decision to close UNSW model/preprocessing optimization for now. It is documentation and audit only. No training, evaluation, seed123 run, seed999 run, XAI run, Streamlit launch, Git action, checkpoint modification, final checkpoint replacement, or result-metrics modification was performed for this closure task.

## Final Decision

A9 remains the accepted frozen UNSW baseline.

A11 seed42 is rejected as diagnostic only. It is preserved as an experiment artifact, but it is not promoted, does not replace A9, and does not justify seed123/seed999 confirmation.

The next project phase should move to federated/security implementation using the CICIDS final/promoted model with warnings and the UNSW A9 accepted baseline.

## Accepted UNSW Baseline

- Model identity: A9 corrected-protocol hierarchical baseline
- Checkpoint: `models/final/final_unsw_hierarchical.pt`
- SHA256: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- Binary macro-F1: `0.894488`
- Attack-family macro-F1: `0.500429`
- Rare-class macro-F1: `0.385669`

A9 is not a perfect UNSW model. Its attack-family and rare-class performance remain weak. It is accepted because the later controlled attempts did not produce a safer, clearly better replacement under the approved review rules.

## Optimization History

| Experiment | Direction | Outcome |
| --- | --- | --- |
| A9 | Corrected-protocol hierarchical baseline | Accepted frozen UNSW baseline. |
| A9.6 | Attack-loss weighting | Rejected. Binary macro-F1 improved, but attack-family and rare-class macro-F1 regressed. |
| A9.7 / A9.8 | Stronger Head 2 branch and multi-seed comparison | Rejected. Multi-seed branch gains were too small and did not pass the approved promotion rule. |
| A9.9 | Attack-only specialist | Rejected. The direction failed due to overfitting and weak test performance. |
| A9.10 | Frozen-A9 embedding specialist | Rejected diagnostic only. It did not meaningfully beat A9 and rare-class macro-F1 stayed below A9. |
| A11 | Enhanced feature protocol seed42 | Rejected diagnostic only. It failed the core attack-family and rare-class gates. |

## Why A11 Was Attempted

A11 tested whether an enhanced UNSW feature protocol could improve the unresolved attack-family attribution problem without replacing the final A9 checkpoint prematurely. The goal was to see whether better features and train-only class weighting could lift the weak Head 2 behavior while preserving the corrected UNSW benchmark protocol.

## A11 Preprocessing And Training Result

A11 preprocessing succeeded as an isolated enhanced-feature protocol:

- Dataset: `unsw_nb15`
- Feature count: `192`
- Train/validation/test split was recorded in the A11 manifest.
- Class weights were computed from the training split only.
- The checkpoint was selected by validation score only, not by test metrics.
- No CICIDS, federated, security, XAI, dashboard, or final-promotion work was part of A11.

A11 seed42 checkpoint:

`models/experiments/unsw_a11_enhanced_feature_protocol_seed42.pt`

SHA256:

`2F7D138E94169F11FC2EDB872DC87D0B013B4E0E41D4022A36FEA5C138A899E8`

A11 seed42 test metrics:

- Binary macro-F1: `0.896630`
- Attack-family macro-F1: `0.494685`
- Rare-class macro-F1: `0.342636`
- Correctly attributed rate: `0.725117`
- Missed-as-benign rate: `0.043038`
- Benign false alarm rate: `0.171784`

## A11 Screen Gates

| Gate | Requirement | Result |
| --- | --- | --- |
| Attack-family macro-F1 | `>= 0.515` | FAIL |
| Rare-class macro-F1 | `>= A9 0.385669` | FAIL |
| Binary macro-F1 | Not damaged | PASS |
| Weak classes | Visible | PASS |
| Single-seed promotion | Not allowed | Enforced |

Overall A11 result: `FAIL_SCREEN`.

## Why Seed123 And Seed999 Are Not Justified

A11 seed42 failed the two core UNSW promotion gates: attack-family macro-F1 and rare-class macro-F1. Running seed123 and seed999 would spend more project time confirming a candidate that already failed the approved screen. The professional decision is to stop A11 at diagnostic evidence rather than promote optimism from a single seed.

## Why A9 Remains Accepted

A9 remains accepted because it is the best frozen, corrected-protocol UNSW baseline that survived the review process. A11 slightly improved binary macro-F1, but it regressed both core UNSW targets:

| Metric | A9 | A11 seed42 | A11 minus A9 |
| --- | ---: | ---: | ---: |
| Binary macro-F1 | `0.894488` | `0.896630` | `+0.002142` |
| Attack-family macro-F1 | `0.500429` | `0.494685` | `-0.005744` |
| Rare-class macro-F1 | `0.385669` | `0.342636` | `-0.043033` |

The small binary gain does not compensate for weaker attack-family and rare-class behavior.

## Remaining UNSW Limitations

UNSW remains limited by weak attack-family attribution, fragile rare-class behavior, and sensitivity to changes that increase minority pressure. The project should present A9 honestly as an accepted baseline, not as a solved UNSW classifier. The closure means optimization is paused for project control and thesis coherence; it does not claim that no future research could improve UNSW.

## Honest Presentation

The thesis/project record should state that UNSW optimization was explored through multiple controlled attempts, but no later attempt met the promotion bar. A9 should be reported as the accepted frozen UNSW baseline. A11 should be reported as an informative enhanced-feature diagnostic that improved binary macro-F1 slightly but failed the core attack-family and rare-class objectives.

## Next Phase Recommendation

Move to federated/security implementation using:

- CICIDS final/promoted model with documented warnings.
- UNSW A9 accepted frozen baseline.

The exact next main-control decision should be to approve federated/security phase planning, with no A11 promotion and no additional UNSW seed confirmation.
