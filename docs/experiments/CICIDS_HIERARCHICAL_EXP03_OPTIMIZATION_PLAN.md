# CICIDS Hierarchical EXP03 — Optimization Plan (planning only)

Status: `Plan only — NOT implemented, NOT trained`. No EXP03 config, checkpoint, or metrics were
created. Requires main-control approval before any config preparation or training.

Generated: `2026-06-25`

Current final-status update: this planning document is historical. EXP03 1.25 seed999 was later
promoted as the official CICIDS hierarchical final model at `models/final/final_cicids_hierarchical.pt`;
the previous baseline is backed up under
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

Companion: `results/audits/cicids_hierarchical_exp03_optimization_plan.json`,
`results/audits/cicids_hierarchical_exp03_candidate_matrix.csv`. Builds on
`docs/experiments/CICIDS_HIERARCHICAL_EXP01_FAILURE_ANALYSIS.md` and
`docs/experiments/CICIDS_HIERARCHICAL_EXP02_PLAN.md`.

---

## 1. Status summary

- **Accepted baseline (unchanged):** `models/final/final_cicids_hierarchical.pt`.
- **EXP01** (Head-2 MLP capacity): `REJECTED_DIAGNOSTIC_ONLY` — capacity is not the CICIDS Head-2 lever.
- **EXP02** (attack_loss_weight 1.0→1.5, linear Head 2, 3 seeds):
  `HEAD2_AND_RARE_CLASS_IMPROVEMENT_FAMILY_NOT_PROMOTED` — it improved Head-2/rare metrics but slightly
  worsened routing (more attacks missed as benign, lower correct attribution), so it is **not** promoted
  as the final CICIDS model.
- **Current final model changed:** No.

## 2. Accepted baseline metrics

| Metric | Baseline |
| --- | --- |
| Binary Head-1 macro-F1 | 0.972167 |
| Attack-family Head-2 macro-F1 | 0.849111 |
| Rare-class macro-F1 | 0.716987 |
| End-to-end correct attribution | 0.909008 |
| Attack missed as benign | 0.053807 |
| Benign false alarm | 0.010008 |

## 3. EXP02 3-seed comparison vs baseline (seeds 42 / 123 / 999)

Std = population std (n=3).

| Metric | Baseline | EXP02 mean | EXP02 std | Delta |
| --- | --- | --- | --- | --- |
| Binary macro-F1 | 0.972167 | 0.973222 | 0.001065 | **+0.001055** |
| Attack-family macro-F1 | 0.849111 | 0.859641 | 0.006148 | **+0.010530** |
| Rare-class macro-F1 | 0.716987 | 0.751845 | 0.006462 | **+0.034858** |
| Correct attribution | 0.909008 | 0.905235 | 0.002834 | **−0.003773** |
| Missed as benign | 0.053807 | 0.056220 | 0.001520 | **+0.002413** |
| Benign false alarm | 0.010008 | 0.007776 | 0.001869 | **−0.002232** |

**What actually moved (from the per-seed per-class CSVs):**

- The **consistent** gain is **Web-BruteForce** (rare): baseline F1 0.3636 (precision **0.24**) → EXP02
  F1 0.678 / 0.744 / 0.693 (precision 0.73 / 0.90 / 0.76) across all three seeds. This rare-class
  precision recovery is the real, reproducible EXP02 win and drives most of the +0.0349 rare-macro gain.
- The **hard pair did NOT reliably move.** DoS-SlowHTTPTest recall: baseline 0.437 → **seed42 0.522**
  (F1 0.553→0.597) but **seed123 0.431** and **seed999 0.445** (≈ baseline). The 3-seed mean on the pair
  is essentially baseline — only the lucky seed42 moved it. This confirms the EXP01 failure analysis:
  the pair is **feature-limited**, and a global loss weight does not reliably separate it.
- SQL-Injection (12 samples) drifted down (0.80 → 0.67 / 0.62 / 0.59) — single-sample noise, not signal.

