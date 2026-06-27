# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-25T06:26:40.343748+00:00`

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
- Best epoch: `3` (epochs run: `8`)
- Best validation hierarchical score: `0.908071`
- Validation binary macro-F1 (best epoch): `0.9719183853466928`
- Validation attack-family macro-F1 (best epoch): `0.8442228168257088`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.977116`
- precision: `0.973176`
- recall: `0.945927`
- f1: `0.959358`
- macro_f1: `0.971716`
- attack false negatives (attacks predicted benign): `22291`
- confusion (tn,fp,fn,tp): `1020789, 10748, 22291, 389945`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.960816`
- macro-F1 on attack rows (all 14 classes): `0.863955`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9998 | 0.9998 | 0.9998 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9997 | 0.9918 | 0.9957 | 86401 |
| `DDoS-LOIC-UDP` | 0.6967 | 1.0000 | 0.8212 | 271 |
| `DoS-Hulk` | 1.0000 | 0.9997 | 0.9998 | 69514 |
| `DoS-SlowHTTPTest` | 0.6961 | 0.5224 | 0.5969 | 20941 |
| `DoS-GoldenEye` | 0.9980 | 0.9984 | 0.9982 | 6127 |
| `DoS-Slowloris` | 0.9708 | 0.9915 | 0.9810 | 1642 |
| `Bot` | 0.9793 | 0.9993 | 0.9892 | 42717 |
| `FTP-BruteForce` | 0.7071 | 0.8351 | 0.7658 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9916 | 0.9789 | 0.9852 | 24489 |
| `Web-BruteForce` | 0.7262 | 0.6354 | 0.6778 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.6667 | 0.6667 | 0.6667 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.7529713525736423`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.6967 | 1.0000 | 0.8212 | 271 |
| `DoS-Slowloris` | 0.9708 | 0.9915 | 0.9810 | 1642 |
| `Web-BruteForce` | 0.7262 | 0.6354 | 0.6778 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.6667 | 0.6667 | 0.6667 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1020789` (0.9896 of 1031537 benign)
- attack detected and correctly attributed: `374413` (0.9082 of 412236 attacks)
- attack detected but wrong family: `15532` (0.0377)
- attack missed as benign: `22291` (0.0541)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed42.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed42`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp02_attack_loss_weight_seed42.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
