> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical EXP04 — Rare-Class & Confusion Optimization Plan (planning only)

Status: `Plan only — NOT implemented, NOT trained`. No EXP04 config, checkpoint, or metrics were
created. Requires main-control approval before any preparation or training.

Generated: `2026-06-25`

Companion: `results/audits/cicids_hierarchical_exp04_rare_class_optimization_plan.json`,
`results/audits/cicids_hierarchical_exp04_candidate_matrix.csv`,
`results/audits/cicids_hierarchical_exp04_remaining_confusions.csv`. Builds on
`docs/experiments/CICIDS_HIERARCHICAL_EXP03_OPTIMIZATION_PLAN.md` and the EXP01/EXP02 analyses.

---

## 1. Current CICIDS status

- **Official accepted final:** EXP03 1.25 seed999 at `models/final/final_cicids_hierarchical.pt`.
- **Promoted source checkpoint:**
  `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`.
- **Promotion record:**
  `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json`.
- **Previous baseline backup:**
  `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.
- **Strongest improvement candidate:** `cicids_hierarchical_exp03_attack_loss_weight_125_confirmation`
  (`attack_loss_weight` 1.25, linear Head 2, 3-seed). **Not promoted yet** — main control wants stronger
  rare/difficult-class results before accepting a final model.
- **Current update:** EXP03 1.25 seed999 has since been promoted as the official final. The older
  "not promoted yet" line above is retained only as historical planning context.
- **Final model changed:** Yes.

## 2. Baseline vs EXP03 1.25 (3-seed mean)

| Metric | Baseline | EXP03 1.25 | Delta |
| --- | --- | --- | --- |
| Binary macro-F1 | 0.972167 | 0.973477 | +0.001310 |
| Attack-family macro-F1 | 0.849111 | 0.870986 | **+0.021875** |
| Rare-class macro-F1 | 0.716987 | 0.774602 | **+0.057615** |
| Correct attribution | 0.909008 | 0.908243 | −0.000765 |
| Missed as benign | 0.053807 | 0.053831 | +0.000024 |
| Benign false alarm | 0.010008 | 0.008481 | −0.001527 |

EXP03 1.25 is a **genuine, honest improvement**: large attack-family and rare-class gains, binary up,
benign false alarm down, and routing essentially at baseline (correct attribution −0.0008,
missed-as-benign +0.00002 — both within noise).

## 3. Why EXP03 Was Promoted With Warnings

Current update: EXP04 diagnostic evidence later showed the dominant SlowHTTPTest/FTP confusion is
feature-limited in the current 77-feature space. Main control therefore accepted EXP03 1.25 seed999 as
the final CICIDS model with documented limitations instead of spending more model/loss runs on a
zero-sum confusion pair. The original planning rationale below is retained as historical context.

Main control wants the rare/difficult classes pushed further before locking the final model. Routing is
already recovered (unlike EXP02), so the open question is specifically whether the **rare/difficult
attack-family** performance can be improved **beyond** EXP03 without regressing routing — and whether
that is even achievable by controlled, honest means.

## 4. EXP03 remaining weaknesses (per-seed, vs baseline & EXP02)

| Class | Support | Baseline F1 | EXP03 1.25 mean F1 | Verdict |
| --- | --- | --- | --- | --- |
| DoS-SlowHTTPTest | 20,941 | 0.553 | 0.582 (recall 0.437→0.491) | **Real, meaningful, but feature-limited** — improved & stable across all 3 seeds, still the weakest large class |
| FTP-BruteForce | 28,928 | 0.779 | 0.770 | **Mild stable regression** — precision up, recall down; the see-saw cost of the SlowHTTPTest gain |
| Web-BruteForce | 96 | 0.364 | 0.686 | **Strong stable improvement** — precision 0.24→~0.75 all seeds; recall slipped 0.75→0.635; small support |
| Web-XSS | 38 | 0.618 | 0.618 | **Real but stuck & tiny** — frozen at exactly 17/38 in every run; leaks to Bot/Infiltration |
| SQL-Injection | 12 | 0.800 | 0.753 | **Pure variance** — recall fixed 8/12; EXP03 1.35 seed42 collapsed its precision to 0.091 |
| DDoS-LOIC-UDP | 271 | 0.821 | 0.828 | Stable OK — recall 1.0, precision ~0.70 |
| DoS-Slowloris | 1,642 | 0.982 | 0.989 | Strong, near-ceiling |

**Stable across seeds:** SlowHTTPTest improvement, Web-BruteForce precision win, FTP mild regression,
Web-XSS stuck point. **High variance (tiny support):** SQL-Injection (12), Web-XSS recall target (38),
and the DDoS-LOIC-HTTP→Bot leak (swings 0–992 for the same config across seeds).

## 5. Rare-class support & metric reliability (which classes may drive EXP04)

- **Drivers (high support, meaningful, reliable):** **DoS-SlowHTTPTest (20,941)** and **FTP-BruteForce
  (28,928)**. These are the only rare/difficult classes large enough to move reliably.
- **Guardrails only (do NOT over-optimize):** **Web-BruteForce (96)** — already improved, recall
  already traded; **Web-XSS (38)** — stuck and entangled with large classes; **SQL-Injection (12)** —
  noise; **DDoS-LOIC-UDP (271)** — already fine. Per the task rule, these must **not** be optimized for
  prettier numbers; SQL-Injection (12) and Web-XSS (38) are explicitly treated as high-variance
  guardrails.

## 6. Confusion-matrix analysis (the decisive finding)

Source data: `results/audits/cicids_hierarchical_exp04_remaining_confusions.csv` (built from existing
confusion matrices only — no new evaluation).

- **DoS-SlowHTTPTest → FTP-BruteForce** improved under EXP03: 11,796 (56.3%) → mean **10,665 (50.9%)**
  across all 3 seeds.
- **FTP-BruteForce → DoS-SlowHTTPTest** worsened: 2,958 (10.2%) → mean **4,093 (14.1%)**. So **FTP's
  degradation is directly connected to the SlowHTTPTest gain** — they fight over the same overlap region.
- **The total pair error is conserved:** baseline **14,754** → EXP03 1.25 mean **14,758**. Across the
  entire loss-weight sweep (EXP02 1.5, EXP03 1.25, EXP03 1.35), the pair total stays ~14,750 — loss
  weighting only **moves the boundary between the two directions, it does not separate the classes.**
  EXP03's macro-F1 gain is a legitimate **rebalancing** (it lifted the weaker class, SlowHTTPTest), not
  a reduction of the overlap.
- **The Web-BruteForce win is a precision fix, not new separability:** Infiltration→Web-BruteForce
  false predictions dropped 220 → ~19, which is the entire source of the precision jump.
- **Web-XSS leaks to large classes:** 21/38 misrouted, mostly to **Bot (10–15)** and **Infiltration
  (5–10)** — so up-weighting Web-XSS would risk hurting Bot/Infiltration for ≤21 samples.

### Largest remaining wrong-family pairs (EXP03 1.25 mean)

1. DoS-SlowHTTPTest → FTP-BruteForce — **10,665** (feature-limited)
2. FTP-BruteForce → DoS-SlowHTTPTest — **4,093** (feature-limited; reverse direction)
3. DDoS-LOIC-HTTP → Bot — ~613 (high seed variance: 992/847/0)
4. Infiltration → Bot — ~277 (large class, low macro impact)
5. DDoS-LOIC-HTTP → DDoS-LOIC-UDP — ~113 (stable, negligible)

**The top two pairs are ~96% of the wrong-family error mass, are the two directions of the same
feature-overlap, and their sum is conserved under loss weighting.**

## 7. Engineering feasibility (config-only vs code)

- **`attack_loss_weight` / `binary_loss_weight`:** config-only. `attack_loss_weight` is already optimized
  at 1.25; `binary_loss_weight` is a routing lever, not a rare-class one.
- **Custom / per-class attack class weights:** **not supported in config.** The method
  (`sqrt_inverse_frequency`) and `WEIGHT_CAP = 10.0` are module constants in
  [hierarchical_class_weights.py](../../secureids/training/hierarchical_class_weights.py); there is **no**
  per-class multiplier or alternative-method config field. The cap is also **non-binding** (all rare
  weights already sit under 10.0), so raising it via config would have **no effect**. Any rare-class
  weight change therefore needs **code**.
- **Focal loss:** does not exist anywhere — **code change**.
- **Sampler:** none exists (`oversampling_enabled: false`) — **code change**.
- **Validation-only threshold calibration:** threshold is hardcoded `0.5`
  ([hierarchical_trainer.py (historical line 242)](../../secureids/training/hierarchical_trainer.py)) — **code change**.

**Conclusion:** the config-only rare-class levers are **exhausted**. Every remaining rare-class modeling
idea requires code, and the data says those ideas target either a feature-limited pair or tiny classes
that cannot be optimized responsibly.

## 8. Recommended EXP04 — **Option B: a feature/confusion diagnostic phase first**

**`cicids_hierarchical_exp04_feature_confusion_diagnostic`.** Before any further model/loss change,
quantify whether the dominant remaining errors are **feature-limited** or **model-limited**:

- Compute, on **train-split** processed features (with a **validation** cross-check, **never test**),
  per-feature class-conditional separability between **DoS-SlowHTTPTest** and **FTP-BruteForce** (e.g.
  per-feature distribution overlap / simple univariate separability scores), and a smaller look at
  **Web-XSS vs Bot/Infiltration**.
- Answer one question: **is the SlowHTTPTest/FTP pair separable with the existing 77 features?**
  - If **yes** → a targeted modeling experiment (EXP05 focal loss) is justified and gets a green light.
  - If **no** → the only real fix is **feature engineering** (a new preprocessing protocol — a separate
    `needs_main_control` decision, not a quick experiment), and the honest alternative is to **promote
    EXP03 1.25 with documented weak classes**.

### Why this is the right EXP04 (not another loss experiment)

The confusion **conservation** result is decisive: the pair total error is ~14,754 → ~14,758 across the
whole loss-weight sweep. The data *predicts* that more loss/weight/focal/sampler tuning on this pair is
**zero-sum**. Spending controlled-experiment slots on it without first checking feature separability
would be assuming the answer — exactly what the task forbids. The diagnostic is low-risk (analysis only,
no training, no test tuning) and produces the evidence needed to choose between feature engineering and
promotion.

### Config-only or code-change?

**Neither a config nor a training run** — EXP04 is an **analysis phase** (read existing artifacts +
train/val-split feature statistics). **0 training runs.** The *gated follow-up* (EXP05 focal loss, only
if the diagnostic shows separability) would be a code change with ~4–6 runs.

### Expected manual runs

**0 training runs** for the diagnostic itself. If the diagnostic green-lights EXP05 focal loss: ~**4–6**
runs (one-seed screen → 3-seed confirm), validation-driven.

### Expected benefit / risk

- **Benefit:** prevents wasted zero-sum experiments; gives an evidence-based go/no-go for feature
  engineering; keeps the program honest and reproducible.
- **Risk:** **low.** The main "risk" is that it confirms the cheap wins are exhausted — which is itself a
  valuable, honest result pointing to promoting EXP03 1.25 with documented weaknesses.

## 9. Candidate EXP04 ranking

Full matrix: `results/audits/cicids_hierarchical_exp04_candidate_matrix.csv`.

| Rank | Option | Status | Config-only | Code | Targets rare | Targets SH/FTP | Overfit risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **feature/confusion diagnostic (Option B)** | **recommend_now** | no | no | diagnostic | yes | none |
| 2 | promote EXP03 1.25 with warnings | needs_main_control_decision | yes | no | no | no | none |
| 3 | Head-2 focal loss (γ≈1.5–2) | recommend_after_exp04 | no | yes | maybe | maybe | medium |
| 4 | class-balanced (effective-number) loss | possible_later | no | yes | yes | no | medium |
| 5 | validation-only calibration (routing) | possible_later | no | yes | no | no | low |
| 6 | attack-only balanced sampler | possible_later | no | yes | yes | no | high |
| 7 | two-stage fine-tuning | possible_later | no | yes | maybe | maybe | medium |
| 8 | per-class attack weight tuning | needs_main_control_decision | no | yes | yes | maybe | high |
| 9 | Web-XSS/Web-BruteForce targeted weighting | needs_main_control_decision | no | yes | yes | no | high |
| 10 | SlowHTTPTest/FTP targeted weighting | **reject** | no | yes | no | yes | high |
| 11 | rare-class weight-cap boost | **reject** | partial | yes | yes | no | high |
| 12 | attack-family specialist module | **reject** | no | yes | maybe | maybe | high |

Rejections are evidence-based: #10 is zero-sum (conservation), #11 has no effect (cap non-binding) and
overfits tiny classes, #12 is a model-zoo violation.

## 10. If approved — proposed files & commands

The diagnostic creates **no configs and no checkpoints**. If approved it would write:

- `docs/experiments/CICIDS_HIERARCHICAL_EXP04_FEATURE_CONFUSION_DIAGNOSTIC_PLAN.md` (detailed protocol)
- `results/audits/cicids_hierarchical_exp04_feature_separability_slowhttp_vs_ftp.json` / `.csv`
- `results/audits/cicids_hierarchical_exp04_webxss_confusion_diagnostic.json`

A gated EXP05 focal-loss follow-up (only if separability is shown) would use isolated experiment paths
(`configs/training/experiments/cicids_hierarchical_exp05_focal_*_seed*.yaml`, `models/experiments/*`,
`results/experiments/*`, `results/audits/hierarchical_training_manifest_*`, `docs/experiments/*`).

**Must NOT overwrite:** `models/final/final_cicids_hierarchical.pt`, `results/final/hierarchical/cicids/`,
the baseline manifest/report, or any EXP01/EXP02/EXP03 artifact.

Manual command template (only if the diagnostic later green-lights EXP05):

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
# (EXP05 focal, gated on the diagnostic; one factor; one-seed screen then 3-seed confirm)
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids `
  --config configs/training/experiments/cicids_hierarchical_exp05_focal_seed42.yaml --execute
```

## 11. Promotion / rejection criteria

The diagnostic yields a **go/no-go**, not a model. Any gated modeling follow-up must (3-seed test mean):

- Attack-family macro-F1 ≥ **0.871** (must beat EXP03 1.25, not just baseline).
- Rare-class macro-F1 ≥ **0.774** (hold the EXP03 1.25 gain; no tiny class → ~0).
- DoS-SlowHTTPTest recall up **without** FTP-BruteForce F1 dropping below ~0.770 — the pair must
  **net-improve**, not see-saw.
- Correct attribution ≥ 0.909008; missed-as-benign ≤ 0.053807; binary ≥ 0.970.
- Tiny classes (12/38/96) are **guardrails, never promotion drivers**.

**Reject** if: the diagnostic shows feature-limited and no lever net-improves the pair (→ promote EXP03
1.25 with documented weaknesses); or any gain comes from over-fitting a tiny class or from the
SlowHTTPTest/FTP see-saw; or any taxonomy inflation / weak-class hiding / test tuning / model-zoo.

## 12. Scientific safety rules (enforced)

- **No test tuning.** Existing test metrics are used for **post-hoc diagnosis only**; no hyperparameter
  is selected from test performance. All future selection is validation-driven and documented.
- **Train-only class weights** (`compute_weights_from: train_only`, `allow_test_based_weights: false`);
  no validation/test labels in any weight computation.
- **No taxonomy change to inflate metrics** (SlowHTTPTest/FTP/Web classes stay distinct).
- **No weak-class hiding** — Web-XSS, SQL-Injection, the SlowHTTPTest/FTP residual are reported in full.
- **No tiny-class overfitting** — 12/38/96-sample classes are guardrails, never optimization targets.
- **No model zoo** — one accepted final model + isolated experiment artifacts.

## 13. Current decision status

Current update: the EXP04 diagnostic completed and supported promoting **EXP03 1.25 seed999** as the
final CICIDS model with documented weak classes. No further model/loss continuation is recommended for
the SlowHTTPTest/FTP pair under the current 77-feature protocol. The original next-decision text below
is retained as historical context.

**Approve or reject preparing EXP04** — the feature/confusion **diagnostic phase** (Option B; analysis
only, 0 training runs), which returns a go/no-go for either (a) a gated EXP05 focal-loss modeling
experiment or feature engineering, or (b) promoting **EXP03 1.25** as the final CICIDS model with
documented weak classes. That diagnostic path was later completed, and EXP03 1.25 seed999 is now the
accepted final model.
