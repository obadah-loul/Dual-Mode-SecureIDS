# CENTRALIZED_TRAINING_REPORT.md

## Status: COMBINED CENTRALIZED BASELINE

Centralized (non-federated) baseline training on the shared SecureIDSNet
binary architecture. Each dataset keeps its own preprocessing, input_dim,
checkpoint, and result files; only the model architecture is shared.

- UNSW-NB15: COMPLETED (real results)
- CICIDS2018: COMPLETED (real results)

Report generated (UTC): 2026-06-23T19:00:59.807596+00:00

---

## UNSW-NB15 (input_dim 190)

### Status: COMPLETED (real results)

Dataset: unsw_nb15
Task: binary
Model: SecureIDSNet (single shared binary architecture)
Input dim: 190
Training config: configs\training\unsw_nb15_binary.yaml
Device: cuda (cuda_available=True)
Seed: 42
Best epoch: 12 (epochs run: 17)
Created (UTC): 2026-06-23T18:17:48.486274+00:00

### Data Sizes

- train: X [69982, 190], y [69982]
- val:   X [12350, 190], y [12350]
- test:  X [175341, 190], y [175341]
- train class distribution: {'0': 31450, '1': 38532}
- pos_weight: 0.8162047129658466

### Final Test Metrics (evaluated once, after best validation checkpoint)

- accuracy:  0.887590
- precision: 0.988220
- recall:    0.844915
- f1:        0.910966
- macro_f1:  0.879268
- n_samples: 175341

### Confusion Matrix (label 0 = Benign/Normal, 1 = Attack)

- true 0 / pred 0 (tn): 54798
- true 0 / pred 1 (fp): 1202
- true 1 / pred 0 (fn): 18508
- true 1 / pred 1 (tp): 100833

### Output Artifacts

- checkpoint: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\final_unsw_binary.pt
- history csv: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\unsw_training_history.csv
- test metrics json: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\unsw_test_metrics.json
- confusion matrix csv: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\unsw_confusion_matrix.csv
- training manifest: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\training_manifest_unsw_nb15.json

### Safety Confirmation

- final_checkpoint: true
- test_set_used_for_tuning: false (test evaluated once after best
  validation checkpoint selection)
- preprocessing_safety_check_passed: true
- no fake metrics; all values above are from this real run

---

## CICIDS2018 (input_dim 77)

### Status: COMPLETED (real results)

Dataset: cicids2018
Task: binary
Model: SecureIDSNet (single shared binary architecture)
Input dim: 77
Training config: configs\training\cicids2018_binary.yaml
Device: cuda (cuda_available=True)
Seed: 42
Best epoch: 7 (epochs run: 11)
Created (UTC): 2026-06-23T19:00:59.792904+00:00

### Data Sizes

- train: X [6737603, 77], y [6737603]
- val:   X [1443772, 77], y [1443772]
- test:  X [1443773, 77], y [1443773]
- train class distribution: {'0': 4813839, '1': 1923764}
- pos_weight: 2.5023022574494584

### Final Test Metrics (evaluated once, after best validation checkpoint)

- accuracy:  0.979563
- precision: 0.985292
- recall:    0.942494
- f1:        0.963418
- macro_f1:  0.974619
- n_samples: 1443773

### Confusion Matrix (label 0 = Benign/Normal, 1 = Attack)

- true 0 / pred 0 (tn): 1025737
- true 0 / pred 1 (fp): 5800
- true 1 / pred 0 (fn): 23706
- true 1 / pred 1 (tp): 388530

### Output Artifacts

- checkpoint: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\final_cicids_binary.pt
- history csv: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\cicids_training_history.csv
- test metrics json: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\cicids_test_metrics.json
- confusion matrix csv: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\centralized\cicids_confusion_matrix.csv
- training manifest: C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\training_manifest_cicids2018.json

### Safety Confirmation

- final_checkpoint: true
- test_set_used_for_tuning: false (test evaluated once after best
  validation checkpoint selection)
- preprocessing_safety_check_passed: true
- no fake metrics; all values above are from this real run

---

## Scope (what these runs are NOT)

- No federated learning yet.
- No secure communication / gradient trust / Byzantine / robust aggregation
  yet.
- No XAI yet.
- No dashboard model demo yet.
- No GitHub push.

## Manual Pre-Run Checklist (CICIDS2018 full centralized training)

Before running CICIDS full training, confirm:

- the local .venv is active
- PyTorch is installed and CUDA is available
- processed CICIDS files exist under data/processed/cicids2018/binary
- config input_dim is 77 and feature_names length is 77
- final CICIDS checkpoint models/final/final_cicids_binary.pt does not
  already exist, or pass --overwrite intentionally
- the UNSW checkpoint/results still exist and must not be overwritten
- results/final/centralized exists or will be created cleanly
- no GitHub push is planned for generated artifacts

## Monitoring Advice (CICIDS2018)

- CICIDS is much larger than UNSW (~6.7M training rows); expect a longer run.
- Monitor GPU use in another terminal: nvidia-smi -l 5
- Watch free disk space for the checkpoint and result files.
- Do not close the terminal while training is running.
- If training crashes, inspect partial files before re-running, and do not
  report partial outputs as final.
