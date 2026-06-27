# Dual-Mode SecureIDS Framework — Project Alignment

## 1. Project Identity

SecureIDS V2 is continuing as one IDS framework with two deployment modes: Centralized Mode and Federated Mode.

We are continuing V2. The current V2 centralized IDS work is the upgraded centralized baseline/mode, not a temporary branch to discard. We are not going backward to rebuild old CNN/FFN unless that is approved later as a small reference baseline.

The final project identity is:

**Dual-Mode SecureIDS Framework**

This framing keeps the project message clear: SecureIDS supports strong centralized IDS training when traffic data can be collected in one place, and it supports federated/privacy-preserving IDS training when data is distributed and raw traffic cannot be shared.

## 2. Final Project Goal

The final goal is to present SecureIDS V2 as a dual-mode intrusion detection framework that can be deployed according to the data-sharing reality of the environment.

Centralized mode gives strong reference performance when all data can be collected in one place. Federated mode supports distributed and privacy-preserving training when raw traffic cannot be shared across clients or organizations.

The project is not trying to prove federated learning is always more accurate than centralized learning. Instead, the project shows why both modes exist, what tradeoffs each mode supports, and how federated security can be improved through robust aggregation and integrity checks.

## 3. Why Centralized and Federated Both Exist

Centralized and federated learning answer different deployment needs.

Centralized mode is appropriate when all network traffic data can be collected into one trusted training environment. In that setting, centralized training can use the complete dataset directly and becomes the reference performance mode for SecureIDS V2.

Federated mode is appropriate when data is distributed across clients, organizations, or sites and raw traffic cannot be shared. In that setting, clients train locally and share model updates instead of raw records.

This means centralized and federated modes should not be framed as simple winners and losers. Centralized mode is the strong reference mode when collection is possible. Federated mode is the privacy-preserving distributed mode when collection is not possible.

## 4. Repository Artifact Mapping

The current V2 repository maps to the Dual-Mode SecureIDS Framework as follows.

| Framework Layer | Current V2 Files/Folders | Role in Final Story |
|---|---|---|
| Centralized Mode | `models/final/final_cicids_binary.pt`, `models/final/final_cicids_hierarchical.pt`, `models/final/final_unsw_binary.pt`, `models/final/final_unsw_hierarchical.pt`, `results/final/centralized`, `results/final/hierarchical` | Upgraded centralized reference mode for binary and hierarchical IDS results. |
| Federated Mode | `secureids/federated/fedavg.py`, `secureids/federated/training.py`, `secureids/federated/splitting.py`, `secureids/federated/hierarchical_training.py`, `models/federated/fedavg_cicids_binary.pt`, `models/federated/fedavg_unsw_binary.pt`, `models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt`, `results/federated/cicids`, `results/federated/unsw`, `results/experiments/federated_security/unsw_hierarchical_clean_fedavg` | Distributed/privacy-preserving mode using FedAvg and federated training workflows. |
| Security/Robustness Layer | `secureids/federated/byzantine_attacks.py`, `secureids/federated/robust_aggregation.py`, `secureids/security/update_integrity.py` | Federated security layer for malicious-client attacks, robust aggregation, and integrity evidence. |
| UI/Demo Layer | `dashboard/app.py` | Demo surface that should load saved real outputs and run small safe demos instead of heavy full training live. |
| XAI Layer | `secureids/xai/__init__.py` | Optional/supporting explainability layer unless real implementation and results are completed. |

## 5. Centralized Mode Definition

Centralized Mode is the SecureIDS deployment mode for environments where all training data can be collected in one place.

In the final project story, V2 centralized is the upgraded centralized baseline/mode. It should be frozen and presented as the reference IDS mode once the relevant model and result artifacts are verified.

Known centralized model artifacts:

- `models/final/final_cicids_binary.pt`
- `models/final/final_cicids_hierarchical.pt`
- `models/final/final_unsw_binary.pt`
- `models/final/final_unsw_hierarchical.pt`

