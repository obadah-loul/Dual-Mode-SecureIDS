# CICIDS Deep Pre-Training Engineering + Model-Quality Audit

Status: `Audit / analysis only`. No training, smoke, preprocessing, evaluation, XAI, Streamlit,
checkpoint, or Git action was performed. Only the four A9.x CICIDS audit deliverables were created.
V1 was used as read-only reference only.

Generated: `2026-06-24`

Companion: `docs/CICIDS_MODEL_OPTIMIZATION_RECOMMENDATIONS.md`,
`results/audits/cicids_deep_pretraining_engineering_audit.json`,
`results/audits/cicids_model_optimization_recommendations.csv`.

---

## 1. Purpose and boundaries

Before running the (long) full CICIDS hierarchical training, perform a deep engineering and
model-quality audit so we do not waste hours on a weak, mislabeled, or unsafe setup. This is an
audit + improvement-proposal phase: **not** training approval and **not** implementation approval.

Boundaries honored: work inside V2 only; V1 read-only; no full CICIDS training; no long
preprocessing/evaluation; no XAI; no Streamlit; no checkpoint/metric writes; no file
delete/move/archive; no Git; no fake metrics; no claiming expected performance as achieved; no
implementation of model/code fixes (only audit docs/JSON/CSV).

Architecture wording used throughout: **"input schema matches a supported adapter/pipeline"** — we
never say traffic "belongs to" a dataset/model.

## 2. Files inspected

V2: `configs/training/cicids2018_hierarchical.yaml`, `configs/taxonomy/cicids2018_attack_taxonomy.yaml`,
`data/processed/cicids2018/hierarchical/{split_summary,attack_family_label_mapping,feature_names}.json`,
`results/audits/hierarchical_full_training_readiness_cicids2018.json`,
`results/audits/hierarchical_class_weight_strategy_cicids2018.json`,
`secureids/models/secureids_hierarchical_advanced_net.py`,
`secureids/training/{hierarchical_trainer,hierarchical_evaluation,hierarchical_metrics,hierarchical_class_weights,hierarchical_config,hierarchical_datasets}.py`,
`secureids/cli.py`, `secureids/datasets/{schema_detector,router}.py`.

V1 (read-only reference, names/roles only): `scripts/v5/{calibration_v5,selection_policy,specialists_v5,ensemble_v5,hierarchy,ids_metrics,conflict_audit,split_builder,feature_engineering}.py`,
`results/final_v6/FINAL_MODEL_SUMMARY.md`.

## 3. Commands / checks run (read-only)

Glob/Grep/Read inspections only (CICIDS data dir, datasets layer, CICIDS audits, hierarchical
training modules, the shared report file, V1 tree; CLI gate via Grep). **Nothing** trained,
preprocessed, evaluated, wrote checkpoints/metrics, or touched Git.

---

## 4. Model architecture audit

`SecureIDSHierarchicalAdvancedNet`: input transition + residual MLP encoder
(`hidden_dims=(256,128,128)`, LayerNorm, dropout 0.20, GELU, residual_expansion 2) → gated block →
128-d shared embedding → `binary_head=Linear(128,1)` + `attack_head=Linear(128,14)`.

- **CICIDS dims wired correctly:** `input_dim=77`, `attack_head_dim=14`, `binary_output_dim=1`,
  `attack_output_dim=14`. The readiness `model_forward_check` confirms output shapes
  `binary_logit (4096,)`, `attack_logits (4096,14)`, `embedding (4096,128)` — matching
  training/evaluation expectations.
- **Capacity for 77→14:** the encoder (~0.48M params) is comfortably sized for 77 features; Head 2
  is a single linear layer (14-way). For CICIDS the families are far more separable than UNSW, so a
  linear Head 2 is a reasonable baseline. A non-linear Head 2 branch (`attack_head_type: mlp`, added
  in A9.7-prep, default off) is available as a **later** experiment (I2), not for the first run.
- **No UNSW-only assumptions in the model:** dims come from config; the model is dataset-generic and
  the A9 (UNSW) linear default is preserved. ✔

## 5. Loss and training-logic audit

- **Masked multi-task loss is correct and dataset-generic:** BCEWithLogits on all rows
  (pos_weight), CrossEntropy on attack rows only (`mask==1 & y_attack!=-1`), `ignore_index=-1`,
  all-benign batch → zero attack-loss tensor (no NaN). Verified previously for UNSW; same code path.
