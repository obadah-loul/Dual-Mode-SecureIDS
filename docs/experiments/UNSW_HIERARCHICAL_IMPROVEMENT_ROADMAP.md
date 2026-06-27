# UNSW-NB15 Hierarchical Improvement Roadmap

Status: `planning only — no training, no checkpoint change, no promotion`
Generated: `2026-06-25`
Companion: `docs/experiments/UNSW_HIERARCHICAL_IMPROVEMENT_AUDIT.md`,
`results/audits/unsw_hierarchical_improvement_audit.json`,
`results/audits/unsw_hierarchical_improvement_candidates.csv`.

---

## 1. Where we are

- **Accepted baseline:** A9 corrected-protocol hierarchical UNSW (`models/final/final_unsw_hierarchical.pt`), frozen but reopenable.
- **Headline:** binary macro-F1 **0.894488**, attack-family macro-F1 **0.500429**, rare-class macro-F1 **0.385669**.
- **Exhausted levers:** A9.6 (`attack_loss_weight` 1.5) failed; A9.7/A9.8 (Head 2 branch capacity, 3 seeds) failed and **branch capacity is officially abandoned** as the next major direction.
- **Bottleneck:** the `Analysis ↔ Backdoor ↔ DoS ↔ Exploits` overlap cluster (RC1) + rare-class precision under severe imbalance (RC2). Head 1 is healthy.
- **Noise band (must clear to promote):** attack-family macro-F1 ≈ **±0.0143**, rare ≈ **±0.0566** (A9.8, 3 seeds).

## 2. Naming for the next experiment

- **`A9.9` — attack-family specialist router** (continues the A9 line; the A9.9 *design* already exists, so this is the **A9.9 implementation** track).
- Stage suffixes:
  - `A9.9-prep` — config/module scaffolding + prep record (no training).
  - `A9.9-screen` — one-seed (42) screening run.
  - `A9.9-confirm` — 3-seed (42/123/999) confirmation.
- If a precision variant is screened: `A9.9b` (e.g. train-only attack-row balancing or a class-weight temperature).

## 3. Recommended run sequence

1. **A9.9-prep (no training).** Main control approves prep. Produce the specialist config, model/trainer/eval modules, `results/audits/unsw_a9_9_specialist_prep.json`, and a plan doc. Predefine **all** promotion gates and artifact paths before any run.
2. **A9.9-screen (1 seed = 42).** De-risk the new code path; get a directional attack-family macro-F1 (oracle attack rows) and routed end-to-end read. Gate: directional improvement over A9 seed 42 **and** no rare-precision collapse. If it clearly regresses, stop and reassess (do not multi-seed a loser).
3. **A9.9-confirm (seeds 42/123/999).** Report mean ± std for binary, attack-family, rare, and per-class Analysis/Backdoor/DoS. Compare **3-seed mean vs A9 linear 3-seed mean (0.494965)**.
4. **Decision.** Promote only if the gates in §5 pass. Otherwise reject and consider candidate 12 (move to federated/security).
5. **(Optional) A9.9b screen** if A9.9 passes the screen but rare precision is fragile — add train-only class-balancing or a precision temperature, then re-confirm.

**Expected manual runs:** 4 minimum (1 screen + 3 confirm); ~6 if A9.9b is screened.

## 4. Candidate ranking summary

| Rank | Candidate | Status | Notes |
| ---: | --- | --- | --- |
| 1 | attack_family_specialist (frozen Head 1) | **recommend_now** | task decomposition; highest upside; code change |
| 2 | two_stage_attack_only_fine_tuning | recommend_after_next | backup to specialist |
| 3 | attack_class_weight precision-repair (temperature) | recommend_after_next | lift rare precision; pairs with specialist |
| 4 | selection_objective_reweight 0.3/0.7 | possible_later | bounded, selection-only |
| 5 | head2_focal_loss (precision-gated) | possible_later | A9.6 cautions; strict floors only |
| 6 | val-only Head-1 threshold calibration | possible_later | FP/FN trade; not an attack-family lever |
| 7 | attack_row balanced sampler (train-only) | possible_later | only inside specialist |
| 8 | feature/preprocessing enhancement | needs_main_control_decision | breaks comparability; leakage risk |
| 9 | super-class reporting head | needs_main_control_decision | diagnostic only; never inflate |
| 10 | increase attack_loss_weight again | **reject** | A9.6 dead end |
| 11 | Head 2 branch capacity again | **reject** | A9.7/A9.8 abandoned |
| 12 | keep A9, move to federated/security | needs_main_control_decision | valid stop given ~0.60 ceiling |

## 5. Promotion / rejection criteria (predefine before the final test)

**Promote A9.9 over A9 only if all hold (3-seed means):**
- Attack-family macro-F1 3-seed mean − A9 linear 3-seed mean (0.494965) **> the noise band** (target ≥ **+0.015**, and beyond the approved margin).
- Rare-class macro-F1 3-seed mean **≥ 0.385669** (no regression).
- Shellcode and Worms **precision floors not breached** (no recall-for-precision collapse like A9.6).
- Binary macro-F1 **not regressed** (Head 1 is frozen, so this should hold by construction).
- At least one of **Analysis / Backdoor / DoS** lifts off the floor without collapsing another.

**Reject if:** the gain is within the noise band, rare precision collapses, or the routed end-to-end attribution does not improve. A within-noise "win" is **not** a promotion.

## 6. Guardrails against test tuning and fake metrics

- **Validation-only** model selection and any calibration; **one** final test after all choices are frozen.
- Compare 3-seed mean vs 3-seed mean (not vs the favorable seed-42 point).
- Class weights / sampling probabilities from **train attack labels only**; never read val/test labels for weights, sampling, or preprocessing.
- **Macro-F1 over the full fixed 9-class set** — never drop or merge collapsed classes to raise the number.
- Keep A9 frozen; **isolated** experiment paths; no overwrite of any `models/final/` or `results/final/` artifact.
- Report **routed end-to-end** and **oracle attack-row** metrics separately and label them clearly.
- No promise of attack-family macro-F1 above the realistic **~0.60** ceiling; do not claim success before training + evaluation.

## 7. If the next experiment fails

- If **A9.9-screen** regresses: stop; do not multi-seed a loser. Record the negative result; consider A9.9b (precision variant) or candidate 3 (weight precision-repair) as a smaller alternative.
- If **A9.9-confirm** lands within the noise band: A9 remains accepted; document the specialist as "tested, not promoted" with its 3-seed mean ± std (same discipline as A9.6/A9.7/A9.8).
- After **two** non-promotable attack-family experiments beyond the abandoned branch capacity, treat the corrected-protocol attack-family ceiling (~0.60) as effectively reached and move to §8.

## 8. When to stop UNSW and move to federated/security

Stop attack-family tuning and accept A9 as the final UNSW model when any of:
- The specialist (and at most one precision variant) fails to clear the noise band across 3 seeds; **or**
- Gains require taxonomy changes, family merging, or feature changes that break comparability or risk leakage; **or**
- The remaining headroom is dominated by intrinsic RC1 overlap (Analysis/Backdoor near-zero by construction).

At that point, the professionally honest move is to **freeze A9 as the final UNSW hierarchical baseline (with documented limitations)** and advance the project to **federated (FedAvg/secure aggregation), robustness/security, and XAI** scope — where new contribution is available — rather than chasing within-noise gains on an intrinsically-entangled 9-class problem.

## 9. Next main-control decision

**Approve or reject `A9.9-prep`** (preparation only, not training) for the attack-family specialist — or select candidate 12 (keep A9, move to federated/security). No training, checkpoint change, or promotion occurs without explicit approval.
