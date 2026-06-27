# UNSW Deep Result-Weakness Audit (Task A9.65)

Status: `Analysis-only`. No code, config, preprocessing, training, smoke, checkpoint, or
final-metric changes were made. Only the A9.65 audit documents and audit JSON/CSV were created.

Generated: `2026-06-24`

Scope: a deep, skeptical, read-only investigation into **why the UNSW-NB15 hierarchical
Head 2 (attack-family) is weak**, whether any hidden code/design/data/metric bug is
limiting it, and what is realistically achievable on the corrected official UNSW protocol.

---

## 1. Executive summary

- **No bug was found.** Labels, masks, taxonomy ordering, the masked multi-task loss, the
  class-weight wiring, the metric computation, and the confusion-matrix ordering were all
  independently verified and are correct. The reported A9 numbers are **honest and not
  inflated** (the binary macro-F1 reconstructs exactly from the confusion matrix, and the
  Head 2 macro-F1 is computed over the full 9-class set so never-predicted classes correctly
  score 0).
- **The weakness is real and largely intrinsic to UNSW-NB15, not a pipeline defect.** The
  attack-family macro-F1 (0.5004) is held down almost entirely by **Analysis (F1 0.012)** and
  **Backdoor (F1 0.070)**, which are mutually confused with **DoS** and **Exploits** in the
  feature space *by construction* of the UNSW labels.
- **The single most actionable structural lever** is that **Head 2 is only a linear layer on
  top of a shared embedding that is shaped mostly by the easy binary task**. This is a
  capacity/representation limit, not a bug.
- **A9.6 failed for a diagnosable reason:** increasing the global `attack_loss_weight` to 1.5
  added more minority/hard pressure, which **lowered rare-class precision** (Shellcode
  precision 0.308 → 0.236) and **did not separate Analysis/Backdoor**, so macro-F1 dropped.
- **Focal loss is therefore NOT the clearly-best next step.** Focal loss + the existing class
  weights is *another* minority/hard-pressure lever and risks repeating A9.6's precision
  collapse. It is kept as a later, precision-gated option, not the recommendation.
- **>0.9 attack-family macro-F1 is unrealistic** on the corrected official UNSW split. A
  realistic, honest target after a few controlled experiments is **0.53–0.60**, with the
  qualitative goal of lifting at least one of Analysis/Backdoor/DoS off the floor without
  collapsing Shellcode/Worms precision.

**Bottom line:** A9 is a sound, honest baseline. The next gains should come from **Head 2
capacity + better checkpoint selection + rare-class precision repair**, validated with
**multi-seed** runs — not from piling more loss pressure on the minority classes.

---

## 2. Files inspected

Result artifacts (A9):
`results/final/hierarchical/unsw/test_metrics.json`, `per_class_attack_metrics.csv`,
`rare_class_metrics.csv`, `attack_family_confusion_matrix.csv`, `binary_confusion_matrix.csv`,
`hierarchical_routing_summary.json`, `training_history.csv`, `class_weight_snapshot.json`,
`results/audits/hierarchical_training_manifest_unsw_nb15.json`,
`docs/HIERARCHICAL_TRAINING_REPORT.md`.

Result artifacts (A9.6):
`results/final/hierarchical/unsw_a9_6_head2_loss_weight/test_metrics.json`,
`attack_family_confusion_matrix.csv`, `training_history.csv`.

Data / labels:
`data/processed/unsw_nb15/hierarchical/split_summary.json`,
`attack_family_label_mapping.json`, `hierarchical_preprocessing_manifest.json`,
`feature_names.json`.

Configs:
`configs/training/unsw_nb15_hierarchical.yaml`, `..._a9_6_head2_loss_weight.yaml`,
`configs/preprocessing/unsw_nb15_binary.yaml`, `..._hierarchical.yaml`,
`configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`.

Code:
`secureids/models/secureids_hierarchical_advanced_net.py`,
`secureids/training/hierarchical_trainer.py`, `hierarchical_evaluation.py`,
`hierarchical_metrics.py`, `hierarchical_class_weights.py`, `hierarchical_config.py`.

