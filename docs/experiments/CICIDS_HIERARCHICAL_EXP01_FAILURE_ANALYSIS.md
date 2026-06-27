# CICIDS Hierarchical EXP01 — Failure Analysis

Status: `Analysis only` (existing outputs). No training, evaluation, preprocessing, checkpoint
change, or file move was performed.

Generated: `2026-06-25`

Experiment: `cicids_hierarchical_exp01_head2_mlp_capacity`. Companion:
`results/audits/cicids_hierarchical_exp01_failure_analysis.json`.

---

## 0. One-paragraph summary

EXP01 added a non-linear MLP Head 2 (linear→`128→128→14`, GELU+LayerNorm+dropout) to raise
attack-family macro-F1. It did not, because **the CICIDS Head 2 bottleneck is not head capacity** —
it is (a) **one large feature-overlap confusion pair, DoS-SlowHTTPTest ↔ FTP-BruteForce**, which
accounts for ~96% of all wrong-family errors, and (b) **tiny-support rare classes** (SQL-Injection 12,
Web-XSS 38, Web-BruteForce 96) whose F1 is dominated by single-sample noise. The MLP could not touch
the overlap (the discriminative information is missing from the shared embedding, not from the head),
and it merely reshuffled the noisy rare classes. Separately, the selected EXP01 epoch produced a
**more conservative Head 1** (fewer false alarms, but more missed attacks), which slightly worsened
end-to-end attribution. Net: EXP01 is within noise of the baseline and is rejected.

## 1. Why did Head 2 MLP capacity fail to improve attack-family macro-F1?

- **The error mass is a feature-overlap pair, not a capacity shortfall.** Baseline attack-family
  confusion matrix: true `DoS-SlowHTTPTest` is predicted as `FTP-BruteForce` for **11,796 / 20,941
  (56%)** of its samples; conversely `FTP-BruteForce → DoS-SlowHTTPTest` is 2,958. These two flows
  (slow HTTP DoS vs FTP brute-force) overlap in the 77-feature flow space. Together they are
  ~14,750 of the ~15,329 total wrong-family errors (~96%).
- A bigger **head** can only re-draw boundaries within the **shared 128-d embedding**. If the shared
  encoder has already collapsed SlowHTTPTest and FTP into overlapping regions (it is optimized mostly
  for the easy binary task and the 10 near-ceiling classes), no amount of Head-2 non-linearity
  recovers information the embedding does not contain. EXP01 confirms this: `DoS-SlowHTTPTest` recall
  stayed 0.437→0.431 and `FTP-BruteForce` precision stayed 0.688→0.686 — **the pair did not move.**
- The 10 large classes were already at F1 ≥ 0.985 (ceiling), so the extra capacity had nothing to
  gain there either.

## 2. Why did binary macro-F1 improve while Head 2 worsened?

- Binary was already near ceiling (val_binary ≈ 0.972–0.975 across all epochs; range ~0.003). The
  selected EXP01 epoch (5) landed at a **more conservative Head 1 operating point**: precision
  0.9742→0.9846, recall 0.9462→0.9426, FP 10,324→6,066, FN 22,181→23,680. Fewer benign false alarms
  raised binary macro-F1, but more attacks slipped through as benign.
- This is a **shared-encoder side effect plus epoch selection**, not a designed change: adding Head-2
  MLP gradients perturbs the shared encoder, and the `0.5*binary + 0.5*attack` validation score then
  picked a different epoch whose blend happened to favor the (near-ceiling) binary term.

## 3. Did EXP01 become more conservative? Did fewer false alarms cost missed attacks?

**Yes to both.** Benign false-alarm rate fell 0.010008→0.005881 (good), but attack-missed-as-benign
rate rose 0.053807→0.057443 (+1,499 attacks) and end-to-end correct attribution fell
0.909008→0.906020. The end-to-end regression is **entirely a Head-1 effect**: among *detected*
attacks, wrong-family count actually fell (15,329→15,062). EXP01 traded attack recall for benign
precision — the opposite of what a Head-2 improvement should do.

## 4. Which classes improved / worsened?

- **Improved (noise):** Web-BruteForce 0.3636→0.4131 (96 samples). 
- **Worsened (noise):** SQL-Injection 0.80→0.72 (**12 samples**; a 1-sample swing; this single class
  causes most of the −0.0021 macro and −0.0074 rare-macro drops). DoS-Slowloris 0.9819→0.9781,
  DDoS-LOIC-UDP 0.8212→0.8187 (both ~unchanged).
- **Unchanged (the ones that matter):** DoS-SlowHTTPTest 0.5535→0.5498, FTP-BruteForce 0.7787→0.7788,
  Web-XSS 0.6182→0.6182. The 10 large classes stayed ≥0.985.

## 5. Did the MLP help Web-BruteForce but hurt SQL-Injection / rare macro-F1?

