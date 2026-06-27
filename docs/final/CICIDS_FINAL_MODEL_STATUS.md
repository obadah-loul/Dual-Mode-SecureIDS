# CICIDS Final Model Status

Generated: `2026-06-25`

Status: `official final promoted`

## Current Official Final

The accepted official CICIDS hierarchical final model is now **EXP03 1.25 seed999**.

| Field | Value |
| --- | --- |
| Final checkpoint | `models/final/final_cicids_hierarchical.pt` |
| Promoted source checkpoint | `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` |
| Promotion record | `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json` |
| Backup directory | `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136` |
| Rollback target | `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136/models_final/final_cicids_hierarchical.pt` |

The previous CICIDS baseline was backed up during promotion. The rollback target above preserves the
pre-promotion `models/final/final_cicids_hierarchical.pt`.

## Validation-Based Selection

EXP03 1.25 seed999 was selected because it had the highest validation hierarchical score among the
EXP03 1.25 confirmation seeds.

| Seed | Best validation hierarchical score |
| ---: | ---: |
| 42 | `0.909871` |
| 123 | `0.905829` |
| 999 | `0.913383` |

The selected final checkpoint was selected by validation metrics, not by test metrics. Test metrics were
recorded for audit and reporting only.

## Hash Verification

| Hash | Value |
| --- | --- |
| Source SHA256 | `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0` |
| Final SHA256 | `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0` |
| Hashes match | `True` |

The matching hashes document that the final checkpoint matches the promoted EXP03 1.25 seed999 source
checkpoint.

## Experiment History

- EXP01 (`cicids_hierarchical_exp01_head2_mlp_capacity`): rejected / diagnostic only.
- EXP02 (`attack_loss_weight = 1.5`): useful improvement family, but not promoted because routing
  regressed.
- EXP03 1.25: promoted as the official CICIDS hierarchical final model.
- EXP04: diagnostic evidence explaining remaining limitations; it supports stopping model/loss tuning
  for the dominant SlowHTTPTest/FTP confusion under the current 77-feature protocol.

## Limitations To Report

- DoS-SlowHTTPTest <-> FTP-BruteForce remains the dominant unresolved confusion.
- FTP-BruteForce mean F1 is slightly lower than the old baseline on average.
- Web-XSS and SQL-Injection have tiny test support and must not be over-claimed.
- The 3-seed aggregate had small warnings for correct attribution and missed-as-benign, mainly due to
  seed123.
- EXP04 diagnostic evidence suggests the dominant SlowHTTPTest/FTP issue is feature-limited in the
  current 77-feature space.

## Safety Notes

This status page records the completed promotion state. It does not create metrics, recompute results,
modify checkpoints, or tune on test data.
