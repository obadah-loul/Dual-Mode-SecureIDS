# UNSW Strong-Results Improvement Roadmap (Task A9.65)

Status: `Analysis / planning only`. No experiment was implemented, no config was created,
no training was run. A9 remains the current accepted UNSW hierarchical baseline.

Generated: `2026-06-24`

Companion documents: `docs/UNSW_DEEP_RESULT_WEAKNESS_AUDIT.md`,
`results/audits/unsw_deep_result_weakness_audit.json`,
`results/audits/unsw_next_experiment_ranking.csv`,
`results/audits/unsw_deep_result_weakness_findings.csv`.

---

## 1. Goal and honesty contract

The user wants a strong, impressive, **and honest** project. This roadmap is written to that
contract:

- We pursue **much stronger Head 2 results where the science allows it**.
- We **do not** promise attack-family macro-F1 above 0.9 — it is not achievable on the corrected
  official UNSW split (see §6).
- We treat A9 as a **frozen baseline**, change **one controlled factor at a time**, validate with
  **multiple seeds**, and **never tune on the test split**.

---

## 2. What is realistically improvable vs. what is UNSW-limited

**Improvable (worth experiments):**
- Head 2 **capacity / representation** for family boundaries (the shared embedding is
  binary-dominated and Head 2 is a single linear layer).
- **Checkpoint selection** alignment toward attack-family macro-F1 (binary is near-saturated and
  over-weighted in selection).
- **Rare-class precision** (Shellcode/Worms/Backdoor are over-assigned; recall is already high).
- A little binary FP/threshold behaviour via **validation-only calibration**.

