# Dataset-Aware Precondition Gate Fix

Status: `Implemented and verified (55 passed) — NOT trained`. No training, preprocessing rebuild,
long evaluation, XAI, Streamlit, checkpoint change, file delete/move/archive, or Git action was
performed.

Generated: `2026-06-24`

Companion: `results/audits/dataset_aware_precondition_gate_fix.json`,
`docs/CICIDS_HIERARCHICAL_TRAINING_READINESS.md`,
`results/audits/cicids_hierarchical_training_readiness.json`.

---

## 1. Purpose

Before manual CICIDS hierarchical training, remove the last warning blocking full readiness: the
trainer's `validate_execute_preconditions()` required UNSW/A8.8 files for **every** dataset, creating
a false dependency where CICIDS training passed only because UNSW files happened to exist on this
machine. This task makes the gate **dataset-aware** so CICIDS no longer depends on UNSW evidence,
while UNSW safety is preserved exactly.

## 2. Previous Issue

In `secureids/training/hierarchical_trainer.py`, `validate_execute_preconditions()` ran the
"A8.8 resolution gate" **unconditionally for all datasets**:

- required `docs/UNSW_SPLIT_PROTOCOL_DECISION.md`;
- required `results/audits/pre_training_high_findings_resolution.json`;
- required that JSON's `ready_for_unsw_training == True`.

For CICIDS this is a UNSW-specific dependency with no CICIDS relevance. On a clean machine/checkout
lacking the UNSW A8.8 artifacts, CICIDS training would be **blocked for a UNSW-unrelated reason**.

## 3. Exact Behavior Before

```
validate_execute_preconditions(config, project_root, overwrite):
    ...plan checks (dataset-agnostic)...
    # ran for EVERY dataset, including cicids2018:
    require docs/UNSW_SPLIT_PROTOCOL_DECISION.md
    require results/audits/pre_training_high_findings_resolution.json
    require ready_for_unsw_training == True
    ...class-weight strategy PASS, overwrite guard, per-split finite checks...
```

## 4. Exact Behavior After

The UNSW/A8.8 checks are extracted into a small pure helper
`_dataset_precondition_errors(config, project_root)` that branches on the **canonical**
`config.dataset` (never a CLI alias):

```
if config.dataset == "unsw_nb15":
    require docs/UNSW_SPLIT_PROTOCOL_DECISION.md
    require results/audits/pre_training_high_findings_resolution.json
    require ready_for_unsw_training == True        # UNSW safety preserved exactly
elif config.dataset == "cicids2018":
    pass                                           # no UNSW/A8.8 dependency
else:
    error: "unsupported dataset for hierarchical training preconditions: <name>."
```

`validate_execute_preconditions()` now calls `errors.extend(_dataset_precondition_errors(...))`. All
**dataset-agnostic** checks still run for every dataset:

- config validation (task/model_name);
- the read-only plan (data dir, feature/class counts, readiness/manifest PASS, array shapes);
- the per-dataset class-weight-strategy PASS check;
- the overwrite guard (checkpoint + existing-final-output protection);
- the per-split finite label/data/mask checks.

A trivial dead variable (`short`) in the class-weight section was also removed (no behavior change).

## 5. UNSW Checks Preserved

The UNSW branch keeps the same three requirements with the same blocking semantics. Tests confirm
UNSW still fails without its evidence and passes only when both files exist and
`ready_for_unsw_training == True`. UNSW safety was not weakened.

## 6. CICIDS No Longer Depends On UNSW Files

CICIDS preconditions now produce **no** errors even when the project root contains **no** UNSW files.
CICIDS readiness no longer hinges on UNSW artifacts; it relies solely on the dataset-agnostic and
CICIDS-relevant checks.

## 7. Tests Added

`tests/test_hierarchical_preconditions_dataset_aware.py` (synthetic temp paths + `SimpleNamespace`;
no full datasets, no training, no checkpoints):

1. CICIDS produces no precondition errors with **no** UNSW files present.
2. CICIDS unaffected even if a UNSW resolution exists with `ready_for_unsw_training == False`.
3. The real CICIDS config's canonical dataset has no UNSW dependency (tmp root, no UNSW files).
4. UNSW fails when its evidence files are absent (both messages).
5. UNSW fails when `ready_for_unsw_training` is not true.
6. UNSW passes when evidence is present and ready.
7. The real UNSW config fails without evidence and passes with it.
8. An unsupported dataset fails clearly with a dataset-specific message.

Verified together with the existing safe-fix / CLI-gate / adapter / schema tests:
`55 passed in 2.30s`.

## 8. No Training Performed

No full CICIDS training, preprocessing rebuild, long evaluation, XAI, or Streamlit was run. No
checkpoints or final metrics were created or modified. No files were deleted/moved/archived. V1 was
not modified. No Git operations. No metrics/predictions were faked or claimed as achieved. Only quick
focused tests were run.

## 9. Remaining Risks

- **Ordinary training risks/caveats only:** long runtime / memory (~6.7M training rows, ~3 GB eager
  X load), rare-class variance (tiny supports such as SQL-Injection 12 test rows), the random-split
  near-duplicate reporting caveat, and the standard first-checkpoint review. None block honest
  training.
- No new blocker was introduced; overwrite protection and finite label/data checks remain intact.

## 10. Next Step

Return to the project-controller / main-control chat. The CICIDS readiness is now
**READY_FOR_MANUAL_TRAINING**; the only remaining decision is to approve or defer the manual CICIDS
hierarchical training run. The dataset-aware gate fix is complete and verified.
