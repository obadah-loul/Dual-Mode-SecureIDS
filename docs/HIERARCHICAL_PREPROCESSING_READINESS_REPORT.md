# Hierarchical Preprocessing Readiness Report

Status: `Task A4 complete - validation/readiness only`

## 1. Readiness Decision

- cicids2018: `PASS` and ready for hierarchical model implementation.
- unsw_nb15: `PASS` and ready for hierarchical model implementation.

- Blocking issues: `0`
- Warnings: `0`

## 2. Output Paths

- `results/audits/hierarchical_preprocessing_readiness_cicids2018.json`
- `results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json`
- `docs/HIERARCHICAL_PREPROCESSING_READINESS_REPORT.md`

## 3. Dataset Summaries

### cicids2018

- Status: `PASS`
- Ready for model implementation: `true`
- Expected feature dimension: `77`
- Detected feature dimension: `77`
- Blocking issues: `0`
- Warnings: `0`

| Split | X shape | Binary 0 | Binary 1 | Attack-family classes present |
| --- | --- | ---: | ---: | ---: |
| train | `(6737603, 77)` | 4813839 | 1923764 | 14 |
| val | `(1443772, 77)` | 1031537 | 412235 | 14 |
| test | `(1443773, 77)` | 1031537 | 412236 | 14 |

Attack-family total distribution:

- `DDoS-HOIC`: 686012
- `DDoS-LOIC-HTTP`: 576191
- `DDoS-LOIC-UDP`: 1730
- `DoS-Hulk`: 461912
- `DoS-SlowHTTPTest`: 139890
- `DoS-GoldenEye`: 41508
- `DoS-Slowloris`: 10990
- `Bot`: 286191
- `FTP-BruteForce`: 193360
- `SSH-Bruteforce`: 187589
- `Infilteration / Infiltration`: 161934
- `Web-BruteForce`: 611
- `Web-XSS`: 230
- `SQL-Injection`: 87

Rare-class summary:

- `DDOS attack-LOIC-UDP` -> `DDoS-LOIC-UDP` (family count: 1730)
- `DoS attacks-Slowloris` -> `DoS-Slowloris` (family count: 10990)
- `Brute Force -Web` -> `Web-BruteForce` (family count: 611)
- `Brute Force -XSS` -> `Web-XSS` (family count: 230)
- `SQL Injection` -> `SQL-Injection` (family count: 87)

### unsw_nb15

- Status: `PASS`
- Ready for model implementation: `true`
- Expected feature dimension: `192`
- Detected feature dimension: `192`
- Blocking issues: `0`
- Warnings: `0`

| Split | X shape | Binary 0 | Binary 1 | Attack-family classes present |
| --- | --- | ---: | ---: | ---: |
| train | `(149039, 192)` | 47600 | 101439 | 9 |
| val | `(26302, 192)` | 8400 | 17902 | 9 |
| test | `(82332, 192)` | 37000 | 45332 | 9 |

Attack-family total distribution:

- `Generic`: 58871
- `Exploits`: 44525
- `Fuzzers`: 24246
- `DoS`: 16353
- `Reconnaissance`: 13987
- `Analysis`: 2677
- `Backdoor`: 2329
- `Shellcode`: 1511
- `Worms`: 174

Rare-class summary:

- `Shellcode` -> `Shellcode` (family count: 1511)
- `Worms` -> `Worms` (family count: 174)

## 4. Mapping And Manifest Validation

- Dataset-specific Head 2 mappings were validated.
- Common superclass mappings are reporting-only and are not training targets.
- No fake shared CICIDS/UNSW multiclass label list was created.
- Manifests record dataset name, hierarchical task type, input dimension,
  taxonomy config path, preprocessing config path, no-test-tuning, and
  no-scaler/encoder-refit flags.

## 5. Preservation And Safety

- Existing binary processed outputs remain present.
- Existing binary centralized checkpoints remain present.
- Existing binary FedAvg checkpoints remain present.
- No advanced hierarchical model code exists.
- No hierarchical checkpoints exist.
- No hierarchical training metrics exist under `results/final` or `results/federated`.
- No security, attack, Trimmed Mean, or XAI result output files checked by A4 exist.
- Pre-existing skeleton dashboard/security/attack/XAI placeholders were not extended by A4.

## 6. What Was Not Done

- No model code was implemented.
- No model training or evaluation was run.
- No checkpoints or model metrics were created.
- No calibration/routing implementation was created.
- No security, Byzantine attack, Trimmed Mean, XAI, or dashboard implementation work was started by A4.
- V1 was not modified.

## 7. Recommendation

It is safe to proceed after main-review approval.

Recommended next step: Task A5 should be
`SecureIDS-HierarchicalAdvancedNet` architecture implementation design/code
skeleton with smoke-only forward-pass validation, not full training yet.