**Fragility note:** the +0.0105 attack-family mean gain is only ~1.7× its population std (0.0061), and
seed999 (0.8509) is barely above baseline (0.8491). The Head-2 gain is real but fragile and partly
carried by one seed; the rare-class (Web-BruteForce) gain is the more dependable part of EXP02.

## 4. Why EXP02 is not promoted yet

EXP02 is a genuine **improvement family** for Head-2/rare metrics, but it bought that gain with a
**Head-1 conservatism trade-off**: upweighting the attack-family loss shifts the shared encoder (and the
validation-selected epoch) toward attack-family discrimination, and Head 1 drifts slightly conservative —
**correct attribution −0.0038** and **missed-as-benign +0.0024** on the 3-seed mean. For an IDS, "more
attacks slipping through as benign" is exactly the regression we cannot accept silently. A final model
must improve Head-2/rare **without** regressing routing/missed-attack behavior. EXP02 does not yet clear
that bar, so the baseline stays accepted.

## 5. EXP03 goal

**Keep the EXP02 Head-2 / rare-class gains while recovering routing and missed-attack behavior** back to
(or better than) the baseline. Concretely: attack-family macro-F1 ≥ ~0.855 and rare-class macro-F1
≥ ~0.74, **and** correct attribution ≥ 0.909008 **and** missed-as-benign ≤ 0.053807, on the 3-seed mean.

## 6. Recommended EXP03 — conservative `attack_loss_weight` reduction sweep

**`cicids_hierarchical_exp03_attack_loss_weight_conservative_sweep`** — sweep `attack_loss_weight`
**{1.25, 1.35}** on the **baseline linear Head 2**, with `binary_loss_weight` held at **1.0**. One
controlled factor vs baseline; **config-only** (no code, no preprocessing, no taxonomy, no model change).

### 6.1 Why this is best after EXP02

- The **single lever proven responsible** for both effects is the attack-vs-binary loss balance: raising
  it to 1.5 produced the Head-2/rare gain **and** the Head-1 conservatism. Backing it off toward a knee
  (1.25, 1.35) is the most direct way to keep one and recover the other.
- It is **config-only** — `attack_loss_weight` is already wired
  (`hierarchical_trainer.py:266` → `compute_hierarchical_loss`); lowest implementation risk, fully
  reproducible.
- It is the **cheapest controlled next step** (2-value screen + 3-seed confirm = 4–6 runs) before
  committing to any code-change experiment.
- It is **evidence-based**: the consistent EXP02 gain (Web-BruteForce precision) is the kind of effect a
  smaller weight should largely retain, while the conservative Head-1 drift should ease as the weight
  drops.

### 6.2 Conservative attack-loss sweep — value analysis (requirement 1)

| Value | Verdict | Reasoning |
| --- | --- | --- |
| 1.15 | Lower priority | Too close to baseline 1.0; likely loses the Web-BruteForce rare gain. Include only if 1.25 also reverts the gain. |
| **1.25** | **Recommended** | Brackets the low side of the knee; biggest routing-recovery potential while plausibly keeping rare gain. |
| **1.35** | **Recommended** | Brackets the high side of the knee; closest to EXP02 (1.5) so most likely to retain the Head-2/rare gain while easing conservatism. |
| 1.5 | Already done (EXP02) | The current improvement-family point; the routing regression we are trying to undo. |
| 1.75 | **Rejected for now** | Too aggressive. At 1.5 the pair already moved in only 1/3 seeds and missed-as-benign already rose; more weight worsens routing with no reliable Head-2 payoff. A9.6 precedent: `attack_loss_weight` 1.5 hurt UNSW Head-2/rare precision. |

- **Would 1.5→1.25/1.35 keep Head-2 gains while reducing routing regression?** Plausibly yes — that is
  the hypothesis under test — but it is **uncertain**: the knee may not exist (the gain could be given
  back in proportion to the routing recovered, a Pareto wash). That is exactly why EXP03 is a small
  controlled sweep with explicit promotion/rejection criteria, not a presumed win.
