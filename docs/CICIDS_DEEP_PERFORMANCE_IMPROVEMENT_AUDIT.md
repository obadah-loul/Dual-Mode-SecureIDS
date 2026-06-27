# CICIDS Deep Performance Improvement Audit

Generated on: `2026-06-25`

Current final-status update: this audit is historical planning context. EXP03 1.25 seed999 is now the
official CICIDS hierarchical final model at `models/final/final_cicids_hierarchical.pt`; the previous
baseline is backed up under
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

Final recommendation: `RUN_EXP01_AS_PREPARED`

## Purpose And Boundaries

This audit reviews the accepted CICIDS centralized hierarchical result and the
prepared EXP01 plan before EXP01 training is run. It is a planning and strategy
audit only.

This task did not run full CICIDS training, EXP01 training, preprocessing,
long evaluation, XAI, Streamlit, Git, checkpoint writes, result deletion, fake
metrics, or fake predictions. V1 was inspected only as read-only reference.

## Current Baseline Summary

Accepted baseline candidate:

- Checkpoint: `models/final/final_cicids_hierarchical.pt`
- Acceptance status: `ACCEPT_WITH_WARNINGS`
- Model: `SecureIDSHierarchicalAdvancedNet`
- Dataset/task: `cicids2018` / `hierarchical`
- Input dimension: `77`
- Attack-family Head 2 dimension: `14`

Accepted metrics:

| Metric | Value |
| --- | ---: |
| Binary Head 1 macro-F1 | `0.972167` |
| Binary accuracy | `0.977486` |
| Binary precision | `0.974214` |
| Binary recall | `0.946193` |
| Binary F1 | `0.960000` |
| Attack-family Head 2 macro-F1 | `0.849111` |
| Attack-family accuracy on attack rows | `0.961306` |
| Rare-class macro-F1 | `0.716987` |
| End-to-end attack detected and correctly attributed rate | `0.909008` |
| Attack missed as benign rate | `0.053807` |
| Benign false alarm rate | `0.010008` |

The result is already strong. The remaining improvement opportunity is not
mostly binary detection; it is attack-family attribution inside Head 2.

## Current EXP01 Summary

Prepared but not approved:

- Experiment ID: `cicids_hierarchical_exp01_head2_mlp_capacity`
- Idea: modest Head 2 MLP capacity increase
- Config: `configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml`
- Future checkpoint: `models/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.pt`
- Future results: `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/`
- Future report: `docs/experiments/CICIDS_HIERARCHICAL_EXP01_HEAD2_MLP_CAPACITY_REPORT.md`

EXP01 changes only:

- `model.attack_head_type: linear -> mlp`
- `model.attack_head_hidden_dim: 128`
- `model.attack_head_norm: true`
- `model.attack_head_dropout: 0.20`
- isolated experiment output paths

It preserves dataset, split, taxonomy, dimensions, shared encoder, binary head,
loss weights, train-only class weights, threshold `0.5`, validation-only
checkpoint selection, and final test once after best validation selection.

Current task context states EXP01 verification already passed with focused
lightweight tests; this audit did not rerun those tests.

## Files And Artifacts Inspected

Accepted result and metrics:

- `docs/CICIDS_HIERARCHICAL_RESULT_ACCEPTANCE.md`
- `results/audits/cicids_hierarchical_result_acceptance.json`
- `docs/CICIDS_IMPROVEMENT_OPPORTUNITY_AUDIT.md`
- `results/audits/cicids_improvement_opportunity_audit.json`
- `results/audits/cicids_improvement_candidates.csv`
- `docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md`
- `results/final/hierarchical/cicids/test_metrics.json`
- `results/final/hierarchical/cicids/training_history.csv`
- `results/final/hierarchical/cicids/attack_family_confusion_matrix.csv`
- `results/final/hierarchical/cicids/per_class_attack_metrics.csv`
- `results/final/hierarchical/cicids/rare_class_metrics.csv`
- `results/final/hierarchical/cicids/hierarchical_routing_summary.json`
- `results/audits/hierarchical_training_manifest_cicids2018.json`

Preprocessing and data metadata:

- `data/processed/cicids2018/hierarchical/feature_names.json`
- `data/processed/cicids2018/hierarchical/split_summary.json`
- `data/processed/cicids2018/hierarchical/attack_family_label_mapping.json`
- `data/processed/cicids2018/hierarchical/hierarchical_preprocessing_manifest.json`
- `results/audits/hierarchical_class_weight_strategy_cicids2018.json`

Config, code, tests, and reference material:

- `configs/training/cicids2018_hierarchical.yaml`
- `configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP01_PLAN.md`
- `results/audits/cicids_hierarchical_exp01_prep.json`
- `results/audits/cicids_hierarchical_exp01_selection.csv`
- `secureids/models/secureids_hierarchical_advanced_net.py`
- `secureids/training/hierarchical_config.py`
- `secureids/training/hierarchical_trainer.py`
- `secureids/training/hierarchical_evaluation.py`
- `secureids/training/hierarchical_class_weights.py`
- `secureids/cli.py`
- V1 read-only reference: `README.md`, `results/final_v6/FINAL_MODEL_SUMMARY.md`,
  `results/final_v6/validation_vs_test_gap_report.txt`, and selected V5/V6
  training/reporting scripts.

## Commands And Checks Run

Only lightweight inspection commands were used:

- `Get-Content` for JSON, CSV, YAML, and Markdown artifacts.
- `Select-String` for code/config feature checks.
- `rg` on V1 as read-only reference.
- No tests were rerun for this audit.
- No training, preprocessing, full array loading, long evaluation, XAI, or
  checkpoint-modifying command was run.

## CICIDS Preprocessing And Artifact Analysis

The processed CICIDS hierarchical feature set contains `77` features. The
features are flow-statistical, including protocol, packet counts, packet
lengths, flow bytes/rate, inter-arrival times, TCP flag counts, subflow
features, initial window bytes, active time, and idle time.

Feature relevance:

- DoS-SlowHTTPTest and FTP-BruteForce can plausibly depend on timing, packet
  rate, packet length, idle/active, and bidirectional flow statistics.
- Web-BruteForce, Web-XSS, and SQL-Injection may need application/content or
  service-specific signal that the current 77 flow features do not obviously
  expose.
- The current features include `Protocol`, but not obvious raw ports, HTTP
  methods, URI/content features, or FTP command semantics.

Split and class distribution:

- Train: `6,737,603` rows, `1,923,764` attack rows.
- Validation: `1,443,772` rows, `412,235` attack rows.
- Test: `1,443,773` rows, `412,236` attack rows.
- Attack-family labels are aligned with the binary mask. Benign rows use
  attack-family ignore index `-1`.

Weak-class support is the limiting reality:

- `Web-BruteForce`: train `428`, val `87`, test `96`.
- `Web-XSS`: train `157`, val `35`, test `38`.
- `SQL-Injection`: train `63`, val `12`, test `12`.
- `DoS-SlowHTTPTest`: train `98,130`, val `20,819`, test `20,941`.
- `FTP-BruteForce`: train `135,304`, val `29,128`, test `28,928`.

Conclusion:

- Preprocessing is valid and should not be changed before EXP01.
- Feature engineering could help later, especially for web/SQL classes, but it
  would create a new data protocol and requires explicit main-control approval.
- The random row-split / near-duplicate caveat must remain disclosed. V1/V6
  shows that grouped splits can reduce leakage but also lower headline scores.
  A grouped-split experiment is scientifically valuable, but it is not an
  immediate "improve current baseline" step.

## Training Config Analysis

Baseline training config:

- Batch size: `4096`
- Max epochs: `30`
- Optimizer: `adamw`
- Learning rate: `0.001`
- Weight decay: `0.0001`
- Early stopping metric: `val_hierarchical_score`
- Patience: `5`
- Scheduler: none found
- Threshold: trainer uses `0.5`
- Checkpoint selection: validation only
- Test: once after best validation checkpoint
- Loss weights: `binary_loss_weight=1.0`, `attack_loss_weight=1.0`

Training history:

- Best validation score at epoch `3`: `0.894858`.
- Epoch `8` nearly returned to the best score: `0.893624`.
- Training stopped after no new best score for the configured patience window.
- Validation Head 2 macro-F1 improved rapidly from `0.741289` to `0.817354`
  by epoch 3, then oscillated between roughly `0.733` and `0.815`.

Interpretation:

- This does not prove simple undertraining. It looks more like the existing
  optimization finds a good Head 1/Head 2 compromise quickly, then Head 2
  oscillates.
- A scheduler or longer patience could be useful later, but it is less targeted
  than changing Head 2 capacity.
- Changing training budget first risks spending a long CICIDS run on a weakly
  diagnostic variable.

## Model Architecture Analysis

The architecture is a shared residual/gated MLP encoder with:

- shared encoder widths `[256, 128, 128]`
- binary Head 1: single linear logit
- attack-family Head 2 baseline: linear classifier over the shared embedding
- optional Head 2 MLP branch already implemented

