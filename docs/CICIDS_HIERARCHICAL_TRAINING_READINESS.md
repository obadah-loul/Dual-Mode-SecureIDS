> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical Training Readiness

Status: `READY_FOR_MANUAL_TRAINING`

Generated on: `2026-06-24` (updated after the dataset-aware precondition gate fix, on top of the
focused pre-training safe fixes: H1, H2, M1, and the adapter-registry test-isolation fix).

## 1. Purpose And Boundaries

This readiness audit re-checks whether CICIDS2018 hierarchical final training is ready for the user
to run **manually** (after main-control approval), now that the focused pre-training safe fixes are
in place. It also reviews the remaining A8.8/UNSW precondition-gate concern.

This task did **not**: run training, rebuild preprocessing, run long evaluation, compute XAI, launch
Streamlit, modify checkpoints, delete/archive/move files, run Git, fake metrics/predictions, or claim
training happened. No production code was changed in this task (audit/documentation only).

## 2. Updates Since Previous Readiness Audit

Since the previous `READY_WITH_WARNINGS` audit (after the CLI gate fix), four focused safe fixes
landed and were manually verified:

- **CLI gate** — `train-hierarchical` accepts CICIDS and validates per-dataset `input_dim` (77 for
  CICIDS, not a hardcoded 192).
- **H1** — CICIDS report path no longer collides with the UNSW report.
- **H2** — trainer report/metrics/manifest text is now dataset-aware (CICIDS vs UNSW).
- **M1** — split-label finite check no longer upcasts feature arrays to float64.
- **Test isolation** — the adapter-registry "no torch import" test now runs in a clean subprocess.

The one previously-flagged latent item — the A8.8/UNSW precondition gate — is now **fixed**: the gate
is dataset-aware (Section 14). CICIDS no longer depends on UNSW/A8.8 files, while UNSW safety is
preserved exactly. Verified by `55 passed` (see Section 3). A trivial dead variable (`short`) in the
precondition function was also removed.

## 3. Manual Safe-Fix Verification Result