Known centralized result folders:

- `results/final/centralized`
- `results/final/hierarchical`

## 6. Federated Mode Definition

Federated Mode is the SecureIDS deployment mode for environments where traffic data is distributed and raw traffic cannot be shared.

In this mode, each client trains locally and contributes model updates for aggregation. FedAvg is the clean federated baseline, while malicious-client attacks and robust aggregation are the main remaining work for the federated security story.

Known federated code artifacts:

- `secureids/federated/fedavg.py`
- `secureids/federated/training.py`
- `secureids/federated/splitting.py`
- `secureids/federated/hierarchical_training.py`

Known federated model/result artifacts:

- `models/federated/fedavg_cicids_binary.pt`
- `models/federated/fedavg_unsw_binary.pt`
- `models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt`
- `results/federated/cicids`
- `results/federated/unsw`
- `results/experiments/federated_security/unsw_hierarchical_clean_fedavg`

## 7. Security and Robustness Layer

The security and robustness layer exists mainly to protect Federated Mode.

Robust aggregation is for defending federated mode against malicious clients. Byzantine attack simulations such as SignFlip, Gaussian, and Scaling should be used to evaluate how the federated system behaves under hostile client updates. Defense comparisons such as FedAvg vs Trimmed Mean should be treated as federated robustness evidence, not as centralized performance claims.

Known security/robustness artifacts:

- `secureids/federated/byzantine_attacks.py`
- `secureids/federated/robust_aggregation.py`
- `secureids/security/update_integrity.py`

Integrity evidence, including SHA-256 reporting, should support reproducibility and trust in saved artifacts. TLS evidence can be added if feasible, but it should not be claimed unless it is actually implemented and documented.

## 8. UI/Demo Vision

The UI/demo should present the Dual-Mode SecureIDS story clearly without running heavy training live.

The dashboard should load saved real outputs and run only small safe demos. It should not launch full centralized training, full federated training, preprocessing, or expensive evaluation as a live demo action.

Known UI artifact:

- `dashboard/app.py`

The final demo should let a viewer understand:

- when Centralized Mode is appropriate;
- when Federated Mode is appropriate;
- how malicious-client attacks affect federated training;
- how robust aggregation improves federated security;
- how integrity evidence supports artifact trust.

## 9. XAI Layer

The XAI layer is optional/supporting unless real implementation and results are completed.

Known XAI artifact:

- `secureids/xai/__init__.py`

XAI should not be promoted as a final completed contribution unless there are real explainability outputs, a clear method, and verified results. If implementation is incomplete, XAI can be described as a supporting or future extension layer.

## 10. Remaining Gaps

The following items still need verification or completion later:

- final SignFlip/Gaussian/Scaling attack result grid;
- 0%, 25%, 50% malicious-client comparison;
- FedAvg vs Trimmed Mean final defense comparison;
- SHA-256 evidence/report;
- TLS evidence if feasible;
- XAI implementation/results;
- dashboard readiness;
- final demo script;
- final Dual-Mode final report package.

## 11. Recommended Next Work Order

1. Lock this Dual-Mode alignment document.
2. Audit current federated/security artifacts.
3. Freeze centralized mode outputs as reference mode.
4. Verify clean FedAvg results.
5. Complete Byzantine attack grid.
6. Complete Trimmed Mean defense comparison.
7. Produce SHA-256 integrity evidence.
8. Prepare UI-ready saved outputs.
9. Add/verify XAI only as supporting layer.
10. Build final dashboard/demo.
11. Prepare final report, README, figures, and reproducibility guide.

## 12. Safety Rules

- Do not delete/archive files without approval.
- Do not claim federated always beats centralized.
- Do not run heavy training in UI/demo.
- Do not fake results.
- Do not tune on test data.
- Do not push to GitHub without approval.
- Treat failed/diagnostic experiments as evidence, not final claims.
