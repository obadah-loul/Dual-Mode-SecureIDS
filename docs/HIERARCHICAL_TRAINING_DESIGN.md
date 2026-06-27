# Hierarchical Training Design

Status: `Task A8.5 class-weight strategy locked - no full training run`

## 1. Scope

Task A6 defines the future centralized hierarchical training design for the
approved advanced model:

`SecureIDS-HierarchicalAdvancedNet`

This task creates training configs, smoke configs, read-only config validators,
read-only planning helpers, and documentation. It does not train models,
evaluate final performance, create checkpoints, create final metrics, start
hierarchical FedAvg, or implement later security/XAI/dashboard layers.

## 2. Dataset Dimensions

| Dataset | Input dimension | Head 1 output | Head 2 output |
| --- | ---: | ---: | ---: |
| CICIDS2018 | 77 | 1 binary logit | 14 attack-family logits |
| UNSW-NB15 | 190 | 1 binary logit | 9 attack-category logits |

The architecture remains shared. Dataset-specific config values provide the
input dimension and Head 2 dimension.

## 3. Model Contract

Future training must instantiate only:

`SecureIDSHierarchicalAdvancedNet`

The model returns:

- `binary_logit`: Head 1 benign/normal vs attack logit.
- `attack_logits`: Head 2 dataset-specific attack-family logits.
- `embedding`: shared representation reserved for future analysis and XAI.

No alternate model architecture is introduced in A6.

## 4. Head 2 Targets

CICIDS2018 uses the A4.5 raw-preserving 14-class mapping:

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

UNSW-NB15 uses the official 9-class `attack_cat` mapping:

- `Generic`
- `Exploits`
- `Fuzzers`
- `DoS`
- `Reconnaissance`
- `Analysis`
- `Backdoor`
- `Shellcode`
- `Worms`

The common superclass mapping remains reporting-only and is not a training
target.

## 5. Loss Design

Future training uses masked multi-task loss:

```text
total_loss =
    1.0 * BCEWithLogitsLoss(binary_logit, y_binary)
    + 1.0 * CrossEntropyLoss(attack_logits[attack_rows], y_attack_family[attack_rows])
```

Masking contract:

- Benign/normal rows: `y_binary = 0`, `y_attack_family = -1`,
  `attack_family_mask = 0`.
- Attack rows: `y_binary = 1`, valid non-negative `y_attack_family`,
  `attack_family_mask = 1`.
- Head 1 uses all rows.
- Head 2 uses only rows where `attack_family_mask = 1`.
- `ignore_index = -1`.

## 6. Class Imbalance

Task A8.5 locks the class-weight strategy before full training.

Future training must compute class weights from the training split only:

- Binary Head 1: balanced class weights from `y_binary_train.npy`, normalized
  so the mean class weight is near `1.0`, then capped at `10.0`.
- Attack-family Head 2: sqrt inverse-frequency weights from attack rows in
  `y_attack_family_train.npy` where `attack_family_mask_train.npy == 1`,
  normalized so the mean class weight is near `1.0`, then capped at `10.0`.
- Raw inverse-frequency Head 2 weights are rejected for final training because
  A8 showed dangerously extreme rare-class weights.
- Validation labels and test labels must not be used for weighting.
- Oversampling and manual rare-class duplication are disabled.

This keeps validation and test data out of preprocessing, weighting, and
selection decisions while still giving rare classes controlled extra weight.

## 7. Rare And Hard Classes

Required future reporting includes per-class precision, recall, F1, and support
for Head 2. It also requires rare-class reporting.

CICIDS rare raw labels preserved by the A4.5 mapping:

- `DDOS attack-LOIC-UDP` -> `DDoS-LOIC-UDP`
- `DoS attacks-Slowloris` -> `DoS-Slowloris`
- `Brute Force -Web` -> `Web-BruteForce`
- `Brute Force -XSS` -> `Web-XSS`
- `SQL Injection` -> `SQL-Injection`

UNSW rare classes tracked in the config:

- `Shellcode`
- `Worms`

Hard/weak class reporting should compare validation and final test behavior,
but final model selection must not use test results.

## 8. Best Checkpoint Selection

Best epoch selection is validation-only:

```text
val_hierarchical_score =
    0.5 * val_binary_macro_f1
    + 0.5 * val_attack_family_macro_f1
```

The final test split is evaluated once after the best validation epoch is
selected. Test metrics must not tune thresholds, class weights, early stopping,
or model selection.

## 9. Planned Configs

Created full-training configs:

- `configs/training/cicids2018_hierarchical.yaml`
- `configs/training/unsw_nb15_hierarchical.yaml`

Created non-final smoke configs:

- `configs/training/smoke_cicids2018_hierarchical.yaml`
- `configs/training/smoke_unsw_nb15_hierarchical.yaml`

The full-training configs are plans for later approval. They are not executed
in A6.

## 10. Planned Full-Training Outputs

CICIDS2018 planned outputs:

- `models/final/final_cicids_hierarchical.pt`
- `results/final/hierarchical/cicids/training_history.csv`
- `results/final/hierarchical/cicids/test_metrics.json`
- `results/final/hierarchical/cicids/binary_confusion_matrix.csv`
- `results/final/hierarchical/cicids/attack_family_confusion_matrix.csv`
- `results/final/hierarchical/cicids/per_class_attack_metrics.csv`
- `results/final/hierarchical/cicids/rare_class_metrics.csv`
- `results/audits/hierarchical_training_manifest_cicids2018.json`
- `docs/HIERARCHICAL_TRAINING_REPORT.md`

UNSW-NB15 planned outputs:

- `models/final/final_unsw_hierarchical.pt`
- `results/final/hierarchical/unsw/training_history.csv`
- `results/final/hierarchical/unsw/test_metrics.json`
- `results/final/hierarchical/unsw/binary_confusion_matrix.csv`
- `results/final/hierarchical/unsw/attack_family_confusion_matrix.csv`
- `results/final/hierarchical/unsw/per_class_attack_metrics.csv`
- `results/final/hierarchical/unsw/rare_class_metrics.csv`
- `results/audits/hierarchical_training_manifest_unsw_nb15.json`
- `docs/HIERARCHICAL_TRAINING_REPORT.md`

None of these full-training outputs are created in A6.

## 11. Pre-Run Checks For A Later Training Task

Before any future full hierarchical training run:

- Confirm the selected config loads with the expected dataset dimensions.
- Confirm the hierarchical processed folder exists.
- Confirm `X_train`, `X_val`, `X_test`, Head 1 labels, Head 2 labels, and masks
  exist.
- Inspect NumPy shapes with mmap only before training.
- Confirm feature-name count equals input dimension.
- Confirm attack-family class count equals Head 2 dimension.
- Confirm A4/A4.5 readiness JSON status is `PASS`.
- Confirm future final output files do not already exist, unless an approved
  overwrite task explicitly allows replacement.
- Confirm the final test set will be used once, after validation selection.

## 12. A6 Safety Boundary

Task A6 did not:

- Run full hierarchical training.
- Run final hierarchical evaluation.
- Create hierarchical checkpoints.
- Create final hierarchical metrics.
- Start hierarchical FedAvg.
- Start calibration or routing.
- Start TLS, SHA-256 integrity, or gradient trust logging.
- Start sign-flip, Gaussian noise, or scaling attacks.
- Start Trimmed Mean or robust aggregation comparisons.
- Start permutation importance, SHAP, IG, or other XAI.
- Start dashboard work.
- Modify V1.
- Modify existing binary centralized or FedAvg artifacts.