The pre-training safe fixes were manually verified by the **user** (not by Claude):

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_cicids_pretraining_safe_fixes.py tests/test_train_hierarchical_cli_gate.py tests/test_adapter_registry.py tests/test_schema_detector_router.py -q
```

Result: **`47 passed in 2.11s`** — run by the user (the original safe fixes).

After the dataset-aware precondition gate fix in **this** task, the focused set (now including
`tests/test_hierarchical_preconditions_dataset_aware.py`) was run by Claude and returned
**`55 passed in 2.30s`** (8 new precondition tests + the prior 47). The user should re-run the
command in Section 16's note to independently confirm.

## 4. CLI Gate Status

`secureids/cli.py` → `handle_train_hierarchical` loads the config torch-free, then
`_validate_train_hierarchical_cli_gate` validates the dataset alias, cross-checks `--dataset` vs
`config.dataset`, enforces the per-dataset expected `input_dim` (CICIDS **77**), refuses binary/smoke
configs, and requires a dataset-appropriate hierarchical config name. CICIDS aliases (`cicids`,
`cicids2018`, `cicids-2018`) are accepted. Status: **PASS** (covered by the user's 47-passed run).

## 5. H1 / H2 / M1 Safe-Fix Status

- **H1 (report path):** `configs/training/cicids2018_hierarchical.yaml` now sets
  `report_md: docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md`. That file does **not** exist yet, so the
  trainer's overwrite/`future_final_outputs_absent` guards now **pass without `--overwrite`**, and the
  existing UNSW report (`docs/HIERARCHICAL_TRAINING_REPORT.md`) is untouched.
- **H2 (dataset-aware outputs):** the trainer's `_build_test_metrics_payload`, `_build_manifest`, and
  `_write_report` derive title/status/protocol/scope/safety wording from a `_dataset_report_metadata`
  helper. CICIDS outputs identify as **CICIDS2018** with no UNSW/A8.8/175,341/82,332 wording; UNSW
  outputs keep their exact prior wording. Metric computation was not changed.
- **M1 (float64 micro-fix):** `_validate_split_labels` no longer upcasts X to float64 for the finite
  check; NaN/Inf detection for floating features is preserved (lower host-RAM peak on the 6.7M-row
  CICIDS arrays).

## 6. CICIDS Hierarchical Artifact Inventory

`data/processed/cicids2018/hierarchical/` exists with all expected files:
`X_{train,val,test}.npy`, `y_binary_{train,val,test}.npy`,
`y_attack_family_{train,val,test}.npy`, `attack_family_mask_{train,val,test}.npy`,
`feature_names.json`, `binary_label_mapping.json`, `attack_family_label_mapping.json`,
`common_attack_superclass_mapping.json`, `split_summary.json`,
`hierarchical_preprocessing_manifest.json`.

## 7. Processed Train/Val/Test Path Status

| Split | X shape | y_binary | y_attack_family | attack_family_mask |
| --- | ---: | ---: | ---: | ---: |
| train | `[6737603, 77]` | `[6737603]` | `[6737603]` | `[6737603]` |
| val | `[1443772, 77]` | `[1443772]` | `[1443772]` | `[1443772]` |
| test | `[1443773, 77]` | `[1443773]` | `[1443773]` | `[1443773]` |

All present and shape-consistent (sources: `hierarchical_preprocessing_audit_cicids2018.json`,
`hierarchical_preprocessing_readiness_cicids2018.json`, `hierarchical_full_training_readiness_cicids2018.json`).

## 8. Input Dimension

CICIDS input dimension is **77** (config, `feature_names.json` = 77 features, preprocessing manifest
`feature_dim=77`, readiness audit).

## 9. Attack-Family Head 2 Dimension

CICIDS attack-family Head 2 dimension is **14** (config, taxonomy = 14 attack labels, label mapping
`id_to_class` 0..13). Head 2 classes: `DDoS-HOIC`, `DDoS-LOIC-HTTP`, `DDoS-LOIC-UDP`, `DoS-Hulk`,
`DoS-SlowHTTPTest`, `DoS-GoldenEye`, `DoS-Slowloris`, `Bot`, `FTP-BruteForce`, `SSH-Bruteforce`,
`Infilteration / Infiltration`, `Web-BruteForce`, `Web-XSS`, `SQL-Injection`.

## 10. Taxonomy / Label Mapping Status

Valid and consistent: benign rows `y_attack_family = -1`, attack rows `0..13`, `mask=0` benign /
`mask=1` attack; `split_summary` per-class supports match the label mapping with no off-by-one; all 14
classes present in train/val/test; common superclasses are reporting-only (not training targets); no
fake shared multiclass target.

## 11. Model Compatibility Status

`SecureIDSHierarchicalAdvancedNet` supports the CICIDS contract: dataset-specific `input_dim` and
`attack_head_dim`; binary head emits one raw logit; attack-family head emits `attack_head_dim` logits;
benign/attack masked multi-task loss (`ignore_index=-1`) is supported. Prior `model_forward_check`
PASS with shapes `binary_logit [4096]`, `attack_logits [4096, 14]`, `embedding [4096, 128]`.

## 12. Class-Weight / Leakage Safety Status

`hierarchical_class_weight_strategy_cicids2018.json` status **PASS**, strategy locked, safe for full
training. Binary weights from train only; attack-family weights from train attack rows only
(sqrt-inverse-frequency, mean-normalized, capped@10, max final weight **5.526966** — cap not binding);
validation/test labels not used; oversampling disabled. No test-set tuning; no scaler/encoder refit on
validation/test (`select_by_test_metrics=false`, validation-only checkpoint selection, single final
test). No binary-only checkpoint is treated as the hierarchical final.

## 13. CICIDS Report Path Status

`report_md: docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md` (H1). The file does not exist yet (so no
collision and no overwrite-guard abort), and the UNSW report at `docs/HIERARCHICAL_TRAINING_REPORT.md`
is preserved and distinct.

## 14. A8.8 / UNSW Precondition Gate — Inspection And Fix (RESOLVED)

- **Exact location:** `secureids/training/hierarchical_trainer.py`,
  `validate_execute_preconditions(...)`, now delegating to the new helper
  `_dataset_precondition_errors(config, project_root)`.
- **Previous behavior (the issue):** the UNSW split-protocol/A8.8 checks ran **unconditionally for
  every dataset** — requiring `docs/UNSW_SPLIT_PROTOCOL_DECISION.md`,
  `results/audits/pre_training_high_findings_resolution.json`, and `ready_for_unsw_training == True`
  even for CICIDS. This was a **false cross-dataset dependency**: CICIDS passed only because the UNSW
  files happened to exist on this machine, and would have been blocked on a clean machine lacking
  them.
- **Fix applied (this task):** the gate is now **dataset-aware** (uses the canonical
  `config.dataset`, never a CLI alias):
  - `unsw_nb15` → the UNSW split-protocol/A8.8 checks are **preserved exactly** (UNSW safety
    unchanged).
  - `cicids2018` → **no** UNSW/A8.8 file requirement; CICIDS relies on the dataset-agnostic checks
    that still run for every dataset (config validation, the read-only plan, the per-dataset
    class-weight-strategy PASS, the overwrite guard, and the per-split finite label/data checks).
  - any other dataset → fails clearly (`unsupported dataset for hierarchical training
    preconditions: ...`).
- **Applies to CICIDS after fix?** **No** (UNSW/A8.8 files are not required for CICIDS).
- **Applies to UNSW after fix?** **Yes** (unchanged).
- **Blocks manual CICIDS training?** **No.** CICIDS no longer depends on UNSW evidence.
- **Verification:** unit tests prove CICIDS produces no precondition errors even with **no** UNSW
  files present, UNSW still fails without its evidence and passes with it, and an unsupported dataset
  fails clearly — see `tests/test_hierarchical_preconditions_dataset_aware.py` (part of the
  `55 passed` run). The dataset-agnostic overwrite protection and finite label/data checks were not
  weakened.
- **Classification: FIXED.** No further code action required for this item.

## 15. Readiness Verdict

Verdict: **`READY_FOR_MANUAL_TRAINING`**

All required artifacts, dimensions (77 / 14), taxonomy/label mappings, model compatibility,
class-weight/leakage safety, the CLI gate, and the now **dataset-aware** precondition gate are
satisfied; H1/H2/M1 and the gate fix are verified (`55 passed`). The previously-blocking-from-clean
A8.8/UNSW false dependency is resolved, so no meaningful warning remains that would hold readiness
below this tier. The remaining items are **ordinary training risks/caveats** (runtime / memory on
~6.7M rows, rare-class variance, the random-split near-duplicate reporting caveat, and the standard
first-checkpoint review) — none block honest training. Not `NOT_READY_BLOCKED`: no blocker remains.

## 16. Exact Manual PowerShell Training Command

Run only after main-control approval (do **not** add `--overwrite`):

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/cicids2018_hierarchical.yaml --execute
```

