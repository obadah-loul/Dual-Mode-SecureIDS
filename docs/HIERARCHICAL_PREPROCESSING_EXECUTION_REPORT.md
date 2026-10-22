> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Preprocessing Execution Report

Status: `Task A4.5 complete - CICIDS Head 2 labels regenerated only`

## 1. What Changed

Task A4.5 revised only the CICIDS2018 Head 2 taxonomy and regenerated only the
CICIDS hierarchical preprocessing outputs.

Reason:

- A4 accepted the preprocessing readiness state.
- A4 also showed that the old CICIDS 8-class family mapping hid
  `DoS attacks-Slowloris` inside `DoS` and `DDOS attack-LOIC-UDP` inside
  `DDoS`.
- The final advanced goal requires rare/raw attack-type preservation where
  scientifically possible.

The CICIDS Head 2 mapping is now a raw-preserving 14-class mapping. UNSW-NB15
taxonomy and hierarchical outputs were not regenerated and remain unchanged.

## 2. Regenerated Output Group

- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\hierarchical`
- `results/audits/hierarchical_preprocessing_audit_cicids2018.json`

UNSW output group unchanged:

- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\unsw_nb15\hierarchical`
- `results/audits/hierarchical_preprocessing_audit_unsw_nb15.json`

## 3. CICIDS2018 Summary After A4.5

- Status: `PASS`
- Feature dimension: `77`
- Expected feature dimension: `77`
- Head 2 attack-type class count: `14`
- Ignore index: `-1`
- Mask values: benign/normal `0`, attack `1`
- Binary labels exactly match accepted binary `y_*` files.
- Common superclasses remain reporting-only.
- No fake shared CICIDS/UNSW multiclass label list was created.

| Split | X shape | y_binary | y_attack_family | mask | binary 0 | binary 1 | attack classes present | mask valid |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| train | `(6737603, 77)` | `(6737603,)` | `(6737603,)` | `(6737603,)` | 4813839 | 1923764 | 14 | `true` |
| val | `(1443772, 77)` | `(1443772,)` | `(1443772,)` | `(1443772,)` | 1031537 | 412235 | 14 | `true` |
| test | `(1443773, 77)` | `(1443773,)` | `(1443773,)` | `(1443773,)` | 1031537 | 412236 | 14 | `true` |

## 4. Final CICIDS Head 2 Class Supports

| Head 2 class | Support |
| --- | ---: |
| `DDoS-HOIC` | 686012 |
| `DDoS-LOIC-HTTP` | 576191 |
| `DDoS-LOIC-UDP` | 1730 |
| `DoS-Hulk` | 461912 |
| `DoS-SlowHTTPTest` | 139890 |
| `DoS-GoldenEye` | 41508 |
| `DoS-Slowloris` | 10990 |
| `Bot` | 286191 |
| `FTP-BruteForce` | 193360 |
| `SSH-Bruteforce` | 187589 |
| `Infilteration / Infiltration` | 161934 |
| `Web-BruteForce` | 611 |
| `Web-XSS` | 230 |
| `SQL-Injection` | 87 |

## 5. Rare And Weak/Hard Class Preservation

Rare CICIDS raw labels now preserved as separate Head 2 classes:

- `DDOS attack-LOIC-UDP` -> `DDoS-LOIC-UDP`
- `DoS attacks-Slowloris` -> `DoS-Slowloris`
- `Brute Force -Web` -> `Web-BruteForce`
- `Brute Force -XSS` -> `Web-XSS`
- `SQL Injection` -> `SQL-Injection`

Weak/hard or security-important classes preserved separately:

- `FTP-BruteForce`
- `Infilteration / Infiltration`
- `DoS-SlowHTTPTest`

## 6. What Was Not Done

- No hierarchical model code was created.
- No `SecureIDS-HierarchicalAdvancedNet` implementation was created.
- No centralized or federated hierarchical training was run.
- No model evaluation or model metrics were created.
- No checkpoints were created.
- No calibration, routing, security, attacks, Trimmed Mean, XAI, or dashboard
  work was started.
- V1 was not modified.

## 7. Preservation

- Existing CICIDS binary processed outputs were not overwritten.
- Existing UNSW binary processed outputs were not overwritten.
- Existing UNSW hierarchical outputs were not overwritten.
- Existing binary centralized/FedAvg checkpoints and result artifacts were not
  modified.
- No scaler, encoder, or imputer was refit.
- No test-set tuning was performed.

## 8. Command Run

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m secureids.cli preprocess-hierarchical --dataset cicids --execute --overwrite
```

## 9. Recommendation

After main-review approval of A4.5, the next step should still be an A5
architecture implementation design/code skeleton with smoke-only forward-pass
validation. Do not jump directly to full hierarchical training.
