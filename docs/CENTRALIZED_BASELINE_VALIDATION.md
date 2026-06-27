# Centralized Baseline Validation

Status: `PASS`

This report validates existing centralized baseline artifacts only. It does not run training, retraining, model evaluation, preprocessing, federated learning, attack simulation, XAI, dashboard work, or Git operations.

## Dataset Checks

### UNSW-NB15

- Status: `PASS`
- Expected dataset/task/model/input_dim: `unsw_nb15` / `binary` / `SecureIDSNet` / `190`
- Artifact existence checks:
  - `checkpoint_exists`: `True`
  - `metrics_exists`: `True`
  - `history_exists`: `True`
  - `confusion_matrix_exists`: `True`
  - `manifest_exists`: `True`
- Manifest checks:
  - `dataset`: `True` (actual: `unsw_nb15`, expected: `unsw_nb15`)
  - `task`: `True` (actual: `binary`, expected: `binary`)
  - `model`: `True` (actual: `SecureIDSNet`, expected: `SecureIDSNet`)
  - `input_dim`: `True` (actual: `190`, expected: `190`)
  - `test_set_used_for_tuning`: `True` (actual: `False`, expected: `False`)
  - `preprocessing_safety_check_passed`: `True` (actual: `True`, expected: `True`)
  - `no_federated_training`: `True` (actual: `True`, expected: `True`)
  - `no_attack_simulation`: `True` (actual: `True`, expected: `True`)
  - `no_xai`: `True` (actual: `True`, expected: `True`)
  - `final_checkpoint`: `True` (actual: `True`, expected: `True`)

### CICIDS2018

- Status: `PASS`
- Expected dataset/task/model/input_dim: `cicids2018` / `binary` / `SecureIDSNet` / `77`
- Artifact existence checks:
  - `checkpoint_exists`: `True`
  - `metrics_exists`: `True`
  - `history_exists`: `True`
  - `confusion_matrix_exists`: `True`
  - `manifest_exists`: `True`
- Manifest checks:
  - `dataset`: `True` (actual: `cicids2018`, expected: `cicids2018`)
  - `task`: `True` (actual: `binary`, expected: `binary`)
  - `model`: `True` (actual: `SecureIDSNet`, expected: `SecureIDSNet`)
  - `input_dim`: `True` (actual: `77`, expected: `77`)
  - `test_set_used_for_tuning`: `True` (actual: `False`, expected: `False`)
  - `preprocessing_safety_check_passed`: `True` (actual: `True`, expected: `True`)
  - `no_federated_training`: `True` (actual: `True`, expected: `True`)
  - `no_attack_simulation`: `True` (actual: `True`, expected: `True`)
  - `no_xai`: `True` (actual: `True`, expected: `True`)
  - `final_checkpoint`: `True` (actual: `True`, expected: `True`)

## Training Report Check

- Path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\docs\CENTRALIZED_TRAINING_REPORT.md`
- Exists: `True`
- Contains UNSW: `True`
- Contains CICIDS: `True`
- Contains completion language: `True`
- Status: `PASS`

## Safety Confirmation

- No training was run.
- No retraining was run.
- No model evaluation was run.
- No checkpoints, metrics, histories, confusion matrices, or training manifests were modified.
- No datasets, splits, preprocessing outputs, preprocessing artifacts, thresholds, or model architecture were changed.
- No federated learning, security, attack, XAI, dashboard, Git commit, or Git push work was performed.
