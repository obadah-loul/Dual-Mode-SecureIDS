# Hierarchical FedAvg Runner — Implementation Plan (for Codex)

Status: `implementation-ready planning only — do not implement the runner yet`
Generated: `2026-06-25`
Companions: `docs/experiments/HIERARCHICAL_FEDAVG_RUNNER_ARCHITECTURE_AUDIT.md`,
`results/audits/hierarchical_fedavg_runner_architecture_audit.json`,
`results/audits/hierarchical_fedavg_runner_required_outputs.csv`.

This document specifies exactly how Codex should implement the real hierarchical **clean** FedAvg runner once
main control approves. It is implementation-ready but **no runner is implemented here**.

---

## 0. Guiding principles

- Reuse the centralized hierarchical model, loss, weights, and evaluator unchanged so FL and centralized are
  directly comparable.
- From-scratch deterministic init; centralized final checkpoint is **reference only** (never warm-started,
  never modified).
- Honest reporting: deltas vs the frozen baseline; no single-seed superiority claim.
- All outputs land in **experiment** trees; `models/final` and `results/final` are never written.

## 1. Phase-by-phase plan

**Phase A — Runner core (UNSW-validated).**
Implement `run_hierarchical_fedavg_training` with the execute gate, from-scratch seeded init, per-client
masked multi-task local training, sample-count FedAvg aggregation, best-by-validation selection on
`val_hierarchical_score`, and a single final test. Validate end-to-end on UNSW (smallest).

**Phase B — Client splitting + audits.**
Add the attack-family-aware stratified IID split and the client-split audit (per-family support,
minimum-support warnings, IID balance check). Reads only `y_*_train`.

**Phase C — Artifacts + comparison + manifest + report.**
Write `test_metrics.json` (full bundle), `round_history.csv`, `client_distribution.csv`, per-client logs,
`aggregation_audit.json`, optional `update_integrity_audit.json`, binary/attack-family confusion CSVs,
`centralized_vs_fedavg_comparison.csv`, the FL manifest (`results/audits/...manifest.json`), and the
`docs/experiments/...REPORT.md`.

**Phase D — Config extension + dry-run validator.**
Extend both clean configs' `outputs` with the new keys and extend `hierarchical_plan.py` `_validate_outputs`
to require/validate them (still non-final). Confirm `federated-plan` dry-run still passes.

**Phase E — CLI + tests.**
Add `federated-train-hierarchical` and the deterministic test suite (Section 5).

**Phase F — CICIDS confirmatory run.** Only after UNSW passes and is reviewed.

## 2. Code modules to add / modify

**Add:**

- `secureids/federated/hierarchical_training.py` — the runner.
  - `run_hierarchical_fedavg_training(dataset, config_path, project_root, execute, overwrite=False)`.
  - Internal helpers: `_validate_pre_run` (dims/heads, data presence, output guards, no-overwrite),
    `_train_local_client` (masked multi-task local epochs), `_aggregate_round`
    (`aggregate_state_dicts_weighted`), `_evaluate_split` (wraps `evaluate_hierarchical`),
    `_write_fl_artifacts`, `_build_fl_manifest`, `_write_fl_report`, `_build_comparison_table`.
  - Reuse from `secureids.training.hierarchical_trainer`: `build_model`, `_load_split_arrays`,
    `_split_to_tensors`, `_make_loader` (or equivalents). Reuse `compute_hierarchical_loss`,
    `build_train_only_class_weights`, `collect_hierarchical_outputs`, `evaluate_hierarchical`.

**Modify:**

- `secureids/federated/splitting.py` — add `plan_attack_family_stratified_iid_client_indices(y_binary_train,
  y_attack_family_train, attack_family_mask_train, num_clients, seed)` that stratifies benign rows by the
  binary label and attack rows by family id; returns indices + a support summary. Keep the existing binary
  splitter untouched for the binary runner.
- `configs/federated/experiments/{unsw,cicids}_hierarchical_clean_fedavg.yaml` — add output keys
  (`client_split_audit`, `aggregation_audit`, `update_integrity_audit`, `round_metrics`,
  `per_client_metrics`, `comparison_table`); keep `status: not_run_yet`.
- `secureids/federated/hierarchical_plan.py` — extend `_validate_outputs` to require/validate the new keys
  (still rejecting final paths); keep all existing safety checks.
- `secureids/cli.py` — add the `federated-train-hierarchical` subcommand + handler.

**Do NOT modify:** `secureids/federated/training.py` (binary runner), the centralized
`hierarchical_trainer.py`/`hierarchical_evaluation.py` logic (import and reuse only),
`secureids/models/secureids_hierarchical_advanced_net.py`, anything under `models/final` or `results/final`.

## 3. Config plan

Both clean configs already define: `status`, `dataset`, `task: hierarchical_federated`, `model`
(architecture/`input_dim`/`attack_head_dim`), `hierarchical_data`, `centralized_reference`
(`use: reference_only`, `warm_start_from_centralized: false`), `federation` (5 clients, stratified_iid, seed
42, rounds 20, fraction 1.0, local_epochs 1, execute_gate_required), `aggregation: fedavg`, `attack: none`,
`integrity` (sha256 on), `outputs` (7 keys), and `safety`.

