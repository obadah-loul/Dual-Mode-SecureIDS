# CICIDS Hierarchical EXP03 1.25 — Formal Aggregate Review & Promotion Audit

Status: `Audit only — promotion NOT executed`. No checkpoint, result, manifest, or report under
`models/final/` or `results/final/` was created, copied, modified, or overwritten.

Generated: `2026-06-25`

Current status update: **PROMOTED_WITH_WARNINGS**. EXP03 1.25 seed999 is now the official CICIDS
hierarchical final model at `models/final/final_cicids_hierarchical.pt`. The historical status line
above records the state at the time of the aggregate audit, before the promotion was executed.

Promotion record: `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json`.
Promoted source checkpoint:
`models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`.
Previous baseline backup:
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.
Rollback target:
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136/models_final/final_cicids_hierarchical.pt`.

Hash verification:

- Source SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Final SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Hashes match: `True`

Companion: `results/audits/cicids_hierarchical_exp03_125_aggregate_review.json`,
`results/audits/cicids_hierarchical_exp03_125_aggregate_metrics.csv`,
`results/audits/cicids_hierarchical_final_candidate_summary.csv`,
`docs/experiments/CICIDS_HIERARCHICAL_EXP03_125_SAFE_PROMOTION_PLAN.md`.

---

## 1. Current status

- **Official accepted final after promotion:** `models/final/final_cicids_hierarchical.pt`
  (size 1,961,387 bytes, last written 2026-06-25 00:22 local — recorded for integrity).
- **Strongest candidate:** `cicids_hierarchical_exp03_attack_loss_weight_125_confirmation` (3-seed).
- **Selected candidate checkpoint:**
  `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` (exists, 1,964,481 bytes).
- **Recommendation:** **`PROMOTE_WITH_WARNINGS_PENDING_MAIN_CONTROL_APPROVAL`**.

Current status: EXP03 1.25 seed999 is the official final model. This document is the formal record that
EXP03 1.25 was the best CICIDS candidate and justified the later promotion.

## 2. Experiment history

- **EXP01 (`head2_mlp_capacity`) — REJECTED / diagnostic only.** A non-linear MLP Head 2 did not improve
  attack-family macro-F1 (0.849111 → 0.846994, within noise); the hard SlowHTTPTest/FTP pair did not
  move. Capacity is not the CICIDS Head-2 lever. Baseline remained accepted.
- **EXP02 (`attack_loss_weight` 1.5) — improvement family, NOT promoted.** 3-seed mean lifted
  attack-family (0.859641) and rare-class (0.751845) but regressed routing (correct-attribution 0.905235,
  missed-as-benign 0.056220). The Head-2/rare gain came at a Head-1 conservatism cost, so it was not
  promoted.
- **EXP03 screening (`{1.25, 1.35}` at seed42, validation-only).** `1.25` was selected; `1.35`
  destabilized tiny classes (seed42 SQL-Injection precision collapsed to 0.091 / F1 0.16) without moving
  the hard pair. `1.25` advanced to 3-seed confirmation.
- **EXP03 1.25 confirmation (seeds 42/123/999, linear Head 2, `binary_loss_weight` 1.0).** The strongest
  CICIDS result family so far — the subject of this audit.

## 3. Per-seed metrics (EXP03 1.25, test split; validation score for selection)

| Seed | best_epoch | val_hier_score | Binary macro-F1 | Attack-family macro-F1 | Rare macro-F1 | Correct attrib. | Missed-as-benign | Benign FP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 9 | 0.909871 | 0.972019 | 0.867881 | 0.765155 | 0.909144 | 0.053081 | 0.010484 |
| 123 | 4 | 0.905829 | 0.973807 | 0.869983 | 0.778473 | 0.902253 | 0.057191 | 0.006692 |
| **999** | 6 | **0.913383** | **0.974604** | **0.875094** | **0.780177** | **0.913331** | **0.051221** | **0.008267** |

Seed999 has the **highest validation hierarchical score** and is also the strongest seed on test — the
two agree, so the selection is not a test cherry-pick.

## 4. 3-seed aggregate (mean ± sample std) and comparisons

| Metric | Baseline | EXP02 mean | **EXP03 1.25 mean ± std** | Δ vs baseline | Δ vs EXP02 |
| --- | --- | --- | --- | --- | --- |
| Binary macro-F1 | 0.972167 | 0.973222 | **0.973477 ± 0.001324** | +0.001310 | +0.000255 |
| Attack-family macro-F1 | 0.849111 | 0.859641 | **0.870986 ± 0.003710** | **+0.021875** | +0.011345 |
| Rare-class macro-F1 | 0.716987 | 0.751845 | **0.774602 ± 0.008225** | **+0.057615** | +0.022757 |
| Correct attribution | 0.909008 | 0.905235 | **0.908243 ± 0.005594** | −0.000765 | +0.003008 |
| Missed as benign | 0.053807 | 0.056220 | **0.053831 ± 0.003055** | +0.000024 | −0.002389 |
| Benign false alarm | 0.010008 | 0.007776 | **0.008481 ± 0.001905** | −0.001527 | +0.000705 |

**Versus baseline:** large, low-variance gains on attack-family (+0.0219) and rare-class (+0.0576),
binary up, benign false alarm down; routing essentially at baseline (the two routing deltas are far
inside their std).

**Versus EXP02 1.5:** EXP03 1.25 **dominates** — better attack-family (+0.0113), rare (+0.0228),
correct-attribution (+0.0030) **and** missed-as-benign (−0.0024). Lowering the weight from 1.5 to 1.25
kept the Head-2/rare gains and recovered the routing EXP02 had lost.

## 5. The selected checkpoint (seed999) beats baseline on every headline metric

| Metric | Baseline | seed999 | Δ |
| --- | --- | --- | --- |
| Binary macro-F1 | 0.972167 | 0.974604 | +0.002437 |
| Attack-family macro-F1 | 0.849111 | 0.875094 | +0.025983 |
| Rare-class macro-F1 | 0.716987 | 0.780177 | +0.063190 |
| Correct attribution | 0.909008 | 0.913331 | +0.004323 |
| Missed as benign | 0.053807 | 0.051221 | −0.002586 (better) |
| Benign false alarm | 0.010008 | 0.008267 | −0.001741 (better) |

**Important honesty note:** the tiny mean-level routing dip (§4) comes entirely from seed123. The
**actually-promoted artifact (seed999) is uniformly better than baseline**, including both routing
metrics. The warnings below are family-level and limitation-level, not regressions of the selected
checkpoint.

## 6. Weak-class movement (vs baseline)

| Class | Support | Baseline F1 | EXP03 mean F1 | seed999 F1 | Verdict |
| --- | --- | --- | --- | --- | --- |
| DoS-SlowHTTPTest | 20,941 | 0.553 | 0.582 | 0.581 | Improved, stable, still feature-limited |
| FTP-BruteForce | 28,928 | 0.779 | 0.771 | 0.781 | Mild mean dip (seed123); seed999 ≥ baseline |
| Web-BruteForce | 96 | 0.364 | 0.686 | 0.697 | Strong stable gain (precision 0.24→~0.75) |
| Web-XSS | 38 | 0.618 | 0.618 | 0.618 | Stuck/tiny — guardrail, do not over-claim |
| SQL-Injection | 12 | 0.800 | 0.753 | 0.762 | Pure variance — guardrail, do not over-claim |

## 7. Remaining limitations (reported honestly)

- **DoS-SlowHTTPTest ↔ FTP-BruteForce** is the dominant unresolved confusion (~14,758 pair errors,
  conserved across the loss-weight sweep).
- **FTP-BruteForce** family-mean F1 is slightly below baseline (0.7787 → 0.7705), driven by seed123; the
  selected seed999 is at/above baseline.
- **Web-XSS (38)** is frozen at F1 0.618; **SQL-Injection (12)** is high-variance — both tiny-support,
  must not be over-claimed.
- 3-seed mean correct-attribution is 0.000765 below baseline and missed-as-benign 0.000024 above — both
  within noise and absent from the selected seed999 checkpoint.

## 8. EXP04 diagnostic evidence (why we stop model/loss tuning here)

The EXP04 feature/confusion diagnostic concluded the SlowHTTPTest/FTP pair is **feature-limited**: a
trivial linear probe on the same 77 features reaches ~0.682 balanced accuracy on the pair, **matching or
exceeding** the deep model (0.675) — no model headroom. Only 3 of 77 features separate the classes and
the natural separator (destination port) is absent. Conclusion: more model/loss runs would only
redistribute the conserved pair error, so **promoting EXP03 1.25 with documented limitations is the
honest choice**; raising the ceiling would require a feature-engineering / new-preprocessing protocol (a
separate main-control decision).

## 9. Selected checkpoint and why it is validation-selected

- **Selected:** `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`.
- **Why seed999:** highest **validation** hierarchical score among the three seeds (0.913383 vs 0.909871
  / 0.905829), where `val_hierarchical_score = 0.5·val_binary_macro_f1 + 0.5·val_attack_family_macro_f1`.
  This is a **validation-based** selection (each seed's `checkpoint_not_selected_by_test_metrics: true`);
  the test split was evaluated once after the best-validation checkpoint and was not used to choose the
  seed. That seed999 is also the best test seed simply confirms the choice.

## 10. Statements

- **No fake results:** every number here was read from the existing per-seed `test_metrics.json`, routing
  summaries, per-class/rare-class CSVs, and confusion matrices, or computed from them; the 3-seed means
  reproduce the provided aggregate exactly. Nothing was fabricated or cherry-picked.
- **No test tuning:** checkpoint and seed selection were validation-only; test was evaluated once per
  seed; no hyperparameter, seed, or threshold was chosen from test performance.
- **No overwrite:** no `models/final/` or `results/final/` artifact was modified, copied, or replaced;
  the final checkpoint is untouched (integrity recorded). This is a promotion **plan**, not a promotion.

## 11. Final recommendation

Current outcome: **PROMOTED_WITH_WARNINGS**. EXP03 1.25 seed999 is now the official CICIDS final model.
The original recommendation text below is retained as historical context from before main-control
approval and promotion execution.

**`PROMOTE_WITH_WARNINGS_PENDING_MAIN_CONTROL_APPROVAL`.** EXP03 1.25 is the strongest CICIDS result
family and the selected seed999 checkpoint beats the baseline on every headline metric with the
limitations documented above. Proceed per
`docs/experiments/CICIDS_HIERARCHICAL_EXP03_125_SAFE_PROMOTION_PLAN.md` **only after main-control
approval** (backup-before-replace mandatory). Next decision: **main control approves or declines the safe
final promotion.**
