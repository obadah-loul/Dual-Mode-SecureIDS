# Hierarchical Class-Weight Strategy

Status: `Task A8.5 complete - class-weight strategy locked before full training`

Generated UTC: `2026-06-24T02:13:04.845234+00:00`

## Decision

Full centralized hierarchical training must use train-split-only class weights with smoothing and a cap.

- Binary Head 1: balanced class weights from `y_binary_train.npy`, mean-normalized, capped at `10.0`.
- Attack Head 2: sqrt inverse-frequency weights from train attack rows only, mean-normalized, capped at `10.0`.
- No validation labels, test labels, oversampling, manual rare-class duplication, or all-split balancing may be used.

## Why Raw Inverse-Frequency Was Rejected

Task A8 showed that raw inverse-frequency Head 2 weights would be dangerously large.

- CICIDS raw max Head 2 weight: `2181.138322` for `SQL-Injection`.
- UNSW raw max Head 2 weight: `103.40367` for `Worms`.

Those values would let a handful of rare rows dominate the attack-family loss and destabilize early training.

## Why Sqrt Inverse-Frequency

Sqrt inverse-frequency keeps the ranking that rare classes need, but compresses the gap between common and rare classes. Mean normalization keeps the class-weight scale close to the unweighted loss, and the cap prevents a single rare class from dominating the optimizer.

## Train-Only Rule

Weights are computed only from the training split. Validation remains reserved for model selection and early stopping, and the test split remains reserved for one final evaluation after the best validation checkpoint is selected. This avoids test-set tuning and fake performance claims.

## Oversampling

Oversampling is disabled. No rows are duplicated and no manual rare-class balancing is introduced in A8.5. If sampling changes are needed later, they require a separate approval task.

## Locked Config Values

```yaml
class_weights:
  binary:
    enabled: true
    source_split: train
    method: balanced
    normalize_mean: true
    max_weight: 10.0
    use_validation_labels: false
    use_test_labels: false
  attack_family:
    enabled: true
    source_split: train_attack_rows_only
    method: sqrt_inverse_frequency
    normalize_mean: true
    max_weight: 10.0
    use_validation_labels: false
    use_test_labels: false
    oversampling: false
```

## Dataset Effects

### cicids2018

- status: `PASS`
- safe_for_full_training: `true`
- max final attack weight: `5.526966`
- cap: `10.0`
- validation labels used: `false`
- test labels used: `false`
- oversampling enabled: `false`
- rare mean final weight: `2.58487`
- non-rare mean final weight: `0.119517`

| Rare class | Train support | Final weight |
| --- | ---: | ---: |
| `DDoS-LOIC-UDP` | 1183 | 1.275454 |
| `DoS-Slowloris` | 7688 | 0.500323 |
| `Web-BruteForce` | 428 | 2.120485 |
| `Web-XSS` | 157 | 3.501122 |
| `SQL-Injection` | 63 | 5.526966 |

### unsw_nb15

- status: `PASS`
- safe_for_full_training: `true`
- max final attack weight: `3.954528`
- cap: `10.0`
- validation labels used: `false`
- test labels used: `false`
- oversampling enabled: `false`
- rare mean final weight: `2.641793`
- non-rare mean final weight: `0.530916`

| Rare class | Train support | Final weight |
| --- | ---: | ---: |
| `Shellcode` | 965 | 1.329059 |
| `Worms` | 109 | 3.954528 |

## Compatibility

The locked strategy is compatible with centralized training because it produces deterministic tensors from each dataset's train split. It is also compatible with future same-dataset FedAvg because every client in a dataset-specific run uses the same Head 2 label space and the global train-derived weighting policy can be documented in the federated manifest.

## Safety Boundary

- No full hierarchical training was run.
- No model evaluation was run.
- No final checkpoints or final metrics were created.
- No hierarchical FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work was started.
