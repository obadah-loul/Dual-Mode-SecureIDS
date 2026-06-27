# Federated Security Phase Planning Audit

Generated on: 2026-06-25

Status: planning and audit only. No code implementation, config implementation, training, evaluation, preprocessing, XAI, Streamlit, Git action, checkpoint change, final model change, or final result change was performed for this task.

## Project State

The project now has finalized centralized hierarchical references for both datasets:

| Dataset | Final status | Checkpoint | SHA256 |
| --- | --- | --- | --- |
| CICIDS2018 | Finalized and promoted with warnings | `models/final/final_cicids_hierarchical.pt` | `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0` |
| UNSW-NB15 | A9 accepted frozen baseline; optimization closed for now | `models/final/final_unsw_hierarchical.pt` | `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA` |

A11 is rejected as diagnostic only. It must not be promoted, continued to seed123/seed999, or used as the final UNSW model.

## Areas Inspected

- `secureids/federated/`
- `secureids/security/`
- `secureids/aggregation/`
- `secureids/attacks/`
- `secureids/evaluation/`
- `secureids/training/`
- `secureids/models/`
- `configs/federated/`
- `docs/`
- `docs/experiments/`
- `docs/final/`
- `results/audits/`
- `results/federated/`
- `models/final/`
- `models/federated/`
- V1 as read-only reference for Week 5/7 security and attack concepts

`secureids/distributed/` is not present in V2.

## Existing Capabilities In V2

V2 already has a binary FedAvg foundation:

- FedAvg config validation: `secureids/federated/config.py`
- Stratified IID client partition planning: `secureids/federated/splitting.py`
- Weighted FedAvg state-dict aggregation: `secureids/federated/fedavg.py`
- FedAvg dry-run validation: `secureids/federated/dry_run.py`
- FedAvg training runner: `secureids/federated/training.py`
- CLI commands: `federated-dry-run` and `federated-train`
- Dataset FedAvg configs:
  - `configs/federated/unsw_nb15_fedavg.yaml`
  - `configs/federated/cicids2018_fedavg.yaml`
- Existing binary FedAvg outputs:
  - `models/federated/fedavg_unsw_binary.pt`
  - `models/federated/fedavg_cicids_binary.pt`
  - `results/federated/unsw/`
  - `results/federated/cicids/`
  - `results/audits/fedavg_manifest_unsw_nb15.json`
  - `results/audits/fedavg_manifest_cicids2018.json`
  - `docs/FEDERATED_LEARNING_REPORT.md`

The binary FedAvg results are useful engineering evidence. They must not be presented as final hierarchical federated evidence.

There are lightweight deterministic tests for:

- FedAvg aggregation math.
- Stratified IID client split planning.
- Federated config validation.
- Federated training safety gates.

The adapter registry also records planned federated hierarchical checkpoint names, but the files do not exist:

- `models/federated/fedavg_cicids_hierarchical.pt`: missing
- `models/federated/fedavg_unsw_hierarchical.pt`: missing

## Missing Capabilities

The next phase still needs V2-native implementation for:

- Hierarchical FedAvg configs and runner support for `SecureIDSHierarchicalAdvancedNet`.
- Dataset-specific hierarchical client partitioning with attack-family distribution tracking.
- Non-IID split support.
- Robust aggregation beyond FedAvg: trimmed mean, coordinate median, and optionally Krum.
- Byzantine attack simulation: sign-flip, Gaussian noise, scaling, and possibly label-flip only if it is clearly scoped to training labels.
- Attack/defense evaluation protocol with clean, attacked, and defended runs kept separate.
- Client update SHA-256 integrity logging.
- Checkpoint/hash registries for centralized and federated artifacts.
- TLS or secure-channel evidence in V2.
- Secure aggregation, if feasible. This should be treated as optional unless a realistic implementation scope is approved.
- Final reporting tables comparing centralized, clean FedAvg, attacked FedAvg, and robust aggregation.
- Reproducibility command sheet.
- Dashboard/XAI linkage later, after final federated/security artifacts exist.

## V1 Reference Assessment

V1 contains useful read-only reference material:

- `scripts/v5/gradient_security.py`: SHA-256 gradient serialization and verification concepts.
- `scripts/v5/attacks.py`: sign-flip, Gaussian noise, scaling, FedAvg, and trimmed mean concepts.
- `scripts/v5/generate_robust_aggregation_evidence.py`: robust aggregation evidence and caveat structure.
- `scripts/v5/run_final_secure_federated_ids_grid.py`: TLS/SHA timing, attack grid, and reporting ideas.
- V1 `results/week5_*` and `results/week7_*`: security and Byzantine evidence style.

These should not be copied wholesale. V2 should port concepts into clean modules with tests, dataset-aware configs, and honest reporting.

## Dataset Final Model Usage Plan

CICIDS:

- Use `models/final/final_cicids_hierarchical.pt` as the centralized reference.
- Preserve warnings:
  - SlowHTTPTest to FTP-BruteForce remains dominant unresolved confusion.
  - FTP-BruteForce mean F1 is slightly lower than the old baseline.
  - Web-XSS and SQL-Injection have tiny support and must not be overclaimed.
  - EXP04 suggested the remaining SlowHTTPTest/FTP issue may be feature-limited.
