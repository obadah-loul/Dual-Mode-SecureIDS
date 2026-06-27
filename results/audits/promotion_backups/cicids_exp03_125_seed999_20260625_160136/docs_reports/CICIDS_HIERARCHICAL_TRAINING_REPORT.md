# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-24T20:22:00.062147+00:00`

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
- Best validation hierarchical score: `0.894858`
- Validation binary macro-F1 (best epoch): `0.9723621448611364`
- Validation attack-family macro-F1 (best epoch): `0.8173542240528427`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.977486`
- precision: `0.974214`
- recall: `0.946193`
- f1: `0.960000`
- macro_f1: `0.972167`
- attack false negatives (attacks predicted benign): `22181`
- confusion (tn,fp,fn,tp): `1021213, 10324, 22181, 390055`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.961306`
- macro-F1 on attack rows (all 14 classes): `0.849111`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 0.9999 | 0.9999 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9997 | 0.9950 | 0.9973 | 86401 |
| `DDoS-LOIC-UDP` | 0.6967 | 1.0000 | 0.8212 | 271 |
| `DoS-Hulk` | 0.9995 | 0.9997 | 0.9996 | 69514 |
| `DoS-SlowHTTPTest` | 0.7554 | 0.4367 | 0.5535 | 20941 |
| `DoS-GoldenEye` | 0.9979 | 0.9933 | 0.9956 | 6127 |
| `DoS-Slowloris` | 0.9725 | 0.9915 | 0.9819 | 1642 |
| `Bot` | 0.9862 | 0.9994 | 0.9927 | 42717 |
| `FTP-BruteForce` | 0.6876 | 0.8977 | 0.7787 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9954 | 0.9755 | 0.9854 | 24489 |
| `Web-BruteForce` | 0.2400 | 0.7500 | 0.3636 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 1.0000 | 0.6667 | 0.8000 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.7169872427532258`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.6967 | 1.0000 | 0.8212 | 271 |
| `DoS-Slowloris` | 0.9725 | 0.9915 | 0.9819 | 1642 |
| `Web-BruteForce` | 0.2400 | 0.7500 | 0.3636 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 1.0000 | 0.6667 | 0.8000 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1021213` (0.9900 of 1031537 benign)
- attack detected and correctly attributed: `374726` (0.9090 of 412236 attacks)
- attack detected but wrong family: `15329` (0.0372)
- attack missed as benign: `22181` (0.0538)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\final_cicids_hierarchical.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\cicids`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids2018.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
