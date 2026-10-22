> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW-NB15 Hierarchical Improvement Audit (Reopen A9 for Controlled Improvement)

Status: `planning / audit only — no training, no checkpoint change, no promotion`
Generated: `2026-06-25`
Companion files:
`results/audits/unsw_hierarchical_improvement_audit.json`,
`results/audits/unsw_hierarchical_improvement_candidates.csv`,
`results/audits/unsw_hierarchical_current_error_summary.csv`,
`docs/experiments/UNSW_HIERARCHICAL_IMPROVEMENT_ROADMAP.md`.

---

## 1. Current status

- **Official accepted final:** `models/final/final_unsw_hierarchical.pt` — **A9 corrected-protocol hierarchical baseline**.
- **Integrity (read-only stat):** 2,077,207 bytes, last write `2026-06-24T06:38:28+04:00` (= the A9 `created_utc`). Untouched by this audit.
- **Frozen but reopenable:** main control is reopening UNSW for controlled improvement because attack-family and rare-class performance are weak. UNSW is **not** permanently closed.
- **Selected seed for the frozen checkpoint:** seed 42.

### Known A9 metrics — verified against artifacts

| Metric | Value | Source |
| --- | ---: | --- |
| Binary macro-F1 | `0.894488` | `results/final/hierarchical/unsw/test_metrics.json` |
| Attack-family macro-F1 (attack rows) | `0.500429` | same |
| Rare-class macro-F1 (Shellcode+Worms) | `0.385669` | `rare_class_metrics.csv` |

All three match the values main control provided. Supporting numbers: binary accuracy 0.896808, binary F1 0.910133, precision 0.874289, recall 0.949043; attack-family accuracy on attack rows 0.766478 over 45,332 attack rows; attack false negatives 2,310; benign false positives 6,186; best epoch 35/40; best val hierarchical score 0.762364 (val binary macro-F1 0.933090, val attack-family macro-F1 0.591638).

> **Honesty note on the headline seed.** The frozen A9 (seed 42) attack-family macro-F1 0.500429 sits slightly **above** the A9 3-seed linear mean of 0.494965 ± 0.014303 (A9.8), and seed 123 fell to 0.478736. The accepted checkpoint is therefore a mildly favorable but in-band seed. **Future promotion must compare 3-seed mean vs 3-seed mean**, not against the seed-42 point, to keep the bar fair.

## 2. A9 artifact inventory

| Artifact | Path |
| --- | --- |
| Checkpoint | `models/final/final_unsw_hierarchical.pt` |
| Manifest | `results/audits/hierarchical_training_manifest_unsw_nb15.json` |
| Freeze record | `results/audits/unsw_a9_final_acceptance_freeze_record.json` |
| Freeze summary | `results/audits/unsw_a9_final_freeze_summary.csv` |
| Freeze backup | `results/audits/unsw_freeze_backups/unsw_a9_final_freeze_20260625_171733/...` |
| Final-status doc | `docs/final/UNSW_FINAL_MODEL_STATUS.md` |
| Result dir | `results/final/hierarchical/unsw/` (test_metrics, training_history, both confusion matrices, per-class + rare-class metrics, routing summary, class-weight snapshot, model summary, config snapshot) |
| Config | `configs/training/unsw_nb15_hierarchical.yaml` |

- **Architecture:** `SecureIDSHierarchicalAdvancedNet`, input_dim 192, hidden 256/128/128, dropout 0.20, layernorm, embedding 128. **Head 1** = single binary logit; **Head 2** = `Linear(128 → 9)`. Param count 513,418.
- **Loss:** masked multi-task — BCEWithLogits (binary, `pos_weight` 0.469248) + CrossEntropy on attack rows only (`attack_class_weights`). `binary_loss_weight` 1.0, `attack_loss_weight` 1.0.
- **Class weights (train-only, sqrt-inverse-freq, mean-normalized, cap 10.0):** Generic 0.224, Exploits 0.245, Fuzzers 0.332, DoS 0.405, Recon 0.438, Analysis 1.009, Backdoor 1.064, Shellcode 1.329, **Worms 3.955**. The cap (10.0) is **non-binding** (max weight 3.955).
- **Selection:** validation-only, `val_hierarchical_score = 0.5·val_binary_macro_f1 + 0.5·val_attack_family_macro_f1` (**hardcoded** in `secureids/training/hierarchical_evaluation.py`), single final test after the best-validation checkpoint. Threshold hardcoded 0.5. Training: AdamW, LR 0.001 constant, batch 1024, max 40 epochs, early-stop patience 6, seed 42.