- Do not rerun CICIDS optimization.

UNSW:

- Use `models/final/final_unsw_hierarchical.pt` as the centralized reference.
- Preserve limitations:
  - Weak attack-family macro-F1.
  - Weak rare-class macro-F1.
  - Analysis, Backdoor, DoS, and Exploits confusion remains difficult.
- Do not use A11 as final.
- Do not rerun UNSW optimization.

Centralized final checkpoints should be reference baselines only for the first professional federated/security phase. Clean FL should train from deterministic initialization so the project can honestly claim federated training. Any later warm-start from centralized checkpoints must be separately approved and reported as a warm-start ablation, not the main FL result.

## Federated Learning Plan

Use one shared framework with dataset-specific configs. The framework should reuse common client/server/aggregation/reporting code, while configs specify dataset, input dimension, attack head dimension, processed paths, final centralized reference, and output paths.

Recommended first FL target:

1. Hierarchical clean FedAvg dry-run scaffold.
2. Dataset-specific hierarchical FedAvg configs for CICIDS and UNSW.
3. Deterministic IID split over training rows only.
4. Client distribution reports for binary labels and attack-family labels.
5. Local client training with `SecureIDSHierarchicalAdvancedNet`.
6. Weighted FedAvg aggregation by client sample count.
7. Global validation after each round.
8. Best round selected by validation-only hierarchical score.
9. Final test evaluation once after best validation round, only after main-control approval.

Non-IID split should come after clean IID FedAvg works. It should be an explicit experiment, not the default baseline.

## Security Layer Plan

The realistic V2 security layer should begin with integrity evidence:

- SHA-256 hash each serialized client update.
- Record client id, round, update hash, payload size, verification status, and aggregation inclusion.
- Hash final checkpoints and result manifests.
- Refuse or mark tampered updates when hash verification fails.

TLS should be treated carefully:

- If real localhost TLS timing is implemented, document it as transport-overhead evidence, not full production security.
- Do not claim encrypted secure aggregation unless that is actually implemented.
- Do not import V1 certificates or private keys into final V2 evidence.

Secure aggregation is optional. If not implemented, the report should say update integrity and secure-channel timing were implemented, but cryptographic secure aggregation was not.

## Byzantine Simulation Plan

Implement attack functions on client updates/model deltas, not on final checkpoints:

- Sign-flip: negate malicious client updates.
- Gaussian noise: replace or perturb malicious updates with scaled Gaussian noise.
- Scaling attack: multiply malicious updates by a large factor.
- Label-flip: optional later, only if implemented as a clearly documented training-label attack and separated from gradient/update attacks.

Use controlled malicious client percentages:

- Clean: 0 percent.
- Primary attacked setting: 25 percent.
- Stress setting: 50 percent, reported as beyond normal robust aggregation tolerance for small client counts.

Attack results must be separate from clean baselines. Do not mix attacked metrics into clean FedAvg or centralized baseline tables.

## Robust Aggregation Plan

Implement and test aggregators in V2:

- FedAvg: already exists as baseline.
- Trimmed mean: first robust defense to implement.
- Coordinate median: second robust defense; simple and deterministic.
- Krum: optional if feasible; requires distance-based update comparison and clear limitations for small client counts.

Deterministic tests should verify:

- Known tiny tensors aggregate to expected values.
- Outliers damage FedAvg.
- Trimmed mean and median reduce outlier impact in feasible settings.
- Krum selects an honest update in a controlled toy case, if implemented.
- Shape, dtype, and key compatibility checks fail safely.

## Reporting And Evidence Plan

Final evidence should include:

- Centralized reference registry.
- Clean FedAvg results per dataset.
- Attacked FedAvg results per dataset.
- Robust aggregation defense results per dataset.
- Security hash and integrity audit.
- Communication/security overhead table if TLS timing is implemented.
- Attack/defense comparison table.
- Dataset-specific summary reports.
- Reproducibility command sheet.
- Final checkpoint hash registry.
- Dashboard/XAI linkage report later.
- Professor-safe wording that distinguishes real training, simulation, integrity logging, TLS timing, and unavailable secure aggregation.

## Risks

- The existing FedAvg implementation is binary-task oriented; using it as-is for hierarchical final claims would be misleading.
- CICIDS and UNSW have incompatible schemas and attack taxonomies, so forced shared checkpoints or labels would be fake.
- Robust aggregation results can be overstated if evaluated only on synthetic deltas or only with cosine similarity.
- Scaling attacks can preserve direction while damaging norm, so norm ratio and MSE must be reported.
- TLS timing over localhost is useful overhead evidence but not a full real-world deployment proof.
- A11 must not leak back into final UNSW usage.
- Historical V1 artifacts must not be pasted into V2 as if newly reproduced.

## Next Decision Needed

Main control should approve or reject a federated/security implementation scaffold.

The safest approved next task would be scaffold-only: add V2-native robust aggregation, Byzantine attack, and security integrity modules plus deterministic tests and future configs, without running training or creating final metrics. Heavy manual runs should come only after that scaffold passes review.