Current weakness:

- Head 1 is strong and should be protected.
- Head 2 is strong overall but not strong enough on a small group of hard or
  rare classes.
- The baseline linear Head 2 must separate 14 attack families from one shared
  representation that is also optimized for the binary task.

EXP01 realism:

- EXP01 adds a small non-linear Head 2 branch without changing the encoder or
  binary head.
- This directly targets family separation and is especially logical for the
  DoS-SlowHTTPTest vs FTP-BruteForce confusion pair.
- It may help rare web classes, but the very small train/validation/test support
  means those classes remain unstable even if the model improves.

Two-stage/specialist models:

- A two-stage attack-family specialist could be stronger for the hard
  SlowHTTPTest/FTP boundary and the tiny web/SQL classes.
- It is also a larger design change, needs new code/tests, and risks messy
  model-zoo behavior if introduced before the small Head 2 MLP experiment.
- It should be a later controlled experiment, not an EXP01 replacement.

## Loss And Imbalance Analysis

Current loss path:

- Binary BCE with train-only positive-class weight.
- Attack-family CrossEntropy on attack rows only.
- Masking ignores benign rows for Head 2.
- Attack class weights are train-only sqrt inverse frequency, mean-normalized,
  capped at `10.0`.

Important weight values:

- `DoS-SlowHTTPTest`: `0.140041`
- `FTP-BruteForce`: `0.119262`
- `Web-BruteForce`: `2.120485`
- `Web-XSS`: `3.501122`
- `SQL-Injection`: `5.526966`

Interpretation:

- Rare classes already receive extra weight without using validation/test
  labels.
- The high-support SlowHTTPTest/FTP pair receives low weights because it is not
  rare. Their issue is likely class overlap or decision boundary shape, not
  absence of sample count.
- Increasing global `attack_loss_weight` may help Head 2, but it changes the
  binary/attack optimization balance and is less precise than EXP01.
- Focal loss, label smoothing, class-balanced loss, and balanced samplers are
  plausible later candidates, but they need implementation and careful
  validation-only controls.

Conclusion:

- Loss/imbalance changes should not replace EXP01.
- They are good EXP02/EXP03 style candidates if EXP01 is weak or diagnostic.

## Evaluation And Metric Behavior Analysis

Head 1:

- Binary macro-F1 `0.972167` and benign false alarm rate `0.010008` are already
  excellent.
- Threshold/calibration changes are therefore not the main first lever.

Head 2:

- Attack-family macro-F1 `0.849111` is held down by a few classes.
- Accuracy on attack rows `0.961306` remains high because large easy classes
  are classified very well.

Confusion matrix diagnosis:

- DoS-SlowHTTPTest: `9,145 / 20,941` correct, `11,796` predicted as
  FTP-BruteForce.
- FTP-BruteForce: `25,970 / 28,928` correct, `2,958` predicted as
  DoS-SlowHTTPTest.
- Web-BruteForce: `72 / 96` correct, but low precision due to other classes
  predicted as Web-BruteForce.
- Web-XSS: `17 / 38` correct, with errors into Bot, Infiltration, and
  Web-BruteForce.
- SQL-Injection: `8 / 12` correct, with errors into Bot, Infiltration, and
  Web-BruteForce.

Main diagnosis:

- The main weakness is Head 2 family classification, not Head 1 detection.
- The largest high-support opportunity is the SlowHTTPTest/FTP boundary.
- Rare web/SQL metrics are too low-support to optimize aggressively as the
  sole first target.

## Engineering Quality Analysis

Strengths:

- Baseline outputs are preserved.
- EXP01 output paths are isolated under `models/experiments`,
  `results/experiments`, and `docs/experiments`.
- CLI gate and config loader now narrowly allow CICIDS experiment configs only
  under approved naming/path patterns.
- The trainer uses validation-only checkpoint selection and evaluates test once
  after selection.
- Class weights are train-only.

Risks and observations:

- The trainer threshold is effectively fixed at `0.5`; validation-only
  threshold/calibration would need a separate controlled design.
- No scheduler is currently configured.
- Focal loss, label smoothing, balanced samplers, and specialist modules are not
  current safe config-only switches.
- Adding multiple knobs at once would damage comparability.

Conclusion:

- EXP01 is clean and comparable.
- Replacing EXP01 with a stronger idea would require new code/config prep and
  main-control approval.

## V1/V6 Reference Analysis

Useful V1/V6 ideas:

- Strict grouped split to measure duplicate-leakage-resistant performance.
- Validation-only calibration.
- Guarded routing with explicit budgets.
- Specialist models for weak classes.
- Per-class confusion/error reporting.
- Frozen selection before one untouched test pass.

