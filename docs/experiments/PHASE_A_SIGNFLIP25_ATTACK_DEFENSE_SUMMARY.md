# Phase A SignFlip 25% Hierarchical Federated Attack/Defense Summary

## Status

Phase A is accepted as complete.

This is the minimum professional hierarchical federated attack/defense evidence
for the current SecureIDS V2 reporting and demo scope.

## Purpose

Phase A compares three hierarchical federated conditions:

- Clean hierarchical FedAvg baseline.
- SignFlip attack with 25% malicious clients under FedAvg.
- SignFlip attack with 25% malicious clients under Trimmed Mean defense.

The comparison is reported for both target datasets:

- UNSW-NB15.
- CICIDS2018.

## Scope and Threat Model

This is simulated federated Byzantine attack testing, not real hacking. The
malicious behavior is introduced inside the federated-learning experiment to
measure robustness under controlled conditions.

A 25% malicious-client fraction means 1 out of 5 federated clients is malicious.
SignFlip means the malicious client flips or scales its model update to poison
aggregation. FedAvg is the normal vulnerable baseline aggregator. Trimmed Mean is
the robust aggregation defense.

SHA-256 integrity provides tamper-evidence for update integrity. It is not the
Byzantine defense itself; the defense evaluated here is Trimmed Mean.

## Phase A Result Matrix

| Dataset | Scenario | Attack | Malicious % | Aggregator | Binary macro-F1 | Attack-family macro-F1 | Rare-class macro-F1 | Missed-as-benign | Best round | Status |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | --- |
| UNSW-NB15 | clean_baseline | none | 0.00 | FedAvg | 0.882305 | 0.475889 | 0.307115 | 0.062097 | 16 | selected_clean_baseline |
| UNSW-NB15 | signflip25_attacked_fedavg | SignFlip | 0.25 | FedAvg | 0.824630 | 0.378122 | not_reported | 0.049479 | 3 | completed_phase_a |
| UNSW-NB15 | signflip25_trimmed_mean_defense | SignFlip | 0.25 | Trimmed Mean | 0.896008 | 0.473813 | not_reported | 0.085150 | 14 | completed_phase_a |
| CICIDS2018 | clean_baseline | none | 0.00 | FedAvg | 0.971947 | 0.851652 | 0.748521 | 0.053261 | 19 | selected_clean_baseline |
| CICIDS2018 | signflip25_attacked_fedavg | SignFlip | 0.25 | FedAvg | 0.950954 | 0.770096 | not_reported | 0.057256 | 1 | completed_phase_a |
| CICIDS2018 | signflip25_trimmed_mean_defense | SignFlip | 0.25 | Trimmed Mean | 0.971527 | 0.841040 | not_reported | 0.054018 | 14 | completed_phase_a |

## UNSW-NB15 Comparison

Clean baseline:

- Binary macro-F1: 0.882305.
- Attack-family macro-F1: 0.475889.
- Rare-class macro-F1: 0.307115.
- Missed-as-benign rate: 0.062097.

SignFlip FedAvg:

- Binary macro-F1 dropped to 0.824630.
- Attack-family macro-F1 dropped to 0.378122.
- Missed-as-benign improved numerically to 0.049479.

Trimmed Mean:

- Binary macro-F1 recovered to 0.896008.
- Attack-family macro-F1 recovered to 0.473813.
- Missed-as-benign worsened to 0.085150.

Interpretation:

Trimmed Mean improved macro-F1 robustness on UNSW-NB15, but introduced a safety
tradeoff in missed attacks.

## CICIDS2018 Comparison

Clean baseline:

- Binary macro-F1: 0.971947.
- Attack-family macro-F1: 0.851652.
- Rare-class macro-F1: 0.748521.
- Missed-as-benign rate: 0.053261.

SignFlip FedAvg:

- Binary macro-F1 dropped to 0.950954.
- Attack-family macro-F1 dropped to 0.770096.
- Missed-as-benign worsened to 0.057256.

Trimmed Mean:

- Binary macro-F1 recovered to 0.971527.
- Attack-family macro-F1 recovered to 0.841040.
- Missed-as-benign improved to 0.054018.

Interpretation:

Trimmed Mean strongly recovered CICIDS2018 performance near the clean baseline.

## Main Conclusion

Phase A demonstrates that malicious SignFlip clients degrade standard FedAvg and
that Trimmed Mean can improve robustness. The defense is strongest on CICIDS2018
and more nuanced on UNSW-NB15 due to class imbalance and safety tradeoffs.

## Phase B / C Notes

Gaussian and Scaling attacks are optional Phase B/C work. Experiments with a 50%
malicious-client fraction are also optional Phase B/C work.

These extensions are not required for the current minimum evidence.

## Archive-Only Binary Federated Artifacts

Standalone binary federated artifacts are archive/baseline only. They are not
used as the final hierarchical attack/defense target:

- `models/federated/fedavg_cicids_binary.pt`
- `results/federated/cicids/`
- `configs/federated/cicids2018_fedavg.yaml`
- `models/federated/fedavg_unsw_binary.pt`
- `results/federated/unsw/`
- `configs/federated/unsw_nb15_fedavg.yaml`

## Reporting / Demo Use

Use this Phase A summary as the minimum attack/defense evidence in final
reporting and demo.

Keep the clean baseline decision documents as the selected clean references.
Do not claim Trimmed Mean solves all safety issues; state the nuanced finding
honestly.
