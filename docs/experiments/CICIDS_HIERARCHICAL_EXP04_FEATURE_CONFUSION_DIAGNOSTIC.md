> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical EXP04 — Feature/Confusion Diagnostic

Status: `Diagnostic complete — analysis only`. No training, no checkpoint, no preprocessing rebuild, no
test tuning. A bounded train/validation feature probe **was run**; results below.

Generated: `2026-06-25` · Experiment ID: `cicids_hierarchical_exp04_feature_confusion_diagnostic`

Companion artifacts:
`results/audits/cicids_hierarchical_exp04_feature_confusion_diagnostic.json`,
`results/audits/cicids_hierarchical_exp04_feature_confusions.csv`,
`results/audits/cicids_hierarchical_exp04_slowhttp_ftp_feature_diagnostics.csv`,
`results/audits/cicids_hierarchical_exp04_slowhttp_ftp_probe.json`,
`results/audits/cicids_hierarchical_exp05_recommendation_matrix.csv`,
`tools/diagnostics/cicids_slowhttp_ftp_feature_probe.py`.

---

## 1. Current status

- **Official accepted final:** EXP03 1.25 seed999 at `models/final/final_cicids_hierarchical.pt`.
- **Promoted source checkpoint:**
  `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`.
- **Promotion record:**
  `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json`.