- **Is 1.75 too aggressive?** Yes (see table).
- **Small sweep or one value?** A **small 2-value sweep** ({1.25, 1.35}) — we do not yet know where the
  knee is, but a broad grid would be wasteful.
- **How many runs are justified?** **4** (range 4–6) — see §9.

## 7. Binary / routing protection (requirement 2)

- **Protect Head 1 more — yes**, but the cheapest and cleanest protection is to **stop over-upweighting
  attack loss** (reduce 1.5 → 1.25/1.35). That is the EXP03 lever itself.
- **Change `binary_loss_weight`?** **No, not in EXP03.** It is config-adjustable
  (`hierarchical_trainer.py:265`), but changing it would add a second moving factor and break one-factor
  discipline. Keep it at **1.0**; revisit a `binary_loss_weight` increase as a separate experiment only
  if reducing `attack_loss_weight` alone fails to recover routing.
- **Change the validation selection metric?** **No, not now.** The `0.5·binary + 0.5·attack` formula is
  **hardcoded** (`hierarchical_trainer.py:725/884/1026`; the config `formula:` string is descriptive
  only), so changing it is a code change — and the EXP01 analysis showed baseline and EXP01 both already
  select their max-val-attack epoch, so a re-weighting is unlikely to change the chosen epoch for CICIDS.
  Low priority.
- **Add a routing guardrail metric?** **Yes** — and it needs **no code**: the routing summary already
  reports correct-attribution and missed-as-benign. Formalize them as **hard promotion guardrails**
  (promote only if correct-attribution ≥ baseline and missed-as-benign ≤ baseline on the 3-seed mean).
- **Keep `binary_loss_weight` at 1.0 and adjust `attack_loss_weight` only?** **Yes** — that is the
  recommendation.

## 8. Validation-only threshold / routing calibration (requirement 3)

- **Useful?** Conceptually **yes** — the missed-as-benign regression is a Head-1 **operating-point**
  issue, and a validation-calibrated decision threshold (< 0.5) recovers attack recall (fewer missed
  attacks) at a controlled benign-false-alarm cost, **without touching Head 2**.
- **But it needs code.** The threshold is **hardcoded at 0.5** (`hierarchical_trainer.py:242`;
  `hierarchical_metrics.py` default `threshold=0.5`); there is no calibration loop. So this is **not
  config-only**.
- **Exact design (if later approved):**
  - **Validation metric that selects the threshold:** maximize **validation** end-to-end correct
    attribution (equivalently minimize **validation** missed-as-benign) **subject to validation benign
    false alarm ≤ 0.012**.
  - **Candidate thresholds:** a fixed grid **{0.30, 0.35, 0.40, 0.45, 0.50}** (only ≤ 0.5, to recover
    recall).
  - **Freeze before test:** compute the grid on the **validation** split at the already
    validation-selected best checkpoint, pick the winner, and **write it to the manifest before any test
    evaluation**.
  - **Test once:** apply the frozen threshold to the **test** split exactly once and report.
  - **Leakage prevention:** the grid is never computed on test; the checkpoint is validation-selected;
    the threshold is validation-selected; one final test; the threshold is recorded in the manifest.
- **Now or after the sweep?** **After** — as **EXP04**. It needs code, the config-only sweep may already
  recover routing, and calibration should be applied to the **chosen final loss config**, not a moving
  target. Ranked #2 overall, `recommend_after_exp03`.

## 9. Multi-seed design (requirement 5)

- **Recommendation: one-seed validation-only screening first, then 3-seed confirmation** of the single
  winner.
- **Screening seed: 42**, but the choice is made on **validation metrics only** (val attack-family
  macro-F1 to confirm gain retention + val routing for recovery). This matters: seed42 was the
  **optimistic** seed for the hard pair, so we must not let its lucky **test** pair-movement drive the
  screening decision.
