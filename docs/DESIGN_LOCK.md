# DESIGN_LOCK.md

## 1. Final Project Title

Secure, Robust, and Explainable Federated Intrusion Detection System

## 2. Purpose of This Design Lock

This document freezes the V2 direction before implementation begins. Its purpose
is to prevent old week-by-week confusion from recurring and to keep all future
work aligned with one clean project architecture, one honest dataset strategy,
and one reproducible implementation path.

## 3. Current Project State

- V1 is complete through corrected final Week 9.
- Week 10 is not completed.
- Known Week 10 issue: official UNSW-NB15 is incompatible with the frozen
  CICIDS2018 pipeline because the feature schemas and labels differ.
- V2 is a clean rebuild, not a patch of V1.

## 4. Old V1 Lessons

- Week 3 CNN checkpoints are not final.
- V6 ensemble is not final.
- `super_cnn_best.pt` is the old Week 9 reference checkpoint only.
- Old V1 Week 5 and Week 7 extras are useful concepts, but must be rebuilt
  cleanly into V2 modules.
- Old V1 became confusing because models, experiments, scripts, and results
  accumulated week by week.

## 5. Final Dataset Strategy

- CICIDS2018
- UNSW-NB15
- Binary Benign vs Attack task
- Dataset-specific adapters
- Dataset-specific preprocessors
- No direct forced CICIDS-to-UNSW frozen-model evaluation
- No fake generalization claim

## 6. Final Model Strategy

V2 uses one final architecture: SecureIDSNet.

The final deliverable will use two dataset-specific final checkpoints:

- `models/final/final_cicids_binary.pt`
- `models/final/final_unsw_binary.pt`

The architecture is the shared neural network design. A checkpoint is the saved
set of trained weights for a specific dataset and task. A preprocessing adapter is
the dataset-specific transformation path that maps raw or cleaned dataset records
into the feature representation expected by that dataset's checkpoint.

## 7. V2 Architecture

- Dataset Layer
- Preprocessing Layer
- Model Layer
- Federated Learning Layer
- Secure Communication Layer
- Gradient Trust and Audit Layer
- Byzantine Attack Layer
- Robust Aggregation Layer
- XAI Layer
- Streamlit UI/Demo Layer
- CLI/Reproducibility Layer

## 8. Core Modules and Folder Rules

- `configs/`: configuration files for datasets, preprocessing, training,
  federated runs, security settings, and reproducibility.
- `data/raw/`: local raw datasets only. Raw datasets must not be committed.
- `data/interim/`: intermediate cleaned or staged data outputs. These are
  generated artifacts and must not be committed.
- `data/processed/`: final processed arrays, tables, or splits produced by
  preprocessing. These are generated artifacts and must not be committed.
- `data/audits/`: dataset schema audits, label audits, leakage checks, and other
  data validation outputs.
- `secureids/`: main Python package for all reusable V2 source code.
- `dashboard/`: Streamlit dashboard and professor demo entry point.
- `experiments/`: reproducible experiment entry points and run definitions.
- `models/final/`: approved final model checkpoints only.
- `models/checkpoints/`: non-final training checkpoints and recovery checkpoints.
- `results/final/`: final approved metrics, summaries, and deliverable outputs.
- `results/audits/`: audit logs and validation outputs from approved runs.
- `results/figures/`: generated figures for reports, slides, and the dashboard.
- `results/xai/`: generated explainability outputs.
- `results/logs/`: run logs, audit logs, and reproducibility logs.
- `tests/`: automated tests for adapters, preprocessing, models, aggregation,
  security checks, and CLI behavior.
- `docs/`: design documents, reproducibility notes, and final project
  documentation.

Draft or scratch work belongs outside the final V2 project in
`C:\IDS\IDS_V2\draft`.

## 9. Core Required Features

- CICIDS2018 adapter
- UNSW-NB15 adapter
- dataset schema audit
- binary label mapping
- leakage-safe preprocessing
- saved preprocessors
- centralized training
- federated FedAvg training
- TLS evidence
- SHA-256 gradient integrity
- secure aggregator
- audit logging
- accept/reject tracking
- anomaly detection
- sign-flip attack
- Gaussian noise attack
- scaling attack
- Trimmed Mean aggregation
- attack diagnostics
- overhead measurement
- XAI outputs
- Streamlit dashboard
- reproducibility documentation

## 10. Optional Features

The following features are optional and must not delay or confuse the core
project:

- differential privacy
- privacy-utility table
- suspicion dashboard
- full multi-seed reruns
- Byzantine threshold sweep
- multiclass extensions

## 11. XAI Plan

Permutation importance is the required stable baseline for explainability.

The XAI layer must include:

- local benign explanation
- local attack explanation
- top feature charts
- Integrated Gradients optional if stable
- SHAP optional if practical

Required future outputs:

- `results/final/xai/cicids_global_feature_importance.csv`
- `results/final/xai/unsw_global_feature_importance.csv`
- `results/final/xai/cicids_top_features.png`
- `results/final/xai/unsw_top_features.png`
- `results/final/xai/cicids_local_benign_example.md`
- `results/final/xai/cicids_local_attack_example.md`
- `results/final/xai/unsw_local_benign_example.md`
- `results/final/xai/unsw_local_attack_example.md`
- `results/final/xai/xai_summary.md`

## 12. Streamlit UI Plan

The Streamlit UI will include these tabs:

- Project Overview
- Dataset Audit
- Prediction Demo
- Federated Security Results
- Byzantine Attack Defense
- XAI Explanation
- Reproducibility / Logs

The UI is the main professor demo. It must not run full training live. The UI
loads saved models, preprocessors, samples, CSVs, figures, and XAI outputs.

## 13. Final Presentation Plan

The 10-minute story:

- problem
- datasets/task
- architecture
- security result
- UI prediction demo
- XAI
- UNSW compatibility handled honestly
- conclusion

## 14. No-Fake-Results Policy

- Do not force UNSW-NB15 into CICIDS2018 model.
- Do not claim incompatible multiclass outputs.
- Do not refit scalers/encoders on test data.
- Do not tune on test.
- Do not report placeholder metrics as real.
- Every final result must be reproducible from scripts/configs.
- Failed or blocked experiments must be reported honestly.

## 15. Safe Reuse of Old V1 Work

- V1 is read-only reference.
- Reuse stable concepts/code only after review.
- Do not copy old messy structure.
- Do not import old private keys/certs.
- Do not treat old Week 3/V6 models as final.
- Week 5 extras should become secure communication/trust/audit modules.
- Week 7 extras should become attack/detection/threshold/recovery modules.

## 16. Git and GitHub Policy

- Do not push to GitHub.
- Do not create PRs.
- Do not create branches unless approved.
- Local commits only if explicitly approved.
- Do not commit raw datasets, private keys, certs, venv, caches, large generated
  artifacts, or scratch files.
- Before final push, show git status, exact files to be committed, and ask the
  user for explicit final approval.

## 17. Approval Gate

No heavy implementation begins until `DESIGN_LOCK.md` is reviewed and approved by
the user.
