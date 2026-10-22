# Hierarchical Federated Experiment Report

> **October 2026 interpretation:** Historical numerical outputs are retained,
> but these records reflect a **single-process, single-seed experiment**,
> nominal 25% / realized 20% malicious clients, and full-state scaling rather
> than parameter-delta SignFlip. Original saved paths below are historical
> machine paths, not portable installation instructions. See
> [the evidence-qualified project report](../PROJECT_VERIFICATION_REPORT.md).

Dataset: `cicids2018`
Protocol: `cicids_hierarchical_robust_trimmed_mean_reference_final_exp03_125_seed999`
Aggregation: `trimmed_mean`
Attack: `sign_flip`
Requested malicious fraction: `0.25` (actual: **1 of 5 = 20%**)
Selected malicious clients: `['client_00']`

Status: historical run recorded as completed; not rerun during final integration.

Safety notes:

- Centralized final checkpoint was reference-only.
- Initialization was from scratch.
- No `models/final/` or `results/final/` path was written.
- This FL checkpoint is experimental and not promoted.

Results:

- Best round: `14`
- Rounds run: `20`
- Test metrics path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\federated_security\cicids_hierarchical_robust_trimmed_mean\test_metrics.json`
- Manifest path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\federated_security_cicids_hierarchical_robust_trimmed_mean_manifest.json`
- Historical SHA-256 self-check reported: `True` (not independent origin authentication or externally anchored integrity proof)