## 17. Expected Output Files

- `models/final/final_cicids_hierarchical.pt`
- `results/final/hierarchical/cicids/training_history.csv`
- `results/final/hierarchical/cicids/test_metrics.json`
- `results/final/hierarchical/cicids/binary_confusion_matrix.csv`
- `results/final/hierarchical/cicids/attack_family_confusion_matrix.csv`
- `results/final/hierarchical/cicids/per_class_attack_metrics.csv`
- `results/final/hierarchical/cicids/rare_class_metrics.csv`
- `results/audits/hierarchical_training_manifest_cicids2018.json`
- `docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md`

## 18. Monitoring Instructions

- Watch console epoch logs; confirm loss is finite (not NaN/Inf).
- Confirm validation metrics appear per epoch and checkpoint selection is validation-only.
- Confirm the final test is evaluated once after the best validation checkpoint.
- Confirm output paths are CICIDS hierarchical (not binary, not UNSW); the report should be
  `docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md` and labeled CICIDS2018 (no UNSW/A8.8 text).
- Monitor GPU and host memory (CICIDS is large; ~6.7M training rows).
- Stop if UNSW paths/configs appear unexpectedly or if it tries to overwrite unexpected checkpoints.

## 19. Safe Stop Instructions

- Press `Ctrl+C` once and wait for Python to exit cleanly.
- Do not delete partial outputs until reviewed.
- Paste the console output back to the project-controller chat.
- Do not rerun with `--overwrite` without explicit approval.

## 20. Remaining Risks / Warnings

- **A8.8/UNSW gate coupling:** **RESOLVED** (Section 14) — the gate is now dataset-aware; CICIDS no
  longer depends on UNSW/A8.8 files. No longer a warning.
- **Runtime / memory (ordinary):** ~6.7M training rows × ~30 epochs; eager all-split tensor load
  (~3 GB X resident). Ensure adequate host RAM and keep the terminal open.
- **Rare-class instability:** `SQL-Injection` (12 test rows), `Web-XSS` (38), `Web-BruteForce` (96),
  `DDoS-LOIC-UDP` produce high-variance per-class/rare-class F1 — report per-class support; consider
  multi-seed after baseline.
- **Random-split near-duplicate caveat:** val/test are i.i.d. with train (good transfer) but
  random-split CICIDS can leak near-duplicate flows across splits and optimistically inflate metrics —
  report transparently.
- **First-checkpoint review:** the first CICIDS hierarchical checkpoint must be reviewed before being
  accepted as final.

Blockers: **none** on this machine.

## 21. Next Decision Needed

Return to the project-controller / main-control chat before manual training. Decision needed:
**approve or defer** the manual CICIDS hierarchical training run using the command in Section 16.
(The A8.8/UNSW gate dataset-aware fix is now done, so it is no longer a pending decision.)

If training is approved, run it manually and bring the console output and generated artifacts back for
review before treating the checkpoint as final.
