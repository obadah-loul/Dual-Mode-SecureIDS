# Pre-Training Code, Design, and Result-Quality Audit (Task A8.75)

> **A8.8 update (2026-06-24):** The two HIGH findings below are now **RESOLVED**.
> **F1** (UNSW split) — corrected to the standard benchmark protocol (train on the
> 175,341-row partition, test on 82,332; feature dim 190→192); UNSW artifacts
> regenerated; legacy binary baselines preserved and marked pre-correction. See
> [UNSW_SPLIT_PROTOCOL_DECISION.md](UNSW_SPLIT_PROTOCOL_DECISION.md). **F2**
> (class-weight wiring) — `compute_hierarchical_loss` now applies the locked binary
> and attack-family weights, proven by `tests/test_hierarchical_weighted_loss.py`. See
> [PRE_TRAINING_HIGH_FINDINGS_RESOLUTION.md](PRE_TRAINING_HIGH_FINDINGS_RESOLUTION.md).
> The conditional go is now a **clean GO** for implementing/running UNSW A9 training.

Status: `Audit complete — no training, checkpoints, or final metrics were created`
Generated UTC: `2026-06-24`
Auditor scope: full V2 codebase, configs, docs, tests, processed data, mappings, and safety guards
Project: Secure, Robust, Explainable, and Hierarchical Federated Intrusion Detection System
Final system: `SecureIDSHierarchicalAdvancedNet`

---

## 1. Executive Summary

The V2 project is in a clean, safe, well-organized state immediately before its first
real centralized hierarchical training. The engineering foundation is strong:
`compileall` is clean, the full test suite passes (87/87), the A8 readiness gate and
the A8.5 class-weight lock both report `PASS` for both datasets, no final hierarchical
checkpoints or metrics exist yet, the binary baselines are preserved, and `.gitignore`
correctly excludes data, virtual environments, checkpoints, keys, and the scratch
`draft/` folder. There is one organized final architecture (no competing or V1-dumped
models), and the future-stage modules are empty placeholders.

The audit nevertheless found two **HIGH** issues that should be resolved or explicitly
accepted **before** the first real UNSW run, because the first run will bake them into
the headline final model:

1. **F1 — UNSW official train/test partition appears swapped.** The physical raw files
   are sized opposite to the canonical UNSW-NB15 partition, so V2 trains on the smaller
   canonical-test split (82,332 rows → 69,982 train) and evaluates on the larger
   canonical-train split (175,341 rows). This inverts the standard protocol, discards
   ~53% of available training data, shrinks rare-class support, and makes results
   non-comparable to published benchmarks. It is not a leakage bug, but it is a
   result-quality and comparability bug.

2. **F2 — The masked loss cannot apply the A8.5-locked attack-family class weights.**
   `compute_hierarchical_loss` has no `weight=` path for the attack head. The locked
   rare-class weights would be silently ignored unless A9 extends the loss — which would
   directly undermine the project's rare-class objective.

Neither issue blocks the *pipeline* from running, and neither is a defect in already-run
work; both are forward-looking risks for the A9 training implementation. The remaining
findings are MEDIUM (model-selection stability on tiny rare-class validation support,
unimplemented final metrics, and class-weight definition/application consistency) and LOW
(stale config labels, encoder-unknowns, a minor clip mismatch).

**Decision: CONDITIONAL GO** for implementing and running UNSW full centralized
hierarchical training in A9, conditioned on resolving/accepting F1 and committing to
correct class-weight wiring (F2/F5/F6) in the A9 trainer.

---

## 2. Audit Scope

Performed (read-only inspection + allowed safe commands):

- Project architecture and file organization
- Dataset and preprocessing logic (binary → hierarchical reuse)
- Hierarchical label / mask / ignore-index integrity
- Model architecture and masked multi-task loss
- Class-weight strategy (readiness preview + A8.5 lock)
- Planned metrics validity and model-selection protocol
- Training-readiness gate and CLI command safety
- Result/artifact safety and overwrite protection
- No-fake-results and validation/test separation
- V1/V6 reuse policy compliance

Explicitly NOT done (per task constraints): no full training, no UNSW/CICIDS real
training, no hierarchical FedAvg, no security/attacks/Trimmed Mean/XAI/dashboard work,
no checkpoints or final metrics, no Git operations, no V1 modification, no deletions or
overwrites of checkpoints/results.

---

## 3. Files Inspected (representative)

Source:
- `secureids/models/secureids_hierarchical_advanced_net.py` (model + masked loss)
- `secureids/preprocessing/hierarchical.py`, `splitting.py`
- `secureids/training/hierarchical_config.py`, `hierarchical_readiness.py`,
  `hierarchical_class_weights.py`, `hierarchical_smoke.py`, `hierarchical_datasets.py`,
  `hierarchical_metrics.py`, `metrics.py`
- `secureids/cli.py`

Configs:
- `configs/training/unsw_nb15_hierarchical.yaml`, `cicids2018_hierarchical.yaml`
- `configs/preprocessing/unsw_nb15_binary.yaml`
- `configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`

