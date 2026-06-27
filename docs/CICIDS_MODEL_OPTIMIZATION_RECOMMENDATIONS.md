# CICIDS Model-Optimization Recommendations (Pre-Training)

Status: `Recommendations / design only`. No code, config, checkpoint, or metric was changed. These
are proposals for main-control decision before/after the first CICIDS hierarchical training.

Generated: `2026-06-24`

Companion: `docs/CICIDS_DEEP_PRETRAINING_ENGINEERING_AUDIT.md`,
`results/audits/cicids_deep_pretraining_engineering_audit.json`,
`results/audits/cicids_model_optimization_recommendations.csv`.

Classes used: `apply_before_training`, `apply_after_baseline`, `reject`, `needs_main_chat_decision`.
Severities: `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`, `IMPROVEMENT`.

---

## 1. Recommendation summary

The CICIDS hierarchical setup is **fundamentally sound** (clean data, correct labels/masks/metrics,
safe train-only class weights, a correct CLI gate, a clean adapter/router layer). It should reach
**strong, honest** results. But **two HIGH issues must be fixed before the first run** — otherwise
the provided command either aborts or emits UNSW-mislabeled CICIDS artifacts. After a clean baseline,
a short list of approval-gated improvements can push quality and rigor further without faking
results. **No major architecture change is recommended before the baseline.**

Final call: **PROCEED_AFTER_SAFE_FIXES** (apply H1 + H2, plus the optional safe M1 micro-fix).

---

## 2. Apply before training (safe, mandatory or low-risk)

### H1 — Distinct CICIDS report path (HIGH, apply_before_training, needs main-control)
- **Change:** in `configs/training/cicids2018_hierarchical.yaml`, set
  `outputs.report_md: docs/HIERARCHICAL_TRAINING_REPORT_CICIDS2018.md` (currently
  `docs/HIERARCHICAL_TRAINING_REPORT.md`, which is the UNSW A9 report).
- **Evidence:** the shared file exists; the trainer overwrite guard + plan `future_final_outputs_absent`
  will block the run, and `--overwrite` would destroy the A9 report.
- **Benefit:** the as-is command can run cleanly and A9 is preserved. **Risk:** Low (config only).
  **Scope:** 1 line. **Scientific claims:** none. **UNSW comparability:** unaffected. **New tests:**
  optional (assert CICIDS report path is distinct from UNSW).

### H2 — Dataset-aware report / protocol / manifest text (HIGH, needs_main_chat_decision, before training)
- **Change:** in `secureids/training/hierarchical_trainer.py`, derive the protocol string, report
  title, and scope text from `config.dataset` (and `split_summary` sizes) instead of the hardcoded
  UNSW strings at `_build_test_metrics_payload` line 587, `_write_report` lines 738/740/746-748, and
  `_build_manifest`.
- **Evidence:** a CICIDS run would otherwise emit `dataset: cicids2018` with `protocol: "UNSW ...
  175,341 rows"` and a UNSW-titled report.
- **Benefit:** truthful, professor-facing CICIDS artifacts. **Risk:** Low-Medium (shared trainer code
  — keep UNSW output byte-identical for the UNSW config). **Scope:** small, localized to the writers.
  **Scientific claims:** fixes a correctness defect (does not inflate anything). **UNSW comparability:**
  unaffected if UNSW text is preserved. **New tests:** yes — assert the CICIDS report/metrics carry
  CICIDS labels (dataset, row counts) and no "UNSW"/"175,341" strings.

### M1 — Drop the float64 upcast in the finite check (MEDIUM, apply_before_training, optional, low-risk)
- **Change:** in `_validate_split_labels`, replace `np.isfinite(np.asarray(X, dtype=np.float64))` with
  a float32-friendly finite check (optionally chunked); optionally `mmap` X in `_load_split_arrays`.
- **Evidence:** ~4.15 GB transient for the 6.74M-row train split; eager all-split load ~3 GB.
- **Benefit:** lower host-RAM peak on CICIDS; no metric change. **Risk:** Very low. **Scope:** tiny.
  **Scientific claims:** none. **UNSW comparability:** none. **New tests:** not required.

### L3 — Per-dataset report naming default (LOW, apply_before_training)
- Operationally covered by H1; make the trainer's default report name include the dataset to prevent
  future collisions.

---

## 3. Apply after baseline (improve quality/rigor honestly)

### M2 — Document the random-split + near-duplicate caveat (MEDIUM, after_baseline, needs main-control)
- val/test are i.i.d. (identical distributions) → good transfer, but random-split CICIDS can leak
  near-duplicate flows across splits and inflate metrics. Report the split type and caveat. Do **not**
  change the split before the baseline (it breaks comparability and is a major change).

