# Federated Security Implementation Roadmap

Generated on: 2026-06-25

Status: planning only. This roadmap does not implement code, create implementation configs, run training, run evaluation, rebuild preprocessing, launch XAI, launch Streamlit, use Git, or modify checkpoints/final results.

## Current Final Dataset State

CICIDS final centralized reference:

- Checkpoint: `models/final/final_cicids_hierarchical.pt`
- SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Status: finalized and promoted with warnings
- Required warning: SlowHTTPTest to FTP-BruteForce remains the dominant unresolved confusion
- Required warning: FTP-BruteForce mean F1 is slightly lower than the old baseline
- Required warning: Web-XSS and SQL-Injection have tiny support

UNSW final centralized reference:

- Checkpoint: `models/final/final_unsw_hierarchical.pt`
- SHA256: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- Status: A9 accepted frozen baseline; optimization closed for now
- Required limitation: weak attack-family macro-F1
- Required limitation: weak rare-class macro-F1
- Required limitation: Analysis, Backdoor, DoS, and Exploits remain difficult

A11:

- Status: rejected diagnostic only
- Do not use as final
- Do not continue seed123/seed999

## Architecture Recommendation

Use a shared V2 federated/security framework with dataset-specific hierarchical configs.

Shared framework:

- Client partitioning.
- Local client training loop.
- Server round loop.
- Aggregation contracts.
- Attack simulation contracts.
- Security/integrity logging.
- Metrics and report writers.
- Reproducibility manifests.

Dataset-specific configs:

- Dataset name and aliases.
- Processed hierarchical split paths.
- Input dimension.
- Attack-family head dimension.
- Taxonomy and label mappings.
- Centralized final reference checkpoint and hash.
- Output paths.
- Dataset-specific warnings and limitations.

Centralized final checkpoints should be used as references only in the first implementation sequence. Clean FL should train from deterministic initialization. A centralized warm-start can be a later ablation only if main control approves it and the report labels it clearly.

## Implementation Phases

### Phase 0: Planning Complete

Created now:

- `docs/experiments/FEDERATED_SECURITY_PHASE_PLANNING_AUDIT.md`
- `docs/experiments/FEDERATED_SECURITY_IMPLEMENTATION_ROADMAP.md`
- `results/audits/federated_security_phase_planning_audit.json`
- `results/audits/federated_security_component_inventory.csv`
- `results/audits/federated_security_required_outputs.csv`

### Phase 1: Scaffold And Tests

Codex should implement first, after main-control approval:

- V2 robust aggregation module with FedAvg adapter, trimmed mean, median, and optional Krum.
- V2 Byzantine attack module with sign-flip, Gaussian noise, and scaling attacks.
- V2 security/integrity module for SHA-256 update hashing and checkpoint hash registry.
- Deterministic unit tests for all of the above.
- No training and no final metrics in this scaffold task.

### Phase 2: Hierarchical Federated Dry-Run

Implement dataset-specific hierarchical FL config schema and dry-run validation:

- CICIDS hierarchical FedAvg planned config.
- UNSW hierarchical FedAvg planned config.
- Input dimension and attack head dimension checks.
- Processed hierarchical split checks.
- Client distribution preview using training labels only.
- Output path guards under non-final federated paths.
- Centralized reference hash validation.

No training should run in this phase.

### Phase 3: Clean Hierarchical FedAvg

Manual heavy runs later, after approval:

- CICIDS clean hierarchical FedAvg.
- UNSW clean hierarchical FedAvg.
- Save round histories, client logs, client distributions, metrics, manifests, and reports.
- Keep centralized references unchanged.
- Evaluate test once after best validation round.

### Phase 4: Security Integrity Layer

Add/update evidence around clean FL:

- Per-client update SHA-256.
- Update verification status.
- Aggregation inclusion/exclusion status.
- Final checkpoint hash registry.
- Optional localhost TLS timing if approved.

