# UNSW Advanced Hierarchical Performance-Engineering Plan (Task A9.7-design)

Status: `Design / analysis only`. No training, smoke, preprocessing, checkpoint, or final-metric
work was performed. No source, config, A9, or A9.6 artifact was modified. Only the A9.7-design
documents and audit JSON/CSV were created. **A9 remains the accepted UNSW hierarchical baseline.**

Generated: `2026-06-24`

Companion documents: `docs/UNSW_NEXT_EXPERIMENT_DESIGN_DECISION.md`,
`results/audits/unsw_advanced_performance_engineering_plan.json`,
`results/audits/unsw_experiment_design_ranking.csv`. Builds on
`docs/UNSW_DEEP_RESULT_WEAKNESS_AUDIT.md` (A9.65).

---

## 1. Executive summary

This is a **performance-engineering** review, not a bug hunt (A9.65 already confirmed there are no
bugs). The goal is to design the **strongest clean path** to raise UNSW Head 2 (attack-family)
macro-F1 above the A9 baseline without fake results, leakage, or random retraining.

The decisive engineering observation: **Head 2 is starved of capacity.** Of the model's **513,418
parameters, the attack-family head is a single `Linear(128 → 9)` ≈ 1,161 params — about 0.23% of
the network** — sitting on a 128-d embedding that the easy, near-saturated binary task shapes first
and most. A single linear layer cannot draw the **non-linear boundaries** needed to separate the
overlapping UNSW families.

Therefore the recommended next experiment is **`A9.7 head2_branch_capacity`**: give Head 2 its own
small non-linear branch (`128 → 128 → 9`, GELU + LayerNorm + Dropout) while changing **nothing
else**. This is strictly stronger than focal loss because it adds **capacity, not minority loss
pressure** — and minority loss pressure is exactly what made A9.6 fail (it lowered rare-class
precision and never separated Analysis/Backdoor). The experiment is one controlled factor, low
complexity, and must be validated with **≥3 seeds (mean ± std)**.

**Realistic targets (honest):** attack-family macro-F1 **0.51–0.54** after A9.7 (3-seed mean), and
**0.53–0.60** after 1–3 stacked experiments, headline **~0.55**. **>0.9 is not realistic** on the
corrected official UNSW protocol and we do not promise it.

---

## 2. Files inspected

Reused from the A9.65 read-only audit (model, trainer, loss, evaluation, metrics, class-weights,
configs, split summary, feature names, both confusion matrices, both training histories) plus one
new read this task: `results/final/hierarchical/unsw/model_summary.json` (exact `param_count`).

Key code: `secureids/models/secureids_hierarchical_advanced_net.py`,
`secureids/training/hierarchical_trainer.py`, `hierarchical_evaluation.py`,
`hierarchical_class_weights.py`. Key configs: `configs/training/unsw_nb15_hierarchical.yaml`,
`..._a9_6_head2_loss_weight.yaml`. Key data: `data/processed/unsw_nb15/hierarchical/*`.

## 3. Commands run

Read-only only: read `model_summary.json`; all other evidence reused from A9.65 (one ripgrep + two
globs + file reads). Nothing trained, evaluated, preprocessed, or touched Git.

---

## 4. A9 / A9.6 recap

| Metric | A9 (baseline) | A9.6 (`attack_loss_weight`=1.5) |
| --- | ---: | ---: |
| Binary macro-F1 | 0.894488 | 0.911474 |
| Binary F1 / attack recall | 0.910133 / 0.949 | 0.922570 / 0.943 |
| Attack false negatives / benign false positives | 2,310 / 6,186 | 2,593 / 4,581 |
| **Attack-family macro-F1** | **0.500429** | **0.485478** |
| Attack-family accuracy | 0.766478 | 0.761140 |
| Rare-class macro-F1 | 0.385669 | 0.362125 |

A9.6 improved binary but **harmed Head 2 and rare classes** → A9 stays the baseline.

---

## 5. What is already strong (do not risk it)

