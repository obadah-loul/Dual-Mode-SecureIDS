# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-24T21:55:31.942545+00:00`

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
- Best epoch: `5` (epochs run: `10`)
- Best validation hierarchical score: `0.897248`
- Validation binary macro-F1 (best epoch): `0.9745745178832511`
- Validation attack-family macro-F1 (best epoch): `0.819922345207341`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `501,391`

## Final test - Head 1 (binary)

- accuracy: `0.979397`
- precision: `0.984628`
- recall: `0.942557`
- f1: `0.963134`
- macro_f1: `0.974419`
- attack false negatives (attacks predicted benign): `23680`
- confusion (tn,fp,fn,tp): `1025471, 6066, 23680, 388556`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.962228`
- macro-F1 on attack rows (all 14 classes): `0.846994`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 1.0000 | 0.9999 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9988 | 0.9985 | 0.9986 | 86401 |
| `DDoS-LOIC-UDP` | 0.6931 | 1.0000 | 0.8187 | 271 |
| `DoS-Hulk` | 1.0000 | 0.9997 | 0.9998 | 69514 |
| `DoS-SlowHTTPTest` | 0.7576 | 0.4315 | 0.5498 | 20941 |
| `DoS-GoldenEye` | 0.9974 | 0.9990 | 0.9982 | 6127 |
| `DoS-Slowloris` | 0.9645 | 0.9921 | 0.9781 | 1642 |
| `Bot` | 0.9956 | 0.9985 | 0.9971 | 42717 |
| `FTP-BruteForce` | 0.6862 | 0.9002 | 0.7788 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9953 | 0.9800 | 0.9876 | 24489 |
| `Web-BruteForce` | 0.3014 | 0.6562 | 0.4131 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.6923 | 0.7500 | 0.7200 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.709622469873287`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.6931 | 1.0000 | 0.8187 | 271 |
| `DoS-Slowloris` | 0.9645 | 0.9921 | 0.9781 | 1642 |
| `Web-BruteForce` | 0.3014 | 0.6562 | 0.4131 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.6923 | 0.7500 | 0.7200 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1025471` (0.9941 of 1031537 benign)
- attack detected and correctly attributed: `373494` (0.9060 of 412236 attacks)
- attack detected but wrong family: `15062` (0.0365)
- attack missed as benign: `23680` (0.0574)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp01_head2_mlp_capacity.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp01_head2_mlp_capacity`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp01_head2_mlp_capacity.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
