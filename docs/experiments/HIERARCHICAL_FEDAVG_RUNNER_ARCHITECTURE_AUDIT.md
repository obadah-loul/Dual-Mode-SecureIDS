# Hierarchical FedAvg Runner — Architecture Audit

Status: `architecture planning only — no implementation, no training, no evaluation`
Generated: `2026-06-25`
Companions: `docs/experiments/HIERARCHICAL_FEDAVG_IMPLEMENTATION_PLAN.md`,
`results/audits/hierarchical_fedavg_runner_architecture_audit.json`,
`results/audits/hierarchical_fedavg_runner_required_outputs.csv`.

---

## 1. Current project state

The federated/security **scaffold** is complete and tested (53 deterministic tests). What exists today:

- A real **binary** FedAvg runner (`secureids/federated/training.py`) for `SecureIDSNet`.
- Aggregation primitives: `aggregate_state_dicts_weighted` (FedAvg) and robust variants
  (`trimmed_mean`/`median`/`krum`).
- Byzantine attack transforms (`sign_flip`/`gaussian`/`scaling`) and `select_malicious_clients`.
- SHA-256 client-update integrity helpers.
- A config schema + **dry-run** validator for future hierarchical FL/security configs
  (`secureids/federated/hierarchical_plan.py`) and the `federated-plan` CLI.
- Six future federated/security configs, including the two **clean** hierarchical FedAvg configs
  (`configs/federated/experiments/{unsw,cicids}_hierarchical_clean_fedavg.yaml`, `status: not_run_yet`).

**What does not exist:** the real **hierarchical** clean FedAvg *runner*. Clean hierarchical FedAvg is
currently dry-run/config-validation only.

Official models (reference only, never modified):

| Dataset | Checkpoint | SHA-256 | Status |
| --- | --- | --- | --- |
| CICIDS2018 | `models/final/final_cicids_hierarchical.pt` | `2C15…74C0` | FINALIZED_PROMOTED_WITH_WARNINGS |
| UNSW-NB15 | `models/final/final_unsw_hierarchical.pt` | `5FE6…CBEA` | A9_ACCEPTED_FROZEN_BASELINE |

A11 is **rejected / diagnostic only** — must not be final, promoted, or used in the FL/security pipeline.

Centralized baselines used **only** for comparison (read from `results/final/hierarchical/*/test_metrics.json`):

| Dataset | Binary macro-F1 | Attack-family macro-F1 | Rare macro-F1 |
| --- | ---: | ---: | ---: |
| UNSW-NB15 (A9) | 0.894488 | 0.500429 | 0.385669 |
| CICIDS2018 | 0.974604 | 0.875094 | 0.780177 |

## 2. Areas inspected

`secureids/federated/` (fedavg, training, splitting, robust_aggregation, byzantine_attacks,
hierarchical_plan), `secureids/security/update_integrity.py`,
`secureids/models/secureids_hierarchical_advanced_net.py`,
`secureids/training/` (hierarchical_trainer, hierarchical_evaluation, hierarchical_class_weights,
hierarchical_config), the two clean FL configs, `secureids/cli.py` federated wiring, the processed
hierarchical data (`data/processed/*/hierarchical`), and the existing federated/security tests.

## 3. Scaffold status (what the runner can reuse vs must add)

**Reuse unchanged:**

- `SecureIDSHierarchicalAdvancedNet` + `compute_hierarchical_loss` (masked multi-task loss).
- `build_train_only_class_weights(dataset)` → `binary_pos_weight` + `attack_class_weights` (per class id),
  train-only, sqrt-inverse-frequency, mean-normalized, capped at 10.0.
- `collect_hierarchical_outputs` + `evaluate_hierarchical` → the full metric bundle and the
  `val_hierarchical_score = 0.5*binary_macro_f1 + 0.5*attack_family_macro_f1` selection score.