Yes — but both movements are **statistical noise at these supports** (96 and 12 samples). The MLP's
boundary reshuffle nudged a couple of tiny-class samples either way; it is not a real capability
change. Decisions must **not** be driven by classes with <100 test samples.

## 6. Is the issue capacity, loss pressure, imbalance, feature overlap, or selection?

Ranked by evidence:
1. **Feature/representation overlap (primary, confirmed):** DoS-SlowHTTPTest↔FTP-BruteForce share
   flow characteristics; the shared embedding does not separate them. ~96% of error mass.
2. **Rare-class variance (primary, confirmed):** SQL-Injection/Web-XSS/Web-BruteForce (12/38/96
   samples) make macro-F1 and rare-macro-F1 noisy by ±0.05–0.08; they are not reliably improvable or
   measurable single-seed.
3. **Loss balance / Head-1 conservatism (secondary, likely):** the shared encoder is binary-dominated;
   the `0.5/0.5` selection rewards near-ceiling binary, and EXP01 drifted conservative — costing
   attack recall. This is the one *training* lever not yet tested.
4. **Capacity (rejected by EXP01):** not the lever.
5. **Selection-metric mismatch (minor here):** both runs already selected the epoch that maximized
   `val_attack_family_macro_f1` (baseline epoch 3 = 0.8174 max; EXP01 epoch 5 = 0.8199 max), so a
   `0.3/0.7` re-weighting would **not** have changed the selected epoch. Selection-metric tuning is
   therefore low priority for CICIDS.

## 7. Did validation improve while test Head 2 worsened? (val/test gap)

- EXP01 `val_attack_family_macro_f1` 0.817354→0.819922 (**up**) but `test_attack_family_macro_f1`
  0.849111→0.846994 (**down**). A small **reverse val/test gap**: the MLP fit a little validation
  noise that did not transfer. Magnitude (~0.002–0.003) is within rare-class noise — i.e. EXP01 is
  effectively *indistinguishable* from baseline on Head 2 macro, not reliably worse.
- Both runs: test attack-macro > val attack-macro (no overfitting in the classic sense); the gap is
  rare-class-variance-dominated.

## 8. Architecture vs loss vs data vs rare-variance vs routing — verdict

| Hypothesis | Verdict | Basis |
| --- | --- | --- |
| Architecture (head capacity) | **Rejected** | EXP01 MLP changed nothing on the hard pair |
| Loss balance (attack vs binary) | **Untested, most promising training lever** | encoder binary-dominated; Head-1 drifted conservative |
| Data / feature overlap | **Confirmed primary** | SlowHTTPTest↔FTP 56% confusion |
| Rare-class variance | **Confirmed primary** | 12/38/96-sample classes dominate macro noise |
| Evaluation / routing | **Confirmed contributor** | end-to-end loss is a Head-1 miss effect, not Head-2 |

## 9. Baseline vs EXP01 — comparison details

- **Training history:** both plateau quickly; baseline best epoch 3, EXP01 best epoch 5; train_attack_loss
  trends similar. No overfitting signal beyond the small reverse val/test gap (§7).
- **Validation trajectory:** binary near-flat (~0.972–0.975); attack-family is the moving term
  (0.74→0.82); both runs select their max-val-attack epoch.
- **Binary confusion:** EXP01 more conservative (FP −4,258, FN +1,499).
- **Attack-family confusion:** the SlowHTTPTest↔FTP pair persists nearly identically.
- **Per-class / rare-class:** changes confined to <100-sample noise classes + the unchanged hard pair.
- **Routing:** end-to-end drop is a Head-1 miss effect.
- **Artifacts/wording:** EXP01 outputs correctly labeled CICIDS2018 (no UNSW/A8.8 leak); isolated paths.

## 10. Implications for the next experiment (EXP02)

1. **Stop adding Head-2 capacity.** Revert to the baseline linear Head 2.
2. **Target the reliable signal, not the noise.** The decision-relevant opportunity is the large,
   reliable confused pair (DoS-SlowHTTPTest recall, FTP-BruteForce precision). Treat rare-class
   macro-F1 as a **guardrail**, not the optimization target (too noisy at 12–96 samples).
3. **Test the loss-balance hypothesis next** (the one untested training lever): a moderate
   `attack_loss_weight` increase shifts the shared encoder toward attack-family discrimination and
   counters the Head-1 conservatism — a clean, config-only, single-factor controlled experiment.
4. **Use ≥3 seeds.** Single-seed deltas here are within noise; promotion must be on a multi-seed mean
   beyond the noise band.
5. If loss-balance does not move the SlowHTTPTest/FTP pair, escalate to **focal loss** (targeted hard
   examples) and only then to **feature engineering** (which changes the preprocessing protocol and is
   not a quick experiment). See `CICIDS_HIERARCHICAL_EXP02_PLAN.md`.

## 11. Safety confirmation

No training, preprocessing rebuild, long evaluation, XAI, Streamlit, checkpoint modification, file
delete/move/archive, Git, or faked metrics. V1 not modified. Existing-outputs analysis only.