- **Binary Head 1** is excellent and near-saturated: macro-F1 0.894, F1 0.910, attack recall 0.949;
  only **5.1%** of attacks are missed-as-benign.
- **Clean, leakage-free methodology:** train-only class weights, validation-only checkpoint
  selection, one final test, correct attack-row masking (`ignore_index = -1`).
- **Honest metrics:** macro-F1 over the **full fixed 9-class set** (never-predicted classes score 0);
  Head 2 scored on attack rows only; both the teacher-forced headline and the harsher routed
  attribution rate (0.7208) are reported. Binary macro-F1 reconstructs exactly from the confusion
  matrix. This is professor-facing quality.
- **Strong families already:** Generic 0.981, Reconnaissance 0.823, Fuzzers 0.768, Exploits 0.691.
- **Reproducible & well-instrumented:** per-epoch history, confusion matrices, routing summary,
  manifest, class-weight snapshot, model summary.

## 6. What is weak

- **Head 2 macro-F1 = 0.500**, dominated by **Analysis (0.012)** and **Backdoor (0.070)**, then
  **DoS (0.388)**.
- **Wrong-family attribution is the main blocker, not missed detection:** 22.8% of attacks are
  detected-but-wrong-family vs only 5.1% missed-as-benign. The hierarchy detects attacks well; it
  *labels the family* poorly.
- **Rare-class precision** is low (Shellcode 0.308, Worms 0.221) — class weighting bought recall at
  precision's expense.
- **Head 2 capacity is ~0.23% of the model** on a binary-dominated embedding.

## 7. What should NOT be changed

The binary head and binary loss; the corrected UNSW protocol / `input_dim 192` / 9-class Head 2 /
masking; train-only weights, validation-only selection, single final test, and all metric
definitions; A9 and A9.6 artifacts; and the oversampling-disabled policy.

---

## 8. Findings by area (with classification)

### 8.1 Model architecture — **likely issue (primary lever)**
Encoder ≈ 512k params; **Head 2 = single `Linear(128,9)` ≈ 1,161 params**. Binary loss saturates
early (train 0.077; val macro ~0.93, flat); Head 2 plateaus (val macro ~0.59). The shared embedding
is organized for benign-vs-attack first. *Impact: high. Complexity: low. Overfit risk: low–medium.
Needs controlled experiment: yes. Before more training: yes.*

### 8.2 Head 2 capacity & attribution — **likely issue**
The confusion matrix shows wrong-family attribution into **DoS/Backdoor "sinks"**; a single linear
layer cannot model the non-linear boundaries of the {Analysis, Backdoor, DoS, Exploits} cluster.
This is the cleanest thing to fix. *Impact: medium–high. Complexity: low. Overfit: low–medium.*

### 8.3 Loss design — **confirmed issue (explains A9.6)**
Masking/weight wiring is correct, but **global `attack_loss_weight` is blunt.** A9.6 (1.5) lowered
rare precision (Shellcode 0.308→0.236) and didn't separate Analysis/Backdoor → macro down.
*Implication: more minority pressure is the wrong direction; focal-loss-with-weights risks the same.*

### 8.4 Class-weight strategy — **possible issue**
sqrt-inverse-frequency, mean-normalized, cap 10 (max used 3.95 for Worms). Rare recall high,
precision low ⇒ the cap/temperature may **over-assign** rare classes. A cap-down experiment can
**repair precision** (opposite direction to A9.6). *Impact: low–medium. Complexity: low.*

### 8.5 Sampler / batch strategy — **unlikely issue**
~0.75 Worms and ~6.6 Shellcode per 1,024-row batch, but rare **recall is already high** — the
problem is **precision**. Balanced sampling/oversampling would not help macro-F1 and could hurt
precision; oversampling is also disabled by policy. *Do not pursue for macro-F1.*

### 8.6 Validation objective & selection — **possible issue**
`0.5·binary + 0.5·attack`, yet val-binary span ≈ 0.013 vs val-attack span ≈ 0.12. The near-flat
binary term occupies half the selection signal. A **0.3/0.7** reweight (validation-only) can bias
selection toward better Head 2 epochs. *Impact: low (selection-only, bounded by the plateau).*

