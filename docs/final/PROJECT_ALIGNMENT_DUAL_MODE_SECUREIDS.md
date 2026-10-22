# Dual-Mode SecureIDS — Current Project Alignment

Updated 22 October 2026. This replaces the earlier deployment vision with the
implemented research scope. The [verification report](../PROJECT_VERIFICATION_REPORT.md)
qualifies the scientific evidence; the [README](../../README.md) gives execution steps.

## Project identity and dual-mode meaning

SecureIDS is a cybersecurity research prototype with centralized reference
experiments and simulated federated experiments. Both use dataset-specific
hierarchical classification. It is not a deployed privacy-preserving IDS.
The dashboard's mode selector explains these two research settings; both choices
run the selected federated checkpoint on a saved processed record.

## Actual component connections

| Component | Implementation | Verified role / boundary |
|---|---|---|
| Dataset adapters | `secureids/datasets/` | Separate CICIDS2018 and UNSW schemas; no cross-dataset feature interchange |
| Preprocessing | `secureids/preprocessing/` | Existing train-fitted artifacts; raw CSVs absent; not executed for replay |
| Hierarchical model | `secureids/models/secureids_hierarchical_advanced_net.py` | Shared residual/gated MLP, one binary logit, dataset-specific family logits |
| Centralized references | `results/final/hierarchical/` | Saved historical metrics; promoted/frozen checkpoint IDs in `configs/selected_models.json` |
| Simulated federation | `secureids/federated/hierarchical_training.py` | Sequential local clients over centrally available arrays; full participation and family-aware IID supported |
| Aggregation / attacks | `secureids/federated/robust_aggregation.py`, `byzantine_attacks.py` | Sample-weighted FedAvg and coordinate-wise Trimmed Mean; historical full-state SignFlip |
| Fingerprints | `secureids/security/update_integrity.py` | Local hashes and supplied-record comparisons; no authenticated origin, TLS, or secure aggregation |
| Replay | `secureids/inference/live_demo.py`, `dashboard/app.py` | Genuine original weights and selected processed rows; binary decision gates the family output |
| Explainability | `secureids/xai/local_attribution.py` | Implemented and locally exercised Gradient x Input; not SHAP/LIME or causal proof |
| Artifact installation | `tools/demo_package.py` | Offline hash-checked compact ZIP installation; no preprocessing fitting or training |

CICIDS uses 77 features and 14 families; current UNSW uses 192 features and nine
families. Legacy 190-feature UNSW binary artifacts are archival. The selected
centralized CICIDS reference is EXP03 loss1.25/seed999; the base training YAML is
the earlier recipe. The selected clean federated rounds are CICIDS19 and UNSW16.

## Scientific and security interpretation

The Phase A matrix is historical exploratory evidence. Requested 25% selected
one of five clients (20% realized). The nominal 50% archive selected two of five
(40% realized). SignFlip inverted absolute floating model states, not only local
parameter deltas. The matrix has no clean Trimmed Mean control or federated
multi-seed confirmation. UNSW's defended macro-F1 and missed-attack rate move in
different directions; report both. Oracle family metrics are distinct from
routed outcomes.

Checkpoint selection was validation-based within runs. Across development, test
feedback influenced later decisions. An untouched confirmatory evaluation,
raw-row identity and duplicate/session isolation have not been established.
Historic hash self-checks do not establish transport integrity or client trust.

## Current delivery and remaining work

The compact CICIDS candidate has one checkpoint/four genuine rows; the complete
private replay has two checkpoints/seven rows. Neither includes a full dataset
or implements arbitrary raw-traffic classification. UNSW-derived bundle
republication remains blocked pending rights clarification. No blanket model/code
license is invented. See [distribution notices](../DATASET_RIGHTS.md).

Owner publication approval and an approved artifact distribution location remain
necessary. Additional attacks, partial/non-IID client execution, TLS, distributed
deployment and confirmatory research are future scope, not unfinished steps
required for this replay. No original model retraining, full preprocessing or
historical experiment rerun is required or performed for final integration.
