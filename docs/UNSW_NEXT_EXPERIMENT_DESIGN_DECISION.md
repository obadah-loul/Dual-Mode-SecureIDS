> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW Next-Experiment Design Decision (Task A9.7-design)

Status: `Design decision only`. No experiment was implemented, no config was created, no training
was run. A9 remains the accepted UNSW hierarchical baseline. **Stop for main-review approval before
execution.**

Generated: `2026-06-24`

Companion: `docs/UNSW_ADVANCED_PERFORMANCE_ENGINEERING_PLAN.md`,
`results/audits/unsw_advanced_performance_engineering_plan.json`.

---

## 1. Chosen next experiment

**`A9.7 head2_branch_capacity`** — add a dedicated non-linear Head 2 (attack-family) branch on top
of the existing shared embedding, changing nothing else.

This is selected over focal loss, class-weight-cap-down, and two-stage training because it is the
single, lowest-risk change that directly addresses the confirmed structural bottleneck (Head 2 is
~0.23% of the model — a single `Linear(128 → 9)`) **without adding the minority loss pressure that
made A9.6 fail**.

## 2. Hypothesis

Giving Head 2 its own small non-linear branch lets it model the **non-linear family boundaries** in
the overlapping {Analysis, Backdoor, DoS, Exploits} cluster that a single linear layer cannot,
improving attack-family macro-F1 over A9 — while the strong, near-saturated binary head and the
rare-class precision floors remain stable (because capacity, not loss pressure, is what changes).

## 3. Exact factor(s) to change (one factor: Head 2 architecture)

Replace the Head 2 output layer:

```
# A9 (current):
attack_head = nn.Linear(embedding_dim, attack_head_dim)   # 128 -> 9

# A9.7 (proposed, opt-in via config flag model.head2_hidden_dims: [128]):
attack_head =
  Linear(128, 128) -> LayerNorm(128) -> GELU -> Dropout(p = model.dropout) -> Linear(128, 9)
```

- Branch reads the **same** shared 128-d gated embedding.
- Adds ≈ **17.5k params** (~3.4% of the 513,418-param model); ~15× the Head 2 capacity.
- Activation GELU (matches the encoder), LayerNorm for stability, Dropout = the model's existing
  `dropout` (0.20) for regularization.
- Implemented **behind a config flag** so that, absent the flag, the model is byte-for-byte A9
  (preserves A9 reproducibility).

## 4. What stays unchanged (controls)

