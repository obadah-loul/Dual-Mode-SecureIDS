# DATASET_SCHEMA_AUDIT.md

## Purpose

The dataset audit framework has been created for the clean V2 rebuild.
It inspects raw CSV inventories, headers, small samples, candidate label
columns, likely numeric/categorical columns, and sample missing values
before any preprocessing or training begins.

## Expected Raw Data Locations

- `data/raw/cicids2018`
- `data/raw/unsw_nb15`

## Audit Policy

- CICIDS2018 and UNSW-NB15 are audited separately.
- The audit reads CSV headers and small samples only.
- No final audit results exist until raw files are placed in V2
  `data/raw` and the audit command is run.
- No training or preprocessing has been performed.
- No row counts, label counts, or performance metrics are invented.

## Current Status

Raw CSV files were found and inspected with header/sample-only
auditing. These are not final preprocessing outputs or model
performance results.

## File Inventory Summary

| Dataset | Path | Status | Size |
| --- | --- | --- | --- |
| cicids2018 | `data\raw\cicids2018\Bot.csv` | found | 348.2 MB |
| cicids2018 | `data\raw\cicids2018\Brute Force -Web.csv` | found | 752.4 KB |
| cicids2018 | `data\raw\cicids2018\Brute Force -XSS.csv` | found | 267.0 KB |
| cicids2018 | `data\raw\cicids2018\DDOS attack-HOIC.csv` | found | 766.8 MB |
| cicids2018 | `data\raw\cicids2018\DDOS attack-LOIC-UDP.csv` | found | 2.0 MB |
| cicids2018 | `data\raw\cicids2018\DDoS attacks-LOIC-HTTP.csv` | found | 766.3 MB |
| cicids2018 | `data\raw\cicids2018\DoS attacks-GoldenEye.csv` | found | 49.9 MB |
| cicids2018 | `data\raw\cicids2018\DoS attacks-Hulk.csv` | found | 501.7 MB |
| cicids2018 | `data\raw\cicids2018\DoS attacks-SlowHTTPTest.csv` | found | 148.2 MB |
| cicids2018 | `data\raw\cicids2018\DoS attacks-Slowloris.csv` | found | 13.5 MB |
| cicids2018 | `data\raw\cicids2018\FTP-BruteForce.csv` | found | 207.9 MB |
| cicids2018 | `data\raw\cicids2018\Infilteration.csv` | found | 185.1 MB |
| cicids2018 | `data\raw\cicids2018\SQL Injection.csv` | found | 102.0 KB |
| cicids2018 | `data\raw\cicids2018\SSH-Bruteforce.csv` | found | 220.5 MB |
| unsw_nb15 | `data\raw\unsw_nb15\UNSW_NB15_testing-set.csv` | found | 30.8 MB |
| unsw_nb15 | `data\raw\unsw_nb15\UNSW_NB15_training-set.csv` | found | 14.7 MB |

## CICIDS2018 Schema Audit

| File | Status | Columns | Label Column | Sample Rows |
| --- | --- | ---: | --- | ---: |
| `data\raw\cicids2018\Bot.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\Brute Force -Web.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\Brute Force -XSS.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DDOS attack-HOIC.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DDOS attack-LOIC-UDP.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DDoS attacks-LOIC-HTTP.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DoS attacks-GoldenEye.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DoS attacks-Hulk.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DoS attacks-SlowHTTPTest.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\DoS attacks-Slowloris.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\FTP-BruteForce.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\Infilteration.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\SQL Injection.csv` | ok | 79 | Label | 50 |
| `data\raw\cicids2018\SSH-Bruteforce.csv` | ok | 79 | Label | 50 |

## UNSW-NB15 Schema Audit

| File | Status | Columns | Label Column | Sample Rows |
| --- | --- | ---: | --- | ---: |
| `data\raw\unsw_nb15\UNSW_NB15_testing-set.csv` | ok | 45 | label | 50 |
| `data\raw\unsw_nb15\UNSW_NB15_training-set.csv` | ok | 45 | label | 50 |

## Next Step

Place the official raw CICIDS2018 and UNSW-NB15 files under the expected
V2 raw-data directories, then run:

```bash
python -m secureids.cli audit-data --dataset all
```
