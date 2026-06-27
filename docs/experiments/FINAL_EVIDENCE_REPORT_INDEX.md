# Final Evidence Report Index

## Purpose

This index ties together the final SecureIDS V2 evidence for reporting and demo
use. It identifies the selected clean hierarchical federated baselines, the
final Phase A security/robustness matrix, centralized-versus-federated
comparison evidence, integrity evidence, supporting reports, archive-only
artifacts, and final reporting boundaries.

## Final Reported Scope

The final reported federated security matrix is Phase A only:

- Attack: SignFlip 25%.
- Aggregators: FedAvg versus Trimmed Mean.
- Datasets: UNSW-NB15 and CICIDS2018.

Phase B 50% malicious-client work is stopped. Gaussian and Scaling attacks were
not run for the final matrix.

TLS-based secure transport is a future deployment extension. The final
prototype focuses on federated robustness, SHA-256 integrity verification, and
live IDS inference.

Gaussian Noise and Scaling are additional Byzantine attack types/future
extensions. The finalized robustness evidence focuses on Phase A SignFlip 25%
for a clear FedAvg versus Trimmed Mean comparison across CICIDS2018 and
UNSW-NB15.

Phase B 50% is an extreme stress-test setting and is not part of the finalized
reported robustness matrix.

## Final / Selected Clean Hierarchical Federated Baselines

### UNSW-NB15

Selected checkpoint:

`models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt`

Selected result folder:

`results/experiments/federated_security/unsw_hierarchical_clean_fedavg/`

Decision note:

`docs/experiments/UNSW_HIERARCHICAL_FEDERATED_MODEL_SELECTION_DECISION.md`

Selected metrics:

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | 0.882305 |
| Attack-family macro-F1 | 0.475889 |
| Rare-class macro-F1 | 0.307115 |
| Missed-as-benign rate | 0.062097 |

### CICIDS2018

Selected checkpoint:

`models/experiments/federated_security/cicids_hierarchical_clean_fedavg.pt`

Selected result folder:

`results/experiments/federated_security/cicids_hierarchical_clean_fedavg/`

Decision note:

`docs/experiments/CICIDS_HIERARCHICAL_FEDERATED_MODEL_SELECTION_DECISION.md`

Selected metrics:

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | 0.971947 |
| Attack-family macro-F1 | 0.851652 |
| Rare-class macro-F1 | 0.748521 |
| Missed-as-benign rate | 0.053261 |

## Centralized vs Federated Comparison

Use this concise documentation table when a report or demo needs to compare the
centralized hierarchical reference against the selected clean hierarchical
federated baselines:

`docs/experiments/CENTRALIZED_VS_FEDERATED_COMPARISON.md`

The comparison uses existing saved metrics only. It does not introduce new
training, preprocessing, evaluation, or experiment results.

## Final Phase A Security / Robustness Matrix

Use the Phase A SignFlip 25% evidence as the final reported attack/defense
matrix:

`results/experiments/federated_security/phase_a_signflip25_attack_defense_matrix.csv`

Report/demo summary:

`docs/experiments/PHASE_A_SIGNFLIP25_ATTACK_DEFENSE_SUMMARY.md`

This matrix compares clean hierarchical FedAvg, SignFlip 25% under FedAvg, and
SignFlip 25% under Trimmed Mean for UNSW-NB15 and CICIDS2018.

## Integrity and Tamper-Evidence

Phase A manifests under `results/audits/` include SHA-256/update-hash integrity
evidence for federated client updates.

Important interpretation:

- SHA-256 update hashes provide tamper-evidence and integrity tracking.
- SHA-256 is not the Byzantine defense itself.
- Trimmed Mean is the Byzantine robustness defense evaluated in Phase A.

## Supporting Reports and Manifests

Key supporting Phase A reports and manifests include:

- `results/audits/federated_security_unsw_hierarchical_byzantine_signflip_manifest.json`
- `results/audits/federated_security_unsw_hierarchical_robust_trimmed_mean_manifest.json`
- `results/audits/federated_security_cicids_hierarchical_byzantine_signflip_manifest.json`
- `results/audits/federated_security_cicids_hierarchical_robust_trimmed_mean_manifest.json`
- `docs/experiments/FEDERATED_SECURITY_UNSW_HIERARCHICAL_BYZANTINE_SIGNFLIP_REPORT.md`
- `docs/experiments/FEDERATED_SECURITY_UNSW_HIERARCHICAL_ROBUST_TRIMMED_MEAN_REPORT.md`
- `docs/experiments/FEDERATED_SECURITY_CICIDS_HIERARCHICAL_BYZANTINE_SIGNFLIP_REPORT.md`
- `docs/experiments/FEDERATED_SECURITY_CICIDS_HIERARCHICAL_ROBUST_TRIMMED_MEAN_REPORT.md`

## Archive-Only / Not Main Final Reporting

The following artifacts are not part of the main final reported evidence:

- Standalone binary FedAvg artifacts.
- UNSW rounds=40 clean improvement evidence.
- UNSW safety-gated rounds=40 failed selector evidence.
- UNSW SignFlip 50% FedAvg stress-test result.
- Legacy/pre-A8 UNSW binary traces.
- Unrun Phase B 50% configs.
- Gaussian Noise and Scaling attacks, which were not run for final reporting.
- TLS, which is future deployment hardening and not implemented evidence in the
  final prototype.

These artifacts may be mentioned only as archive, diagnostic, or optional future
work if specifically asked.

## Current Limitations

- Dashboard live inference is implemented for selected benchmark attack
  scenarios, including one-row inference, model routing, SHA-256 hashes,
  Phase A robustness evidence, and safety/limitations text.
- XAI is implemented as local Gradient x Input attribution for the live demo.
  Do not claim SHAP or LIME unless separately implemented later.
- Phase A attack/defense rows do not report rare-class macro-F1.
- TLS-based secure transport is a future deployment extension, not a final
  implemented claim.
- 50% malicious-client, Gaussian Noise, and Scaling experiments are optional
  future extensions, not part of the final reported matrix.

## Recommended Live Demonstration / Report Story

1. Show dual-mode SecureIDS framing.
2. Show selected clean hierarchical federated baselines for UNSW-NB15 and
   CICIDS2018.
3. Show the Phase A SignFlip 25% attack/defense matrix.
4. Explain that SignFlip simulates malicious federated clients flipping model
   updates.
5. Explain that 25% malicious means one malicious client out of five.
6. Explain that FedAvg is vulnerable and Trimmed Mean is the robust aggregation
   defense.
7. Explain SHA-256 as integrity/tamper-evidence, not the defense itself.
8. Mention that UNSW-NB15 is harder and has a more nuanced defense tradeoff.
9. Mention that CICIDS2018 shows strong near-clean recovery with Trimmed Mean.
10. Do not show archive-only artifacts unless asked.

## Recommended Next Integration Steps

- Build the final report/demo around the selected clean baselines, centralized
  reference comparison, and Phase A security matrix.
- Keep SHA-256 described as integrity/tamper-evidence and Trimmed Mean described
  as the robust aggregation defense.
- Add an explicit limitations slide or section for rare-class attack/defense
  gaps, TLS as future deployment hardening, Gaussian/Scaling as optional future
  attacks, and stopped Phase B 50% work.