- **Loss:** masked multi-task; CrossEntropy on attack rows; `binary_loss_weight = 1.0`;
  **`attack_loss_weight = 1.0`** (back to A9, not A9.6's 1.5); `ignore_index = -1`. **No focal loss.**
- **Class weights:** train-only A8.5/A8.8 sqrt-inverse-frequency, mean-normalized, **cap = 10.0**.
- **Shared encoder:** `hidden_dims = (256,128,128)`, gated block, dropout 0.20, LayerNorm,
  `residual_expansion = 2` — unchanged. **Binary head:** single `Linear(128,1)` — unchanged.
- **Optimizer/schedule:** AdamW lr 1e-3, weight_decay 1e-4, batch 1024, max_epochs 40, early-stop
  patience 6 on `val_hierarchical_score`. No new scheduler.
- **Selection:** validation-only, `0.5·binary + 0.5·attack` macro-F1; threshold 0.5; single final
  test after best-validation checkpoint.
- **Data:** corrected UNSW protocol, `input_dim 192`, `attack_head_dim 9`, same processed arrays.
- **Baselines:** A9 and A9.6 outputs frozen and untouched.

## 5. Evaluation protocol (mandatory for honest promotion)

- **≥3 seeds** (e.g. 42, 43, 44); report **mean ± std** for binary macro-F1, attack-family macro-F1,
  rare-class macro-F1, and per-class F1 (especially Analysis/Backdoor/DoS/Shellcode/Worms).
- Promote only if the mean beats A9 **beyond the noise band** (≈ ±0.02–0.03 observed).
- Validation-only selection; **no test-set tuning**; one final test per seed.

## 6. Files / configs that would be created later (NOT now)

- Config: `configs/training/unsw_nb15_hierarchical_a9_7_head2_branch.yaml`
- Checkpoint(s): `models/final/final_unsw_hierarchical_a9_7_head2_branch[_seedN].pt`
- Result folder: `results/final/hierarchical/unsw_a9_7_head2_branch/` (+ per-seed subfolders or a
  seeds summary)
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_7_head2_branch.json`
- Report: `docs/HIERARCHICAL_TRAINING_REPORT_A9_7_HEAD2_BRANCH.md`
- Code: an additive, flag-gated Head 2 branch in
  `secureids/models/secureids_hierarchical_advanced_net.py` (default off = A9 behavior).

A9.7 must **not** write into `models/final/final_unsw_hierarchical.pt`,
`results/final/hierarchical/unsw/`, `results/audits/hierarchical_training_manifest_unsw_nb15.json`,
or any A9.6 path.

## 7. Success criteria (3-seed mean)

- Attack-family macro-F1 ≥ **0.535** and beats A9 beyond the noise band (≥ ~0.02 absolute).
- Attack-family accuracy ≥ 0.760.
- Binary macro-F1 ≥ 0.884 and binary F1 ≥ 0.905.
- Attack false negatives ≤ 2,450; benign false positives ≤ 7,000.
- Rare-class macro-F1 ≥ 0.385669; Shellcode F1 ≥ 0.4099 (precision ≥ 0.25); Worms F1 ≥ 0.2814
  (precision ≥ 0.18).
- At least one of Analysis / Backdoor / DoS improves over A9 without rare-class collapse.
- Training stable, complete, no NaN; A9/A9.6 untouched; separate output paths used.

## 8. Failure criteria

- Attack-family macro-F1 fails to beat A9 beyond noise or stays < 0.535 (3-seed mean).
- Any binary safety gate fails (macro-F1 < 0.884, F1 < 0.905, FN > 2,450, FP > 7,000).
- Rare-class macro-F1 < 0.385669, or Shellcode/Worms precision collapses below the floors.
- Analysis, Backdoor, and DoS all stay stagnant while strong classes absorb the gains.
- Training unstable/incomplete/NaN, any A9/A9.6 artifact overwritten, or non-separate paths used.

## 9. Why not the alternatives first

- **Why not focal loss first.** Focal loss combined with the existing class weights is **another
  minority/hard-pressure lever** — the same direction that **already failed in A9.6** (Shellcode
  precision 0.308 → 0.236; Analysis/Backdoor unmoved; macro −0.015). Focal loss only **reweights**
  the loss; it cannot create the **non-linear boundary** the overlapping cluster needs. Keep focal
  loss for **later and gated** (γ≈1.5, `attack_loss_weight` 1.0, hard rare-precision floors).
- **Why not class-weight-cap-down first.** Cap-down only repairs rare-class **precision** and won't
  resolve the DoS/Exploits/Backdoor confusion that drives most wrong-family attribution. It is the
  right **A9.9 follow-up** (precision repair) once capacity is in place, not the first move.
- **Why not two-stage fine-tuning first.** Same goal (decouple Head 2 from the binary-dominated
  trunk) but it is **multi-step and higher-risk**: a frozen encoder may lack family-discriminative
  directions, and partial fine-tuning adds knobs (LRs, freeze schedule). A9.7 is the clean,
  single-factor first step; escalate to two-stage only if A9.7's gains are small.

## 10. Why this design avoids random retraining

- **One controlled factor** (Head 2 architecture) vs a frozen A9 baseline.
- **Additive, flag-gated** change → A9 remains exactly reproducible.
- **Separate output paths**; A9/A9.6 never overwritten.
- **Pre-registered** success/failure gates and a **≥3-seed** protocol, so promotion is based on
  signal beyond noise — not on a lucky single run.
- **Validation-only** selection and a **single final test**; no test-set tuning, no fake metrics.

## 11. Stop condition

Stop here and wait for main-review/user approval. Do **not** implement the Head 2 branch, do **not**
create the A9.7 config, and do **not** train. On approval, execute Task A9.7 exactly as specified
above.
