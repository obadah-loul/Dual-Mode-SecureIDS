# Hierarchical Preprocessing Design

Status: `Task A2 design with Task A4.5 CICIDS Head 2 revision`

## 1. Purpose

This document designs how preprocessing should be extended later for `SecureIDS-HierarchicalAdvancedNet`. It does not implement preprocessing, create arrays, train models, evaluate metrics, or modify existing processed artifacts.

## 2. Label Outputs

Hierarchical preprocessing should preserve both binary labels and attack-family labels.

Proposed binary label files:

- `y_binary_train.npy`
- `y_binary_val.npy`
- `y_binary_test.npy`

Proposed attack-family label files:

- `y_attack_family_train.npy`
- `y_attack_family_val.npy`
- `y_attack_family_test.npy`

Proposed mappings:

- `binary_label_mapping.json`
- `attack_family_label_mapping.json`
- `common_attack_superclass_mapping.json`

## 3. Binary Label Format

- CICIDS2018: benign labels such as `BENIGN`/`Benign` map to `0`; all attack labels map to `1`.
- UNSW-NB15: `label == 0` maps to `0`; `label == 1` maps to `1`.
- Binary labels are used by Head 1 for every row.

## 4. Attack-Family Label Format

- CICIDS2018 attack-family labels come from the stripped CICIDS `Label` value for attack rows.
- UNSW-NB15 attack-family labels come from stripped `attack_cat` where `label == 1`.
- Benign rows should receive a sentinel attack-family value such as `-1` and a mask value of `0`.
- Attack rows should receive a dataset-specific attack-family class index and a mask value of `1`.

Proposed mask files:

- `attack_family_mask_train.npy`
- `attack_family_mask_val.npy`
- `attack_family_mask_test.npy`

## 5. Benign Rows And Head 2

Benign rows are excluded from Head 2 loss. They remain present for Head 1 binary detection and for final routing analysis. During masked multi-task training:

- Binary loss applies to all rows.
- Attack-family loss applies only where `attack_family_mask == 1`.
- Benign rows have `y_attack_family = -1` or another documented ignore index.

## 6. Masked Multi-Task Training Contract

The approved preferred design is masked multi-task training:

```text
total_loss = binary_loss(all rows) + lambda_attack * attack_family_loss(attack rows only)
```

The attack-family loss must not be computed for benign rows. Test-set labels must not be used for tuning `lambda_attack`, thresholds, class weights, or rare-class decisions.

## 7. Dataset-Specific Taxonomies

CICIDS2018 and UNSW-NB15 keep separate attack-family mappings:

- CICIDS attack-family output dimension is `14` after the Task A4.5
  raw-preserving Head 2 revision.
- UNSW attack-family output dimension equals the number of UNSW `attack_cat` labels retained after audit/design.
- No fake exact shared Head 2 class list is created.

Current CICIDS Head 2 classes:

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

Current UNSW Head 2 classes remain the official `attack_cat` categories:

- `Generic`
- `Exploits`
- `Fuzzers`
- `DoS`
- `Reconnaissance`
- `Analysis`
- `Backdoor`
- `Shellcode`
- `Worms`

## 8. Common Superclass Reporting

Common superclasses may be saved for reporting/dashboard comparison only. They are not the primary training target unless a later approved task explicitly changes the design.

Recommended reporting-only file:

- `common_attack_superclass_mapping.json`

## 9. Current Preprocessing Extension Strategy

The existing preprocessing can be extended safely by adding new hierarchical configs rather than modifying accepted binary outputs in place.

Proposed future output directories:

- `data/processed/cicids2018/hierarchical/`
- `data/processed/unsw_nb15/hierarchical/`

Proposed files per dataset:

- `X_train.npy`, `X_val.npy`, `X_test.npy`
- `y_binary_train.npy`, `y_binary_val.npy`, `y_binary_test.npy`
- `y_attack_family_train.npy`, `y_attack_family_val.npy`, `y_attack_family_test.npy`
- `attack_family_mask_train.npy`, `attack_family_mask_val.npy`, `attack_family_mask_test.npy`
- `feature_names.json`
- `binary_label_mapping.json`
- `attack_family_label_mapping.json`
- `common_attack_superclass_mapping.json`
- `split_summary.json`
- `hierarchical_preprocessing_manifest.json`

## 10. Centralized Training Compatibility

Centralized hierarchical training should consume one dataset at a time with dataset-specific input dimension and attack-family output dimension. Existing binary centralized results remain foundation baselines only.

## 11. FedAvg Compatibility

Hierarchical FedAvg should run separately per dataset. Client splitting should be based on training rows only. Future client reports should track both binary class distribution and attack-family distribution per client.

## 12. Manifest Requirements

Hierarchical preprocessing manifests should record:

- Binary label mapping.
- Attack-family label mapping.
- Common superclass mapping.
- Rare-class threshold: `1.0%` audit threshold unless later changed by approved design.
- Counts source: raw CICIDS `Label`; raw UNSW `label` and `attack_cat`.
- Generated output paths.
- Feature count.
- Attack-family class count.
- Benign/attack row counts.
- Per-attack support counts.
- No-test-tuning statement.
- Confirmation that common superclasses are reporting-only.

## 13. Rare-Class Evaluation Design

Future hierarchical reports should include:

- Per-class precision.
- Per-class recall.
- Per-class F1.
- Macro-F1.
- Rare-class F1.
- Support counts.
- Attack-family confusion matrix.
- Rare-class error analysis.
- Head 1 false-negative analysis for missed attacks.

## 14. No-Fake Cross-Dataset Claims

- CICIDS and UNSW taxonomies remain separate.
- Common superclasses are reporting/dashboard labels only.
- No cross-dataset attack-family training is claimed.
- No direct CICIDS-to-UNSW frozen-feature attack-family evaluation is claimed.
- All mappings must be traceable to raw label counts.

## 15. Task A1 Audit References

- `docs/ATTACK_TAXONOMY_AUDIT.md`
- `results/audits/cicids_attack_taxonomy_counts.csv`
- `results/audits/unsw_attack_taxonomy_counts.csv`

## 16. Task A2 Locked Config And Dry-Run References

Task A2 locks the dataset-specific taxonomy and preprocessing config paths for
future hierarchical preprocessing. Task A4.5 revises only the CICIDS taxonomy
to preserve all 14 raw attack labels as separate Head 2 classes before model
implementation. UNSW remains unchanged. These design/config updates still do
not train, evaluate, modify model code, create checkpoints, or create final
metrics.

Locked taxonomy configs:

- `configs/taxonomy/cicids2018_attack_taxonomy.yaml`
- `configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`

Hierarchical preprocessing config contracts:

- `configs/preprocessing/cicids2018_hierarchical.yaml`
- `configs/preprocessing/unsw_nb15_hierarchical.yaml`

Dry-run audit records:

- `results/audits/hierarchical_preprocessing_dry_run_cicids2018.json`
- `results/audits/hierarchical_preprocessing_dry_run_unsw_nb15.json`

The configs preserve dataset-specific Head 2 taxonomies, use `-1` as the
Head 2 ignore index for benign/normal rows, use mask value `0` for
benign/normal rows and `1` for attack rows, and keep common superclasses as a
reporting-only layer.