Prior review docs (for reconciliation):
`docs/UNSW_HIERARCHICAL_IMPROVEMENT_PLAN.md`,
`docs/UNSW_NEXT_CONTROLLED_IMPROVEMENT_DECISION.md`.

## 3. Commands run

All inspection was **read-only**:

- One ripgrep content search for stale `\b190\b` references across the repo.
- Two file globs to enumerate `results/final/hierarchical/**` and `results/audits/unsw_*`.
- Everything else was direct file reads.

No command trained, evaluated, preprocessed, created checkpoints/metrics, modified source/configs,
or touched Git.

---

## 4. A9 / A9.6 recap

| Metric | A9 (baseline) | A9.6 (`attack_loss_weight`=1.5) | Δ (A9.6 − A9) |
| --- | ---: | ---: | ---: |
| Test binary macro-F1 | 0.894488 | 0.911474 | +0.016986 |
| Test binary F1 | 0.910133 | 0.922570 | +0.012437 |
| Attack false negatives | 2,310 | 2,593 | +283 |
| Benign false positives | 6,186 | 4,581 | −1,605 |
| **Test attack-family macro-F1** | **0.500429** | **0.485478** | **−0.014951** |
| Attack-family accuracy | 0.766478 | 0.761140 | −0.005338 |
| Rare-class macro-F1 | 0.385669 | 0.362125 | −0.023544 |

Per-class test F1:

| Class | Train support | A9 F1 | A9.6 F1 | A9 precision | A9 recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Generic | 33,959 | 0.9808 | 0.9811 | 0.998 | 0.964 |
| Reconnaissance | 8,902 | 0.8227 | 0.8286 | 0.803 | 0.843 |
| Fuzzers | 15,445 | 0.7679 | 0.7425 | 0.837 | 0.710 |
| Exploits | 28,482 | 0.6907 | 0.6996 | 0.778 | 0.621 |
| Shellcode | 965 | 0.4399 | 0.3684 | 0.308 | 0.770 |
| DoS | 10,397 | 0.3877 | 0.3375 | 0.324 | 0.483 |
| Worms | 109 | 0.3314 | 0.3558 | 0.221 | 0.659 |
| Backdoor | 1,505 | 0.0704 | 0.0481 | 0.045 | 0.163 |
| Analysis | 1,675 | 0.0123 | 0.0076 | 0.037 | 0.007 |

The macro-F1 is the unweighted mean of these nine F1s. **Analysis + Backdoor alone cost the
macro roughly 0.18** (two classes near 0 instead of, say, 0.45). That is the whole story of the
ceiling.

---

## 5. Confirmed bugs

**None.** The following were each independently verified as correct:

- **Label / taxonomy ordering.** `attack_family_label_mapping.json` maps Generic 0, Exploits 1,
  Fuzzers 2, DoS 3, Reconnaissance 4, Analysis 5, Backdoor 6, Shellcode 7, Worms 8. The
  `per_class_attack_metrics.csv` `class_id` order and the confusion-matrix column order match
  exactly. **No off-by-one.**
- **Support consistency.** `split_summary.json` test counts equal the `test_metrics.json`
  per-class supports to the row (Generic 18,871; Analysis 677; Backdoor 583; Shellcode 378;
  Worms 44). No silent label drift between preprocessing and evaluation.
- **Mask integrity.** `split_summary.json` confirms, for every split,
  `y_attack_family == -1` exactly where `mask == 0`, `mask_0_count == benign_count`, and attack
  rows carry valid `0..8` labels. The trainer's `_validate_split_labels` enforces the same at
  run time.
- **Loss masking.** `compute_hierarchical_loss` applies Head 2 CrossEntropy only to
  `(mask == 1) & (y_attack != ignore)`; benign rows are excluded; an all-benign batch returns a
  zero attack-loss tensor (no NaN).
