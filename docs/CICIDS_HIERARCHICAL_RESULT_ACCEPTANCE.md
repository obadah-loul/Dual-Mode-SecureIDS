> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical Result Acceptance

Generated on: `2026-06-25`

Acceptance classification: `SUPERSEDED_BY_EXP03_125_SEED999_FINAL`

## 0. Current Final Status Update

The accepted official CICIDS hierarchical final model is now **EXP03 1.25 seed999**.

| Field | Value |
| --- | --- |
| Final checkpoint | `models/final/final_cicids_hierarchical.pt` |
| Promoted source checkpoint | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` |
| Promotion record | `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json` |
| Backup directory | `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136` |
| Rollback target | `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136/models_final/final_cicids_hierarchical.pt` |

Selection was validation-based: seed42 `0.909871`, seed123 `0.905829`, seed999 `0.913383`.
Seed999 was selected because it had the highest validation hierarchical score. Test metrics were not
used for checkpoint selection.

Hash verification from the promotion record:

- Source SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Final SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Hashes match: `True`

The original baseline accepted in this document is now the **previous baseline** and is preserved in the
backup directory above. The historical audit below is kept for provenance and comparison.

## 1. Purpose And Scope

This is an existing-result acceptance audit for the completed CICIDS2018
centralized hierarchical training run.

Scope boundaries:

- No retraining was run for this audit.
- No full preprocessing rebuild was run.
- No new evaluation pass or new metrics were generated.
- No fake metrics, fake predictions, or improved-result claims are made.
- The audit uses the existing CICIDS outputs only.

The original goal was to lock the then-current CICIDS centralized hierarchical
final-candidate/baseline candidate, while preserving the warnings needed for
honest reporting and future comparison. That candidate has since been superseded
by the EXP03 1.25 seed999 final model recorded in Section 0.

## 2. Acceptance Classification

Classification: `ACCEPT_WITH_WARNINGS`

Interpretation:

- Historically accepted as the then-current CICIDS centralized hierarchical
  final candidate / baseline candidate.
- Do not hide weak rare or difficult classes.
- Do not claim the result is perfect.
- Do not block future controlled improvement experiments.
- Future comparisons should treat this as the previous baseline and EXP03 1.25
  seed999 as the current official final.

## 3. Run Identity

| Field | Value |
| --- | --- |
| Dataset | `cicids2018` |
| Task | `hierarchical` |
| Model | `SecureIDSHierarchicalAdvancedNet` |
| Input dimension | `77` |
| Attack-family Head 2 dimension | `14` |
| Checkpoint | `models/final/final_cicids_hierarchical.pt` |
| Training report | `docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md` |
| Metrics | `results/final/hierarchical/cicids/test_metrics.json` |
| Manifest | `results/audits/hierarchical_training_manifest_cicids2018.json` |

## 4. Core Accepted Metrics

These are the accepted rounded values for the current CICIDS centralized
hierarchical candidate:

| Metric | Value |
| --- | ---: |
| Binary Head 1 macro-F1 | `0.972167` |
| Binary accuracy | `0.977486` |
| Binary precision | `0.974214` |
| Binary recall | `0.946193` |
| Binary F1 | `0.960000` |
| Attack-family Head 2 macro-F1 | `0.849111` |
| Attack-family accuracy on attack rows | `0.961306` |
| Rare-class macro-F1 | `0.716987` |
| End-to-end attack detected and correctly attributed rate | `0.909008` |
| Attack missed as benign rate | `0.053807` |
| Benign false alarm rate | `0.010008` |

## 5. Weak/Difficult Classes

The accepted candidate has strong aggregate performance, but the following
classes must remain visible in the final reporting:

| Class | F1 | Support | Warning |
| --- | ---: | ---: | --- |
| `Web-BruteForce` | `0.3636` | `96` | Weak rare web attack class |
| `Web-XSS` | `0.6182` | `38` | Rare web attack class |
| `DoS-SlowHTTPTest` | `0.5535` | `20941` | Difficult non-rare class |
| `FTP-BruteForce` | `0.7787` | `28928` | Moderate weakness with large support |
| `SQL-Injection` | `0.8000` | `12` | Extremely rare class |

## 6. Honest Interpretation

Head 1 is excellent. The binary detector achieves high macro-F1, accuracy,
precision, recall, and F1, with a low benign false-alarm rate.

Head 2 is strong overall but not perfect. The attack-family head reaches high
accuracy on attack rows, yet macro-F1 is reduced by weak rare web classes and by
the difficult DoS-SlowHTTPTest class.

Rare and difficult class weaknesses must be reported honestly. Web-BruteForce,
Web-XSS, and SQL-Injection have very small support and high variance. DoS-
SlowHTTPTest is not rare, so its weaker F1 is a more meaningful signal of class
overlap, feature ambiguity, or loss/model allocation limits. FTP-BruteForce has
large support and a moderate weakness that should be visible in analysis.

This result was acceptable as the centralized CICIDS hierarchical baseline
candidate, with warnings. It is now the previous baseline after the EXP03 1.25
seed999 promotion.

## 7. Validation Rules Confirmed

The existing CICIDS outputs and manifest confirm:

- Checkpoint selected by validation only.
- Test evaluated once after the best validation checkpoint.
- Class weights computed from the train split only.
- No test tuning.
- No fake metrics.
- No UNSW/A8.8 leakage in the CICIDS result artifacts inspected for this
  acceptance audit.
- No binary-only checkpoint treated as the hierarchical final checkpoint.
- No federated, security, XAI, or dashboard claim from this run.

## 8. Acceptance Decision

Decision at the time of this audit: accept this run as the CICIDS candidate to beat.

Current status: superseded by EXP03 1.25 seed999 as the official final.

This decision means:

- `models/final/final_cicids_hierarchical.pt` now points to the promoted EXP03
  1.25 seed999 final checkpoint.
- The previous baseline is backed up under
  `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.
- Future controlled improvement experiments remain allowed.
- Any future improved model must be compared against this accepted candidate.
- Do not overwrite or delete this checkpoint or result folder without explicit
  approval.

## 9. Final Accepted-Candidate Warnings

Warnings to preserve in the thesis/project record:

- Rare-class instability remains, especially for very small support classes.
- Weak web attack classes remain visible: Web-BruteForce and Web-XSS.
- DoS-SlowHTTPTest is a meaningful weakness because it is not rare.
- The CICIDS random-split near-duplicate caveat must be disclosed when
  interpreting the strength of the centralized benchmark.
- This first accepted CICIDS hierarchical candidate is preserved in the promotion
  backup and should remain available for rollback/comparison.

## 10. Next Recommended Step

Either proceed to federated/security work using this accepted candidate as the
CICIDS centralized baseline, or approve one controlled improvement experiment
only if main control decides the time tradeoff is worth it.

Do not rerun until lucky. Do not hide weak classes. Do not change the taxonomy
just to improve metrics.
