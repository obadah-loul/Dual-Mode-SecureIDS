# UNSW A9.9 Next Experiment Decision

Status: `design_ready_for_main_review`

## Recommendation

The next controlled UNSW experiment should be an attack-family specialist.

Recommended experiment name: `A9.9 attack-family specialist router`

The experiment should keep A9 Head 1 as the accepted binary detector and train a separate specialist classifier only on UNSW training attack rows. Evaluation should report both routed end-to-end metrics and oracle attack-row specialist metrics.

## Why This Should Be Next

A9.6 showed that simple attack-loss scaling is not enough. A9.7 and A9.8 showed that simple Head 2 branch capacity is not enough. The next experiment should therefore change the problem decomposition instead of making another small loss or branch-size tweak.

The specialist strategy directly matches the final project story: a hierarchical IDS first detects attack traffic, then routes detected attacks into an attack-family specialist.

## Why Not Focal Loss Next

Focal loss alone keeps the same mixed training problem and may overemphasize noisy or very rare examples. It can be useful later, but by itself it is less likely to solve the attack-family boundary problem exposed by A9.6 through A9.8.

## Why Not More Head 2 Branch Capacity

A9.8 already showed that simple MLP branch capacity produces only a small attack-family macro-F1 mean gain of `+0.004524`. More branch capacity risks repeating the same limited improvement pattern.

## Realistic Target

Attack-family macro-F1 above `0.9` is not realistic for this corrected UNSW setup.

A realistic short-term target is attack-family macro-F1 around `0.52-0.58`. A strong but still realistic result is around `0.60` if the specialist and train-only attack-row sampling work well. Rare-class macro-F1 should be protected or modestly improved. Binary macro-F1 should remain close to A9 because A9 Head 1 is unchanged.

## Exact A9.9-Prep Task

Prepare, but do not run, an attack-family specialist experiment:

1. Keep A9 as the accepted binary router.
2. Prepare a separate attack-only classifier trained only on UNSW training attack rows.
3. Use validation attack rows only for selection and optional calibration.
4. Use no validation/test labels for class weights or sampling.
5. Prepare routed evaluation through A9 Head 1.
6. Prepare oracle attack-row evaluation for diagnosis.
7. Compare fairly against A9 Head 2.
8. Predefine promotion criteria and safety checks before training.
9. Stop before any training or final metric creation.

## Risks To Accept Or Reject

- Overfitting risk from smaller attack-only data.
- Class-prior and calibration risk if class-balanced sampling is overused.
- End-to-end routed results remain limited by A9 Head 1 false negatives.
- Additional reporting complexity because routed and oracle metrics must not be mixed.
- Extra model artifact complexity if the specialist is later trained.

## Main-Review Decision

Main-review should approve or reject A9.9-prep for the attack-family specialist strategy. No implementation or training should begin from this design task alone.