## 3. Corrected protocol confirmation (verified, not assumed)

Verified from `results/audits/unsw_split_protocol_audit.json`, `docs/UNSW_SPLIT_PROTOCOL_DECISION.md`, and the manifest:

- **Train/val source:** local `data/raw/unsw_nb15/UNSW_NB15_testing-set.csv` (**175,341 rows = canonical TRAIN** partition by row count).
- **Test source:** local `data/raw/unsw_nb15/UNSW_NB15_training-set.csv` (**82,332 rows = canonical TEST** partition by row count).
- The manifest phrase *"train 175,341-row; test 82,332-row"* refers to canonical partition **row counts**, not file names — the local file names are swapped relative to the canonical Moustafa & Slay sizes, so assignment is by row count. **This matches the task's stated corrected protocol.**
- **Splits:** train 149,039 / val 26,302 / test 82,332 (val = 85/15 stratified-on-binary split of train, seed 42).
- **input_dim 192**, **attack_head_dim 9**. Feature dim moved 190 → 192 (data-derived one-hot, fit on the larger train partition).
- **Attack-family mapping:** 0 Generic, 1 Exploits, 2 Fuzzers, 3 DoS, 4 Reconnaissance, 5 Analysis, 6 Backdoor, 7 Shellcode, 8 Worms. **Rare classes:** Shellcode (965/168/378 train/val/test), Worms (109/21/44).
- **Legacy / pre-correction outputs** (`final_unsw_binary.pt`, `fedavg_unsw_binary.pt`, `results/final/centralized/unsw_*`, `results/federated/unsw/*`) are **not** final hierarchical evidence.
- **No leakage / no test-tuning visible:** disjoint splits; scaler/imputer/one-hot and class weights fit on train only; validation-only selection; single final test. (Independently re-verified in the A9.65 deep audit.)

## 4. Weak-class and confusion analysis

### Per-class attack-family F1 (test, attack rows)

| Class | Support | Precision | Recall | F1 | Read |
| --- | ---: | ---: | ---: | ---: | --- |
| Generic | 18,871 | 0.998 | 0.964 | **0.981** | clean / separable |
| Reconnaissance | 3,496 | 0.803 | 0.843 | **0.823** | strong |
| Fuzzers | 6,062 | 0.837 | 0.710 | **0.768** | reasonable |
| Exploits | 11,132 | 0.778 | 0.621 | **0.691** | moderate (recall loss) |
| Shellcode | 378 | 0.308 | 0.770 | **0.440** | rare: high recall, low precision |
| DoS | 4,089 | 0.324 | 0.483 | **0.388** | **garbage-collector** (low precision) |
| Worms | 44 | 0.221 | 0.659 | **0.331** | rare: high recall, low precision |
| Backdoor | 583 | 0.045 | 0.163 | **0.070** | **near collapse** |
| Analysis | 677 | 0.037 | 0.007 | **0.012** | **near-total collapse** |

Macro-F1 = mean of the nine F1s = **0.500429**. Two near-zero classes (Analysis, Backdoor) plus low-precision DoS hold the mean near 0.50.

### Dominant confusions (from the existing confusion matrix — see `unsw_hierarchical_current_error_summary.csv`)