- **Class-weight wiring.** `pos_weight` is passed to `BCEWithLogits` (Head 1) and
  `attack_class_weights` to `F.cross_entropy(weight=...)` (Head 2), length-validated against
  `attack_head_dim` and ordered by class id. `attack_loss_weight` genuinely scales the Head 2
  term, and A9.6 truly used 1.5.
- **Metric honesty.** Head 2 macro-F1 is computed over the **full fixed 9-class set**, so a
  never-predicted class scores 0 and drags the macro down (no inflation). Head 2 metrics use
  **attack rows only**. The headline Head 2 macro-F1 is **teacher-forced** (Head-1-independent);
  the routed end-to-end view is slightly *harsher* (only 0.7208 of true attacks are detected
  **and** correctly attributed), so 0.50 is not an optimistic number. Binary macro-F1 0.894488
  reconstructs exactly from the confusion matrix (benign-F1 0.8789, attack-F1 0.9101).

---

## 6. Findings by audit area

### 6.1 Data and preprocessing

- **`X` source.** Hierarchical `X_*` are copied from the binary pipeline
  (`X_source_policy: copied_from_binary`); scaler/encoder are fit **train-only**
  (`no_scaler_encoder_refit_on_test: true`). Scientifically safe.
- **Feature composition (RC7).** Of **192 features, 133 (69%) are `proto_*` one-hot dummies**,
  most ultra-rare protocols (e.g. `proto_aris`, `proto_aes-sp3-d`). The informative signal lives
  in ~39 numeric flow features + 13 `service_*` + 7 `state_*`. The one-hot columns are
  **StandardScaler-scaled**, which amplifies rare-category spikes. This dilutes the feature
  space, but it is **not the dominant limiter** — the same features yield Generic 0.98 and
  Reconnaissance 0.82. Classified *possible*, medium-priority, modest expected upside.
- **Unknown categories.** Encoder uses `handle_unknown: ignore`, so a test-only protocol becomes
  all-zeros. This is a negligible, scientifically-safe coverage gap (proto is weakly
  discriminative for the hard classes).
- **Split / protocol (RC4).** The A8.8 correction is in place: train+val on the canonical
  175,341-row partition, test on the 82,332-row partition. **The two official partitions have
  different priors** — train+val is 31.9% benign, test is 44.9% benign. This is the source of the
  binary FP inflation on test and the val→test gap; it is a *property of the benchmark*, not a bug.
- **No stale 190 in the active path.** All residual `190` references are in legacy binary/FedAvg
  configs (intentionally legacy), historical design docs, `README.md:46`, two **dimension-agnostic**
  smoke tests, and the pytest cache. The active hierarchical training/preprocessing path and the
  trained artifacts are correctly **192** (RC11, documentation hygiene only).

### 6.2 Labels and taxonomy

Verified clean (see §5). Worth highlighting the **absolute scarcity**: Worms has only **109**
train attack rows, Shellcode 965, Backdoor 1,505, Analysis 1,675 — against Generic 33,959 and
Exploits 28,482 (RC2). Rare classes therefore have high-variance, low-precision behaviour, and the
class weighting (Worms 3.95×, Shellcode 1.33×) buys **recall** (Shellcode 0.77, Worms 0.66) at a
**precision** cost (0.31, 0.22).

### 6.3 Model architecture (RC3 — most actionable)

`SecureIDSHierarchicalAdvancedNet`: an input transition + residual MLP encoder
(`hidden_dims = 256,128,128`, LayerNorm, dropout 0.20) → a gated block → a 128-d shared
embedding, with **two single linear heads**: `binary_head = Linear(128, 1)` and
`attack_head = Linear(128, 9)`.

- The binary task is easy and near-saturated (`train_binary_loss` 0.077; `val_binary_macro_f1`
  ~0.93 and flat), so the shared embedding is organized mostly for **benign-vs-attack** separation.
- Head 2 is asked to carve **nine** families — including the overlapping cluster — out of that
  binary-shaped 128-d space with **one linear layer** (`train_attack_loss` stays high at 0.69;
  `val_attack_family_macro_f1` plateaus ~0.59).
