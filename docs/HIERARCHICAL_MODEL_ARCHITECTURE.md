# Hierarchical Model Architecture

Status: `Task A5 complete - architecture skeleton and smoke-only validation`

## 1. What Was Implemented

Task A5 adds the architecture skeleton for the approved final system:

`SecureIDS-HierarchicalAdvancedNet`

Created implementation:

- `secureids/models/secureids_hierarchical_advanced_net.py`
- `SecureIDSHierarchicalAdvancedNet`
- `compute_hierarchical_loss`
- Synthetic CPU-only tests in `tests/test_hierarchical_advanced_model.py`

The implementation defines model structure and loss behavior only. It does not
load datasets, train, evaluate model performance, save checkpoints, or create
metrics.

## 2. Why The Model Is Hierarchical

The final IDS is hierarchical because it answers two related questions:

1. Head 1: is this row benign/normal or attack?
2. Head 2: if it is an attack, which dataset-specific attack family or
   attack type is it?

Head 1 uses every row. Head 2 is masked so benign/normal rows are ignored for
attack-family loss.

## 3. Dataset-Aware Head 2

Head 2 is dataset-aware because CICIDS2018 and UNSW-NB15 have different feature
spaces and different attack taxonomies. The model class accepts dimensions from
the caller instead of hardcoding them.

Approved A5 dimensions:

| Dataset | Input dimension | Attack Head 2 dimension |
| --- | ---: | ---: |
| CICIDS2018 | 77 | 14 |
| UNSW-NB15 | 190 | 9 |

CICIDS2018 Head 2 uses the A4.5 raw-preserving 14-class mapping:

- `DDoS-HOIC`
- `DDoS-LOIC-HTTP`
- `DDoS-LOIC-UDP`
- `DoS-Hulk`
- `DoS-SlowHTTPTest`
- `DoS-GoldenEye`
- `DoS-Slowloris`
- `Bot`
- `FTP-BruteForce`
- `SSH-Bruteforce`
- `Infilteration / Infiltration`
- `Web-BruteForce`
- `Web-XSS`
- `SQL-Injection`

UNSW-NB15 Head 2 keeps the official 9-class `attack_cat` categories:

- `Generic`
- `Exploits`
- `Fuzzers`
- `DoS`
- `Reconnaissance`
- `Analysis`
- `Backdoor`
- `Shellcode`
- `Worms`

## 4. Shared Encoder

The shared encoder is a tabular neural network built for numeric IDS feature
vectors:

1. Input projection from `input_dim` to the first hidden width.
2. Normalization, GELU activation, and dropout.
3. Residual MLP blocks.
4. Optional hidden-width transitions.
5. Gated representation block.
6. Shared embedding returned for future inspection and XAI.

Default hidden dimensions:

```text
(256, 128, 128)
```

Default normalization:

```text
layernorm
```

LayerNorm is the default because it is stable for tiny smoke batches and later
works cleanly with dataset-specific training. BatchNorm and no normalization
are also supported.

## 5. Residual Blocks

Each residual block applies pre-normalization, a two-layer MLP expansion, GELU,
dropout, and a residual connection:

```text
x + MLP(norm(x))
```

This gives the architecture more capacity than the earlier binary baseline
without adding image or sequence assumptions that do not fit tabular IDS data.

## 6. Gated Representation Block

The gated block learns a channel-wise gate over the shared embedding:

```text
embedding = norm(x + value(x) * sigmoid(gate(x)))
```

This is an attention-style mechanism over the learned tabular representation.
It is lightweight, stable, and compatible with centralized and federated
training because it is just normal trainable PyTorch parameters.

## 7. Forward Output

The forward pass returns a dictionary:

```python
{
    "binary_logit": binary_logit,
    "attack_logits": attack_logits,
    "embedding": embedding,
}
```

Expected shapes for batch size `B`:

- `binary_logit`: `(B,)`
- `attack_logits`: `(B, attack_head_dim)`
- `embedding`: `(B, embedding_dim)`