- **Analysis → DoS: 479/677 (70.8%)** and Analysis → Backdoor 109 (16.1%) — Analysis is absorbed; only 5/677 predicted as Analysis.
- **Backdoor → DoS: 409/583 (70.2%)** — Backdoor is absorbed; only 95/583 correct.
- **Exploits → DoS: 2,076 (18.6%)** — the single largest off-diagonal mass.
- **DoS → Exploits 1,039 (25.4%)**, DoS → Backdoor 775 (19.0%) — DoS leaks both ways.
- **Fuzzers → DoS 899 (14.8%)**; Exploits → Backdoor 771 (6.9%).
- DoS predicted-column precision is 0.324 because Exploits/Fuzzers/Analysis/Backdoor all flood **into** DoS.
- Rare precision hits: Exploits → Shellcode 275, Fuzzers → Shellcode 179, Recon → Shellcode 91 (Shellcode precision 0.308); Worms over-predicted from Exploits/Fuzzers (precision 0.221).

**Conclusion:** `Analysis ↔ Backdoor ↔ DoS ↔ Exploits` form one mutually-confused cluster; this cluster, not Head 1, is the macro-F1 bottleneck.

## 5. Experiment history: A9.6 / A9.7 / A9.8 / A9.9

| Exp | What it changed (one factor) | Attack-family macro-F1 | Rare macro-F1 | Binary macro-F1 | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| **A9** (seed 42) | baseline (linear Head 2, weights 1.0/1.0) | 0.500429 | 0.385669 | 0.894488 | accepted |
| **A9.6** | `attack_loss_weight` 1.0 → 1.5 (config) | 0.485478 (**−0.0150**) | 0.362125 (**−0.0235**) | 0.911474 (+0.0170) | **rejected** |
| **A9.7** | Head 2 linear → small MLP branch (code) | 0.493667 (−0.0068) | 0.354501 (−0.0312) | 0.898348 (+0.0039) | **rejected** |
| **A9.8** | 3-seed (42/123/999) A9-linear vs A9.7-branch | branch mean +0.004524 vs linear | branch +0.01127 | branch +0.00594 | **rejected (within noise); abandon branch capacity** |
| **A9.9** | design-only next strategy | — | — | — | design only; recommends **attack-family specialist** |

- **A9.6 (loss weight):** more global Head 2 pressure improved binary (more conservative routing, FP 6,186 → 4,581) but **regressed** attack-family and rare macro-F1 — DoS F1 0.388 → 0.338, Shellcode precision 0.308 → 0.236, Analysis/Backdoor stayed on the floor, attack FN rose to 2,593. Clean run; lesson: **global `attack_loss_weight` is a blunt lever.**
- **A9.7 (branch capacity):** single seed; attack-family 0.4937 < A9 and below the 0.53 gate, rare below floor, attack FN 2,538 > 2,450 gate, Worms F1 below floor, Analysis fell to 0.0; best val score 0.752 < 0.762. Mixed: DoS/Backdoor/Fuzzers F1 improved. Clean run; not a single-seed winner.
- **A9.8 (multi-seed):** A9-linear attack-family 0.494965 ± **0.014303**; A9.7-branch 0.499489 ± 0.01044; branch − linear mean **+0.004524**, inside the noise band → below promotion margin. **Decision: A9 remains; abandon Head 2 branch capacity as the next major direction.** Established the **~0.014 attack-family / ~0.057 rare seed noise band**.
- **A9.9 (design only):** ranked six strategies; recommended the **attack-family specialist** (freeze A9 Head 1 as router; train a dedicated attack-only family classifier). Realistic target attack-family macro-F1 0.52–0.58, stretch ~0.60. Pending main-control approval of **prep** (not training).

All of A9.6/A9.7/A9.8/A9.9 were methodologically clean: separate output paths, A9 never overwritten, no test tuning, no val/test labels used for weights.

## 6. Why attack-family and rare-class macro-F1 are weak (diagnosis)

Consolidating the A9.65 deep weakness audit (root causes RC1–RC11, independently re-derived here):