- **Class weights:** train-only; binary balanced mean-normalized (`bce_pos_weight=2.502`); attack
  sqrt-inverse-frequency mean-normalized capped@10 (final max **5.527** SQL-Injection, min 0.063
  DDoS-HOIC — cap **not** binding). No validation/test labels used. The readiness `loss_check`
  exercised the real weighted loss and matched these values. ✔
- **No leakage / no test tuning:** validation-only checkpoint selection
  (`0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1`), `select_by_test_metrics=false`,
  single final test after selection, `no_scaler_encoder_refit_on_test`. ✔
- **Optimizer/early-stopping/reproducibility:** AdamW lr 1e-3, weight_decay 1e-4, batch **4096**,
  max_epochs **30**, early-stop patience 5 on `val_hierarchical_score`; seed 42 + seeded DataLoader
  generator; device cuda auto-resolved; trainer raises on non-finite loss. ✔ (No LR scheduler — a
  minor optional polish, not required.)
- **Memory (CICIDS-specific, MEDIUM — M1):** the trainer eager-loads all three splits (no mmap,
  ~3 GB X resident) and `_validate_split_labels` upcasts X to **float64** for the finite check
  (`np.isfinite(np.asarray(X, dtype=np.float64))`) → **~4.15 GB transient** for the 6.74M-row train
  split. Peak host-RAM ~6 GB during preconditions. Feasible on 16-32 GB, but a safe micro-fix is to
  drop the float64 upcast (np.isfinite works on float32).

## 6. CICIDS data / config readiness audit

- **Scale:** train **6,737,603**, val **1,443,772**, test **1,443,773** rows; 77 features. All
  required processed files present; dtypes correct (X float32, masks int8, labels int64).
- **Label/mask/taxonomy integrity = PASS:** for every split, `mask0==benign`, `ignore -1` exactly
  where `mask0`, attack labels valid `0..13`, no invalid binary/mask/attack labels, all 14 Head 2
  classes present in train/val/test. Mapping `id_to_class` is consistent (DDoS-HOIC 0 … SQL-Injection
  13). No off-by-one, no benign rows in Head 2. ✔
- **Imbalance:** binary 71.4% benign / 28.6% attack (pos_weight 2.50 handles it). Attack-family is
  severely imbalanced (DDoS-HOIC 480k vs **SQL-Injection 63** train rows). Rare classes
  (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection) and weak/hard classes
  (FTP-BruteForce, Infiltration, DoS-SlowHTTPTest) are documented in the config. Tiny test supports
  (SQL-Injection **12**, Web-XSS **38**) → high-variance per-class F1 (L2).
- **Split type (MEDIUM — M2):** val and test binary counts are **identical** (benign 1,031,537 both)
  → a **random stratified 70/15/15** split. This is i.i.d. (low covariate shift → val-selection
  transfers cleanly), but random-split CICIDS is known to risk **near-duplicate-flow leakage** across
  train/test, which can inflate apparent metrics. Report this transparently.
- **No hidden UNSW path / no scaler refit on test:** preprocessing fit train-only; X
  `copied_from_binary`; manifest `feature_dim=77` PASS. ✔

## 7. Evaluation-logic audit

- Metrics are dataset-generic and correct (reused from the UNSW audits): binary
  accuracy/precision/recall/F1/**macro-F1**/confusion-matrix/FN-count; Head 2 **macro-F1 over the
  full fixed 14-class set** (never-predicted classes score 0 — no inflation), **attack-rows-only**;
  per-class P/R/F1/support; rare-class macro-F1; routed end-to-end metrics (benign-stopped,
  detected+attributed, wrong-family, missed). Binary and attack-family results are separated. ✔
- Head 2 metrics correctly exclude benign rows (`(mask==1)&(y>=0)`). No fake/placeholder metrics; no
  binary checkpoint treated as hierarchical final (the readiness `no_fake_results_check` and
  `output_safety_check` confirm binary baselines preserved and no hierarchical final exists yet). ✔
- **Reporting bug (HIGH — H2):** the trainer's output **writers hardcode UNSW** text regardless of
  dataset (see §9). The metrics math is correct, but the emitted report/protocol labels would be
  wrong for CICIDS.

## 8. CLI / registry / routing audit

