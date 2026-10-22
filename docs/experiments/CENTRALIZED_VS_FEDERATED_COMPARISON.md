> Recovery correction (22 October 2026): read [scientific corrections](../LOCAL_RECOVERY.md) alongside this historical report. Nominal SignFlip25 realized 1/5 = 20%; stored numbers below are unchanged.

# Centralized vs Federated Comparison

## Purpose

This table presents **saved historical metrics**, comparing centralized
hierarchical references with selected clean hierarchical federated simulations
for UNSW-NB15 and CICIDS2018. The metrics were not recomputed during recovery;
test-informed research selection and dataset limitations apply.

The values below are copied from existing saved metric artifacts only. No new
training, preprocessing, evaluation, federated experiment, or attack/defense
experiment was run to create this comparison.

## Source Artifacts

Centralized hierarchical reference metrics:

- `results/final/hierarchical/unsw/test_metrics.json`
- `results/final/hierarchical/unsw/rare_class_metrics.csv`
- `results/final/hierarchical/cicids/test_metrics.json`
- `results/final/hierarchical/cicids/rare_class_metrics.csv`

Selected clean hierarchical federated metrics:

- `results/experiments/federated_security/phase_a_signflip25_attack_defense_matrix.csv`
- `docs/experiments/UNSW_HIERARCHICAL_FEDERATED_MODEL_SELECTION_DECISION.md`
- `docs/experiments/CICIDS_HIERARCHICAL_FEDERATED_MODEL_SELECTION_DECISION.md`

## Concise Comparison Table

| Dataset | Mode | Checkpoint / source | Binary macro-F1 | Attack-family macro-F1 | Rare-class macro-F1 | Missed-as-benign rate |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| UNSW-NB15 | Centralized hierarchical reference | `models/final/final_unsw_hierarchical.pt` | 0.894488 | 0.500429 | 0.385669 | 0.050957 |
| UNSW-NB15 | Selected clean hierarchical federated FedAvg | `models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt` | 0.882305 | 0.475889 | 0.307115 | 0.062097 |
| CICIDS2018 | Centralized hierarchical reference | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` | 0.974604 | 0.875094 | 0.780177 | 0.051221 |
| CICIDS2018 | Selected clean hierarchical federated FedAvg | `models/experiments/federated_security/cicids_hierarchical_clean_fedavg.pt` | 0.971947 | 0.851652 | 0.748521 | 0.053261 |

## Interpretation

- Centralized mode is the reference setting when traffic data can be collected
  in a trusted central environment.
- Federated results were produced by a **single-process simulation** of
  distributed client training over locally available processed arrays. This is
  not a real multi-site deployment or a verified confidentiality guarantee.
- The saved federated macro-F1 scores can be compared to the centralized
  reference scores for these recorded exploratory conditions, but do not
  establish privacy-preserving production deployment.
- UNSW-NB15 remains the harder dataset, with a larger attack-family and
  rare-class gap between centralized and federated settings.
- CICIDS2018 shows stronger clean federated recovery relative to its centralized
  hierarchical reference.

## Reporting Boundary

This table is a clean-baseline comparison only. It is separate from the Phase A
SignFlip 25% robustness matrix, which compares FedAvg against Trimmed Mean under
Byzantine client-update flipping.

Do not use this table to claim TLS, Gaussian Noise, Scaling, or Phase B 50% as
final implemented evidence. Those remain future extensions or archive-only
items unless a strict grading requirement later demands them.