### 8.7 Optimizer / LR / early stopping — **unlikely issue**
AdamW lr 1e-3 **constant** (no scheduler), no grad clip; best epoch 35, ran to max 40; val attack
plateaued by ~epoch 19–25. A cosine/ReduceLROnPlateau schedule is *optional polish*, unlikely to
move the ceiling. *Low priority.*

### 8.8 Dropout / regularization / capacity — **not enough evidence (points to underfit)**
dropout 0.20, weight_decay 1e-4. Head 2 shows **underfitting** signs (high train attack loss +
plateaued val), not overfitting — which supports **adding** Head 2 capacity (with its own
dropout/LayerNorm) rather than regularizing more. **Keep the shared encoder stable; modify only
Head 2.**

### 8.9 Metric design & evaluation — **confirmed strength (keep)**
Full-class macro-F1, attack-row-only Head 2, teacher-forced + routed views, CM-consistent binary.
No metric hides failures. Result files are sufficient for a professional, professor-facing report.

### 8.10 Data & preprocessing — **possible issue**
**133/192 features are ultra-rare `proto_*` one-hots**, StandardScaler-scaled — signal dilution.
But the easy classes already score well, so features are **not the dominant limiter**. Changing the
feature set alters `feature_dim`, **breaks comparability** with A9/A9.6, and needs its own
preprocessing-safety gates. *Later, medium-priority, modest upside.*

### 8.11 Training history & confusion patterns — **confirmed issue (largely intrinsic)**
Analysis→DoS 479/677, Backdoor→DoS 409/583, DoS→Exploits 1,039. **DoS/Backdoor are over-predicted
sinks.** The **val→test gap** (binary 0.933→0.894; attack 0.592→0.500) tracks the **official-partition
prior shift** (benign 31.9% train vs 44.9% test) — a property of the corrected benchmark, not
overfitting. Much of the Analysis/Backdoor weakness is **intrinsic to UNSW**.

### 8.12 Methodology — **confirmed issue (rigor)**
Per-epoch val attack macro-F1 swings ±0.02–0.03; A9 vs A9.6 differ only **0.015 at N=1 seed** — within
noise. **Every future experiment must use ≥3 seeds and report mean ± std**, promoting only beyond the
noise band.

---

## 9. Ranked improvement options

Full table with risk columns: `results/audits/unsw_experiment_design_ranking.csv`.

| Rank | Experiment | Type | Expected Δ macro-F1 | Overfit risk | Complexity | Sci-validity risk | Verdict |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | **`A9.7 head2_branch_capacity`** | Head-2 architecture | **+0.01…+0.04** | low–med | low | low | **Recommended next** |
| 2 | `A9.8 selection_objective_reweight` | val-only selection | 0.00…+0.01 | low | low | low | Cheap companion |
| 3 | `A9.9 attack_weight_cap_down` | class-weight (precision) | −0.01…+0.02 | low | low | low | Secondary |
| 4 | `head2_focal_loss` | loss form | −0.02…+0.03 | medium | low–med | medium | Later, gated |
| 5 | `feature_cleanup` | preprocessing | 0.00…+0.02 | low | med–high | medium | Later |
| 6 | `two_stage_head2_finetune` | training protocol | +0.01…+0.04 | medium | med–high | medium | Later, complex |
| 7 | `threshold_calibration` | val-only routing | 0.00 (binary) | low | low | low | Optional |
| 99 | oversampling / balanced sampler | sampler | negative/flat | high | medium | high | Avoid for now |

---

## 10. Recommended next experiment — `A9.7 head2_branch_capacity`

**Design.** Replace the Head 2 linear layer with a small non-linear branch over the **same** shared
128-d embedding:

```
shared_embedding (128)
  -> Linear(128, 128) -> LayerNorm(128) -> GELU -> Dropout(p = model.dropout)
  -> Linear(128, 9)   # attack-family logits
```

