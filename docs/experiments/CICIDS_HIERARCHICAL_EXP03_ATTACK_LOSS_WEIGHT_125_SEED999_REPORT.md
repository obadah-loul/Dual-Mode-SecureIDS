> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-25T10:37:36.814731+00:00`

## Scope and protocol

- This is the **CICIDS2018 hierarchical benchmark protocol**: a stratified
  train/validation/test split of the processed CICIDS2018 flows.
- The CICIDS2018 binary centralized/FedAvg baselines are separate prior
  artifacts and are NOT these final hierarchical results.
- `input_dim` = **77**; `attack_head_dim` = **14**.
- Model: `SecureIDSHierarchicalAdvancedNet` (shared encoder + binary Head 1 +
  dataset-aware attack-family Head 2).
- Checkpoint selected by **validation only**
  (`val_hierarchical_score = 0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1`).
- Test evaluated **once** after the best validation checkpoint was selected.
- Class weights computed from the **train split only** (no validation/test labels);
  no test-set tuning.
- Not started yet: hierarchical FedAvg, security/SHA-256, Byzantine attacks,
  Trimmed Mean, XAI, dashboard.

## Training

- Device: `cuda`
- Best epoch: `6` (epochs run: `11`)
- Best validation hierarchical score: `0.913383`
- Validation binary macro-F1 (best epoch): `0.9748248869448586`
- Validation attack-family macro-F1 (best epoch): `0.8519415406313945`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.979468`
- precision: `0.978661`
- recall: `0.948779`
- f1: `0.963489`
- macro_f1: `0.974604`
- attack false negatives (attacks predicted benign): `21115`
- confusion (tn,fp,fn,tp): `1023009, 8528, 21115, 391121`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.964113`
- macro-F1 on attack rows (all 14 classes): `0.875094`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 0.9999 | 0.9999 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9992 | 0.9985 | 0.9988 | 86401 |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Hulk` | 0.9997 | 0.9998 | 0.9997 | 69514 |
| `DoS-SlowHTTPTest` | 0.7489 | 0.4749 | 0.5812 | 20941 |
| `DoS-GoldenEye` | 0.9974 | 0.9964 | 0.9969 | 6127 |
| `DoS-Slowloris` | 0.9951 | 0.9896 | 0.9924 | 1642 |
| `Bot` | 0.9979 | 0.9994 | 0.9987 | 42717 |
| `FTP-BruteForce` | 0.6994 | 0.8849 | 0.7813 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9953 | 0.9927 | 0.9940 | 24489 |
| `Web-BruteForce` | 0.7722 | 0.6354 | 0.6971 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.8889 | 0.6667 | 0.7619 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.780176838600292`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Slowloris` | 0.9951 | 0.9896 | 0.9924 | 1642 |
| `Web-BruteForce` | 0.7722 | 0.6354 | 0.6971 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.8889 | 0.6667 | 0.7619 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1023009` (0.9917 of 1031537 benign)
- attack detected and correctly attributed: `376508` (0.9133 of 412236 attacks)
- attack detected but wrong family: `14613` (0.0354)
- attack missed as benign: `21115` (0.0512)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp03_attack_loss_weight_125_seed999`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed999.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
