# Hierarchical Preprocessing Dry-Run Design

Status: `Task A2 complete - taxonomy config lock and dry-run preparation only`

## 1. Purpose

Task A2 locks dataset-specific attack taxonomy configs and prepares
hierarchical preprocessing dry-run records for the approved
`SecureIDS-HierarchicalAdvancedNet` direction.

This task does not implement model code, execute real hierarchical
preprocessing, create arrays, train, evaluate, create checkpoints, start
security/attack/XAI/dashboard work, or create final metrics.

## 2. A1 Source Summary

Task A1 approved the advanced final direction and produced audit-only taxonomy
counts from actual data.

- CICIDS2018 attack labels: 14
- CICIDS2018 rare labels under the audit-only `< 1.0%` rule: 5
- UNSW-NB15 attack labels: 9
- UNSW-NB15 rare labels under the audit-only `< 1.0%` rule: 2
- Common superclasses are reporting-only.
- No fake exact shared CICIDS/UNSW multiclass label list is created.

Source audit files:

- `docs/ATTACK_TAXONOMY_AUDIT.md`
- `results/audits/cicids_attack_taxonomy_counts.csv`
- `results/audits/unsw_attack_taxonomy_counts.csv`

## 3. Locked Taxonomy Configs

- `configs/taxonomy/cicids2018_attack_taxonomy.yaml`
- `configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`

Each taxonomy config records:

- Dataset name.
- Source label columns.
- Binary mapping.
- Head 2 ignore index: `-1`.
- Head 2 mask values: benign/normal rows `0`, attack rows `1`.
- Rare-class rule: `support_percent < 1.0`.
- Dataset-specific attack labels from A1.
- Mapped attack family.
- Reporting-only common superclass.
- Support count, support percent, and rare flag.

## 4. Hierarchical Preprocessing Configs

- `configs/preprocessing/cicids2018_hierarchical.yaml`
- `configs/preprocessing/unsw_nb15_hierarchical.yaml`

These configs describe the future hierarchical preprocessing contract only.
They point to the existing binary feature-name files to preserve current input
dimensions:

- CICIDS2018 expected current feature dimension: `77`
- UNSW-NB15 expected current feature dimension: `190`

Planned future output directories:

- `data/processed/cicids2018/hierarchical`
- `data/processed/unsw_nb15/hierarchical`

No Task A2 command creates these arrays.

## 5. Dry-Run JSON Records

- `results/audits/hierarchical_preprocessing_dry_run_cicids2018.json`
- `results/audits/hierarchical_preprocessing_dry_run_unsw_nb15.json`

The dry-run records validate that:

- Every observed A1 attack label is represented in the taxonomy config.
- Benign/normal rows use Head 2 ignore index `-1` and mask value `0`.
- Attack rows use Head 2 mask value `1`.
- Common superclasses remain reporting-only.
- No fake shared CICIDS/UNSW multiclass target exists.
- Planned output names and directories are documented.
- Existing binary feature dimensions match the expected dimensions.
- Future centralized training can consume one dataset-specific hierarchical
  processed directory at a time.
- Future FedAvg can aggregate same-dataset hierarchical model instances.

## 6. What The Dry-Run Does Not Do

The dry-run does not:

- Read full raw datasets again.
- Recalculate full row counts.
- Create `.npy` arrays.
- Create `data/processed/*/hierarchical` outputs.
- Modify existing binary processed arrays.
- Implement model code.
- Run training or evaluation.
- Create checkpoints.
- Create final metrics.
- Start TLS, integrity, attack, robust aggregation, XAI, or dashboard layers.

## 7. Dataset-Specific Taxonomy Rule

CICIDS2018 and UNSW-NB15 keep separate Head 2 taxonomies. This is required
because the datasets have different feature schemas and different attack
labels. The common superclass layer is for reporting and dashboard comparison
only.

## 8. Centralized And FedAvg Compatibility

Centralized compatibility is preserved because each future hierarchical
processed directory will expose one dataset-specific feature matrix, binary
labels, attack-family labels, and an attack-family mask.

FedAvg compatibility is preserved because future federated training should run
separately per dataset. Each round will aggregate parameters from model
instances with the same input dimension and same dataset-specific Head 2 output
dimension.

## 9. Next Step After A2 Approval

After A2 review approval, the next step should be real hierarchical
preprocessing implementation and execution preparation. It should not jump
directly to model training.