- This is a **capacity/representation** limit, not a bug, and it is the cleanest single lever:
  give Head 2 its own non-linear branch so it can model family boundaries without forcing that
  non-linearity through the binary-serving trunk.

### 6.4 Loss and training logic

- Masked multi-task loss is correct (§5). `total_loss = bin_w·BCE + atk_w·CE`.
- **`attack_loss_weight` is a blunt global lever (RC5).** A9.6 raised it to 1.5; the result was
  **more over-prediction of already-recalled minorities** (Shellcode precision 0.308 → 0.236; DoS
  F1 0.388 → 0.338) and **no movement on Analysis/Backdoor**, so macro-F1 fell. The lesson: more
  global minority pressure is the wrong direction.
- **No LR scheduler / no grad clipping (RC8).** LR is constant 0.001 for all 40 epochs; training
  hit `max_epochs` (best epoch 35) rather than early-stopping, but `val_attack_family_macro_f1`
  had effectively plateaued by epoch ~19–25. Longer training is unlikely to raise the ceiling.
- **No class-balanced sampler (RC9).** ~0.75 Worms per 1,024-row batch — but rare *recall* is
  already high; the problem is *precision*. A balanced sampler would not help macro-F1 and could
  hurt it. (Oversampling is also disabled by project policy.)

### 6.5 Training configuration

Seed 42 (single seed), batch 1,024, max 40 epochs, AdamW lr 1e-3, weight_decay 1e-4, early-stop
patience 6 on `val_hierarchical_score`. Checkpoint selected by validation only; test evaluated
once. **One factor changed in A9.6** (loss weights + separate output paths) — confirmed clean and
properly isolated.

### 6.6 Metrics and evaluation

Correct and not inflated (§5). One nuance worth stating in the project narrative: the **headline
Head 2 macro-F1 is teacher-forced** (computed on all true-attack rows regardless of Head 1), while
the **routed** metric (`attack_detected_and_correctly_attributed_rate = 0.7208`) already folds in
the ~5% of attacks Head 1 misses. So the routed reality is slightly *worse* than 0.50, not better.

### 6.7 Result files and training history

- `training_history.csv` (A9): `val_binary_macro_f1` ranges only ~0.92–0.933 (span 0.013), while
  `val_attack_family_macro_f1` ranges ~0.47–0.59 (span 0.12). The 0.5/0.5 selection blend is
  therefore driven mostly by the attack term, but a near-flat binary term still occupies half the
  signal (RC10).
- **val → test gap:** binary macro 0.933 → 0.894; attack macro 0.592 → 0.500; benign FP rate
  0.055 → 0.167. Consistent with the official-partition prior shift (RC4), not overfitting per se
  (train attack loss kept falling while val attack F1 plateaued — a mild irreducible-error/overfit
  regime).
- **Confusion structure (RC1):** true Analysis → DoS 479/677 and → Backdoor 109/677 (5 correct);
  true Backdoor → DoS 409/583 (95 correct); true DoS → Exploits 1,039 and → Backdoor 775. DoS and
  Backdoor act as **over-predicted "sinks"** for the overlapping cluster (DoS precision 0.324,
  Backdoor 0.045), while Analysis is essentially never predicted (recall 0.007).

### 6.8 V1/V6 reference ideas (read-only, not copied)

Useful *ideas* (not code) for keeping results honest and informative, consistent with the V1 rule:
validation-only **threshold calibration**, explicit **weak-class / false-negative reports**, and a
**validation-vs-test gap report**. These are reporting/diagnostic ideas; none are used as V2 final
metrics and no V1 file was read for code reuse.

---

## 7. Why A9.6 failed (diagnosis)

A9.6 increased Head 2 loss pressure globally. Because the rare classes were **already
recall-saturated by the class weights**, the extra pressure mostly **traded precision for a little
more recall** (Shellcode precision −0.07; DoS precision −0.02) and pushed more of the overlapping
cluster into the DoS/Backdoor sinks. It could not separate Analysis/Backdoor because those families
**overlap in feature space** (RC1) — no loss-scaling magnitude fixes that. Net: macro-F1 −0.0150,
rare macro-F1 −0.0235. The binary side improved only because a *different* (epoch-36) encoder state
was selected; with a **single seed**, that ~0.017 binary swing is partly selection noise (RC6).