- **Confirmation seeds: 42 / 123 / 999** (same as EXP02 for direct comparability).
- **Expected manual runs: 4** — 2 one-seed screens (1.25, 1.35) + the winner at the 2 remaining seeds
  (123, 999); the seed42 screen run's once-computed test is reused for the 3-seed mean because the
  screening choice used validation only. **Up to 6** if both candidates merit full 3-seed confirmation.
- **Avoid promoting a lucky seed:** the promotion decision is on the **3-seed test mean** with a
  **per-seed robustness floor** (no single seed may drop correct-attribution below ~0.900 or push
  missed-as-benign above ~0.058); report **mean ± std**; require the gain to exceed the ~±0.006
  attack-family noise band.

## 10. SlowHTTPTest → FTP-BruteForce confusion (requirement 4)

Known issue: baseline true DoS-SlowHTTPTest predicted as FTP-BruteForce for 11,796 / 20,941 (56%).

- **Did EXP02 reduce it?** **Partially and inconsistently.** Only seed42 improved SlowHTTPTest recall
  (0.437→0.522); seeds 123/999 stayed at baseline (0.431/0.445). On the 3-seed mean the pair is
  essentially unchanged. The EXP02 macro/rare gains came from **Web-BruteForce**, not the pair.
- **Should EXP03 directly target the pair?** **No — not with per-class hacking.** Three-seed evidence
  says the pair is **feature-limited**; class-weight/sampling/specialist tricks aimed at one pair carry
  **high overfit / model-zoo risk** for little reliable gain.
- **Could class weights / loss / sampling / specialist help?** Possibly marginally, but unreliably and
  at real overfit cost; the **specialist module is rejected** (model-zoo). If the loss-balance line
  (EXP03) and threshold calibration (EXP04) cannot move the pair, the only honest fix is **feature
  engineering** (timing/port/protocol features) — a **new preprocessing protocol** that breaks
  comparability, is not a quick experiment, and **needs main-control decision**.
- **No taxonomy changes to inflate metrics:** explicitly honored — we do **not** merge or relabel
  SlowHTTPTest/FTP to make the number look better.

## 11. Candidate option ranking (requirement 6)

Full matrix with benefit/risk/complexity/runs/flags: `cicids_hierarchical_exp03_candidate_matrix.csv`.

| Rank | Option | Classification | Config-only | Code change | May improve Head 2 | May recover routing |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **attack_loss_weight conservative sweep {1.25,1.35}** | **recommend_now** | yes | no | maybe | **yes** |
| 2 | validation-only binary threshold calibration | recommend_after_exp03 | no | yes | no | **yes** |
| 3 | broad attack_loss_weight sweep (incl. 1.15, 1.75) | possible_later | yes | no | maybe | maybe |
| 4 | Head-2 focal loss (γ≈1.5–2.0) | recommend_after_exp03 | no | yes | maybe | no |
| 5 | validation-selection metric adjustment | possible_later | no | yes | maybe | maybe |
| 6 | class-balanced (effective-number) loss | possible_later | no | yes | maybe | no |
| 7 | targeted class-weights on confused pair | needs_main_control_decision | no | yes | maybe | no |
| 8 | SlowHTTPTest-focused weighting | needs_main_control_decision | no | yes | maybe | no |
| 9 | attack-only sampler | possible_later | no | yes | no | no |
| 10 | keep EXP02 and move on | possible_later | yes | no | no | no |
| 11 | attack-family specialist module | reject | no | yes | maybe | no |

## 12. Files that would be created if main control approves

Nothing below is created yet. If approved:

- Configs: `configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_1p25_seed42.yaml`,
  `..._1p35_seed42.yaml`, then `..._<winner>_seed123.yaml`, `..._<winner>_seed999.yaml`.
- Checkpoints: `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_<value>_seed<seed>.pt`.
- Results dir (per run):
  `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_<value>_seed<seed>/` with
  `test_metrics.json`, `training_history.csv`, `per_class_attack_metrics.csv`, `rare_class_metrics.csv`,
  `binary_confusion_matrix.csv`, `attack_family_confusion_matrix.csv`, `hierarchical_routing_summary.json`,
  `training_config_snapshot.yaml`, `class_weight_snapshot.json`, `model_summary.json`.