- **`train-hierarchical` gate is correct and generalized:** `handle_train_hierarchical` loads the
  config torch-free, then `_validate_train_hierarchical_cli_gate` validates the dataset alias,
  cross-checks `--dataset` vs `config.dataset`, enforces **per-dataset** `input_dim`
  (`TRAIN_HIERARCHICAL_EXPECTED_INPUT_DIMS[canonical]` → CICIDS **77**, not a hardcoded 192), refuses
  binary/smoke configs, and requires a dataset-appropriate hierarchical config name. CICIDS aliases
  (`cicids`, `cicids2018`, `cicids-2018`) are accepted. The handler prints a CICIDS size warning and
  passes `overwrite=args.overwrite` (default **false**). ✔ (Matches the reported "33 passed in
  0.74s".)
- **Schema detector / router (future prediction/dashboard layer) are clean:** metadata-only;
  column-based detection with normalization/aliases; returns "input schema matches a supported
  adapter/pipeline"; unknown/ambiguous → `UnsupportedSchemaError`; route exposes adapter/preprocessing/
  hierarchical/taxonomy/checkpoint-family **identifiers only** — **no model loading, no preprocessing,
  no predictions, no hidden dashboard coupling, no fake checkpoint claims.** Intended CICIDS checkpoint
  path `models/final/final_cicids_hierarchical.pt` is distinct and correct. ✔

## 9. Engineering-quality audit (key issues)

- **H1 (HIGH) — report-path collision:** CICIDS config `outputs.report_md =
  docs/HIERARCHICAL_TRAINING_REPORT.md`, which **already exists** (UNSW A9's report). The trainer's
  overwrite guard (`validate_execute_preconditions` builds `existing_final` for every output except
  `result_dir`) and the plan's `future_final_outputs_absent` check both see it. **Consequence: the
  provided as-is command (no `--overwrite`) will ABORT at the guard**; forcing `--overwrite` would
  overwrite and destroy the UNSW A9 report. All other CICIDS outputs (checkpoint, result_dir,
  manifest) are correctly namespaced. Fix: distinct CICIDS report path.
- **H2 (HIGH) — hardcoded UNSW labeling:** `_build_test_metrics_payload` line **587**
  `"protocol": "A8.8 corrected UNSW benchmark protocol (train 175,341-row partition; test
  82,332-row partition)"`; `_write_report` line **738** `"# Hierarchical Training Report
  (UNSW-NB15)"` and lines **740/746-748** UNSW scope; `_build_manifest` hardcodes the same UNSW
  protocol. A CICIDS run would emit `test_metrics.json` with `dataset: cicids2018` but UNSW protocol
  text (CICIDS has 6.7M train rows), plus a UNSW-titled report — internally contradictory, misleading
  for a professor-facing report. Fix: make protocol/title/scope dataset-aware.
- **M1 (MEDIUM)** float64 finite-check transient (§5). **M3 (MEDIUM)** readiness validates a
  different data path than the trainer (duplication). **L1/L2/L3 (LOW)** weight-preview clarity,
  tiny-class variance reporting, shared report default. (See JSON/CSV for full detail.)
- **Reproducibility / device / Windows paths / NaN handling:** all OK (§5).

## 10. V1/V6 reference findings (read-only; no code copied)

- **Safe reusable ideas:** validation-only threshold/probability **calibration** (`calibration_v5.py`);
  richer **per-class / false-negative / validation-vs-test-gap** reporting (`ids_metrics.py`, v5/v6
  reports — V2 already plans most); **split-conflict / near-duplicate audit** (`conflict_audit.py`,
  `split_builder.py`) relevant to M2.
- **Unsafe / messy (do NOT reuse):** V1 sprawling multi-model **specialists/ensembles/experiment
  grids** (`specialists_v5.py`, `ensemble_v5.py`) — conflicts with V2's clean single-system design;
  V1 coupling of security+dashboard+models — V2's adapter/router separation is cleaner.
- **Needs future approval:** per-class/family specialists or ensembling; **feature engineering**
  (changes feature_dim, breaks comparability); **temporal/day-based split**.

## 11. Performance-expectation analysis (honest)

- **Head 1 binary >0.90 — PLAUSIBLE (likely >0.95).** Evidence-based, not a guess: clean validated
  data (finite X, consistent labels/masks), 28.6% attack with BCE pos_weight 2.50 balancing, 77
  standard flow features, i.i.d. random split (low covariate shift), and an existing CICIDS binary
  baseline. CICIDS benign-vs-attack is a well-separated, high-volume task. (Not a guarantee; not yet
  achieved — this is a pre-training expectation.)
- **Head 2 macro-F1 >0.90 — UNLIKELY to be guaranteed; do not promise.** Weighted-F1 is very likely
  >0.96 (large separable families: DDoS-HOIC, DoS-Hulk, DDoS-LOIC-HTTP, SSH/FTP-BruteForce, Bot). But
  14-class **macro**-F1 is dragged by **Infiltration** (mimics benign — often weak) and the
  **tiny-support** Web/SQL/rare classes (SQL-Injection 12 test rows). Honest expected macro-F1
  **~0.78-0.90**; >0.90 macro is *possible* (CICIDS is far more separable than UNSW) but hinges on
  Infiltration and the rare classes. Report weighted-F1, macro-F1, and per-class F1+support together.
- **Main risks:** Infiltration weakness; tiny-class variance; random-split near-duplicate inflation;
  long run; the H2 mislabeling bug.

## 12. Findings table

| ID | Severity | Category | Blocks training? | Needs main-control? | Summary |
| --- | --- | --- | :-: | :-: | --- |
| H1 | HIGH | artifact safety | Yes (aborts as-is) | Yes | CICIDS `report_md` collides with UNSW A9 report |
| H2 | HIGH | scientific correctness | Yes (mislabels) | Yes | Trainer hardcodes UNSW protocol/title/manifest |
| M1 | MEDIUM | memory/perf | No | No | float64 finite-check ~4 GB transient on 6.7M rows |
| M2 | MEDIUM | methodology | No | Yes | Random split → near-duplicate leakage caveat |
| M3 | MEDIUM | duplication | No | No | Readiness vs trainer use different data paths |
| L1 | LOW | doc clarity | No | No | Two weight previews; clarify applied set |
| L2 | LOW | honest reporting | No | No | Tiny-support classes → high-variance F1 |
| L3 | LOW | config hygiene | No | No | Per-dataset report naming convention |
| I1 | IMPROVEMENT | calibration | No | Yes | Validation-only threshold calibration (later) |
| I2 | IMPROVEMENT | Head 2 capacity | No | Yes | Optional mlp Head 2 (later, not first run) |
| I3 | IMPROVEMENT | leakage audit | No | Yes | Near-duplicate split audit (idea) |
| I4 | IMPROVEMENT | rigor | No | No | Multi-seed (≥3) after baseline |

Counts — BLOCKER 0, HIGH 2, MEDIUM 3, LOW 3, IMPROVEMENT 4.

## 13. Final recommendation

**PROCEED_AFTER_SAFE_FIXES.**

There is **no fundamental blocker** — the data, labels/masks, class weights, metrics, CLI gate, and
routing layer are clean and the design is strong enough to produce honest, strong CICIDS results.
But the run **must not** proceed exactly as-is, because:

1. **H1** will make the provided command **abort** at the overwrite guard (shared report path), and
2. **H2** would produce a **UNSW-mislabeled** CICIDS report/manifest if forced.

Both are **safe, small fixes** (a config path change + dataset-aware report/protocol strings).
Recommended order: apply **H1 + H2** (and the safe **M1** micro-fix) before the first CICIDS run;
defer M2/M3/L*/I* to after the baseline.

## 14. Risks

- Training as-is without H1/H2 → aborted run or a misleading UNSW-labeled CICIDS report and a
  destroyed A9 report.
- Over-claiming Head 2 macro-F1 (rare/Infiltration classes) or ignoring random-split near-duplicate
  inflation → non-honest results.
- Host-RAM pressure on the 6.7M-row run if the float64 transient is left in place on a tight machine.

## 15. Exact next decision needed

Return to the project-controller (main) chat for a main-control decision **before** any training or
model/config changes. Decision needed: **approve the H1 + H2 (+ M1) safe pre-training fixes** (a
distinct CICIDS report path and dataset-aware report/protocol strings, plus the float64 micro-fix),
then re-run the lightweight CLI-gate/compile checks, **then** run the CICIDS training command. Do not
train, and do not implement these fixes, until main control approves. This audit changed no code,
configs, checkpoints, or metrics.