Keep `binary_head = Linear(128, 1)` unchanged. Make the branch **opt-in via a config flag**
(e.g. `model.head2_hidden_dims: [128]`) so that when the flag is absent the model is byte-for-byte
the A9 architecture — A9 stays reproducible. The branch adds **≈17.5k params (~3.4% of the model)**
but **~15× the Head 2 capacity**.

**Why this is stronger than focal loss alone.**
- Focal loss + the existing class weights is **another minority/hard-pressure lever** — the same
  direction that **already failed in A9.6** (rare precision collapsed; Analysis/Backdoor unmoved).
- Focal loss only **reweights** the loss surface; it **cannot create the non-linear decision
  boundary** the overlapping cluster needs. A capacity increase **can**.
- A9.7 changes **capacity, not loss pressure**, so it does not threaten the strong binary head or
  the rare-class precision floors.

**Why Head 2 branch capacity first (vs other options).**
- vs **focal loss**: see above — capacity over pressure.
- vs **class-weight-cap-down**: cap-down only repairs rare *precision* and won't fix DoS/Exploits/
  Backdoor confusion; capacity addresses the broader wrong-family problem. (Run cap-down *after*,
  as A9.9.)
- vs **two-stage fine-tune**: same goal (decouple Head 2 from the binary trunk) but multi-step,
  more knobs, and a frozen encoder may lack family-discriminative directions. A9.7 is the clean,
  single-factor first step; two-stage is a later escalation if A9.7's gains are small.

**Should focal loss be combined?** No — keep it for **later and gated**. Combining capacity + focal
in one run would be two factors and would reintroduce the A9.6 precision risk, muddying attribution
of any change.

---

## 11. Realistic targets and the >0.9 question

- **>0.9 attack-family macro-F1: not realistic** on the corrected official UNSW split.
  Analysis/Backdoor/DoS/Exploits overlap by construction; honest 9-class macro-F1 sits ~0.45–0.60.
- **After A9.7:** attack-family macro-F1 **0.51–0.54** (3-seed mean), rare-class macro-F1 **≥ 0.3857**,
  binary macro-F1 **≥ 0.884**.
- **After 1–3 stacked experiments (A9.7 → A9.8 → A9.9):** **0.53–0.60**, headline **~0.55**, with at
  least one of Analysis/Backdoor/DoS lifted off the floor and rare precision intact.

---

## 12. Exact next task after main-review approval

**Task A9.7 (execution):** implement the opt-in non-linear Head 2 branch behind a model config flag;
create `configs/training/unsw_nb15_hierarchical_a9_7_head2_branch.yaml` (one factor vs A9); train
**UNSW only** with **≥3 seeds**; write to **separate A9.7 output paths**
(`models/final/final_unsw_hierarchical_a9_7_head2_branch.pt`,
`results/final/hierarchical/unsw_a9_7_head2_branch/`,
`results/audits/hierarchical_training_manifest_unsw_nb15_a9_7_head2_branch.json`,
`docs/HIERARCHICAL_TRAINING_REPORT_A9_7_HEAD2_BRANCH.md`); keep A9/A9.6 frozen; select by validation
only; evaluate test once per seed; compare **3-seed mean ± std** against the §gates in the decision
doc. Full specification: `docs/UNSW_NEXT_EXPERIMENT_DESIGN_DECISION.md`.

---

## 13. Safety confirmation

`training_was_run: false` · `smoke_was_run: false` · `preprocessing_was_run: false` ·
`checkpoints_created: false` · `final_metrics_created: false` · source/configs modified: **false** ·
A9/A9.6 artifacts modified: **false** · V1 modified/copied: **false** · Git: **none** ·
CICIDS/FedAvg/security/attacks/Trimmed Mean/XAI/dashboard: **not started** · next-experiment config
created: **false**. Only the A9.7-design documents and audit JSON/CSV were created.
**Stop for main-review approval before implementing A9.7.**
