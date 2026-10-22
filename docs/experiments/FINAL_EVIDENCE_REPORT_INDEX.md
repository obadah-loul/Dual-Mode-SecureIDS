> Recovery correction (22 October 2026): read [scientific corrections](../LOCAL_RECOVERY.md) alongside this historical report. Nominal SignFlip25 realized 1/5 = 20%; stored numbers below are unchanged.

# Final Evidence Report Index

## Purpose

For the current, evidence-qualified interpretation use
[PROJECT_VERIFICATION_REPORT.md](../PROJECT_VERIFICATION_REPORT.md).
Historical reports and matrices below retain their original numeric results.

This index ties together the final SecureIDS V2 evidence for reporting and demo
use. It identifies the selected clean hierarchical federated baselines, the
final Phase A security/robustness matrix, centralized-versus-federated
comparison evidence, integrity evidence, supporting reports, archive-only
artifacts, and final reporting boundaries.

## Final Reported Scope

The final reported federated security matrix is Phase A only:

- Attack: historical SignFlip25 configuration (requested 25%; realized 1/5 = 20%).
- Aggregators: FedAvg versus Trimmed Mean.
- Datasets: UNSW-NB15 and CICIDS2018.

Phase B 50% malicious-client work is stopped. Gaussian and Scaling attacks were
not run for the final matrix.

TLS transport is not implemented. The prototype contains simulated federated
robustness experiments, SHA-256 fingerprint records (not authenticated origin),
and real one-row inference against saved processed benchmark examples.

Gaussian Noise and Scaling were not part of the final evidence. The Phase A
FedAvg versus Trimmed Mean comparison uses the historical nominal SignFlip25
label, but five clients yielded 20% realized malicious participation.

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

Use the Phase A nominal SignFlip25 (20% realized) evidence as the final reported attack/defense
matrix:

`results/experiments/federated_security/phase_a_signflip25_attack_defense_matrix.csv`

Report/demo summary:

`docs/experiments/PHASE_A_SIGNFLIP25_ATTACK_DEFENSE_SUMMARY.md`

The matrix compares clean hierarchical FedAvg, full-state SignFlip (nominal
25%, realized 20%) under FedAvg, and that attack under Trimmed Mean for both
datasets. These historical experimental metrics were not independently rerun.

## Integrity and Tamper-Evidence

Phase A manifests under `results/audits/` include SHA-256/update-hash integrity
evidence for federated client updates.

Important interpretation:

- Historical SHA-256 update hashes are self-computed fingerprints, not independent
  authentication or proof of trustworthy client origin.
- Comparing to an independently supplied trusted record can detect changes to
  recorded bytes; historical self-checks alone cannot establish this guarantee.
- Trimmed Mean was the evaluated robust aggregator; its outcomes do not establish
  general Byzantine resilience or deployment privacy.

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
- UNSW nominal SignFlip50 FedAvg archive: 2 of 5 = 40% realized.
- Legacy/pre-A8 UNSW binary traces.
- Unrun Phase B 50% configs.
- Gaussian Noise and Scaling attacks, which were not run for final reporting.
- TLS, which is future deployment hardening and not implemented evidence in the
  final prototype.

These artifacts may be mentioned only as archive, diagnostic, or optional future
work if specifically asked.

## Current Limitations

- The dashboard runs model inference on a small set of genuine, preprocessed
  benchmark rows and displays saved robustness evidence. It does not sniff
  packets, classify arbitrary raw traffic, operate a federated network or
  independently verify historical dataset provenance.
- XAI is implemented as local Gradient x Input attribution for the live demo.
  Do not claim SHAP or LIME unless separately implemented later.
- Original Phase A attack/defense rows omit rare-class macro-F1. A separately
  labeled [derived supplement](../recovery/rare_class_supplement.csv) uses saved
  per-class scores; the original matrix remains unchanged.
- TLS-based secure transport is a future deployment extension, not a final
  implemented claim.
- 50% malicious-client, Gaussian Noise, and Scaling experiments are optional
  future extensions, not part of the final reported matrix.

## Recommended Live Demonstration / Report Story

1. Show dual-mode SecureIDS framing.
2. Show selected clean hierarchical federated baselines for UNSW-NB15 and
   CICIDS2018.
3. Show the Phase A matrix, labeled requested 25% / realized 20%.
4. Explain that historical SignFlip scales absolute floating client model states.
5. Explain that five configured clients and floor rounding selected one malicious
   client (20%); no 25%-realized result was obtained.
6. Explain the observed FedAvg/Trimmed Mean tradeoff without broad guarantees.
7. Explain historical SHA-256 records as fingerprints, not authenticated origins.
8. Mention that UNSW-NB15 is harder and has a more nuanced defense tradeoff.
9. Mention that CICIDS2018 shows strong near-clean recovery with Trimmed Mean.
10. Do not show archive-only artifacts unless asked.

## Recommended Next Integration Steps

- Build the final report/demo around the selected clean baselines, centralized
  reference comparison, and Phase A security matrix.
- Distinguish SHA-256 fingerprints from verification against an independent
  trusted reference; describe Trimmed Mean as the tested robust aggregator.
- Add an explicit limitations slide or section for rare-class attack/defense
  gaps, TLS as future deployment hardening, Gaussian/Scaling as optional future
  attacks, and stopped Phase B 50% work.