Do not claim cryptographic secure aggregation unless implemented.

### Phase 5: Byzantine Attack Evaluation

Manual heavy runs later, after approval:

- Attacked FedAvg with sign-flip, Gaussian noise, and scaling.
- Malicious fractions: 25 percent primary, 50 percent stress.
- Clean FL baseline remains separate.
- Attacked metrics are saved under attacked result paths only.

### Phase 6: Robust Defense Evaluation

Manual heavy runs later, after approval:

- Trimmed mean defense.
- Coordinate median defense.
- Optional Krum if tests and limitations are acceptable.
- Compare clean FedAvg, attacked FedAvg, and robust defense per dataset.

### Phase 7: Final Reporting And Demo Linkage

After all approved runs:

- Master comparison tables.
- Security audit.
- Attack/defense report.
- Reproducibility command sheet.
- Final dataset/model registry.
- Final checkpoint hash registry.
- Dashboard/XAI linkage report.
- Professor-safe wording.

## What Codex Should Implement First

The next implementation task should be scaffold-only:

1. Add `secureids/aggregation/robust.py`.
2. Add `secureids/attacks/byzantine.py`.
3. Add `secureids/security/integrity.py`.
4. Add tests for deterministic aggregation, attack transforms, hash verification, and failure behavior.
5. Add planning-only config schema stubs only if main control explicitly approves them.

Do not run training during the scaffold.

## What The User Must Run Manually Later

Manual runs will be needed for:

- Hierarchical FL dry-run validation.
- Clean CICIDS hierarchical FedAvg.
- Clean UNSW hierarchical FedAvg.
- Security/integrity audit runs.
- Attacked FedAvg runs.
- Robust aggregation defense runs.
- Final report generation.
- Later XAI/dashboard artifact generation.

Exact commands should be written only after the scaffold and configs are approved.

## Approval Gates

Before scaffold implementation:

- Approve or reject `approve_or_reject_federated_security_implementation_scaffold`.

Before clean FL:

- Approve dataset-specific hierarchical FL configs and output paths.

Before attack/security runs:

- Approve attack types, malicious percentages, client counts, and result paths.

Before final reporting:

- Confirm all clean, attacked, robust, and security outputs are available and not mixed.

## Expected Outputs

Final project evidence should include:

- Centralized vs clean FedAvg table.
- Clean FedAvg vs attacked FedAvg table.
- Attacked FedAvg vs robust aggregation table.
- CICIDS summary preserving final warnings.
- UNSW summary preserving A9 limitations.
- Security hash/integrity registry.
- TLS/communication overhead table if implemented.
- Reproducibility command sheet.
- Final federated/security report.
- Dashboard/XAI linkage report later.

## Failure And Rollback Policy

- Never modify `models/final/`.
- Never modify `results/final/`.
- Put future FL checkpoints under `models/federated/` or a separately approved experiment path.
- Put future FL/security results under `results/federated/` or `results/security/`.
- If a run fails, preserve logs and mark the run failed; do not overwrite clean results.
- Use explicit `--overwrite` only after main-control approval.
- Keep clean, attacked, and defense outputs separate.

## Safety And Anti-Fake-Metric Rules

- Do not present binary FedAvg as hierarchical FL.
- Do not present V1 Week 5/7 results as new V2 results.
- Do not use A11 as final.
- Do not rerun CICIDS or UNSW optimization inside this phase.
- Do not tune on test metrics.
- Do not mix attacked metrics into clean baseline tables.
- Do not claim TLS if only hashing exists.
- Do not claim secure aggregation unless implemented.
- Do not hide unresolved CICIDS and UNSW limitations.

## Exact Next Decision Needed

`approve_or_reject_federated_security_implementation_scaffold`

Recommended answer: approve a scaffold-only implementation task for V2-native robust aggregation, Byzantine attacks, SHA-256 integrity logging, deterministic tests, and no heavy runs.
