> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Dataset Finalization Index

Generated on: 2026-06-25

This index records the ratified dataset-finalization state after review of the wrong-chat process issue. It is documentation and audit only. No training, evaluation, preprocessing rebuild, XAI run, Streamlit launch, checkpoint change, checkpoint copy/replacement, or result-metrics modification is performed by this task.

## CICIDS

Status: finalized and promoted with warnings.

The official CICIDS final hierarchical checkpoint is:

`models/final/final_cicids_hierarchical.pt`

It contains the promoted EXP03 1.25 seed999 model from:

`models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`

Promotion record:

`results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json`

Rollback target:

`results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136/models_final/final_cicids_hierarchical.pt`

Hash verification:

- Official final checkpoint SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Promoted source checkpoint SHA256: `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Final/source hash match: true
- Selection basis: highest validation hierarchical score, not test metrics

Limitations and warnings:

- DoS-SlowHTTPTest to FTP-BruteForce remains the dominant unresolved confusion.
- FTP-BruteForce mean F1 is slightly lower than the old baseline.
- Web-XSS and SQL-Injection have tiny support and must not be over-claimed.
- EXP04 diagnostic suggested the remaining SlowHTTPTest/FTP issue may be feature-limited.

## UNSW

Status: optimization closed for now; A9 remains the accepted UNSW final baseline.

A11 seed42 has been formally rejected as diagnostic only. No final checkpoint replacement occurred. No A11 promotion occurred. UNSW model/preprocessing optimization is closed for now.

The official frozen UNSW checkpoint is:

`models/final/final_unsw_hierarchical.pt`

Accepted model identity:

`A9 corrected-protocol hierarchical baseline`

Freeze record:

`results/audits/unsw_a9_final_acceptance_freeze_record.json`

Rollback target:

`results/audits/unsw_freeze_backups/unsw_a9_final_freeze_20260625_171733/models_final/final_unsw_hierarchical.pt`

Hash verification:

- Official frozen checkpoint SHA256: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- Freeze backup checkpoint SHA256: `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA`
- Final/backup hash match: true

A9 known metrics:

- Binary macro-F1: 0.894488
- Attack-family macro-F1: 0.500429
- Rare-class macro-F1: 0.385669

UNSW optimization closure:

- Closure record: `results/audits/unsw_optimization_closure_record.json`
- Closure report: `docs/experiments/UNSW_OPTIMIZATION_CLOSURE_REPORT.md`
- A11 seed42 checkpoint: `models/experiments/unsw_a11_enhanced_feature_protocol_seed42.pt`
- A11 status: rejected diagnostic only
- A11 binary macro-F1: 0.896630
- A11 attack-family macro-F1: 0.494685
- A11 rare-class macro-F1: 0.342636
- A11 screen gate result: FAIL_SCREEN
- Seed123/seed999: not run; 3-seed confirmation not justified

## Next Planned Work

The next planned work is federated/security implementation using the CICIDS final/promoted model with warnings and the UNSW A9 accepted baseline.