- `aggregate_state_dicts_weighted(state_dicts, sample_counts)` → sample-count FedAvg over the state dict.
- The binary runner (`training.py`) as the **structural template** (round loop, best-by-val selection,
  single final test, artifact/manifest/report writers, output guards).

**Must add:**

- The hierarchical round/client orchestration (per-client masked multi-task local training).
- An **attack-family-aware** stratified IID split (today's splitter stratifies on the binary label only).
- The FL artifact writers and the centralized-vs-FL comparison.

## 4. Binary FedAvg vs required hierarchical FedAvg

| Aspect | Binary FedAvg (today) | Hierarchical FedAvg (required) |
| --- | --- | --- |
| Model | `SecureIDSNet` (1 logit) | `SecureIDSHierarchicalAdvancedNet` (Head 1 + Head 2 + shared encoder) |
| Batch labels | `(X, y)` | `(X, y_binary, y_attack_family, attack_family_mask)` |
| Loss | `BCEWithLogitsLoss` (+ pos_weight) | `compute_hierarchical_loss` (masked multi-task; Head 2 on attack rows only) |
| Class weights | single BCE pos_weight | global train-only `binary_pos_weight` + `attack_class_weights` |
| Round selection | val binary macro-F1 | `val_hierarchical_score` (0.5/0.5) — identical to centralized |
| Aggregation | `aggregate_state_dicts_weighted` | **same** primitive over the hierarchical state dict |
| Metrics | binary + confusion | binary + attack-family + rare + routing + 2 confusion matrices |
| Client split | binary-stratified IID | **attack-family-aware** stratified IID |

The orchestration shape is the same; the model, loss, labels, weights, selection metric, metric bundle,
and split need the hierarchical extensions above.

## 5. Centralized final model usage

**Reference only.** The centralized final checkpoint is **never** loaded as FL initialization and **never**
modified. It is used solely as a fixed comparison baseline (its metrics are already in
`results/final/...`; the `.pt` is opened read-only only if a hash check is wanted). The scaffold already
enforces this: `hierarchical_plan.py` requires `centralized_reference.use == "reference_only"` and
`warm_start_from_centralized == false`.

## 6. Initialization recommendation

**From-scratch federated training with a deterministic seed; centralized checkpoint as reference only.**

Options weighed:

- **From-scratch (deterministic seed) — RECOMMENDED.** Fair (FL and centralized both start from scratch on
  the same corrected protocol), safe (the final checkpoint is never opened for weights, so it cannot be
  modified), reproducible (seed 42 fixes init/split/shuffle), and non-overclaiming (every FL number is
  honestly federated). Consistent with the binary runner and the clean-config safety flags.
- **Fine-tune from the centralized checkpoint — REJECTED.** Warm-starting inherits centralized performance
  (overclaim), risks touching `models/final`, and destroys the FL-vs-centralized comparison.
- **Centralized checkpoint loaded for any weights — REJECTED** for the same reasons; the scaffold forbids it.

So: deterministic seed-created initial weights, **not** centralized initialization.

## 7. First dataset recommendation

**UNSW-NB15 first, CICIDS2018 second.**

UNSW hierarchical fits in RAM (~149k train / 26k val / 82k test, `input_dim` 192) and trains in minutes, so
it validates the entire runner + artifact + audit pipeline cheaply before committing to the much larger
CICIDS run (~6.7M rows, `input_dim` 77). It also matches the existing seed-42 precedent and has a clean,
well-documented A9 baseline. The first run's job is **runner validation**, judged by the FL-vs-centralized
*delta*, so UNSW's weaker absolute attack-family number does not block it.

CICIDS is the better *confirmatory* run (stronger, more stable metrics) but should follow once the runner is
proven. (Honest counterpoint: if main control prioritizes the cleanest FL-quality signal over speed,
CICIDS-first is defensible.)

## 8. Runner architecture

New module `secureids/federated/hierarchical_training.py`,
entry `run_hierarchical_fedavg_training(dataset, config_path, project_root, execute, overwrite=False)`:

1. **Execute gate.** `execute=False` returns a read-only plan and writes nothing; `execute=True` validates
   preconditions, then trains.
2. **Setup.** Read `input_dim`/`attack_head_dim` from config, assert against `{CICIDS 77/14, UNSW 192/9}`;
   load the attack-family mapping (shared Head 2 label space); compute global **train-only** class weights;
   seed everything (42).
3. **Client split.** Attack-family-aware stratified IID over `y_*_train` only (Section: Client splitting).
4. **Rounds.** For each round: broadcast global state → each client copies it, runs `local_epochs` of AdamW
   with the masked multi-task loss + global weights, returns `(state_dict, sample_count)` → server runs
   `aggregate_state_dicts_weighted` → load aggregated state → evaluate **validation** with
   `evaluate_hierarchical` → track best round by `val_hierarchical_score`.
5. **Final test.** Load best-by-validation global state; evaluate **test** once with `evaluate_hierarchical`.
6. **Persist.** One federated checkpoint under `models/experiments/federated_security/`, the full metric
   bundle, round/client artifacts, FL audits, comparison table, manifest, and report.

**Dataset dims & heads** are config-driven and asserted; every client shares the same Head 2 label space.
**Class weights** are the global train-only weights for **all** clients (per-client weights are deliberately
not used, to avoid leaking client-local priors and to stay comparable to centralized).
**Checkpointing** mirrors the centralized payload plus `fl_metadata` (clients, rounds, best_round,
aggregation, seed); never writes `models/final`.

## 9. Client splitting

- **IID first, non-IID later.** `num_clients = 5`, `client_fraction = 1.0`, `seed = 42`.
- **Attack-family-aware stratified IID (required).** Today's `plan_stratified_iid_client_indices` stratifies
  only on the binary label `{0,1}`; the hierarchical split must also stratify **attack rows by family id** so
  rare families (UNSW Shellcode/Worms; CICIDS Web-XSS/SQL-Injection) keep support on every client.
- **Boundaries.** Split the **train** split only (`X_train`/`y_*_train`). Validation and test are global,
  never partitioned, never used for splitting or training — enforced by an assertion that the splitter opens
  no val/test path.
- **Audits.** Per-client total/benign/attack and per-family counts; IID balance vs the global train
  distribution; **minimum-support warnings** for any `(client, family)` below a configurable floor;
  deterministic-reproduction check (same seed → identical indices).

## 10. Aggregation

- **Full model state dict** (encoder, gate, `binary_head`, `attack_head`) via
  `aggregate_state_dicts_weighted`, **weighted by client train sample count**.
- **Buffers / non-trainable:** non-floating tensors and non-tensors are copied from the reference client, not
  averaged (LayerNorm carries no running buffers here, so all aggregated tensors are float parameters).
- **Optimizer state is NOT aggregated** — each client rebuilds AdamW per round (matches the binary runner).
- **Strict shape compatibility:** identical key set and order across clients or it aborts before aggregation.
- **Deterministic ordering:** clients processed in fixed id order for reproducible logging/hashing.
- **No final-artifact aggregation:** only in-memory client states are aggregated.
- **Robust hook:** the robust phase swaps in `aggregate_trimmed_mean`/`median`/`krum` behind the same
  `(client_states, weights)` interface, selected by `aggregation.strategy`.

## 11. Metrics

Computed by the **same** `evaluate_hierarchical` used centrally, so FL and centralized are directly
comparable: binary macro-F1; attack-family macro-F1 on attack rows; rare-class macro-F1; correctly-attributed
rate; missed-as-benign rate; benign false-alarm rate; per-class attack precision/recall/f1/support; binary
and attack-family confusion matrices; round-level validation metrics in `round_history.csv`; and a
centralized-vs-FL comparison as **deltas**.

**Labeling rule:** FL metrics are labeled "federated (clean FedAvg)" and reported as deltas vs the frozen
baseline. No FL-superiority claim unless an FL test metric beats centralized **beyond the documented
seed-noise band**, and never on a single seed. Default wording: "comparable to / within noise of / below"
centralized, with the delta shown.

## 12. Output artifacts

See `results/audits/hierarchical_fedavg_runner_required_outputs.csv`. Per run: federated checkpoint
(`models/experiments/federated_security/`), `test_metrics.json` (full bundle), `round_history.csv`,
`client_distribution.csv` + per-client logs, `client_split_audit.json`, `aggregation_audit.json`, optional
`update_integrity_audit.json`, binary + attack-family confusion CSVs, `centralized_vs_fedavg_comparison.csv`,
an FL manifest under `results/audits/`, and a `docs/experiments/...REPORT.md`.

## 13. Safety gates

`--execute` required; no writes under `models/final/` or `results/final/`; no checkpoint/result overwrite
without `--overwrite`; experiment-only output paths; A11 never referenced as final/init; centralized
checkpoint reference-only/never warm-started; test evaluated once after validation selection; no fake
metrics; no silent promotion; train-only class weights; splitter reads only `y_*_train`; no V1 modification;
seed123/seed999 only after approval; SHA-256 integrity optional and separate from the clean baseline; clean
vs attacked/robust results kept in separate trees.

## 14. Security-phase connection

1. **Clean FedAvg** (this runner) → honest federated baseline per dataset.
2. **Attacked FedAvg** → same runner, `attack.enabled=true` under plain FedAvg, to measure degradation.
3. **Robust aggregation** → `trimmed_mean`/`median`/`krum` under the same attack, to measure recovery.
4. **SHA-256 integrity** → per-round client-update records as tamper evidence (not a defense by itself).
5. **TLS / secure-aggregation** → documentation/integration evidence (`future_optional`), not an accuracy claim.

**Realistic:** clean FL comparable-to/within-noise-of/below centralized (with deltas); measured Byzantine
degradation; measured robust recovery; integrity detects modified updates. **Not realistic:** FL beats
centralized as a general claim; SHA-256 provides confidentiality/secure aggregation; robust aggregation fully
neutralizes strong/colluding attacks; TLS improves accuracy.

## 15. Implementation-ready Codex task list

1. `secureids/federated/hierarchical_training.py` — `run_hierarchical_fedavg_training` (execute gate,
   from-scratch seeded init, per-client masked multi-task training, sample-count FedAvg, best-by-val
   selection, single final test).
2. Attack-family-aware stratified IID split (extend `splitting.py` or add a hierarchical splitter) reading
   only `y_*_train`, with per-family support + minimum-support warnings.
3. FL artifact writers + centralized-vs-FL comparison + FL manifest + report.
4. Extend the clean configs' `outputs` with the new keys and extend `hierarchical_plan.py` `_validate_outputs`
   to require/validate them (still non-final paths).
5. CLI `federated-train-hierarchical` (`--dataset/--config/--execute/--overwrite`), refusing without
   `--execute`.
6. Deterministic tests (init reproducibility, split invariants/min-support, aggregation correctness on the
   hierarchical state dict, dry-run writes nothing, execute gate, no-final-path guard, oracle/routed
   separation, comparison sanity).
7. Docs/audits templates for the clean run.

## 16. Risks

CICIDS scale (run UNSW first); binary-only split would starve rare families (use family-aware split);
warm-start temptation (from-scratch enforced); single-seed overclaiming (delta labeling, no single-seed
promotion); accidental final-path writes (guards + experiment-only paths); per-client weights leaking priors
(use global train-only weights); mixing clean/attacked results (separate trees); non-determinism (fixed seed,
deterministic ordering).

## 17. Exact next decision

**`approve_or_reject_codex_hierarchical_fedavg_runner_implementation`** — approve Codex to implement the real
hierarchical clean FedAvg runner per this audit and the companion implementation plan (code + tests + config
extension + CLI; **execution still gated on a separate later approval**), or defer. No training runs until a
separate approval of a specific `--execute` command.
