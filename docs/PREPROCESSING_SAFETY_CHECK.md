# PREPROCESSING_SAFETY_CHECK.md

## 1. Purpose

This document records the final preprocessing safety gate before centralized training design. It inspects processed feature names, manifests, split summaries, preprocessor artifacts, and processed array metadata without running training or model evaluation.

## 2. Files Inspected

### CICIDS2018

- Feature names: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\feature_names.json`
- Preprocessing manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\preprocessing_manifest.json`
- Split summary: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\split_summary.json`
- Preprocessor artifact: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\preprocessors\cicids2018_binary_preprocessor.joblib`
- Processed arrays checked with `numpy.load(..., mmap_mode="r")`: `X_train.npy`, `X_val.npy`, `X_test.npy`, `y_train.npy`, `y_val.npy`, `y_test.npy`

### UNSW-NB15

- Feature names: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\unsw_nb15\binary\feature_names.json`
- Preprocessing manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\unsw_nb15\binary\preprocessing_manifest.json`
- Split summary: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\unsw_nb15\binary\split_summary.json`
- Preprocessor artifact: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\preprocessors\unsw_nb15_binary_preprocessor.joblib`
- Processed arrays checked with `numpy.load(..., mmap_mode="r")`: `X_train.npy`, `X_val.npy`, `X_test.npy`, `y_train.npy`, `y_val.npy`, `y_test.npy`

## 3. CICIDS2018 Safety Check

- Feature count: 77
- Feature names source: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\cicids2018\binary\feature_names.json`
- Artifact feature names match processed feature names: `true`
- Forbidden/leakage scan status: no matches
- Exact forbidden matches: none
- Suspicious matches: none
- All processed feature arrays are numeric, 2D, and finite: `true`
- Labels are binary across train/validation/test: `true`
- Train-only fitting confirmed: `true`
- Test set not used for fitting confirmed: `true`

Array metadata:

| Split | X shape | X dtype | finite | y shape | y dtype | labels |
| --- | ---: | --- | --- | ---: | --- | --- |
| train | [6737603, 77] | float32 | true | [6737603] | int64 | [0, 1] |
| val | [1443772, 77] | float32 | true | [1443772] | int64 | [0, 1] |
| test | [1443773, 77] | float32 | true | [1443773] | int64 | [0, 1] |

Port identifier policy note: source/destination port identifier fields are excluded from the CICIDS2018 final feature set to reduce leakage and endpoint/service identifier risk.
`Dst Port` and configured source/destination port variants are absent from final feature names.

- Final status: `PASS`

## 4. UNSW-NB15 Safety Check

- Feature count: 190
- Feature names source: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\processed\unsw_nb15\binary\feature_names.json`
- Artifact feature names match processed feature names: `true`
- Forbidden/leakage scan status: no matches
- Exact forbidden matches: none
- Suspicious matches: none
- All processed feature arrays are numeric, 2D, and finite: `true`
- Labels are binary across train/validation/test: `true`
- Train-only fitting confirmed: `true`
- Test set not used for fitting confirmed: `true`

Array metadata:

| Split | X shape | X dtype | finite | y shape | y dtype | labels |
| --- | ---: | --- | --- | ---: | --- | --- |
| train | [69982, 190] | float32 | true | [69982] | int64 | [0, 1] |
| val | [12350, 190] | float32 | true | [12350] | int64 | [0, 1] |
| test | [175341, 190] | float32 | true | [175341] | int64 | [0, 1] |

Required removals checked: `id`, `label`, and `attack_cat` are not present in final feature names.
No direct label-derived or attack-name-derived UNSW feature names were found.

- Final status: `PASS`

## 5. Train-Only Fitting Evidence

CICIDS2018:

- Imputer/scaler fitting policy: `True` / `True` from artifact config snapshot.
- Memory strategy evidence: Chunked CSV reading with .npy memmap outputs; train-fitted median imputation and standard scaling applied in place.
- Split strategy: `stratified_random`; test split is treated as final holdout.

UNSW-NB15:

- Encoder/imputer/scaler fitting policy: `True` / `True` / `True` from artifact config snapshot.
- Memory strategy evidence: Official UNSW training/testing files processed in memory; validation split created only from official training data.
- Split strategy: `official_train_test_with_validation_from_train`; official testing file is treated as final holdout.

Validation and test splits are documented as transformation-only paths using train-fitted artifacts. No model training or evaluation was run during this safety check.

## 6. Overall Decision

PASS: preprocessing is safe for centralized training design.

## 7. Safety Confirmation

- No training was run.
- No checkpoints were created.
- No model metrics were created.
- V1 was not modified.
- No Git commit or push happened.
