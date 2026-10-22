> Recovery correction (22 October 2026): read [scientific corrections](../LOCAL_RECOVERY.md) alongside this historical report. Nominal SignFlip25 realized 1/5 = 20%; stored numbers below are unchanged.

# Phase A Full-State SignFlip: Requested 25%, Realized 20%

## Status

The historical Phase A experiment series was recorded as completed. It is exploratory
evidence, not independent confirmation of a production-ready defense. No training
or benchmark re-evaluation was performed during the October 2026 recovery.

## Purpose

Phase A compares three hierarchical federated conditions:

- Clean hierarchical FedAvg baseline.
- Full-state SignFlip with *requested* 25% malicious clients, *realized* 20%, under FedAvg.
- The same requested/realized attack setting under Trimmed Mean aggregation.

The comparison is reported for both target datasets:

- UNSW-NB15.
- CICIDS2018.

## Scope and Threat Model

This is simulated federated Byzantine attack testing, not real hacking. The
malicious behavior is introduced inside the federated-learning experiment to
measure robustness under controlled conditions.

The configuration requests `malicious_fraction: 0.25`, but the implementation
uses floor rounding with five configured clients. Therefore **one of five clients
was malicious (20% realized, not 25%)**. The historical SignFlip implementation
scales the malicious client's **absolute floating model state**, not its
parameter delta from the global state. FedAvg is the comparison aggregator;
Trimmed Mean is the evaluated robust aggregation technique, not a security guarantee.

The original update hashes were generated and checked within the same simulation.
They are useful fingerprints but **do not independently authenticate client origin
or establish that a received update was untampered**. SHA-256 hashing is not the
Byzantine-robust aggregation technique.

## Phase A Result Matrix

**Interpretation:** `0.25` in the table is the **requested configuration**,
not the realized fraction. For all attacked rows shown, the recorded realized
rate was 1/5 = 0.20. All historical metrics are preserved as originally saved.
These are test-informed exploratory observations, not untouched confirmatory estimates.

| Dataset | Scenario | Attack | Requested fraction | Aggregator | Binary macro-F1 | Attack-family macro-F1 | Rare-class macro-F1 | Missed-as-benign | Best round | Status |
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

Within the saved single-seed experiment conditions, attacked FedAvg had lower
macro-F1 than the selected clean baseline, and attacked Trimmed Mean recovered
macro-F1 in several comparisons. UNSW-NB15 also had a higher missed-as-benign
rate under Trimmed Mean. This supports a qualified **observed tradeoff**, not
a general robustness or safety guarantee. The recorded settings used IID splits,
full-state SignFlip and 20% realized malicious clients; there is no clean
Trimmed Mean control in this Phase A matrix.

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

Use this Phase A summary only alongside [the verification and claims report](../PROJECT_VERIFICATION_REPORT.md)
and [the recovery corrections](../LOCAL_RECOVERY.md).

Keep the clean baseline decision documents as the selected clean references.
Do not claim Trimmed Mean solves all safety issues; state the nuanced finding
honestly.

## Supplemental rare-family reporting

The null/not_reported entries above remain the original saved evidence. The
[derived rare-class supplement](../recovery/rare_class_supplement.csv) computes
means from the saved per-class F1 values using frozen canonical family names.
It is a supplemental calculation, not new predictions or benchmark evaluation.
