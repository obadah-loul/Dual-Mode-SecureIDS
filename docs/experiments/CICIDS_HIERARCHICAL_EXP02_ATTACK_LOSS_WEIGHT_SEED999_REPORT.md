> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-25T07:37:12.665431+00:00`

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
- Best validation hierarchical score: `0.903816`
- Validation binary macro-F1 (best epoch): `0.9741435965782748`
- Validation attack-family macro-F1 (best epoch): `0.8334878791790193`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.979021`
- precision: `0.983200`
- recall: `0.942632`
- f1: `0.962489`
- macro_f1: `0.973964`
- attack false negatives (attacks predicted benign): `23649`
- confusion (tn,fp,fn,tp): `1024897, 6640, 23649, 388587`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.956879`
- macro-F1 on attack rows (all 14 classes): `0.850947`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 0.9999 | 0.9999 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9999 | 0.9856 | 0.9927 | 86401 |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Hulk` | 0.9857 | 0.9998 | 0.9927 | 69514 |
| `DoS-SlowHTTPTest` | 0.7406 | 0.4449 | 0.5559 | 20941 |
| `DoS-GoldenEye` | 0.9977 | 0.8379 | 0.9108 | 6127 |
| `DoS-Slowloris` | 0.9731 | 0.9909 | 0.9819 | 1642 |
| `Bot` | 0.9643 | 0.9994 | 0.9815 | 42717 |
| `FTP-BruteForce` | 0.6882 | 0.8873 | 0.7752 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9966 | 0.9784 | 0.9875 | 24489 |
| `Web-BruteForce` | 0.7625 | 0.6354 | 0.6932 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.5333 | 0.6667 | 0.5926 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.7434279126924013`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Slowloris` | 0.9731 | 0.9909 | 0.9819 | 1642 |
| `Web-BruteForce` | 0.7625 | 0.6354 | 0.6932 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.5333 | 0.6667 | 0.5926 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1024897` (0.9936 of 1031537 benign)
- attack detected and correctly attributed: `371606` (0.9014 of 412236 attacks)
- attack detected but wrong family: `16981` (0.0412)
- attack missed as benign: `23649` (0.0574)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed999.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed999`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp02_attack_loss_weight_seed999.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