The binary logit is not passed through sigmoid inside the model. It is intended
for `BCEWithLogitsLoss`.

## 8. Masked Multi-Task Loss

`compute_hierarchical_loss` implements the approved masked multi-task contract:

```text
total_loss =
    binary_loss_weight * binary_loss(all rows)
    + attack_loss_weight * attack_loss(attack rows only)
```

Inputs:

- `outputs`
- `y_binary`
- `y_attack_family`
- `attack_family_mask`
- `binary_loss_weight`
- `attack_loss_weight`
- `ignore_index`
- optional binary `pos_weight`

Return fields:

- `total_loss`
- `binary_loss`
- `attack_loss`
- `attack_rows`
- `binary_loss_weight`
- `attack_loss_weight`

## 9. Benign Rows And Ignore Index

Benign/normal rows use:

- `y_binary = 0`
- `y_attack_family = -1`
- `attack_family_mask = 0`

These rows contribute to Head 1 binary loss and are ignored for Head 2
attack-family loss.

Attack rows use:

- `y_binary = 1`
- valid non-negative `y_attack_family`
- `attack_family_mask = 1`

These rows contribute to both Head 1 and Head 2 loss.

## 10. Edge Batch Behavior

All-benign batch:

- Head 1 binary loss is computed normally.
- Head 2 attack loss is a zero tensor on the correct device and dtype.
- Total loss remains finite.

All-attack batch:

- Head 1 binary loss is computed normally.
- Every row contributes to Head 2 cross-entropy.
- Total loss remains finite.

Mixed batch:

- Every row contributes to binary loss.
- Only mask-1 rows with valid attack labels contribute to attack loss.

## 11. Centralized Training Compatibility

Future centralized training can instantiate the same architecture with
dataset-specific dimensions:

```python
SecureIDSHierarchicalAdvancedNet(input_dim=77, attack_head_dim=14)
SecureIDSHierarchicalAdvancedNet(input_dim=190, attack_head_dim=9)
```

The A5 task does not implement a centralized training loop.

## 12. FedAvg Compatibility

FedAvg remains compatible because each dataset-specific federated run can use
the same architecture and the same parameter shapes for all clients in that
dataset:

- CICIDS clients use `input_dim=77`, `attack_head_dim=14`.
- UNSW clients use `input_dim=190`, `attack_head_dim=9`.

The A5 task does not implement hierarchical FedAvg training.

## 13. Future Calibration And Routing

Future calibration or routing can be added around the logits after validation
approval:

- Head 1 probability can be derived with sigmoid.
- Head 2 probabilities can be derived with softmax.
- Any thresholds must be selected using validation data only.

A5 intentionally does not implement calibration, confidence thresholds, or
routing policy.

## 14. Future XAI

The returned `embedding`, binary head, and attack-family head allow future XAI
tasks to explain:

- why Head 1 predicted benign/normal or attack,
- why Head 2 predicted a specific attack class,
- which features matter for rare CICIDS classes and UNSW attack categories.

Permutation importance remains the required later XAI method. A5 does not
implement XAI.

## 15. Smoke Validation

Focused smoke tests validate:

- CICIDS forward pass with `input_dim=77`, `attack_head_dim=14`.
- UNSW forward pass with `input_dim=190`, `attack_head_dim=9`.
- Mixed-batch masked loss.
- All-benign batch loss with zero attack loss.
- All-attack batch loss.
- Safety: no real arrays are loaded and no checkpoints/metrics/future-layer
  outputs are created by tests.

## 16. What Was Not Implemented

- No real training.
- No real model evaluation.
- No checkpoints.
- No model metrics.
- No centralized hierarchical trainer.
- No hierarchical FedAvg trainer.
- No calibration/routing implementation.
- No TLS/security layer.
- No SHA-256 integrity layer.
- No gradient trust/audit layer.
- No Byzantine attacks.
- No Trimmed Mean.
- No XAI.
- No dashboard work.
