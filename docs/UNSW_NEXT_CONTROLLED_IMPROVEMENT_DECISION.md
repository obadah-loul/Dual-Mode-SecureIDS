# UNSW Next Controlled Improvement Decision

Task: select the next single controlled experiment after A9.6 review

Status: decision document only. No next experiment was implemented, no config was created, and no training was run.

## Current Decision

Keep A9 as the current accepted UNSW hierarchical baseline.

Treat A9.6 `head2_loss_weight` as a completed controlled experiment that failed to improve Head 2. A9.6 improved binary metrics, but reduced attack-family macro-F1 and rare-class macro-F1, and it increased attack false negatives beyond the safety gate.

## Why A9.6 Failed

A9.6 changed one intended factor: Head 2 loss pressure increased through `attack_loss_weight = 1.5` while binary loss stayed at 1.0.

The result does not support increasing Head 2 loss weight further:

- Attack-family macro-F1 changed by -0.014951.
- Rare-class macro-F1 changed by -0.023544.
- Attack false negatives changed by +283.
- `Analysis`, `Backdoor`, and `DoS` all declined.
- `Shellcode` F1 changed by -0.071488, with precision falling from 0.307937 to 0.236486.

The evidence says Head 2 needs a more targeted objective, not more global loss scaling.

## Recommended Next Experiment

Recommend exactly one next controlled experiment: `head2_focal_loss`.

Planned change if approved later:

- Keep binary loss unchanged.
- Set `attack_loss_weight` back to `1.0`.
- Replace Head 2 cross-entropy with focal loss for attack rows only.
- Start with `gamma = 1.5`.
- Keep train-only attack class weights.
- Keep the current class-weight cap unchanged for this experiment.
- Keep architecture, optimizer, learning rate, schedule, threshold, validation objective, and corrected UNSW protocol unchanged.
- Keep A9 and A9.6 output paths untouched.

## Why This Is The Best Next Single Change

`head2_focal_loss` targets hard attack-family examples and overlapping family boundaries directly. That fits the A9 vs A9.6 evidence better than increasing `attack_loss_weight`, because A9.6 proved that broad Head 2 pressure can improve binary behavior while still harming family attribution.

This is safer than random retraining because it keeps one controlled variable, uses the same baseline comparison, preserves A9, and requires separate future outputs.

A class-weight-cap experiment remains a credible later option, but it is not selected here because the current failure is broader than rare over-assignment alone: `Analysis`, `Backdoor`, and `DoS` also declined.

## Future Output Paths If Approved

Do not create these yet. If main-review/user approves the next experiment later, use separate paths such as:

- Config: `configs/training/unsw_nb15_hierarchical_a9_7_head2_focal_loss.yaml`
- Checkpoint: `models/final/final_unsw_hierarchical_a9_7_head2_focal_loss.pt`
- Result folder: `results/final/hierarchical/unsw_a9_7_head2_focal_loss/`
- Manifest: `results/audits/hierarchical_training_manifest_unsw_nb15_a9_7_head2_focal_loss.json`
- Report: `docs/HIERARCHICAL_TRAINING_REPORT_A9_7_HEAD2_FOCAL_LOSS.md`

## Success Criteria

A future `head2_focal_loss` run may replace A9 only if all gates pass:

- Attack-family macro-F1 must reach at least 0.535000.
- Attack-family accuracy must remain at least 0.760000.
- Binary macro-F1 must remain at least 0.884000.
- Binary F1 must remain at least 0.905000.
- Attack false negatives must remain <= 2,450.
- Benign false positives must remain <= 7,000.
- Rare-class macro-F1 must remain at least 0.385669.
- Shellcode F1 must remain at least 0.409909.
- Worms F1 must remain at least 0.281429.
- At least one of `Analysis`, `Backdoor`, or `DoS` must improve over A9 without rare-class collapse.

## Failure Criteria

- Any A9 safety gate fails.
- Attack-family macro-F1 fails to beat A9 by a meaningful margin or remains below 0.535000.
- Attack false negatives exceed 2,450.
- Rare-class macro-F1 drops below A9 baseline 0.385669.
- Shellcode F1 drops below 0.409909 or Shellcode precision collapses below 0.250000.
- Worms F1 drops below 0.281429 or Worms precision collapses below 0.180000.
- Analysis, Backdoor, and DoS remain stagnant while stronger classes absorb gains.
- Training is unstable, incomplete, or produces NaN metrics.
- Any A9 or A9.6 final artifacts are overwritten.

## Stop Condition

Stop here and wait for main-review/user approval. Do not implement the next experiment, do not create a next config, and do not train.
