# CICIDS Pre-Training Safe Fixes (H1, H2, M1)

Status: `Safe fixes implemented — NOT trained`. No training, preprocessing rebuild, long
evaluation, XAI, Streamlit, checkpoint change, file delete/move, or Git action was performed.

Generated: `2026-06-24`

Companion: `results/audits/cicids_pretraining_safe_fixes.json`,
`docs/CICIDS_DEEP_PRETRAINING_ENGINEERING_AUDIT.md`,
`docs/CICIDS_MODEL_OPTIMIZATION_RECOMMENDATIONS.md`.

---

## 1. Purpose

The CICIDS deep pre-training audit returned **PROCEED_AFTER_SAFE_FIXES**. This task implements the
three approved, low-risk fixes so the CICIDS hierarchical training run will (a) not abort on a report
path collision, (b) produce truthful CICIDS-labeled artifacts, and (c) avoid an unnecessary large
memory spike — **without** changing any metric computation, weakening safety checks, or training.

## 2. Approved scope

- **H1** — CICIDS report-path collision fix.
- **H2** — dataset-aware trainer report/metrics/manifest wording.
- **M1** — float32-safe finite check (implemented; it was small and safe).

Nothing else was changed. This is **not** training approval.

## 3. H1 — Report-path collision fix

- **Before:** `configs/training/cicids2018_hierarchical.yaml` wrote `report_md:
  docs/HIERARCHICAL_TRAINING_REPORT.md` — the **same** file as the UNSW A9 report, so a CICIDS run
  would abort at the overwrite guard (or, if forced, overwrite the UNSW report).
- **After:** `report_md: docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md`.
- The UNSW config and the existing UNSW report file were **not** changed, moved, deleted, or
  archived. All other CICIDS outputs were already CICIDS-namespaced.

## 4. H2 — Dataset-aware report / metrics / manifest text

- **Before:** `secureids/training/hierarchical_trainer.py` hardcoded UNSW strings in the output
  writers regardless of dataset — e.g. `protocol: "A8.8 corrected UNSW benchmark protocol (train
  175,341-row partition; test 82,332-row partition)"`, report title `# … (UNSW-NB15)`, the rare-class
  header `(Shellcode, Worms)`, and UNSW-centric safety keys. A CICIDS run would have been mislabeled
  as UNSW.
- **After:** a small helper `_dataset_report_metadata(config)` returns dataset-aware
  title/status/protocol/scope/safety wording. `_build_test_metrics_payload`, `_build_manifest`, and
  `_write_report` now consume it:
  - **UNSW** runs keep their **exact prior wording** (UNSW-NB15 / A8.8 / 175,341 / 82,332) and the
    UNSW safety keys — backward-compatible.
  - **CICIDS** runs are labeled **CICIDS2018** with a stratified-split protocol description and
    **no UNSW/A8.8 mention**; the rare-class header derives names from the rare-class bundle; the
    safety notes use dataset-neutral, accurate keys.
  - A generic fallback covers any future dataset.
- **No metric computation was changed** — only emitted text/metadata.

## 5. M1 — float32-safe finite check (implemented)

- **Before:** `_validate_split_labels` ran `np.isfinite(np.asarray(X, dtype=np.float64))`, upcasting
  the whole feature array to float64 (~4 GB transient for the CICIDS ~6.7M × 77 train split).
- **After:** `np.asarray(X)` then `np.isfinite(...)` only for floating dtypes (integer/bool feature
  arrays are inherently finite and skipped). NaN/Inf in float features are still flagged — finite
  validation behavior is preserved; no float64 upcast.
- This was **small and safe**, so it was implemented (not deferred).

## 6. Files changed

| File | Change |
| --- | --- |
| `configs/training/cicids2018_hierarchical.yaml` | H1 — CICIDS-specific `report_md` path |
| `secureids/training/hierarchical_trainer.py` | H2 — `_dataset_report_metadata` helper + dataset-aware payload/report/manifest; M1 — float32-safe finite check |
| `tests/test_cicids_pretraining_safe_fixes.py` | New lightweight tests for H1/H2/M1 |
| `docs/CICIDS_PRETRAINING_SAFE_FIXES.md` | This document |
| `results/audits/cicids_pretraining_safe_fixes.json` | Machine-readable summary |

## 7. Tests added/updated

`tests/test_cicids_pretraining_safe_fixes.py` (synthetic/in-memory only; no training, no full data,
no checkpoints):
- **H1:** CICIDS config uses the CICIDS report path; CICIDS config does not use the UNSW report path;
  UNSW report path unchanged.
- **H2:** `_dataset_report_metadata` is dataset-aware; CICIDS payload/manifest/report contain
  CICIDS2018 and **no** `UNSW`/`A8.8`/`175,341`/`82,332`; UNSW payload/manifest/report keep UNSW
  wording; CICIDS rare-class header lists CICIDS rare classes.
- **M1:** clean float32 passes; NaN and Inf in float32 are flagged; integer features are handled
  without error or upcast.

Existing UNSW behavior is preserved (the UNSW branch keeps its exact keys/strings), so prior tests
remain valid.

## 8. Manual verification command (run by the user — not run here)

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_cicids_pretraining_safe_fixes.py tests/test_train_hierarchical_cli_gate.py tests/test_adapter_registry.py tests/test_schema_detector_router.py -q
```

JSON validation:

```powershell
Get-Content "results\audits\cicids_pretraining_safe_fixes.json" -Raw | .\.venv\Scripts\python.exe -m json.tool
```

(Do **not** run the actual CICIDS training command yet.)

## 9. No training performed

No full CICIDS training, preprocessing rebuild, long evaluation, XAI, or Streamlit was run. No
checkpoints or final metrics were created or modified. No files were deleted/moved/archived. V1 was
not modified. No Git operations. No metrics were faked or claimed as achieved.

## 10. Remaining risks

- The **A8.8/UNSW precondition gate** in `validate_execute_preconditions` still requires the UNSW
  split-decision doc + `ready_for_unsw_training=true`. It currently **passes** for CICIDS only
  because those A8.8 files exist. This is a latent cross-dataset coupling; it was **out of the
  approved H1/H2/M1 scope** and changing a safety gate is risky, so it was left untouched and logged
  as a future item. (It does not block CICIDS today.)
- Tests were **not executed** here — the user must run the manual command and confirm green.
- Module-level docstring/comments still mention UNSW (cosmetic; not part of any emitted artifact).

## 11. Next step

**Rerun the CICIDS hierarchical readiness audit after these safe fixes**, confirm the focused tests
pass, and only then proceed to the manual CICIDS training command (separately approved). Do not train
until the readiness re-run and test pass are confirmed by main control.
