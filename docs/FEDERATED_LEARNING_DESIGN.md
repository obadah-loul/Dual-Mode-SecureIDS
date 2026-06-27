# Federated Learning Design

## 1. Purpose

This document defines the first federated learning stage for the V2 project:
a clean FedAvg baseline for binary intrusion detection. It is design-only and
does not implement or execute federated training.

The full project direction remains:

Secure, Robust, and Explainable Federated Intrusion Detection System.

The design keeps the FedAvg baseline compatible with later secure
communication, update integrity, attack simulation, robust aggregation,
explainability, and Streamlit reporting layers without mixing those layers into
the first baseline.

## 2. Accepted Upstream State

Centralized baselines are complete and validated.

UNSW-NB15:

- Checkpoint: `models/final/final_unsw_binary.pt`
- Metrics: `results/final/centralized/unsw_test_metrics.json`
- Manifest: `results/audits/training_manifest_unsw_nb15.json`
- Model: `SecureIDSNet`
- Task: binary classification
- Input dimension: `190`
- Accuracy: `0.8875904665765565`
- Macro-F1: `0.8792684183754923`

CICIDS2018:

- Checkpoint: `models/final/final_cicids_binary.pt`
- Metrics: `results/final/centralized/cicids_test_metrics.json`
- Manifest: `results/audits/training_manifest_cicids2018.json`
- Model: `SecureIDSNet`
- Task: binary classification
- Input dimension: `77`
- Accuracy: `0.9795632692951038`
- Macro-F1: `0.9746194261725205`

The centralized checkpoints are reference artifacts only for the federated
stage. They must not be overwritten, retrained, or used as a shortcut for
federated results.

## 3. Scope

Task 9A scope:

- Design the FedAvg baseline.
- Add dataset-specific FedAvg design configs.
- Keep model, data, thresholds, preprocessing, and centralized artifacts
  unchanged.

Out of scope for Task 9A:

- Federated implementation code.
- Federated training or evaluation.
- New checkpoints, metrics, histories, confusion matrices, or manifests.
- Security layer implementation.
- Byzantine attack implementation.
- Robust aggregation implementation.
- XAI implementation.
- Dashboard model demo.
- Git operations.

## 4. Model And Task Contract

The federated baseline uses one shared architecture:

- Architecture: `SecureIDSNet`
- Task: binary classification only
- Output dimension: `1`
- Loss concept: `BCEWithLogitsLoss`
- Decision threshold: `0.5`

Dataset-specific input dimensions are preserved:

- UNSW-NB15: `input_dim = 190`
- CICIDS2018: `input_dim = 77`

No multiclass federated setup, extra architecture, ensemble, personalization,
FedProx, Krum, or Trimmed Mean is included in the first baseline.

## 5. Data Boundary

Federated learning consumes existing processed arrays only:

- `data/processed/unsw_nb15/binary`
- `data/processed/cicids2018/binary`

The preprocessing boundary remains unchanged. Dataset adapters and
preprocessors stay dataset-specific, while `SecureIDSNet` remains the shared
model architecture.

Training and validation splits are used during federated round selection. Test
splits are held out and evaluated only once after the best validation round is
selected.

## 6. Client Splitting Design

Default first FedAvg baseline:

- Number of clients: `5`
- Split policy: stratified IID split of each dataset training split
- Seed: `42`
- Client fraction: `1.0`
- Client class distribution tracking: required
- Test leakage: forbidden

Each client receives only a partition of the training split. Validation remains
a global validation split used for global model selection after each round.
Test data is not used for client splitting, local training, round selection, or
hyperparameter adjustment.

Later controlled non-IID design:

- Label-skew/client-distribution partitioning may be added later.
- Non-IID experiments must report client sample counts and class distributions.
- Non-IID splitting is not the default first FedAvg baseline.

## 7. Server And Client Round Structure

The planned FedAvg flow is:

1. Initialize a global `SecureIDSNet` with the dataset-specific input dimension.
2. Split the training data into deterministic client partitions.
3. Distribute global weights to selected clients at each round.
4. Train each client locally for `local_epochs`.
5. Collect client weights or model deltas.
6. Aggregate by weighted FedAvg using client sample counts.
7. Update the global model.
8. Evaluate the global model on the validation split after each round.
9. Select the best round using validation macro-F1.
10. Run final test evaluation exactly once using the best validation round.

Round logs must record server state, client participation, client sample
counts, client class distributions, aggregation weights, validation metrics,
and the best-round decision.

## 8. Planned Output Artifacts

No Task 9A outputs below are created now. These are planned paths for the future
FedAvg execution task.

UNSW-NB15 FedAvg:

- `models/federated/fedavg_unsw_binary.pt`
- `results/federated/unsw/fedavg_round_history.csv`
- `results/federated/unsw/fedavg_client_distribution.csv`
- `results/federated/unsw/fedavg_client_logs.csv`
- `results/federated/unsw/fedavg_test_metrics.json`
- `results/federated/unsw/fedavg_confusion_matrix.csv`
- `results/audits/fedavg_manifest_unsw_nb15.json`
- `docs/FEDERATED_LEARNING_REPORT.md`

CICIDS2018 FedAvg:

- `models/federated/fedavg_cicids_binary.pt`
- `results/federated/cicids/fedavg_round_history.csv`
- `results/federated/cicids/fedavg_client_distribution.csv`
- `results/federated/cicids/fedavg_client_logs.csv`
- `results/federated/cicids/fedavg_test_metrics.json`
- `results/federated/cicids/fedavg_confusion_matrix.csv`
- `results/audits/fedavg_manifest_cicids2018.json`
- `docs/FEDERATED_LEARNING_REPORT.md`

## 9. Manifest And Audit Requirements

Future FedAvg manifests should record:

- Dataset, task, model architecture, and input dimension.
- Preprocessing safety status.
- Centralized reference checkpoint and metrics paths.
- Client split policy, seed, and number of clients.
- Per-client sample counts and class distributions.
- Number of rounds, local epochs, optimizer, batch size, and threshold.
- Aggregation algorithm and weighting policy.
- Best validation round and selection metric.
- Confirmation that test evaluation happened once after best-round selection.
- Scope flags for disabled future layers.

## 10. Future Integration Points

These layers are planned future work and must not be implemented in the first
FedAvg baseline.

Secure communication:

- Add TLS transport around server/client communication.
- Keep training payload contracts stable so transport can wrap updates without
  changing model or metric logic.

Gradient/update integrity:

- Add SHA-256 hashes for client updates.
- Record update hashes and verification status in gradient trust/audit logs.
- Do not change aggregation math when integrity logging is enabled.

Attack simulation:

- Add sign-flip, Gaussian noise, and scaling attacks as explicit experimental
  modes.
- Attacks must be disabled by default and logged separately from clean FedAvg.

Robust aggregation:

- Add Trimmed Mean after clean FedAvg is complete.
- Compare Trimmed Mean against FedAvg using the same dataset splits and model
  architecture.

Explainability:

- Add permutation importance as the required first XAI method.
- SHAP or Integrated Gradients can be optional later extensions.
- XAI should consume finalized centralized/federated checkpoints and feature
  names without changing training.

Streamlit dashboard:

- Display centralized results, federated results, security/integrity logs,
  attack and robust aggregation comparisons, and XAI summaries.
- Dashboard work must read generated artifacts and must not trigger training.

## 11. Design Configs

Task 9A adds design configs only:

- `configs/federated/unsw_nb15_fedavg.yaml`
- `configs/federated/cicids2018_fedavg.yaml`

These configs describe the intended FedAvg baseline. They are not executed in
Task 9A and do not create outputs.