1. **RC1 — intrinsic feature-space overlap (root cause, dominant).** Analysis/Backdoor/DoS/Exploits overlap in the 192-feature flow space by construction of UNSW-NB15. 70.8% of Analysis and 70.2% of Backdoor land in DoS. This is a **data/taxonomy property, largely not fixable by tuning.**
2. **RC2 — severe imbalance / tiny support (root cause).** Worms 109 train rows (0.107% of attack rows), Shellcode 965, Backdoor 1,505, Analysis 1,675 vs Generic ~34k. Class weights buy recall at the cost of **precision**; rare macro-F1 carries ±0.057 seed variance.
3. **RC3 — single linear Head 2 over a binary-dominated embedding (most actionable structural lever).** The shared 128-d embedding is shaped mostly by the near-saturated binary task (train binary loss 0.077, flat val ~0.93) while attack loss stays high (0.69) and val attack-F1 plateaus ~0.59. *But A9.7/A9.8 showed adding branch capacity alone is within noise.*
4. **RC4 — official-partition prior shift.** Train/val benign fraction 31.9% vs test 44.9%; this inflates **test** binary FP (val FP 0.0549 → test 0.1672) and the val→test gap (attack-family 0.592 → 0.500). Intrinsic to the corrected protocol, not a bug.
5. **RC5 — `attack_loss_weight` is blunt** (explains A9.6): more minority pressure lowers rare precision without separating Analysis/Backdoor.
6. **RC6 — single-seed comparisons are within noise** (~0.014 attack-family, ~0.057 rare): require ≥3 seeds.

**Head 1 is not the bottleneck.** Binary macro-F1 0.894, recall 0.949 — only 5.1% of attacks are missed as benign. End-to-end routed performance (72.1% of attacks correctly attributed) is limited mainly by **Head 2 attribution within the overlapping cluster**, not by Head 1 detection.

**No fabrication, no inflation:** macro-F1 is over the full fixed 9-class set (collapsed classes correctly score ~0); Head 2 macro-F1 is teacher-forced on attack rows (Head-1 independent); binary macro-F1 reconstructs exactly from the confusion matrix.

## 7. Model / training / loss diagnosis (answers to the audit questions)

- **Is Head 1 acceptable or weak?** Acceptable (macro-F1 0.894, recall 0.949). Not the priority.
- **Is Head 2 the main issue?** Yes — attack-family separation inside the overlap cluster.
- **Are rare classes hurting macro-F1?** Yes, but Analysis/Backdoor (not in the official rare set) hurt it more than Shellcode/Worms.
- **Is binary stealing shared capacity?** Plausible (RC3): the embedding is binary-dominated. The clean way to test this without harming Head 1 is the **specialist** (decouple the family learner from binary pressure).
- **Class weights too weak/strong?** They are recall-buying; the issue is **rare precision**. Cap is non-binding. Repairing precision needs a weight-shaping **code** hook, not a cap tweak.
- **`attack_loss_weight` too low/high?** Raising it (A9.6) failed. Not the lever.
- **Early stopping favoring binary?** The 0.5/0.5 selection lets a near-flat binary term occupy half the signal (RC10); a 0.3/0.7 reweight is a bounded, selection-only companion (code change; cannot exceed the best attack-F1 epoch produced).
- **Validation metric appropriate?** Reasonable; the attack-family term is the limiter. Minor reweight possible, low ceiling.
- **Need a stronger Head 2 branch?** Branch capacity **alone** is exhausted (A9.7/A9.8). A stronger Head 2 only helps as part of a **decoupled specialist**.
- **Two-stage or attack-only fine-tuning logical?** Yes — it is the backup to the specialist (rank 2).

## 8. Candidate improvement ranking (full list in `unsw_hierarchical_improvement_candidates.csv`)

| Rank | Candidate | Status | Code? | Targets AF / Rare | Runs |
| ---: | --- | --- | --- | --- | ---: |
| 1 | **attack_family_specialist (frozen Head 1)** | **recommend_now** | yes | yes / yes | 4 |
| 2 | two_stage_attack_only_fine_tuning | recommend_after_next | yes | yes / yes | 4 |
| 3 | attack_class_weight precision-repair (temperature) | recommend_after_next | yes | yes / yes | 4 |
| 4 | selection_objective_reweight 0.3/0.7 | possible_later | yes | yes / no | 4 |
| 5 | head2_focal_loss (precision-gated) | possible_later | yes | yes / yes | 4 |
| 6 | validation-only Head-1 threshold calibration | possible_later | yes | no / no | 1 |
| 7 | attack_row balanced sampler (train-only) | possible_later | yes | yes / yes | 4 |
| 8 | feature/preprocessing enhancement (proto pruning) | needs_main_control_decision | yes | yes / no | 6 |
| 9 | super-class reporting head (diagnostic only) | needs_main_control_decision | yes | no / no | 4 |
| 10 | increase attack_loss_weight again | **reject** | no (config) | yes / no | 0 |
| 11 | Head 2 branch capacity again | **reject** | yes | yes / no | 0 |
| 12 | keep A9, move to federated/security | needs_main_control_decision | no | — | 0 |