Unsafe or unsuitable to copy now:

- Full ensemble/model-zoo behavior.
- Test-based tuning or repeated test probing.
- Majority relabeling/cleaning if presented as the same benchmark.
- Weighted-F1 optimization that hides rare-class macro weaknesses.
- Routing/specialist complexity before the V2 baseline and first controlled
  neural experiment are evaluated.

V1/V6 implication for V2:

- A later specialist/routing experiment could be valuable, especially for
  SlowHTTPTest/FTP and web/SQL.
- It should be planned as a separate controlled experiment with validation-only
  tuning and strict output isolation, not used to replace EXP01 now.

## Candidate Ranking

| Rank | Candidate | Classification | Expected Benefit | Risk | Replace EXP01? |
| ---: | --- | --- | --- | --- | --- |
| 1 | EXP01 Head 2 MLP capacity | `recommend_now` | Direct Head 2 capacity, already supported, isolated | Small gain or rare-class overfit | No |
| 2 | Stronger Head 2 branch | `recommend_after_exp01` | More Head 2 separation if EXP01 underfits | More capacity risk, needs prep | No |
| 3 | Attack-family loss-weight adjustment | `recommend_after_exp01` | More pressure on Head 2 | May disrupt Head 1/tradeoffs | No |
| 4 | Head 2 focal loss | `possible_later` | Focuses hard examples such as SlowHTTPTest/FTP | Needs code and tuning | No |
| 5 | Attack-only balanced sampler | `possible_later` | Better exposure for rare/hard attack families | Overfit/leakage risk if careless | No |
| 6 | Class-weight tuning | `possible_later` | Train-only targeted weighting | Can destabilize class balance | No |
| 7 | Two-stage attack-family specialist | `possible_later` | Strong for hard pair/web classes | Model-zoo complexity | Not now |
| 8 | Validation-only calibration/routing | `possible_later` | Could improve operating behavior | Needs frozen validation design | No |
| 9 | Label smoothing | `possible_later` | May reduce overconfidence | Unclear benefit for main confusion pair | No |
| 10 | Feature engineering | `possible_later` | Could help web/SQL with service/app signals | New preprocessing protocol | No |
| 11 | Split strategy/grouped split | `possible_later` | Stronger scientific evidence | Likely lowers headline score | No |
| 12 | Random rerun until lucky | `reject` | None scientifically | Invalid story | No |
| 13 | Test-set threshold tuning | `reject` | Artificial score chasing | Leakage | No |
| 14 | Hide weak classes/change taxonomy | `reject` | Inflates appearance only | Misleading | No |

## Honest Performance Ceiling Discussion

The current baseline is already high. A single controlled run should not be
expected to turn every weak class into a perfect class.

Realistic expectations:

- EXP01 meaningful success: attack-family macro-F1 improves by `0.01` or more
  without hurting Head 1.
- A few controlled experiments could plausibly move Head 2 macro-F1 into the
  high `0.86-0.89` range if the SlowHTTPTest/FTP boundary improves.
- A `0.90+` Head 2 macro-F1 is possible only if both the high-support
  SlowHTTPTest/FTP boundary and rare web classes improve, which is not
  guaranteed.
- Strict grouped-split evaluation would probably reduce headline scores and is
  a scientific robustness step, not a score-inflation step.

The honest "wow" result should be a strong metric plus a clean protocol, not a
metric obtained by test tuning, taxonomy changes, or hiding weak classes.

## Main Risks

- EXP01 may produce only a small improvement because the baseline is already
  strong.
- Rare web/SQL support is too small for stable conclusions from one seed.
- SlowHTTPTest/FTP may need feature or specialist logic beyond a simple MLP
  branch.
- Larger changes can easily become a model zoo.
- Preprocessing or split changes would break comparability with the accepted
  baseline unless treated as a new protocol.

## Final Recommendation

Final recommendation: `RUN_EXP01_AS_PREPARED`.

EXP01 should not be replaced now. It is the best first controlled experiment
because it is already supported, isolated, narrowly targets the main Head 2
weakness, and preserves the excellent Head 1 behavior.

If EXP01 fails or produces only a diagnostic result, main control should choose
one next controlled direction from the roadmap: either stronger Head 2 branch,
attack-family loss/imbalance, focal/sampler logic, or a carefully designed
specialist experiment.

## Exact Next Decision Needed

Main control should approve or reject the manual EXP01 training run:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml --execute
```

Do not add `--overwrite`.
