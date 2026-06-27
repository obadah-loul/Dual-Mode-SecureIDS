# UNSW A9.7 — head2_branch_capacity Experiment Plan

Status: `A9.7-prep complete — implementation + config + tests prepared, NOT yet run`.
No training, smoke, preprocessing, checkpoint, or final-metric work was performed. A9 remains the
accepted UNSW hierarchical baseline. **A9.7 has not been trained.**

Generated: `2026-06-24`

Companion design docs: `docs/UNSW_ADVANCED_PERFORMANCE_ENGINEERING_PLAN.md`,
`docs/UNSW_NEXT_EXPERIMENT_DESIGN_DECISION.md`,
`results/audits/unsw_a9_7_head2_branch_capacity_prep.json`.

---

## 1. A9 baseline

| Metric | A9 |
| --- | ---: |
| Binary macro-F1 | 0.894488 |
| Binary F1 | 0.910133 |
| Attack false negatives | 2,310 |
| Benign false positives | 6,186 |
| **Attack-family macro-F1** | **0.500429** |
| Attack-family accuracy | 0.766478 |
| Rare-class macro-F1 | 0.385669 |

A9 checkpoint `models/final/final_unsw_hierarchical.pt`; result folder
`results/final/hierarchical/unsw/`; manifest
`results/audits/hierarchical_training_manifest_unsw_nb15.json`.

## 2. A9.6 failure (why we are not repeating it)

A9.6 (`head2_loss_weight`) raised `attack_loss_weight` 1.0 → 1.5. Binary improved
(macro-F1 0.911474) but **Head 2 and rare classes got worse** (attack-family macro-F1 0.485478,
rare-class macro-F1 0.362125; Shellcode precision 0.308 → 0.236). More global minority loss pressure
was the wrong direction and **must not** be repeated. A9.6 should not replace A9.

## 3. A9.7-design conclusion (accepted)

There is no obvious bug. The main actionable engineering weakness is **Head 2 capacity**: the
attack-family head is a single `Linear(128 → 9)` ≈ **1,161 parameters (~0.23% of the 513,418-param
model)**, sitting on an embedding shaped mostly by the easy, near-saturated binary task. The blocker
is **wrong-family attribution** (22.8% of attacks detected-but-wrong-family vs 5.1% missed), driven
by the overlapping {Analysis, Backdoor, DoS, Exploits} cluster — boundaries a single linear layer
cannot draw.

## 4. Why Head 2 capacity is the target

A non-linear Head 2 branch adds **capacity, not minority loss pressure**, so it directly targets the
attribution problem **without** reintroducing the A9.6 precision-collapse mechanism. It is one
controlled factor, low complexity, and leaves the strong binary head untouched.

## 5. Exact architecture change (the ONE factor)

```
# A9 (baseline) Head 2:
shared embedding (128) -> Linear(128, 9)                         # ~1,161 params

# A9.7 Head 2 (attack_head_type: mlp):
shared embedding (128)
  -> Linear(128, 128)
  -> LayerNorm(128)
  -> GELU
  -> Dropout(0.20)
  -> Linear(128, 9)                                              # ~17,929 params
```

Implemented backward-compatibly in
`secureids/models/secureids_hierarchical_advanced_net.py`:

- New constructor options `attack_head_type` (`linear` | `mlp`), `attack_head_hidden_dim` (128),
  `attack_head_norm` (true), `attack_head_dropout` (defaults to model dropout).
- **Default is `linear`**, so the model is byte-for-byte the A9 architecture when the options are
  absent, and **existing A9 checkpoints stay loadable**.
- `forward()` output keys/shapes are unchanged: `binary_logit (B,)`, `attack_logits (B, 9)`,
  `embedding (B, 128)`. `compute_hierarchical_loss` and class-weight support are unchanged.
- Invalid `attack_head_type` / `attack_head_dropout` raise `ValueError` clearly.
- `secureids/training/hierarchical_trainer.py::build_model` passes the options through (defaulting to
  `linear` when absent).

Net model size grows ≈ **+16,768 params (~3.3%)**, from ~513,418 to ~530,186, for ~15× the Head 2
capacity.

## 6. What stays unchanged (controls vs A9)