---

## 8. Is focal loss still the best next step? — No

Focal loss `(1−p)^γ` down-weights easy examples and focuses on hard ones. But:

1. The Analysis/Backdoor problem is **inter-class overlap**, not "hard examples inside a separable
   class." Focal loss reweights the loss surface; it **cannot separate overlapping families**.
2. Focal loss **on top of the existing class weights** is *another* minority/hard-pressure lever —
   the same direction that **already failed in A9.6** and collapsed rare precision. The original
   A9.5 plan even flagged this risk ("can destabilize rare precision with weights").

Focal loss is therefore **demoted** from "the next step" to a **later, precision-gated option**
(`attack_loss_weight` back to 1.0; γ≈1.5; hard floors on Shellcode/Worms precision; ≥3 seeds). It is
credible, but the evidence does not single it out as best.

---

## 9. Realistic expectations

- **>0.9 attack-family macro-F1: not realistic** on the corrected official UNSW split.
  Analysis/Backdoor/DoS/Exploits overlap by construction; published 9-class UNSW work routinely
  reports near-zero Analysis/Backdoor F1 and macro-F1 in the **~0.45–0.60** band (high
  *weighted*-F1 ~0.75–0.80 is dominated by Generic/Exploits and is a different, easier number).
- **Realistic target: 0.53–0.60** macro-F1 after a few careful controlled experiments, with
  rare-class macro-F1 held ≥ 0.385669 and at least one of Analysis/Backdoor/DoS lifted off the
  floor. A defensible headline goal is **~0.55**. The stretch ceiling on this protocol is ~0.60.

A project that reports a **rigorous, multi-seed ~0.55 macro-F1 with a strong binary head
(macro-F1 ~0.89–0.91), an honest val→test gap, and a clear weak-class analysis** is far more
impressive and credible than an inflated number that would not survive scrutiny.

---

## 10. Recommendation (next single controlled experiment)

**Primary: `A9.7 head2_branch_capacity`** — add a dedicated 2-layer non-linear Head 2 branch
(e.g. `128 → 128 → 9`, GELU + dropout) on the existing shared embedding; keep CrossEntropy,
train-only class weights, `attack_loss_weight = 1.0`, optimizer, LR, threshold, validation
objective, and the corrected UNSW protocol **unchanged**. One controlled factor (Head 2 depth).
It directly targets RC3 and **avoids the A9.6 minority-pressure failure mode**.

Cheap companion / diagnostic: **`A9.8 selection_objective_reweight`** (change only the validation
blend to `0.3·binary + 0.7·attack`). Precision-repair option: **`A9.9 attack_weight_cap_down`**.
Focal loss is a later gated alternative. See `docs/UNSW_STRONG_RESULTS_IMPROVEMENT_ROADMAP.md` and
`results/audits/unsw_next_experiment_ranking.csv` for the full ranking, gates, and realistic targets.

**Methodology requirement (keeps results honest):** run every future experiment with **≥3 seeds**,
report **mean ± std**, keep **A9 as the frozen baseline** on separate output paths, promote only on
differences **beyond the noise band** and the existing success gates, and **never select or tune on
the test split**.

---

## 11. No-edit / no-training safety confirmation

- `training_was_run`: **false** · `smoke_was_run`: **false** · `preprocessing_was_run`: **false**
- `checkpoints_created`: **false** · `final_metrics_created`: **false**
- Source code modified: **false** · Configs modified: **false**
- A9 / A9.6 artifacts modified: **false**
- V1 modified / V1 code copied: **false / false**
- Git operations: **none**
- CICIDS / FedAvg / security / attacks / Trimmed Mean / XAI / dashboard started: **none**
- Only the A9.65 audit documents and audit JSON/CSV were created.
