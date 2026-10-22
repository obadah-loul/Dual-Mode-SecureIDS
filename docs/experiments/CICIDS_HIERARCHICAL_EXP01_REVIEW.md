> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical EXP01 — Result Review

Status: `Analysis only`. No training, evaluation, preprocessing, checkpoint change, or file
move/delete was performed. EXP01 was already run (by the user); this reviews its existing outputs.

Generated: `2026-06-25`

Current final-status update: EXP01 remains rejected/diagnostic. The official CICIDS hierarchical final
model is now EXP03 1.25 seed999 at `models/final/final_cicids_hierarchical.pt`; the previous baseline is
backed up under `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

Experiment: `cicids_hierarchical_exp01_head2_mlp_capacity` (idea: modest Head 2 MLP capacity increase).

Companion: `results/audits/cicids_hierarchical_exp01_review.json`,
`docs/experiments/CICIDS_HIERARCHICAL_EXP01_FAILURE_ANALYSIS.md`,
`docs/experiments/CICIDS_HIERARCHICAL_EXP02_PLAN.md`.

---

## 1. Output validation (methodology safety)

| Check | Result | Evidence |
| --- | --- | --- |
| EXP01 completed successfully | Yes | best_epoch 5 of 10 run; finite losses; full artifact set written |
| Outputs isolated from baseline | Yes | checkpoint `models/experiments/...exp01...pt`; results `results/experiments/...exp01.../`; report under `docs/experiments/`; manifest `..._exp01_...json` |
| Baseline overwritten | No | baseline `models/final/final_cicids_hierarchical.pt` and `results/final/hierarchical/cicids/` untouched; EXP01 config writes only experiment paths |
| Checkpoint selected by validation only | Yes | `checkpoint_selected_by: validation_only (0.5*bin + 0.5*attack)`, `select_by_test_metrics=false` |
| Test evaluated once after selection | Yes | `test_evaluated_once_after_best_validation_checkpoint=true` |
| Class weights train-only | Yes | `class_weights_train_only=true`, `validation_or_test_labels_used_for_weights=false` |
| UNSW/A8.8 text leak | None | protocol = "CICIDS2018 hierarchical benchmark protocol"; CICIDS-specific safety keys (H2 fix holds) |

EXP01 is a **methodologically clean, well-isolated controlled experiment**. It simply did not achieve
its objective.

## 2. Metrics table (baseline vs EXP01)

| Metric | Baseline | EXP01 | Δ (EXP01 − base) |
| --- | ---: | ---: | ---: |
| Binary macro-F1 | 0.972167 | 0.974419 | **+0.002252** |
| Binary precision | 0.974214 | 0.984628 | +0.010414 |
| Binary recall | 0.946193 | 0.942557 | −0.003636 |
| Binary FN (missed attacks) | 22,181 | 23,680 | +1,499 |
| Binary FP (benign flagged) | 10,324 | 6,066 | −4,258 |
| Benign false-alarm rate | 0.010008 | 0.005881 | −0.004127 |
| **Attack-family macro-F1** | **0.849111** | **0.846994** | **−0.002117** |
| Attack accuracy on attack rows | 0.961306 | 0.962228 | +0.000922 |
| **Rare-class macro-F1** | **0.716987** | **0.709622** | **−0.007365** |
| End-to-end correct attribution | 0.909008 | 0.906020 | −0.002988 |
| Attack-missed-as-benign rate | 0.053807 | 0.057443 | +0.003636 |
| Wrong-family rate | 0.037185 | 0.036537 | −0.000648 |
| best_epoch | 3 | 5 | — |
| val_hierarchical_score | 0.894858 | 0.897248 | +0.002390 |
| val_attack_family_macro_f1 | 0.817354 | 0.819922 | +0.002568 |

## 3. Weak-class movement (per-class F1, attack rows)

| Class | Support (test) | Baseline F1 | EXP01 F1 | Δ | Note |
| --- | ---: | ---: | ---: | ---: | --- |
| Web-BruteForce | 96 | 0.3636 | 0.4131 | +0.0495 | noisy small class; "improved" |
| SQL-Injection | **12** | 0.8000 | 0.7200 | **−0.0800** | 12 samples → 1-sample swing; pure noise |
| Web-XSS | 38 | 0.6182 | 0.6182 | 0.0000 | unchanged |
| DoS-SlowHTTPTest | 20,941 | 0.5535 | 0.5498 | −0.0037 | **the real hard class; basically unchanged** |
| FTP-BruteForce | 28,928 | 0.7787 | 0.7788 | +0.0000 | unchanged |
| DDoS-LOIC-UDP | 271 | 0.8212 | 0.8187 | −0.0025 | ~unchanged |
| DoS-Slowloris | 1,642 | 0.9819 | 0.9781 | −0.0038 | ~unchanged |
| (10 other classes) | large | ≥0.985 | ≥0.985 | ≈0 | already at ceiling |

The macro-F1 drop is **dominated by SQL-Injection (12 test samples)** — a single-sample swing — partly
offset by Web-BruteForce. The genuinely-hard, reliable class **DoS-SlowHTTPTest (support 20,941) did
not move**. The MLP did not touch the real bottleneck.

## 4. Promotion-criteria evaluation

EXP01's stated purpose was to **improve Head 2 attack-family performance**. Against that purpose:

| Criterion | Required | EXP01 | Pass? |
| --- | --- | --- | --- |
| Attack-family macro-F1 beats baseline beyond noise | > 0.849111 (+ margin) | 0.846994 (−0.0021) | ❌ |
| Rare-class macro-F1 not worse | ≥ 0.716987 | 0.709622 (−0.0074) | ❌ |
| End-to-end attribution not worse | ≥ 0.909008 | 0.906020 (−0.0030) | ❌ |
| Missed-attack rate not worse | ≤ 0.053807 | 0.057443 (+0.0036) | ❌ |
| Binary not degraded | ≥ ~0.965 | 0.974419 | ✅ (improved) |
| Benign false alarms not worse | ≤ 0.010008 | 0.005881 | ✅ (improved) |

EXP01 **improved the binary side (which was already near ceiling) and reduced benign false alarms, but
failed its primary purpose**: Head 2 macro-F1, rare-class macro-F1, end-to-end attribution, and
missed-attack rate all moved the wrong way (all within single-seed noise, but none in the intended
direction).

## 5. Final classification

**`REJECT_AS_IMPROVEMENT`** — keep as **`DIAGNOSTIC_EXPERIMENT_EVIDENCE`**.

- Do **not** promote the EXP01 checkpoint.
- **Current status:** `models/final/final_cicids_hierarchical.pt` now points to the promoted EXP03 1.25
  seed999 final model; this EXP01 review remains diagnostic history.
- EXP01 is retained as evidence that **Head 2 capacity is not the lever** for CICIDS attack-family
  performance (see the failure analysis).

Important honesty note: the baseline↔EXP01 deltas (~±0.002–0.007 macro) are **single-seed and within
the run-to-run noise band** of these metrics (the rare classes alone swing F1 by ±0.05–0.08 from one
sample). EXP01 should be read as *"did not beat baseline and did not move the real bottleneck,"* not
as a precise quantification of harm.

## 6. Next step

Proceed to the failure analysis (`CICIDS_HIERARCHICAL_EXP01_FAILURE_ANALYSIS.md`) and the EXP02 plan
(`CICIDS_HIERARCHICAL_EXP02_PLAN.md`). The baseline stays accepted until a controlled experiment
beats it on the **reliable** attack-family signal beyond the noise band.
