# CICIDS Hierarchical Federated Model Selection Decision

## Status

The completed CICIDS hierarchical clean FedAvg run is selected and locked as the
current CICIDS clean federated hierarchical baseline.

This decision covers only the clean CICIDS hierarchical federated baseline. No
attack or defense result is selected here.

## Selected Current Model

Selected checkpoint:

`models/experiments/federated_security/cicids_hierarchical_clean_fedavg.pt`

Selected result folder:

`results/experiments/federated_security/cicids_hierarchical_clean_fedavg/`

Selected manifest:

`results/audits/federated_security_cicids_hierarchical_clean_fedavg_manifest.json`

Selected report:

`docs/experiments/FEDERATED_SECURITY_CICIDS_HIERARCHICAL_CLEAN_FEDAVG_REPORT.md`

## Selected Metrics

| Metric | Value |
| --- | ---: |
| Binary accuracy | 0.977296 |
| Binary precision | 0.973014 |
| Binary recall | 0.946739 |
| Binary F1 | 0.959697 |
| Binary macro-F1 | 0.971947 |
| Attack-family accuracy | 0.954970 |
| Attack-family macro-F1 | 0.851652 |
| Rare-class macro-F1 | 0.748521 |
| Best round | 19 |
| Rounds run | 20 |

## Confusion Matrix and Safety Metric

| Value | Count |
| --- | ---: |
| TP | 390280 |
| FP | 10824 |
| FN | 21956 |
| TN | 1020713 |

| Safety metric | Value |
| --- | ---: |
| Missed-as-benign rate | 0.053261 |
| Missed-as-benign count | 21956 |

## Why This Model Is Selected

The CICIDS clean hierarchical FedAvg run provides the completed clean
hierarchical federated baseline needed before the attack/defense matrix. It has
strong binary performance, strong attack-family performance, and a documented
missed-as-benign safety profile.

The command output may describe the run as experimental, but main chat has now
explicitly selected it as the current CICIDS clean hierarchical federated
baseline.

## Notes on CICIDS Binary FedAvg Artifacts

CICIDS binary FedAvg artifacts are archive/baseline-only references. They are
not the final target for current CICIDS hierarchical federated reporting.

## Scope of This Decision

This decision selects only the clean CICIDS hierarchical FedAvg baseline. It does
not select any Byzantine attack result, robust aggregation result, or defense
comparison result.

This decision does not touch UNSW. UNSW model selection is locked separately.

## Reporting / Demo Use

Use this checkpoint for final reporting and demo as the CICIDS clean
hierarchical federated baseline unless a later approved decision replaces it:

`models/experiments/federated_security/cicids_hierarchical_clean_fedavg.pt`

## Final Decision

The CICIDS hierarchical clean FedAvg run is the selected current CICIDS clean
federated hierarchical baseline.