**UNSW-limited (manage, don't over-promise):**
- **Analysis** and **Backdoor** separability. They overlap with DoS/Exploits *by construction*;
  no loss trick separates classes that share feature space. Expect them to stay weak.
- **Worms** absolute support (109 train rows) caps how stable its F1 can be.
- The **val→test gap** from the official-partition prior shift (train 31.9% benign vs test 44.9%).

---

## 3. Ranked experiment roadmap

Each entry is a **single controlled change** vs. A9, on **separate output paths**, validated with
**≥3 seeds (mean ± std)**. Full table: `results/audits/unsw_next_experiment_ranking.csv`.

### Rank 1 — `A9.7 head2_branch_capacity` (recommended next; safest high-evidence)
- **Change:** replace the single `attack_head = Linear(128, 9)` with a dedicated non-linear
  branch (e.g. `Linear(128,128) → GELU → Dropout → Linear(128,9)`). Keep everything else identical
  (CrossEntropy, train-only class weights, `attack_loss_weight = 1.0`, AdamW lr 1e-3, threshold 0.5,
  0.5/0.5 validation objective, corrected protocol).
- **Targets:** RC3 (Head 2 capacity), indirectly RC1 (better non-linear boundaries in the
  overlapping cluster).
- **Why first:** it is the one structural lever that adds capacity **without** adding minority loss
  pressure, so it avoids the exact mechanism that made A9.6 fail.
- **Expected:** attack macro-F1 **+0.01 to +0.04** (3-seed mean). Risk: low–medium (mild overfit;
  mitigated by keeping dropout). 
- **Honest caveat:** unlikely to move Analysis much (intrinsic overlap).

### Rank 2 — `A9.8 selection_objective_reweight` (cheap companion / free diagnostic)
- **Change:** only the validation selection blend → `0.3·val_binary_macro_f1 +
  0.7·val_attack_family_macro_f1`. No training-dynamics change.
- **Targets:** RC10. Biases checkpoint choice toward better Head 2 epochs.
- **Expected:** **0.00 to +0.01**. Risk: very low. Bounded by the plateau (selection cannot exceed
  the best attack-F1 epoch actually produced). Good as a zero-cost first step or bundled diagnostic.

### Rank 3 — `A9.9 attack_weight_cap_down` (precision repair)
- **Change:** lower the attack class-weight cap / soften the sqrt-inverse weights so rare classes
  are **less over-assigned** (the opposite direction to A9.6).
- **Targets:** RC2/RC5 (rare-class precision: Shellcode 0.31, Worms 0.22, Backdoor 0.045).
- **Expected:** **−0.01 to +0.02** macro-F1; the aim is to convert some excess recall into
  precision. Risk: low. Must hold rare-class macro-F1 ≥ 0.385669.

### Rank 4 — `head2_focal_loss` (demoted; later, precision-gated)
- **Change:** Head 2 focal loss (γ≈1.5) on attack rows, `attack_loss_weight` back to 1.0, keep
  train-only weights.
- **Why demoted:** focal + class weights is another minority/hard-pressure lever and risks
  repeating A9.6's rare-precision collapse (RC5); it cannot separate overlapping families (RC1).
- **Expected:** **−0.02 to +0.03** (uncertain). Only run with **hard precision floors** (Shellcode
  ≥ 0.25, Worms ≥ 0.18) and ≥3 seeds.

### Rank 5 — `feature_cleanup` (later; medium effort)
- **Change:** prune ultra-rare `proto_*` dummies / frequency-encode `proto` / leave one-hots
  unscaled (RC7). Requires careful re-preprocessing and **changes `feature_dim`**, so it breaks
  direct comparability and needs its own preprocessing-safety pass.
- **Expected:** **0.00 to +0.02**; modest because the easy classes are not feature-limited.

### Rank 6 — `two_stage_head2_finetune` (later; higher complexity)
- **Change:** joint warmup → freeze the shared encoder → fine-tune a stronger attack-only Head 2.
- **Targets:** RC3 more aggressively (decouples Head 2 from the binary-dominated trunk).
- **Expected:** **+0.01 to +0.04**; risk medium–high (more moving parts; multi-step protocol).

### Rank 7 — `threshold_calibration` (optional; binary only)
- **Change:** validation-only decision-threshold tuning to trade FP/FN (RC4). Helps the binary FP
  story, **not** Head 2 macro-F1, and the benefit is bounded by the val/test prior difference.

### Avoid for now
- **Oversampling / SMOTE / balanced sampler:** rare recall is already high; chasing more recall
  hurts macro-F1, and oversampling is disabled by project policy.
- **Large capacity increases / aggressive regularization sweeps:** overfit + random-tuning risk.
- **Merging Analysis/Backdoor/DoS into a training super-class:** only acceptable as a *secondary
  reporting head*, never as the headline 9-class metric (it would change the problem).
- **Any test-set-informed tuning or selection:** forbidden.

---

## 4. Suggested sequence and combined target

1. `A9.7 head2_branch_capacity` (3 seeds) — primary structural lift.
2. Bundle/`A9.8 selection_objective_reweight` — pick the best Head 2 epoch cheaply.
3. `A9.9 attack_weight_cap_down` — convert excess rare recall into precision.

**Combined realistic outcome:** attack-family macro-F1 **~0.53–0.58** (3-seed mean), rare-class
macro-F1 **≥ 0.385669**, with **at least one** of Analysis/Backdoor/DoS lifted off the floor and a
binary head held at **macro-F1 ~0.89–0.91**. Stretch ceiling on this protocol: **~0.60**.

---

## 5. Promotion gates (reuse and extend the A9.6 plan gates)

A future run may replace A9 as the accepted baseline only if, on **3-seed mean**:
- Attack-family macro-F1 ≥ **0.535** and beats A9 beyond the noise band (≥ ~0.02 absolute).
- Attack-family accuracy ≥ 0.760.
- Binary macro-F1 ≥ 0.884 and binary F1 ≥ 0.905.
- Attack false negatives ≤ 2,450; benign false positives ≤ 7,000.
- Rare-class macro-F1 ≥ 0.385669; Shellcode F1 ≥ 0.4099 (precision ≥ 0.25);
  Worms F1 ≥ 0.2814 (precision ≥ 0.18).
- At least one of Analysis / Backdoor / DoS improves without rare-class collapse.
- Training stable, complete, no NaN; A9/A9.6 artifacts untouched; separate output paths used.

---

## 6. Is attack-family macro-F1 > 0.9 realistic? — No

On the corrected official UNSW-NB15 split this is **not realistic**. Analysis/Backdoor/DoS/Exploits
overlap by construction; honest 9-class macro-F1 in the literature sits in the **~0.45–0.60** band.
A macro-F1 > 0.9 would require near-perfect separation of intrinsically-entangled families and is
not achievable from these features without changing the problem (merging families, or adding richer
data than UNSW provides). The honest, defensible target is **0.53–0.60**, headline **~0.55**.

---

## 7. How to avoid fake results

- **Multi-seed** every experiment (≥3); report mean ± std; ignore sub-noise "wins."
- **Train-only** class weights; **validation-only** selection and calibration; **one** final test.
- **Never** select or tune on test; never report smoke or legacy pre-correction numbers as final.
- Keep **A9 frozen**; write each experiment to **separate paths**; document failures honestly
  (as A9.6 was).
- Report **both** the teacher-forced Head 2 macro-F1 **and** the routed end-to-end attribution rate,
  plus the **val→test gap** and a **weak-class** breakdown, so the numbers are self-explaining.

---

## 8. Safety confirmation

No code, configs, preprocessing, training, smoke, checkpoints, or final metrics were created or
modified by this roadmap. A9 and A9.6 artifacts are untouched. V1 was not modified or copied. No
Git, CICIDS, FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work was started. Only the
A9.65 audit/roadmap documents and audit JSON/CSV were created. **Stop for main-review approval
before implementing any experiment.**
