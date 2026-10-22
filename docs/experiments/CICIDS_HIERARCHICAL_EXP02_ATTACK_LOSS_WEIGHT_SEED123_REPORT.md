> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (CICIDS2018)

Status: `Real centralized hierarchical training (CICIDS2018)`

Generated UTC: `2026-06-25T07:09:45.818508+00:00`

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
- Best validation hierarchical score: `0.912697`
- Validation binary macro-F1 (best epoch): `0.9742062969808583`
- Validation attack-family macro-F1 (best epoch): `0.851188512713987`
- Train class distribution (binary): `{'0': 4813839, '1': 1923764}`
- Model parameters: `484,623`

## Final test - Head 1 (binary)

- accuracy: `0.979038`
- precision: `0.983110`
- recall: `0.942780`
- f1: `0.962523`
- macro_f1: `0.973986`
- attack false negatives (attacks predicted benign): `23588`
- confusion (tn,fp,fn,tp): `1024860, 6677, 23588, 388648`
- n_samples: `1443773`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.962230`
- macro-F1 on attack rows (all 14 classes): `0.864022`
- attack rows evaluated: `412236`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-HOIC` | 0.9999 | 0.9998 | 0.9998 | 102708 |
| `DDoS-LOIC-HTTP` | 0.9994 | 0.9984 | 0.9989 | 86401 |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Hulk` | 0.9981 | 0.9997 | 0.9989 | 69514 |
| `DoS-SlowHTTPTest` | 0.7577 | 0.4315 | 0.5499 | 20941 |
| `DoS-GoldenEye` | 0.9980 | 0.9778 | 0.9878 | 6127 |
| `DoS-Slowloris` | 0.9714 | 0.9921 | 0.9816 | 1642 |
| `Bot` | 0.9939 | 0.9994 | 0.9966 | 42717 |
| `FTP-BruteForce` | 0.6862 | 0.9002 | 0.7787 | 28928 |
| `SSH-Bruteforce` | 1.0000 | 0.9999 | 0.9999 | 28352 |
| `Infilteration / Infiltration` | 0.9947 | 0.9855 | 0.9901 | 24489 |
| `Web-BruteForce` | 0.8971 | 0.6354 | 0.7439 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.5294 | 0.7500 | 0.6207 | 12 |

## Final test - rare classes

- rare-class macro-F1 (DDoS-LOIC-UDP, DoS-Slowloris, Web-BruteForce, Web-XSS, SQL-Injection): `0.7591366452217286`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `DDoS-LOIC-UDP` | 0.7113 | 1.0000 | 0.8313 | 271 |
| `DoS-Slowloris` | 0.9714 | 0.9921 | 0.9816 | 1642 |
| `Web-BruteForce` | 0.8971 | 0.6354 | 0.7439 | 96 |
| `Web-XSS` | 1.0000 | 0.4474 | 0.6182 | 38 |
| `SQL-Injection` | 0.5294 | 0.7500 | 0.6207 | 12 |

## Final test - end-to-end routing

- benign correctly stopped: `1024860` (0.9935 of 1031537 benign)
- attack detected and correctly attributed: `373492` (0.9060 of 412236 attacks)
- attack detected but wrong family: `15156` (0.0368)
- attack missed as benign: `23588` (0.0572)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed123.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\cicids_hierarchical_exp02_attack_loss_weight_seed123`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_cicids_hierarchical_exp02_attack_loss_weight_seed123.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- V1 not modified. No Git operations.
