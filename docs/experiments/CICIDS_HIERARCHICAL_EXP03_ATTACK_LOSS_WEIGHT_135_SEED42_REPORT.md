# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-25T09:37:08.834709+00:00`

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
- Best epoch: `12` (epochs run: `17`)
- Best validation hierarchical score: `0.901976`
- Validation binary macro-F1 (best epoch): `0.9756239396687985`
- Validation attack-family macro-F1 (best epoch): `0.8283281719610163`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.980217`
- precision: `0.982252`
- recall: `0.947841`
- f1: `0.964740`
- macro_f1: `0.975496`
- attack false negatives (attacks predicted benign): `21502`
- confusion (tn,fp,fn,tp): `1024477, 7060, 21502, 390734`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.963603`
- macro-F1 on attack rows (all 14 classes): `0.834674`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 1.0000 | 0.9999 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9997 | 0.9945 | 0.9971 | 86401 |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Hulk` | 0.9995 | 0.9998 | 0.9996 | 69514 |
| `DoS-SlowHTTPTest` | 0.7357 | 0.5190 | 0.6086 | 20941 |
| `DoS-GoldenEye` | 0.9980 | 0.9938 | 0.9959 | 6127 |
| `DoS-Slowloris` | 0.9951 | 0.9921 | 0.9936 | 1642 |
| `Bot` | 0.9862 | 0.9994 | 0.9928 | 42717 |
| `FTP-BruteForce` | 0.7129 | 0.8651 | 0.7817 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9947 | 0.9836 | 0.9891 | 24489 |
| `Web-BruteForce` | 0.8243 | 0.6354 | 0.7176 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.0909 | 0.6667 | 0.1600 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.664142565796166`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Slowloris` | 0.9951 | 0.9921 | 0.9936 | 1642 |
| `Web-BruteForce` | 0.8243 | 0.6354 | 0.7176 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.0909 | 0.6667 | 0.1600 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1024477` (0.9932 of 1031537 benign)
- attack detected and correctly attributed: `376170` (0.9125 of 412236 attacks)
- attack detected but wrong family: `14564` (0.0353)
- attack missed as benign: `21502` (0.0522)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp03_attack_loss_weight_135_seed42.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp03_attack_loss_weight_135_seed42`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_135_seed42.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
