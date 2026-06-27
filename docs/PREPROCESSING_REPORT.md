# PREPROCESSING_REPORT.md

## 1. Purpose

This report documents the completed preprocessing execution for the binary
IDS datasets. It records dataset-specific decisions, output artifacts,
split sizes, label distributions, leakage checks, and safety boundaries.

## 2. Preprocessing Policy

- CICIDS2018 and UNSW-NB15 use dataset-specific preprocessing pipelines.
- Scalers, imputers, and encoders are fitted only on training data.
- Validation and test splits are transformed only with train-fitted artifacts.
- No model training or model evaluation is performed by preprocessing.
- No model performance metrics are produced here.

## 3. cicids2018 Outputs

Input files:

- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\Bot.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\Brute Force -Web.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\Brute Force -XSS.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DDOS attack-HOIC.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DDOS attack-LOIC-UDP.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DDoS attacks-LOIC-HTTP.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DoS attacks-GoldenEye.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DoS attacks-Hulk.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DoS attacks-SlowHTTPTest.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\DoS attacks-Slowloris.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\FTP-BruteForce.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\Infilteration.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\SQL Injection.csv`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018\SSH-Bruteforce.csv`

- Output directory: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary`
- Preprocessor artifact: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\preprocessors\cicids2018_binary_preprocessor.joblib`
- Feature count: 77
- Memory strategy: Chunked CSV reading with .npy memmap outputs; train-fitted median imputation and standard scaling applied in place.

Split sizes and label distributions:

| Split | Rows | Label 0 | Label 1 |
| --- | ---: | ---: | ---: |
| train | 6737603 | 4813839 | 1923764 |
| val | 1443772 | 1031537 | 412235 |
| test | 1443773 | 1031537 | 412236 |

Verification:

- X arrays are 2D: `true`
- y arrays are 1D: `true`
- Feature counts are consistent: `true`
- Feature names match array dimension: `true`
- Labels contain only 0 and 1: `true`
- Target/leakage columns removed: `true`

Output files:

- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\X_train.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\y_train.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\X_val.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\y_val.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\X_test.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\y_test.npy`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\feature_names.json`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\label_mapping.json`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\split_summary.json`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\preprocessing_manifest.json`
- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\preprocessors\cicids2018_binary_preprocessor.joblib`

## 4. Downstream Compatibility

- Training can load NumPy arrays, feature names, label mapping, split
  summaries, manifests, and dataset-specific preprocessor artifacts.
- Federated learning can consume dataset-specific train/validation/test
  arrays and class-distribution metadata.
- XAI can use stable `feature_names.json` ordering for each dataset.
- The dashboard can read manifests, split summaries, label mappings, and
  later model/XAI artifacts without converting preprocessing outputs.

## 5. Safety Confirmation

- No training was run.
- No model checkpoints were created.
- No model performance metrics were created.
- V1 was not modified.
- No Git commit was created.
- No GitHub push occurred.
