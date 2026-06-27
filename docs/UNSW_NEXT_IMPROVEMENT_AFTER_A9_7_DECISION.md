# UNSW Next Improvement After A9.7 Decision

Task: official next-step decision after A9.7 review

Status: decision document only. No experiment was implemented, no config was created, and no training was run.

## Current Best

A9 remains the accepted UNSW hierarchical baseline.

A9.6 and A9.7 are completed controlled experiments that should not replace A9. A9.6 tested stronger global Head 2 loss pressure and failed. A9.7 tested stronger Head 2 branch capacity and failed the single-run replacement gates.

## Why A9.7 Likely Failed

A9.7 added capacity, not loss pressure. That was a reasonable controlled change, but the result shows that capacity alone did not solve the corrected UNSW attack-family problem.

The likely blockers are:

- UNSW attack-family overlap dominates simple architecture capacity.
- `Analysis`, `Backdoor`, `DoS`, and `Exploits` remain hard to separate from the available features.
- The best validation score was lower than A9, so A9.7 did not select a stronger validation model.
- A9.7 reached best epoch 17 and stopped at 23 epochs, consistent with plateau/no further improvement.
- Head 2 branch capacity did not repair rare precision/recall balance; rare-class macro-F1 fell below A9.
- Single-run A9.7 showed mixed signals, so it should not be promoted, but it should also not be treated as a final multi-seed architecture verdict.

## Recommended Professional Direction

Recommended next direction: `formal_multi_seed_a9_vs_a9_7_branch_capacity_comparison_before_any_new_strategy`.

This is not approval to train. It is the decision to ask main-review whether a formal multi-seed comparison should be planned before any new strategy is chosen. The comparison should evaluate whether the small A9.7 improvements in DoS, Backdoor, wrong-family routing, and attack-family accuracy are stable signal or single-run noise.

## What Not To Do Now

- Do not start CICIDS.
- Do not run another training experiment.
- Do not create a new experiment config.
- Do not tune on the test set.
- Do not switch automatically to focal loss.
- Do not change class weights, features, preprocessing, selection objective, or fine-tuning until main-review approves a specific next task.

## Decision

Keep A9. Treat A9.6 and A9.7 as failed controlled experiments. Stop and wait for main-review approval.