### L1 / L2 — Reporting clarity (LOW, after_baseline)
- L1: state that the **sqrt-inverse-frequency mean-normalized** weights (max 5.527) are the applied
  set (not the capped-balanced max-10 preview). L2: report per-class **support** with F1 and flag
  tiny classes (SQL-Injection 12 test rows, Web-XSS 38).

### I1 — Validation-only threshold calibration (IMPROVEMENT, after_baseline, needs main-control)
- Calibrate the Head 1 routing threshold on **validation only** (V1 `calibration_v5.py` idea) to
  trade benign-FP vs attack-FN without retraining. i.i.d. split → should transfer well. **Must** stay
  validation-only (no test tuning).

### I4 — Multi-seed evaluation (IMPROVEMENT, after_baseline)
- After the first baseline, repeat with ≥3 seeds and report mean ± std for headline and rare/weak
  classes, consistent with the UNSW methodology. Stabilizes the noisy tiny-class metrics.

### M3 — Converge readiness/trainer data paths (MEDIUM, after_baseline)
- Optional refactor so readiness validates the exact training data path. Low risk now.

---

## 4. Needs main-control decision (do not do without approval)

### I2 — Optional non-linear Head 2 branch for CICIDS (IMPROVEMENT, needs main-control)
- The model already supports `attack_head_type: mlp` (A9.7-prep). For CICIDS the families are more
  separable, so the **linear baseline should be trained first**. Only consider `mlp` as a later,
  one-factor controlled experiment if baseline Head 2 (esp. Infiltration / Web / SQL) is weak. **Do
  not** bundle it into the first run (would confound the baseline).

### I3 — Split-conflict / near-duplicate audit (IMPROVEMENT, needs_main_chat_decision)
- A read-only audit (V1 `conflict_audit.py` / `split_builder.py` idea) to quantify cross-split
  near-duplicate flows and honestly bound any inflation. Idea only — **do not copy V1 code**.

---

## 5. Reject (do not pursue now)

- **V1-style specialists/ensembles/experiment grids** (`specialists_v5.py`, `ensemble_v5.py`):
  conflict with V2's clean single organized system; reintroduce mess and many competing models.
  **Reject** for V2.
- **Oversampling / SMOTE for rare classes:** project policy disables oversampling; rare-class recall
  is typically already lifted by the capped sqrt weights, and oversampling risks precision collapse.
  **Reject** unless a future task explicitly approves it.
- **Feature engineering / changing `input_dim`** before baseline: would break comparability and the
  77-feature contract. **Reject for the first run**; revisit only with approval after baseline.

---

## 6. Comparability with UNSW

- H1/H2/M1 do **not** affect UNSW comparability (UNSW output stays identical if H2 preserves UNSW
  text). The 14-class CICIDS Head 2 and 9-class UNSW Head 2 are separate label spaces — compare
  **methodology and per-head behavior**, not raw macro-F1 across datasets.
- Any feature/split change (M2, feature engineering) **would** break comparability and must be
  approval-gated and clearly documented as a separate protocol.

## 7. Realistic targets (honest, pre-training — not achieved)

- **Head 1 binary:** macro-F1 / F1 likely **>0.95** (well-supported by data/design). >0.90 plausible.
- **Head 2 attack-family:** weighted-F1 likely **>0.96**; **macro-F1 ~0.78-0.90** realistically.
  **>0.90 macro is not promised** — it depends on Infiltration and the tiny Web/SQL classes.
- Always report binary + attack-family **separately**, with per-class F1 **and** support, and (after
  baseline) multi-seed mean ± std.

## 8. Final prioritized recommendation list

1. **H1** — distinct CICIDS report path *(before training, mandatory)*.
2. **H2** — dataset-aware report/protocol/manifest *(before training, mandatory)*.
3. **M1** — drop float64 finite-check upcast *(before training, optional safe)*.
4. **M2** — document random-split/near-duplicate caveat *(after baseline)*.
5. **L1/L2** — reporting clarity + per-class support *(after baseline)*.
6. **I4** — multi-seed evaluation *(after baseline)*.
7. **I1** — validation-only threshold calibration *(after baseline, approval)*.
8. **I2 / I3 / M3** — optional mlp Head 2 / near-duplicate audit / data-path refactor *(approval)*.
9. **Reject** — V1 specialists/ensembles, oversampling, pre-baseline feature/split changes.

**Then:** train the CICIDS baseline as-is on the architecture (linear Head 2), with only H1/H2(/M1)
applied. Do not implement any of this until main control approves.