Data / artifacts:
- `data/processed/{unsw_nb15,cicids2018}/hierarchical/` (arrays, mappings, split summary, manifest)
- `data/raw/unsw_nb15/UNSW_NB15_{training,testing}-set.csv` (row counts only)
- `models/final/`, `models/federated/`, `results/audits/`, `results/final/`

Docs and tests: the `docs/` stage reports and all 16 test modules under `tests/`.

---

## 4. Commands Run (all safe / non-training)

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m compileall secureids tests -q` | exit 0 (clean) |
| `.venv/Scripts/python.exe -m pytest tests -q` | 87 passed in ~6s |
| `... -m secureids.cli check-hierarchical-training-readiness --dataset all` | PASS / PASS |
| `... -m secureids.cli lock-hierarchical-class-weights --dataset all` | PASS / PASS (max final attack weight: CICIDS 5.53, UNSW 3.86) |
| `wc -l data/raw/unsw_nb15/*.csv` | training-set=82,332 rows, testing-set=175,341 rows |

> Note: the two CLI audit commands above are the task-recommended safe commands. They
> regenerated their own audit JSONs/reports deterministically (content identical except
> the `created_at_utc` timestamp). No training artifacts were produced.

---

## 5. Current Project Status

- Final architecture implemented as a single model (`SecureIDSHierarchicalAdvancedNet`),
  ~485k params (CICIDS, input_dim 77, attack_head_dim 14) / ~513k params
  (UNSW, input_dim 190, attack_head_dim 9), embedding_dim 128 — appropriate for tabular IDS.
- Hierarchical processed data present and integrity-verified for both datasets; all Head 2
  classes present in train/val/test for both datasets.
- A8 readiness gate PASS; A8.5 class-weight strategy locked and PASS.
- **No hierarchical training loop or `train-hierarchical` CLI command exists yet** — this is
  the A9 deliverable. The planned "do-not-run" command would currently fail with an
  argparse error (safe).
- Binary baselines preserved; no final hierarchical artifacts exist.

---

## 6. Issue Table

| ID | Severity | Area | Title |
| --- | --- | --- | --- |
| F1 | HIGH | Dataset/preprocessing | UNSW official train/test partition appears swapped (train on smaller canonical-test split) — **RESOLVED in A8.8** |
| F2 | HIGH | Loss/class weighting | Masked loss cannot apply the A8.5-locked attack-family class weights — **RESOLVED in A8.8** |
| F3 | MEDIUM | Metrics/selection | Tiny rare-class validation support makes val attack-family macro-F1 selection unstable |
| F4 | MEDIUM | Metrics | Final hierarchical metric computation not implemented (only smoke diagnostics) |
| F5 | MEDIUM | Loss/class weighting | Two divergent "sqrt inverse-frequency" definitions coexist |
| F6 | MEDIUM | Loss/class weighting | Binary class-weight application path must match the locked strategy explicitly |
| F7 | LOW | Configs | Stale stage labels (`task_a6_design_only...`, `a6_design_only: true`) in hierarchical configs |
| F8 | LOW | Dataset/preprocessing | UNSW one-hot fit on smaller swapped train partition increases unknown-category encodings at test |
| F9 | LOW | Configs | `class_weight_min_clip` mismatch (config 0.0 vs readiness default 0.1) |
| F10 | INFO | Artifact safety | Strong pipeline safety; no fake/leaked artifacts |
| F11 | INFO | Architecture | Single final architecture; no competing/V1-dumped models |
| F12 | INFO | Readiness/CLI | Hierarchical trainer not implemented yet (expected A9 scope) |

Counts: **BLOCKER 0 · HIGH 2 · MEDIUM 4 · LOW 3 · INFO 3**.

Full detail (impact, recommendation, evidence) is in
`results/audits/pre_training_code_audit.json` and
`results/audits/pre_training_code_audit_findings.csv`.

---

## 7. Risk Analysis

### 7.1 Result-Quality Risks
- **F1 (HIGH).** Training on the smaller canonical-test partition (82,332) and evaluating
  on the larger canonical-train partition (175,341) reduces training data, weakens
  rare-class learning (e.g. UNSW Worms train support = 40 instead of ~130), and breaks
  comparability with the standard UNSW-NB15 protocol. Verified by raw row counts and by the
  attack-count match (V2 test attack rows 119,341 = canonical training-set; V2 train+val
  attack rows 45,332 = canonical testing-set).
- **F4/F5/F6 (MEDIUM).** If final metrics are computed over a variable observed-class set, or
  if the locked class weights are not applied exactly, the reported numbers can be either
  inflated or unfairly weak — both misleading.

### 7.2 Reproducibility Risks
- Seeds are fixed in configs (seed 42) and the loaders use deterministic generators. Audit
  JSONs/manifests record provenance. **Risk:** the A9 trainer must persist the exact applied
  class-weight tensors and selection metric in the training manifest so results are
  reproducible; this is not yet implemented (F12).

### 7.3 Leakage / No-Fake-Results Risks
- **Low.** Scalers/encoders/imputers fit `train_only` (binary config); hierarchical X arrays
  are byte-copied from the binary processed arrays (shape-verified), so no refit on val/test.
  Class weights are computed strictly from train arrays (`validation_files_read=[]`,
  `test_files_read=[]`). Checkpoint selection is configured validation-only with a single
  final test (`use_validation_only: true`, `select_by_test_metrics: false`,
  `final_test_once_after_best_validation: true`). The common superclass mapping is
  reporting-only (`common_superclass_is_training_target: false`). No fake shared
  CICIDS/UNSW multiclass label list exists.

### 7.4 Training Stability Risks
- Masked loss is NaN-safe: all-benign batches return a zero attack-loss tensor on the correct
  device/dtype; attack rows are pre-filtered before `cross_entropy`. Forward/loss verified by
  the readiness gate on a real batch for both datasets. Model uses LayerNorm + GELU + dropout
  0.2 + residual/gated blocks — stable for tabular data. AdamW, lr 1e-3, weight decay 1e-4,
  early stopping on `val_hierarchical_score`. **Residual risk:** F3 (noisy rare-class
  validation) can destabilize *checkpoint selection*, not the optimizer.

### 7.5 Class-Imbalance / Rare-Class Risks
- The A8.5 lock keeps max final attack weights well within the cap (CICIDS 5.53, UNSW 3.86),
  avoiding the dangerous raw inverse-frequency values (raw max ~2181 CICIDS, ~107 UNSW). But
  **F2** means those weights have no application path yet, and **F3** means rare-class
  validation signal is extremely thin (UNSW Worms val=4). These two together are the main
  threat to the rare-class story and must be handled in A9.

### 7.6 Artifact-Safety Risks
- **Low.** No `final_*_hierarchical.pt` and no `results/final/hierarchical/` exist. The A8
  readiness gate refuses to proceed if planned final outputs already exist and asserts the
  binary baselines are preserved. **Residual risk:** the not-yet-written `train-hierarchical`
  command must replicate the binary command's `--execute` / `--overwrite` guards so a re-run
  cannot silently clobber a finished hierarchical checkpoint (F12 recommendation).

---

## 8. Recommended Fixes Before A9

Ordered by priority:

1. **Resolve F1 (UNSW partition).** Confirm whether the raw files were swapped at placement.
   Then either correct the assignment (train on the canonical 175,341-row partition; this
   requires re-running binary + hierarchical preprocessing and re-locking baselines) **or**
   make an explicit, documented decision to keep the non-standard split and label all UNSW
   results accordingly. Do not proceed silently.
2. **Close F2/F5/F6 in the A9 trainer.** Extend `compute_hierarchical_loss` to accept and
   apply an `attack_class_weights` tensor (`F.cross_entropy(weight=...)`), load the exact
   `final_weights` from the A8.5 lock JSON (single source of truth), derive the binary
   `pos_weight` from the locked binary weights, move all weights to the batch device, and add
   a unit test proving the weights change the loss.
3. **Address F3 (selection stability).** Report rare-class validation F1 with support, and
   prefer a selection signal that is robust to n=4 classes (e.g. macro-F1 over sufficiently
   supported classes plus a separate rare-class diagnostic). Keep selection validation-only.
4. **Implement F4 (final metrics).** Per-class precision/recall/F1/support, attack-family
   macro-F1 over the full fixed class set, rare-class macro-F1 over the documented rare set,
   binary + attack confusion matrices, weak/hard-class report, validation-vs-test gap, and a
   precisely-defined end-to-end hierarchical metric. Keep smoke outputs non-final.
5. **Tidy F7/F9 (LOW).** Update stale config stage labels when A9 starts; document the unused
   `min_clip` under the locked strategy.

This audit changed **no** source code or configs (only created the audit deliverables and
re-ran the two recommended safe audit commands).

---

## 9. Go / No-Go Decision

**CONDITIONAL GO** for UNSW full centralized hierarchical training in A9.

- The pipeline scaffolding, safety guards, tests, readiness gate, and class-weight lock are
  all green, and no fake/leaked/competing artifacts exist.
- Proceed to **implement A9** (trainer + class-weight wiring + final metrics + guarded CLI).
- The resulting UNSW **result will only be valid and non-misleading** if, before the run:
  - **F1** is resolved or explicitly accepted-and-documented, and
  - the A9 trainer **actually applies** the A8.5-locked class weights (F2/F5/F6).
- CICIDS hierarchical training should remain deferred until after UNSW, as planned.

No-Go conditions (would flip to NO-GO): running UNSW training while still silently using the
swapped partition *and* an unweighted attack head, which would produce a weak, non-standard,
non-comparable rare-class result presented as the final model.

---

## 10. Safety Confirmation

- No full training, no UNSW/CICIDS real training, no hierarchical FedAvg.
- No final hierarchical checkpoints or final metrics created.
- No security/attacks/Trimmed Mean/XAI/dashboard work started.
- No checkpoints or final results overwritten; binary baselines preserved.
- No Git operations; V1 not modified; nothing deleted.
- Only documentation/audit files created; the two recommended audit commands were re-run and
  regenerated their own deterministic audit outputs.
