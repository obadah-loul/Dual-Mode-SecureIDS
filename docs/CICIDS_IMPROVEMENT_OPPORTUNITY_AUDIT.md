# CICIDS Improvement Opportunity Audit

Generated on: `2026-06-25`

Current final-status update: this audit is historical planning context. EXP03 1.25 seed999 is now the
official CICIDS hierarchical final model at `models/final/final_cicids_hierarchical.pt`; the previous
baseline is backed up under
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

Baseline candidate: `models/final/final_cicids_hierarchical.pt`

Baseline acceptance status: `ACCEPT_WITH_WARNINGS`

## 1. Purpose

This audit analyzes improvement opportunities for the accepted CICIDS
centralized hierarchical baseline candidate. It uses existing CICIDS outputs
only.

This audit does not implement an improvement, create new configs, run training,
run evaluation, or claim improved metrics.

## 2. Weak Classes That Hurt Macro-F1 Most

The lowest F1 values in the accepted result are the main pressure points for
attack-family macro-F1:

| Class | F1 | Support | Interpretation |
| --- | ---: | ---: | --- |
| `Web-BruteForce` | `0.3636` | `96` | Lowest F1; rare web class with high variance |
| `DoS-SlowHTTPTest` | `0.5535` | `20941` | Non-rare weakness; likely more important than a pure rare-class issue |
| `Web-XSS` | `0.6182` | `38` | Rare web class with very small support |
| `FTP-BruteForce` | `0.7787` | `28928` | Moderate weakness with large support |
| `SQL-Injection` | `0.8000` | `12` | Extremely rare class; unstable estimate |

The rare web classes lower macro-F1 because macro-F1 weights each class equally.
DoS-SlowHTTPTest is especially important because it has substantial support, so
its weakness is not explained by rarity alone.

## 3. Weakness Type

The weaknesses are mixed:

- `Web-BruteForce`, `Web-XSS`, and `SQL-Injection` are mostly rare-class and
  high-variance issues.
- `DoS-SlowHTTPTest` is not rare. Its weaker F1 may indicate class overlap,
  feature ambiguity, or an issue in model/loss allocation for the attack-family
  head.
- `FTP-BruteForce` is a moderate weakness with large support and may benefit
  from Head 2 calibration, loss weighting, or class-weight tuning.

This is not only a rare-class problem.

## 4. Head 1 Versus Head 2

The main weakness is Head 2 / attack-family classification.

Head 1 is already excellent and should not be disrupted casually. Any future
improvement should protect the binary detector and focus on attack-family
macro-F1, rare-class macro-F1, and the difficult attack families.

## 5. Simple Rerun Assessment

A simple rerun may move results slightly, but it is not the best use of time.

Rerunning until lucky would weaken the scientific story. Any improvement should
be targeted, controlled, validation-selected, and compared against the accepted
baseline candidate.

## 6. Improvement Candidates

| Candidate | Classification | Target | Expected Benefit | Risk |
| --- | --- | --- | --- | --- |
| Head 2 capacity increase | `needs_main_chat_decision` | Attack-family macro-F1, difficult classes | Could improve Head 2 without changing the binary task if kept modest | May overfit rare classes or disrupt accepted baseline comparability |
| Attack-family loss weighting change | `needs_main_chat_decision` | DoS-SlowHTTPTest, FTP-BruteForce, rare classes | Directly reallocates training pressure to weak families | Can trade off strong classes and requires careful validation-only selection |
| Rare-class sampling / balanced attack-family sampler | `possible_later` | Rare web classes, SQL-Injection | May improve rare-class exposure | Higher leakage/overfit risk if not strictly train-only |
| Class-weight tuning | `possible_later` | Rare and difficult Head 2 classes | Lower implementation scope if already supported | Can destabilize class balance and must remain train-only |
| Validation calibration | `possible_later` | Operating-point decisions | Can improve deployment behavior without touching test labels | Must be validation-only; not a substitute for Head 2 class improvement |
| Specialist attack-family module | `possible_later` | Difficult families | Could target class overlap more directly | Model-zoo complexity before the broader system is complete |
| Threshold tuning | `reject` | Binary operating point | Not the main weakness; test-based tuning is invalid | Risks test leakage and may disrupt excellent Head 1 |
| Reporting-only improvement | `recommend_now` | Thesis clarity and honest interpretation | Improves transparency without changing metrics | Does not improve model performance |
| No immediate improvement; proceed to federated/security first | `recommend_now` | Project completion and system integration | Preserves the accepted baseline and keeps project momentum | Leaves Head 2 weaknesses for future controlled work |

## 7. Risky Or Rejected Ideas

Reject or defer:

- Test-set threshold tuning.
- Oversampling that uses validation/test information.
- Major specialist/model-zoo changes before the centralized baseline is locked
  and preserved.
- Hiding weak classes.
- Changing taxonomy just to improve metrics.
- Rerunning until lucky.

## 8. Recommended Next Controlled Experiment, If Any

Do not rerun immediately by default.

Lock the current result as the accepted baseline candidate first. If main
control wants a single controlled improvement, the safest next experiment is one
Head 2-focused experiment using validation-only selection, such as:

- A modest Head 2 capacity increase / MLP attack head if already supported, or
- An attack-family loss-weight adjustment if the current training path already
  supports it safely.

Do not do multiple experiments at once. Compare any new experiment against this
accepted candidate.

If project time is tight, move to federated/security next and keep this as the
centralized CICIDS baseline.

## 9. Final Recommendation

Recommended strategy:

`lock_current_baseline_then_decide_between_one_controlled_head2_experiment_or_moving_to_federated_security`

The next main-control decision is whether to spend time on one controlled Head
2 experiment, or proceed to federated/security using the accepted CICIDS
centralized hierarchical candidate.
