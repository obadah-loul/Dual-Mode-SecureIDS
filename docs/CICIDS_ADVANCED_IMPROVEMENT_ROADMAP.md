# CICIDS Advanced Improvement Roadmap

Generated on: `2026-06-25`

Current final-status update: this roadmap is historical planning context. EXP03 1.25 seed999 is now the
official CICIDS hierarchical final model at `models/final/final_cicids_hierarchical.pt`; the previous
baseline is backed up under
`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`.

Recommended immediate path: `RUN_EXP01_AS_PREPARED`

## 1. Should We Run EXP01 As Prepared?

Yes. EXP01 should run as prepared after main-control approval.

Reason:

- It targets the main weakness: Head 2 attack-family classification.
- It does not disturb the excellent binary Head 1.
- It is already supported by the current model/trainer path.
- It is isolated under experiment paths and does not overwrite the accepted
  baseline.
- It keeps the comparison clean: one architecture variable changes.

## 2. Should EXP01 Be Replaced By A Stronger Experiment?

No, not yet.

There are stronger-looking ideas, but they are not better first experiments
because they require new code or carry higher risk:

- focal loss
- attack-only balanced sampler
- specialist attack-family module
- validation-only routing/calibration
- feature engineering
- grouped split redesign

Those may be useful later. Replacing EXP01 now would convert a clean prepared
experiment into another prep cycle without evidence that the simple Head 2 MLP
is insufficient.

## 3. Best First Experiment For Maximum Honest CICIDS Improvement

Best first experiment: `cicids_hierarchical_exp01_head2_mlp_capacity`.

It is not the most aggressive possible idea, but it is the best first honest
move: it targets Head 2, preserves Head 1, keeps the baseline comparable, and
does not introduce sampler/loss/specialist complexity before the simplest
capacity question is answered.

## 4. Recommended Immediate Path

1. Approve and run EXP01 manually.
2. Compare EXP01 against the accepted baseline:
   `models/final/final_cicids_hierarchical.pt`.
3. Promote only if Head 2 improves meaningfully and Head 1 remains safe.
4. If EXP01 fails, keep it as diagnostic and move to one next controlled
   experiment.

## 5. Aggressive Path: Up To 10 Controlled Improvement Runs

Each experiment must change one main factor, use validation-only selection, keep
test evaluation once-after-selection, and write isolated outputs.

| Order | Experiment | Main Change | Promotion Criteria | Rejection Criteria |
| ---: | --- | --- | --- | --- |
| 1 | `cicids_hierarchical_exp01_head2_mlp_capacity` | Prepared Head 2 MLP branch | Head 2 macro-F1 > `0.849111` by preferably `>=0.01`; Head 1 macro-F1 >= `0.965`; no routing regression | No meaningful Head 2 gain, Head 1 drop, rare-class collapse, or path/leakage issue |
| 2 | `cicids_hierarchical_exp02_stronger_head2_branch` | Slightly stronger Head 2 only, such as wider/deeper attack branch | Improves over best of baseline/EXP01 without Head 1 harm | Overfit, unstable rare classes, or no gain |
| 3 | `cicids_hierarchical_exp03_attack_loss_weight_1_2` | Conservative Head 2 loss pressure, one value only | Head 2 gain without binary macro-F1 or false-alarm degradation | Head 1 or routing worsens materially |
| 4 | `cicids_hierarchical_exp04_head2_focal_loss` | Attack-family focal loss on attack rows only | Improves hard classes, especially SlowHTTPTest/FTP, without rare-class collapse | Over-focuses rare classes or hurts easy classes/Head 1 |
| 5 | `cicids_hierarchical_exp05_attack_only_balanced_sampler` | Train-only attack-family sampler | Rare/hard Head 2 classes improve with stable Head 1 | Overfit rare classes, leakage risk, or unstable validation |
| 6 | `cicids_hierarchical_exp06_class_weight_tuning` | Train-only class-weight variant | SlowHTTPTest/FTP or rare macro-F1 improves without broad losses | Weighting destabilizes majority classes |
| 7 | `cicids_hierarchical_exp07_slowhttp_ftp_specialist` | Controlled pair specialist for SlowHTTPTest/FTP | Corrects the dominant confusion pair and improves macro-F1 | Model-zoo complexity or degraded routing |
| 8 | `cicids_hierarchical_exp08_web_sql_specialist` | Validation-only specialist/routing for Web/SQL rare classes | Improves Web-BruteForce/Web-XSS/SQL without false alarms | Unstable tiny support or routing overfit |
| 9 | `cicids_hierarchical_exp09_validation_calibration` | Validation-only calibration/operating-point study | Improves routing/false-alarm tradeoff without test tuning | Test leakage or no Head 2 benefit |
| 10 | `cicids_hierarchical_exp10_multiseed_confirmation` | Multi-seed confirmation of best candidate | Mean improvement holds across seeds | Single-run gain disappears |

The sequence is conditional. Do not run all ten automatically.

## 6. Conservative Path If Timeline Matters

1. Run EXP01.
2. If EXP01 clearly improves, promote it or confirm with more seeds.
3. If EXP01 fails, stop CICIDS improvement and accept the baseline or EXP01
   diagnostic result.
4. Move to UNSW improvement or federated/security only after user approval.

## 7. What Must Stay Constant For Comparability

Keep constant unless the experiment explicitly changes one item:

- dataset: `cicids2018`
- split and processed artifacts
- feature dimension: `77`
- taxonomy and Head 2 dimension: `14`
- binary/attack label mapping
- validation-only checkpoint selection
- final test once after validation selection
- train-only class weights
- threshold `0.5` unless doing a validation-only calibration experiment
- no test tuning
- baseline checkpoint and result folder preserved
- output isolation under experiment paths
- no hidden failed experiments

## 8. What Must Not Be Done

Do not:

- tune thresholds on the test set
- run random reruns until lucky
- hide weak classes
- change taxonomy to inflate metrics
- use validation/test labels for class weights or samplers
- overwrite the accepted baseline checkpoint
- merge multiple new tricks into one uncontrolled run
- copy V1 model-zoo behavior into V2 without a controlled design
- present grouped-split or cleaned-data results as directly comparable to the
  current row-split baseline

## 9. When To Stop Improving CICIDS

Stop the CICIDS improvement cycle when one of these is true:

- EXP01 or a later candidate improves Head 2 macro-F1 by at least `0.01`
  absolute while preserving Head 1 and routing safety.
- Three consecutive controlled experiments fail to improve meaningfully.
- The only remaining ideas require test tuning, taxonomy changes, or hidden
  weak classes.
- Project timeline requires moving to UNSW or federated/security.
- The user personally accepts the current CICIDS result.

## 10. Exact Next Main-Control Decision

Decision needed:

`APPROVE_EXP01_TRAINING_AS_PREPARED` or `PAUSE_AND_PREPARE_A_DIFFERENT_EXP01`.

Recommended decision:

`APPROVE_EXP01_TRAINING_AS_PREPARED`

Manual command:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml --execute
```

Do not include `--overwrite`.