- Manifests:
  `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_<value>_seed<seed>.json`.
- Reports:
  `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_<VALUE>_SEED<SEED>_REPORT.md`.
- Prep docs (mirroring EXP02): `docs/experiments/CICIDS_HIERARCHICAL_EXP03_3SEED_PREP_PLAN.md`,
  `results/audits/cicids_hierarchical_exp03_3seed_prep.json`,
  `results/audits/cicids_hierarchical_exp03_3seed_expected_runs.csv`.

**Must NOT overwrite:** `models/final/final_cicids_hierarchical.pt`,
`results/final/hierarchical/cicids/`, `results/audits/hierarchical_training_manifest_cicids2018.json`,
`docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md`, or any EXP01/EXP02 artifact. The CICIDS experiment-config
validator (`_validate_cicids_hierarchical_experiment_outputs`) already enforces isolated
`models/experiments/` + `results/experiments/` paths.

## 13. Proposed naming + manual command templates (only after approval)

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
# Screen (validation-only choice):
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids `
  --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_1p25_seed42.yaml --execute
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids `
  --config configs/training/experiments/cicids_hierarchical_exp03_attack_loss_weight_1p35_seed42.yaml --execute
# Then run the validation-chosen winner at seeds 123 and 999 via per-seed config copies, and
# decide promotion on the 3-seed test mean.
```

## 14. Promotion criteria (3-seed test mean)

Promote an EXP03 candidate over baseline only if **all** hold:

- Attack-family macro-F1 ≥ **0.855** (baseline 0.849 + margin beyond the ~±0.006 noise band), without
  losing the Web-BruteForce rare gain.
- Rare-class macro-F1 ≥ **0.740** (retain most of EXP02's rare gain; no rare class → ~0).
- **Correct attribution ≥ 0.909008** (recovered to baseline or better) — core EXP03 objective.
- **Missed-as-benign ≤ 0.053807** (recovered to baseline or better) — core EXP03 objective.
- Binary macro-F1 ≥ 0.970; benign false alarm ≤ 0.012.
- **Per-seed robustness:** no single seed regresses correct-attribution below ~0.900 or missed-as-benign
  above ~0.058.
- Safety: no baseline/EXP01/EXP02 overwrite; validation-only checkpoint selection; train-only weights;
  one final test per seed.

## 15. Rejection criteria

- Routing not recovered (correct-attribution still < baseline **and** missed-as-benign still > baseline).
- Head-2/rare gain given back (attack-family < ~0.855 or rare-class < ~0.740 — the reduction simply
  reverted EXP02).
- No knee exists (every candidate is a Pareto wash) → stop the loss-weight line; escalate to threshold
  calibration (EXP04).
- Binary macro-F1 < 0.970, or instability/NaN.
- Any factor changed beyond `attack_loss_weight`; any test tuning; any baseline/EXP01/EXP02 overwrite.

## 16. No-test-tuning rules

- The sweep value and the winner are chosen on **validation only**; the test split is evaluated **once**
  per seed after checkpoint + (future) threshold are frozen.
- Class weights remain **train-only** (`compute_weights_from: train_only`,
  `allow_test_based_weights: false`).
- No threshold, no taxonomy, no preprocessing, and no rare-class hiding is tuned against test metrics.
- Decisions are reported as 3-seed **mean ± std** with the per-seed table, weak classes included.

## 17. Next main-control decision

**Approve or reject preparing EXP03** — the config-only conservative `attack_loss_weight` sweep
({1.25, 1.35}, linear Head 2, `binary_loss_weight` = 1.0, one-seed validation screen → 3-seed confirm,
4–6 runs). No config or training has been created/run. The baseline stays the accepted final model until
a controlled experiment beats it on Head-2/rare **and** routing, beyond the noise band.
