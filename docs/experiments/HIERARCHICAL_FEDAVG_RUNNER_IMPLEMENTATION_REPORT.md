# Hierarchical FedAvg Runner Implementation Report

Status: `IMPLEMENTED_AS_SCAFFOLD_NO_TRAINING`

Generated for main-control review: `2026-06-25`

## Decision

The real V2 hierarchical FedAvg runner implementation is now prepared for future manual execution. This task implemented code, clean configs, tests, documentation, and audit scaffolding only.

No actual federated training was run. No clean FedAvg experiment was run. No attacked or robust-defense experiment was run. No checkpoint, final metric, final result, preprocessing output, XAI output, dashboard output, or Git action was created.

## Runner Implemented

Added `secureids/federated/hierarchical_training.py` for future approved hierarchical FedAvg runs. The runner supports:

- hierarchical processed data loading
- deterministic attack-family-aware client splitting
- from-scratch hierarchical model initialization
- local hierarchical client training behind `--execute`
- weighted FedAvg aggregation by client sample count
- SHA-256 update integrity verification before aggregation
- validation-based best-round selection for future actual runs
- test reporting once after future validation selection
- experiment-only checkpoint, metrics, audit, and report paths
- dry-run validation that writes nothing

The dry-run path validates configuration and output safety but does not create output directories, reports, checkpoints, metrics, or manifests.

## Client Split

`secureids/federated/splitting.py` now includes attack-family-aware IID split planning. The split uses train labels only, assigns every train row exactly once, keeps validation and test splits global, and produces binary plus attack-family distribution audits. It also emits warnings when rare attack families are absent from one or more clients.

This replaces binary-only splitting for the clean hierarchical FedAvg configs because binary-only splitting can hide Head 2 rare-family starvation.

## Aggregation And Integrity

Clean hierarchical FedAvg uses weighted state-dict aggregation by client sample count through the existing robust aggregation utility. Client updates are hashed with SHA-256 evidence before aggregation and verified before aggregation. This is update integrity evidence, not production secure aggregation.

Tests verify weighted aggregation, audit structure, and tamper rejection through the runner hook.

## Config Updates

Updated only the two approved clean hierarchical FedAvg configs:

- `configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml`
- `configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml`

Both now specify:

- `initialization: from_scratch`
- `warm_start_from_centralized: false`
- `client_split: attack_family_aware_iid`
- local epochs, global rounds, seed, batch size, learning rate, optimizer, weight decay, threshold
- centralized final checkpoint path and SHA-256 as reference-only metadata
- centralized reference metrics for comparison only
- experiment-only checkpoint and result paths
- A11 excluded as final

## Centralized References

UNSW reference:

- checkpoint: `models/final/final_unsw_hierarchical.pt`
- SHA-256: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- status: `A9_ACCEPTED_FROZEN_BASELINE`

CICIDS reference:

- checkpoint: `models/final/final_cicids_hierarchical.pt`
- SHA-256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- status: `FINALIZED_PROMOTED_WITH_WARNINGS`

These checkpoints are reference-only. The future FL model initializes from scratch and must not warm-start from centralized final checkpoints.

## A11 Exclusion

A11 remains a rejected diagnostic only. It is not used as the UNSW final reference, not used as a federated baseline, not promoted, and not used in any output path.

## CLI

Added:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli federated-train-hierarchical --config "configs\federated\experiments\unsw_hierarchical_clean_fedavg.yaml"
```

Without `--execute`, the command is dry-run only and writes nothing. With `--execute`, the future actual-run path exists in code, but it must not be used until main control approves.

## Validation Run Now

Targeted lightweight tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_hierarchical_federated_training.py tests/test_hierarchical_federated_splitting.py tests/test_hierarchical_federated_cli.py tests/test_hierarchical_federated_config.py tests/test_federated_robust_aggregation.py tests/test_update_integrity.py tests/test_hierarchical_federated_plan.py tests/test_federated_plan_cli.py -q
```

Result: `33 passed in 2.20s`

CLI dry-runs run now:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli federated-train-hierarchical --config "configs\federated\experiments\unsw_hierarchical_clean_fedavg.yaml"
.\.venv\Scripts\python.exe -m secureids.cli federated-train-hierarchical --config "configs\federated\experiments\cicids_hierarchical_clean_fedavg.yaml"
```

Both returned `PASS`. Planned experiment checkpoint, result directory, metrics JSON, and report paths remained absent after dry-run.

Final checkpoint hashes were checked and still match the official references.

## Claims Allowed

Allowed claims:

- The hierarchical FedAvg runner is implemented.
- The clean hierarchical FedAvg configs are ready for future dry-run and manual execution approval.
- Dry-run validation writes nothing.
- Centralized final checkpoints are reference-only.
- Future FL runs initialize from scratch.
- Targeted lightweight tests passed.

Claims not allowed:

- No FL model has been trained.
- No FL checkpoint exists from this task.
- No clean FedAvg result exists.
- No attacked or robust-defense result exists.
- No FL metrics exist.
- No promotion decision exists.

## Why UNSW First

UNSW clean hierarchical FedAvg should run first because it is the lighter future manual run and uses the accepted A9 centralized baseline only as reference metadata. CICIDS should run second because it is heavier and already has a promoted centralized final checkpoint with warnings.

## Next Manual Run

First future manual run, DO NOT RUN until main-control approves:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli federated-train-hierarchical --config "configs\federated\experiments\unsw_hierarchical_clean_fedavg.yaml" --execute
```

## Exact Next Decision Needed

Main control must decide whether to approve or reject the manual UNSW clean hierarchical FedAvg run.