Corrected UNSW protocol; `input_dim 192`; `attack_head_dim 9`; shared encoder `(256,128,128)`,
gated block, dropout 0.20, LayerNorm; binary head (single linear); masked multi-task loss;
**`binary_loss_weight 1.0`, `attack_loss_weight 1.0`** (back to A9, not A9.6's 1.5); train-only
class weights; class-weight cap 10.0; AdamW lr 1e-3, weight_decay 1e-4; batch 1024; max_epochs 40;
early-stop patience 6; validation-only selection `0.5·binary + 0.5·attack`; threshold 0.5; seed 42;
no oversampling; no test-set tuning; no validation/test labels for weights.

## 7. A9.7 output paths (all separate; never overwrite A9 / A9.6)

- Config: `configs/training/unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml`
- Checkpoint: `models/final/final_unsw_hierarchical_a9_7_head2_branch_capacity.pt`
- Result folder: `results/final/hierarchical/unsw_a9_7_head2_branch_capacity/`
  (`training_history.csv`, `test_metrics.json`, `binary_confusion_matrix.csv`,
  `attack_family_confusion_matrix.csv`, `per_class_attack_metrics.csv`, `rare_class_metrics.csv`,
  `hierarchical_routing_summary.json`, `training_config_snapshot.yaml`, `class_weight_snapshot.json`,
  `model_summary.json`)
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_7_head2_branch_capacity.json`
- Report: `docs/HIERARCHICAL_TRAINING_REPORT_A9_7_HEAD2_BRANCH_CAPACITY.md`

**Must NOT overwrite (A9):** `models/final/final_unsw_hierarchical.pt`,
`results/final/hierarchical/unsw/`, `results/audits/hierarchical_training_manifest_unsw_nb15.json`,
`docs/HIERARCHICAL_TRAINING_REPORT.md`.

**Must NOT overwrite (A9.6):** `models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt`,
`results/final/hierarchical/unsw_a9_6_head2_loss_weight/`,
`results/audits/hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`,
`docs/HIERARCHICAL_TRAINING_REPORT_A9_6_HEAD2_LOSS_WEIGHT.md`.

The trainer's precondition guard refuses to overwrite existing final outputs unless `--overwrite` is
passed; the A9.7 paths are new, so the run needs no `--overwrite` and cannot touch A9/A9.6.

## 8. Success criteria (A9.7 may replace A9 only if all hold)

- Attack-family macro-F1 improves from 0.500429 to **≥ 0.530000**.
- Binary macro-F1 ≥ 0.884000 and binary F1 ≥ 0.905000.
- Attack false negatives ≤ 2,450; benign false positives ≤ 7,000.
- Rare-class macro-F1 ≥ 0.385669.
- Shellcode F1 does not drop by more than 0.030; Worms F1 does not drop by more than 0.050.
- At least one of Analysis, Backdoor, or DoS improves over A9.
- No A9 overwrite; no A9.6 overwrite; no test-set tuning.

Honesty note: because single-seed deltas (~0.015) sit within run noise, **promotion should be
confirmed across ≥3 seeds (mean ± std)**. The provided config runs seed 42 (one-factor vs A9); repeat
with seeds 43 and 44 (duplicate the config and change `training.seed`) before final promotion.

## 9. Failure criteria

- Attack-family macro-F1 does not improve meaningfully (stays < 0.530000 or within noise).
- Binary safety collapses (macro-F1 < 0.884, F1 < 0.905, FN > 2,450, FP > 7,000).
- Rare-class macro-F1 collapses below 0.385669, or Shellcode/Worms drop beyond the allowed margins.
- Analysis/Backdoor/DoS all stay unchanged while easy classes absorb gains.
- Any path overwrites A9 or A9.6; any change outside the approved Head 2 branch; any test-set tuning;
  validation/test labels used for weights; unstable/incomplete/NaN training.

## 10. Realistic expectation

`>0.9` attack-family macro-F1 is **not realistic** on the corrected official UNSW split. Honest
target after A9.7: **0.51–0.54** (3-seed mean); after 1–3 stacked experiments: **0.53–0.60**,
headline ~0.55.

## 11. Manual commands (run by the user; nothing was executed here)

```powershell
# 1) Compile check
.\.venv\Scripts\python.exe -m compileall secureids tests

# 2) Focused model/config/safety tests
.\.venv\Scripts\python.exe -m pytest tests\test_hierarchical_head2_branch.py tests\test_hierarchical_advanced_model.py tests\test_hierarchical_training_config.py tests\test_hierarchical_trainer_safety.py -q

# 3) Optional full suite
.\.venv\Scripts\python.exe -m pytest tests -q

# 4) A9.7 training (only after tests pass and main-review approval)
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset unsw --config configs/training/unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml --execute
```

Post-training verification commands are listed in
`results/audits/unsw_a9_7_head2_branch_capacity_prep.json` (`manual_commands_required`) and in the
A9.7-prep final report.

## 12. Stop condition

A9.7 has **not** been run. Stop after A9.7-prep and wait for main-review/user approval before
training. Do not train, do not create checkpoints, do not create metrics.
