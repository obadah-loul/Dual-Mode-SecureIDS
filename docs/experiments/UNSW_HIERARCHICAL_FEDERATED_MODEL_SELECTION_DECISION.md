# UNSW Hierarchical Federated Model Selection Decision

## Status

The current selected UNSW clean federated hierarchical model is the old clean
hierarchical FedAvg baseline. Newer rounds=40 experimental runs are retained as
evidence, but they are not promoted automatically.

## Selected Current Model

Checkpoint:

`models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt`

Result folder:

`results/experiments/federated_security/unsw_hierarchical_clean_fedavg/`

This checkpoint is the current UNSW clean federated hierarchical model for final
reporting and demo use unless a later approved decision changes the selection.

## Selected Metrics

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | 0.882305 |
| Attack-family macro-F1 | 0.475889 |
| Rare-class macro-F1 | 0.307115 |
| Missed-as-benign rate | 0.062097 |
| Best round | 16 |

The selected baseline is preferred because it preserves the safer missed-attack
profile among the available UNSW clean hierarchical federated candidates.

## Non-Promoted Experimental Runs

### Normal Rounds=40 Clean FedAvg Run

Checkpoint:

`models/experiments/federated_hierarchical_v2/unsw_improved_rounds40_clean_fedavg.pt`

Result folder:

`results/experiments/federated_hierarchical_v2/unsw_improved_rounds40_clean_fedavg/`

Known metrics:

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | 0.904613 |
| Attack-family macro-F1 | 0.490750 |
| Rare-class macro-F1 | 0.341730 |
| Missed-as-benign rate | 0.076855 |
| False negatives | 3484 |
| Best round | 38 |

Reason not promoted:

This run improved binary macro-F1, attack-family macro-F1, and rare-class
macro-F1, but it increased missed attacks and the missed-as-benign rate. It is
kept as partial improvement evidence only.

### Safety-Gated Rounds=40 Clean FedAvg Run

Checkpoint:

`models/experiments/federated_hierarchical_v2/unsw_safety_gated_rounds40_clean_fedavg.pt`

Result folder:

`results/experiments/federated_hierarchical_v2/unsw_safety_gated_rounds40_clean_fedavg/`

Known metrics:

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | 0.849291 |
| Attack-family macro-F1 | 0.372090 |
| Rare-class macro-F1 | 0.000000 |
| Missed-as-benign rate | 0.057443 |
| False negatives | 2604 |
| Selected round | 1 |

Reason not promoted:

This run reduced missed attacks, but the safety gate selected an undertrained
round and collapsed attack-family and rare-class performance. It is kept as
failed selector evidence only.

## Final Decision

Use the old clean hierarchical FedAvg baseline as the selected/current UNSW
clean federated hierarchical model:

`models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt`

Both newer rounds=40 checkpoints remain experimental evidence and must not be
reported as promoted final or selected models.

## Notes on Legacy UNSW Binary Artifacts

Legacy UNSW binary artifacts from the earlier 190-feature path are archive-only.
They are not used for current UNSW hierarchical federated work.

Current UNSW hierarchical work uses the verified 192-feature hierarchical path:

`data/processed/unsw_nb15/hierarchical`

## Reporting / Demo Use

For reporting and demo purposes, use the selected old clean hierarchical FedAvg
baseline unless a later approved model-selection decision replaces it. No newer
experimental checkpoint is promoted automatically.