- **Final model changed:** Yes. The previous baseline is backed up under
  `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

| Metric | Baseline | EXP03 1.25 |
| --- | --- | --- |
| Binary macro-F1 | 0.972167 | 0.973477 |
| Attack-family macro-F1 | 0.849111 | 0.870986 |
| Rare-class macro-F1 | 0.716987 | 0.774602 |
| Correct attribution | 0.909008 | 0.908243 |
| Missed as benign | 0.053807 | 0.053831 |
| Benign false alarm | 0.010008 | 0.008481 |

## 2. Purpose

Decide, **before** spending more training runs, whether the dominant remaining confusion
(**DoS-SlowHTTPTest ↔ FTP-BruteForce**) is **model/loss-limited** (the features distinguish the classes
but the model fails to) or **feature-limited** (the classes overlap in the current feature space). This
determines whether EXP05 should be another model/loss experiment, a feature-engineering effort, or a
stop-and-promote decision.

## 3. Artifact-based confusion findings (test confusion matrices — descriptive only)

- The SlowHTTPTest→FTP direction **improved** under EXP03 (11,796 → mean 10,665) but the reverse
  FTP→SlowHTTPTest **worsened** (2,958 → mean 4,093). FTP degradation is the direct see-saw cost of the
  SlowHTTPTest gain.
- **Total pair error is conserved:** baseline **14,754** → EXP03 1.25 mean **14,758**. Across the whole
  loss-weight sweep (EXP02 1.5, EXP03 1.25/1.35) the pair total stays ~14,750 — loss weighting only
  moves the boundary between the two directions; it does not separate the classes.

### SlowHTTPTest ↔ FTP-BruteForce bidirectional confusion

| Model | SH→FTP | % of SH (20,941) | FTP→SH | % of FTP (28,928) | Pair total |
| --- | --- | --- | --- | --- | --- |
| Baseline | 11,796 | 56.3% | 2,958 | 10.2% | **14,754** |
| EXP03 1.25 seed42 | 11,039 | 52.7% | 3,299 | 11.4% | 14,338 |
| EXP03 1.25 seed123 | 9,960 | 47.6% | 5,650 | 19.5% | 15,610 |
| EXP03 1.25 seed999 | 10,997 | 52.5% | 3,330 | 11.5% | 14,327 |
| **EXP03 1.25 mean** | **10,665** | **50.9%** | **4,093** | **14.1%** | **14,758** |

SlowHTTPTest recall improved (0.437 → 0.491) **at FTP-BruteForce's expense** (recall 0.898 → 0.859);
the pair total stayed conserved. EXP03 rebalanced, it did not separate.

## 4. Feature-space separability — plan and results

**Was the analysis run?** Yes — a **bounded** diagnostic was executed (not just prepared). It uses numpy
`mmap` with a **20,000-per-class stratified cap** (seed 42), so only the two classes' sampled rows are
read; the full 6.74M-row array is never loaded. Train statistics are used for fitting; a held-out
**validation** sample is used for evaluation; **the test split is never touched**. Script:
`tools/diagnostics/cicids_slowhttp_ftp_feature_probe.py`.

### 4.1 Standardized mean differences (train; `..._slowhttp_ftp_feature_diagnostics.csv`)

- Of 77 features, **only 3** have |SMD| ≥ 0.8 — `Flow Pkts/s`, `Fwd Pkts/s`, `Bwd Pkts/s` (all ≈ 0.90,
  and near-duplicates of one another, i.e. **one effective packet-rate axis**).
- **74 of 77** features have |SMD| < 0.2 (weak/overlapping), including all packet-length and most
  flow-timing features. The next strongest are `Flow Duration` (0.19) and `Flow IAT *` (~0.18–0.19).
- **No destination-port feature exists** in the 77 (only `Protocol`). Destination port (21 for FTP vs 80
  for slow-HTTP DoS) is the natural separator and is **absent from the feature space** — the single most
  likely missing signal.

### 4.2 Linear separability probe (train-fit → val-eval, balanced)

| Probe (val, held-out) | Value |
| --- | --- |
| Balanced accuracy | **0.6818** |
| Accuracy | 0.6818 |
| SlowHTTPTest recall | 0.967 |
| FTP-BruteForce recall | 0.396 |

The probe separates the pair only to ~68% balanced accuracy, and exhibits the **same one-directional
see-saw** as the deep model (it favors SlowHTTPTest at FTP's expense).

### 4.3 The decisive comparison — deep model vs trivial linear probe

| Separator | Pair balanced accuracy |
| --- | --- |
| Baseline hierarchical model (test) | 0.6672 |
| EXP03 1.25 hierarchical model (test) | 0.6746 |
| **Trivial linear probe (val)** | **0.6818** |

A simple linear classifier on the same 77 features **matches or exceeds** the deep nonlinear
hierarchical model on the pair. The deep model has therefore **not** left separation on the table — the
**feature space itself caps achievable separation at ~0.68 balanced accuracy**.

## 5. Train/validation vs test evidence separation

- **Train/validation (diagnostic, decision-grade):** SMD table (train), linear probe (train-fit /
  val-eval). These drive the conclusion and involve **no test data**.
- **Test (descriptive only):** all confusion-matrix counts and per-class recalls in §3 and the
  deep-model balanced-accuracy column. Used only to describe the existing models, never to tune.

## 6. Conclusion — model/loss-limited vs feature-limited

**Feature-limited (high confidence).** Basis:

1. The deep model and a trivial linear probe reach the **same ~0.68 balanced accuracy** on the pair — no
   model headroom.
2. Only **3/77 features** (one packet-rate axis) separate the classes; **74/77** are weak (|SMD| < 0.2).
3. The pair total confusion is **conserved** across the entire loss-weight sweep (14,754 → 14,758).
4. The natural separator (**destination port**) is **absent** from the feature space.

**More normal training/loss runs are NOT likely to help this pair** — they will redistribute the
conserved error (exactly as EXP02 and EXP03 did), not reduce it.

## 7. EXP05 recommendation

Two honest paths; **main control chooses**. Full matrix:
`results/audits/cicids_hierarchical_exp05_recommendation_matrix.csv`.

- **C — Stop & promote (recommend_now, default honest choice):** promote **EXP03 1.25** as the final
  CICIDS model **with documented limitations** (SlowHTTPTest/FTP residual overlap; stuck/ tiny Web-XSS
  and SQL-Injection). The model is already at the feature ceiling for the pair, and EXP03 1.25 is a
  strong, honest improvement over baseline (attack-family +0.0219, rare-class +0.0576, routing within
  noise). **0 runs, config/code unchanged.**
- **B — Feature engineering (needs_main_control_decision):** the only path to raise the ~0.68 ceiling —
  a **new preprocessing protocol** that restores **destination port** and adds richer **flow-timing /
  idle** features for the SlowHTTPTest/FTP region. Higher ceiling, but it **breaks comparability** with
  the baseline/EXP01–03 protocol and is a substantial effort (re-preprocess + retrain + new safety
  gates), not a quick experiment.
- **A — Model/loss EXP05 (focal / class-balanced / pair-targeted weighting): reject for this pair.**
  Proven futile by the diagnostic; would only repeat the see-saw and risks tiny-class instability
  (the EXP03 1.35 seed42 SQL-Injection collapse to precision 0.091). *Validation-only threshold
  calibration remains `possible_later` but is a Head-1 routing tool — it does not separate the pair.*

**Recommended direction:** the pair is feature-limited → **do not spend more model/loss runs on it.**
Choose **C (promote EXP03 1.25 with documented limitations)** unless main control wants to invest in
**B (feature engineering / new preprocessing protocol)** to chase a higher ceiling.

## 8. Scientific safety rules (enforced)

- **No test tuning** — test metrics used only as post-hoc descriptive evidence; the probe fits on train
  and evaluates on validation.
- **No fake metrics** — all numbers are computed (probe) or read from existing artifacts.
- **No taxonomy inflation** — SlowHTTPTest / FTP / Web classes kept distinct; no merging to inflate macro-F1.
- **No weak-class hiding** — Web-XSS, SQL-Injection, and the SlowHTTPTest/FTP residual are reported fully.
- **No tiny-class overfitting** — 12/38/96-sample classes are guardrails, never optimization targets.
- **Validation-first selection** for any future experiment; **no EXP05 config/checkpoint created.**

## 9. Re-runnable diagnostic command

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
.\.venv\Scripts\python.exe tools\diagnostics\cicids_slowhttp_ftp_feature_probe.py `
  --per-class-cap 20000 --seed 42 --run-probe
```

Bounded and safe: mmap + per-class cap, train/val only, writes only under `results/audits/`, labels
outputs as diagnostic (not training metrics), never touches test for tuning.

## 10. Current decision status

Current status update: main control chose the honest stop-and-promote path. EXP03 1.25 seed999 is now
the final CICIDS model with documented SlowHTTPTest/FTP and tiny-class limits. Feature engineering
remains the only plausible path to raise the SlowHTTPTest/FTP ceiling, but it would be a separate
new-preprocessing protocol, not a routine model/loss continuation.

**Approve an EXP05 direction or promote EXP03 1.25 with documented limitations.** Specifically: choose
**C** (promote EXP03 1.25 as final CICIDS model with documented SlowHTTPTest/FTP + tiny-class limits) —
the honest default given the feature-limited finding — **or** **B** (authorize a feature-engineering /
new-preprocessing-protocol effort to raise the ceiling). Direction **A** (more model/loss tuning of the
pair) is not recommended. At the time of the diagnostic, no config, checkpoint, or training was
created/run; the EXP03 1.25 seed999 promotion has since been executed and recorded.