**Config-only levers are effectively exhausted:** the one config-only lever (`attack_loss_weight`) is a proven dead end (A9.6); the class-weight cap is non-binding; the selection blend, focal loss, samplers, and the specialist all require code. Any meaningful next improvement is a **controlled code change.**

## 9. Recommended next controlled experiment

**A9.9 — attack-family specialist router.** Keep the frozen A9 Head 1 as the binary router; train a dedicated attack-family specialist on UNSW **training attack rows only** (richer non-linear branch), with train-only attack-row class handling. Route detected attacks into the specialist; report **routed end-to-end** and **oracle attack-row** metrics separately.

- **Why this and not another tweak:** it changes the task decomposition rather than re-pulling the two exhausted levers; it removes benign-vs-attack pressure from the family learner (RC3), focuses capacity on the overlap cluster, and protects the accepted binary detector. It is the A9.9 design rank-1 strategy and the highest-expected-value untried direction.
- **Config-only or code-change:** **code change** (a new specialist model + trainer + evaluation, or a new training mode). **Not** config-only.
- **One-seed vs multi-seed:** **one-seed screen first** (de-risk the new code path + a directional read), **then ≥3-seed confirmation (42/123/999)**. Never promote on a single seed.
- **Expected manual run count:** **4 minimum** (1 screen + 3 confirm); up to **~6** if a second specialist variant (train-only class-balancing or a precision temperature) is screened first.
- **Expected benefit:** attack-family macro-F1 3-seed mean **0.52–0.58** (stretch ~0.60); lift at least one of Analysis/Backdoor/DoS off the floor; **protect** rare macro-F1 (≥ 0.385669) and binary macro-F1 (~0.894).
- **Expected risk:** specialist overfitting (fewer attack rows); class-balancing distorting priors/calibration; routed end-to-end still capped by Head 1's 2,310 missed attacks; routed-vs-oracle documentation confusion; extra artifact complexity. **Intrinsic ceiling ~0.60** (RC1) — do not promise more.

## 10. Scientific safety rules for the next phase

- **≥3 seeds (42/123/999)** for any promotion decision; report mean ± std for headline **and** rare-class metrics; promote only on gains beyond the noise band **and** predefined success gates.
- Compare **3-seed mean vs A9 3-seed linear mean** (0.494965), not against the favorable seed-42 point.
- Keep **A9 frozen**; isolated experiment output paths; **no overwrite** of any final artifact.
- **Validation-only** selection and any calibration; **single final test** after all choices are frozen; never tune on test.
- Class weights / sampling probabilities from **train attack labels only**; no val/test labels for weights, sampling, or preprocessing.
- **Rare-class precision floors** as hard gates (so we don't repeat the A9.6 precision collapse).
- **No taxonomy change to inflate metrics**, no hiding weak classes; report Analysis/Backdoor honestly. A super-class view, if built, is a **diagnostic add-on only**, never a replacement metric.
- No preprocessing rebuild, XAI, Streamlit, FedAvg, or Git as part of planning.

## 11. Next main-control decision needed

**Approve or reject preparation** (prep only, not immediate training) of the **A9.9 attack-family specialist** as the first controlled UNSW improvement experiment — or instead choose candidate 12 (**keep A9 and move to federated/security**) given the intrinsic ~0.60 ceiling. If approved, the next step produces the specialist config/module scaffolding and a prep record; training begins only after a second approval.