Codex adds to `outputs` (experiment paths only):
`per_client_metrics`, `client_split_audit`, `aggregation_audit`, `update_integrity_audit`, `round_metrics`,
`comparison_table`. The client-split policy should be recorded as `client_split: attack_family_stratified_iid`
once the new splitter exists (and `hierarchical_plan.py` updated to allow it).

## 4. CLI plan

```
python -m secureids.cli federated-train-hierarchical \
  --dataset {unsw|unsw_nb15|cicids|cicids2018} \
  --config <path to clean hierarchical FedAvg config> \
  [--execute] [--overwrite]
```

Without `--execute`: print "Hierarchical FedAvg requires --execute. No training was started." and return 1
(write nothing). With `--execute`: run the runner; on `FederatedTrainingError`/`FileNotFoundError`, print the
error + "No federated outputs were created" and return 1. Mirror the existing `handle_federated_train`
structure.

## 5. Tests to add (deterministic, torch where needed)

- `test_hierarchical_fedavg_init_reproducible` — same seed → identical initial state dict.
- `test_attack_family_stratified_split` — every client has benign + attack rows; each present family's
  per-client support is within IID tolerance; min-support warning fires when a family is too small; same seed
  → identical indices; no val/test path opened.
- `test_hierarchical_state_dict_aggregation` — `aggregate_state_dicts_weighted` on two known hierarchical
  state dicts equals the sample-weighted mean for float params and copies non-float buffers.
- `test_hierarchical_fedavg_dry_run_writes_nothing` — `execute=False` returns a plan, creates no files,
  modifies no checkpoint.
- `test_hierarchical_fedavg_execute_gate` — calling without `--execute` writes nothing and returns 1.
- `test_hierarchical_fedavg_no_final_path` — config pointed at a `models/final`/`results/final` output is
  rejected.
- `test_hierarchical_fedavg_round_selection` — best round chosen by `val_hierarchical_score`, test evaluated
  once after selection (assert on a tiny synthetic 1-round case).
- `test_centralized_vs_fedavg_comparison_labeling` — comparison table reports deltas and never emits a
  "superior" label from a single seed.
- A guard test that the binary runner (`training.py`) and `models/final` are untouched.

## 6. Future manual run commands (require separate approval; do not run now)

```
# Run 1 (first): UNSW-NB15 clean hierarchical FedAvg, seed 42
python -m secureids.cli federated-train-hierarchical \
  --dataset unsw \
  --config configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml \
  --execute

# Run 2 (confirmatory): CICIDS2018 clean hierarchical FedAvg, seed 42
python -m secureids.cli federated-train-hierarchical \
  --dataset cicids \
  --config configs/federated/experiments/cicids_hierarchical_clean_fedavg.yaml \
  --execute
```

Expected count: **1** approved manual run first (UNSW). CICIDS follows only after UNSW is reviewed.
seed123/seed999 multi-seed confirmation only on later main-control approval.

## 7. Output paths (per run)

- Checkpoint: `models/experiments/federated_security/<dataset>_hierarchical_clean_fedavg.pt`
- Result dir: `results/experiments/federated_security/<dataset>_hierarchical_clean_fedavg/`
  (`test_metrics.json`, `round_history.csv`, `client_distribution.csv`, per-client logs,
  `client_split_audit.json`, `aggregation_audit.json`, optional `update_integrity_audit.json`,
  `binary_confusion_matrix.csv`, `attack_family_confusion_matrix.csv`,
  `centralized_vs_fedavg_comparison.csv`)
- Manifest: `results/audits/federated_security_<dataset>_hierarchical_clean_fedavg_manifest.json`
- Report: `docs/experiments/FEDERATED_SECURITY_<DATASET>_HIERARCHICAL_CLEAN_FEDAVG_REPORT.md`

(`<dataset>` ∈ {`unsw`, `cicids`}; the configs already encode these exact paths.)

## 8. Do-not-do list

- Do not warm-start from or modify any centralized final checkpoint; do not write `models/final` or
  `results/final`.
- Do not use A11 as final or as initialization.
- Do not use per-client class weights; use the global train-only weights.
- Do not aggregate optimizer state.
- Do not partition or train on validation/test; do not use test for round/checkpoint selection.
- Do not fabricate metrics or claim FL superiority from one seed.
- Do not mix clean results with attacked/robust results.
- Do not modify V1, the binary FedAvg runner, or the centralized evaluator logic.
- Do not run training/evaluation/preprocessing/XAI/Streamlit/Git as part of implementation.

## 9. Expected validation before any manual run

- `python -m json.tool` on the two audit JSONs (this task) passes; CSV imports.
- After implementation: full test suite green (existing 53 + the new hierarchical FedAvg tests).
- `python -m secureids.cli federated-plan --config <clean config>` dry-run still PASSES with the extended
  outputs.
- A dry-run (`execute=False`) of the runner writes nothing and modifies no checkpoint.
- A tiny synthetic smoke (few rows, 1 round) confirms shapes/metrics before any full `--execute` run.

## 10. Next decision

**`approve_or_reject_codex_hierarchical_fedavg_runner_implementation`** — approve Codex to implement Phases
A–E (code + tests + config extension + CLI) with execution still gated, or defer. The first real run (UNSW,
seed 42) is a **separate** approval after the runner and its tests are in place and reviewed.
