# UNSW Final Model Status

Generated: `2026-06-25`

Status: `frozen as official UNSW hierarchical final baseline`

## Current Official Final

The accepted official UNSW hierarchical final/baseline is **A9 corrected-protocol hierarchical baseline**.

| Field | Value |
| --- | --- |
| Official checkpoint | `models/final/final_unsw_hierarchical.pt` |
| Manifest | `results/audits/hierarchical_training_manifest_unsw_nb15.json` |
| Freeze record | `results/audits/unsw_a9_final_acceptance_freeze_record.json` |
| Backup checkpoint | `results/audits/unsw_freeze_backups/unsw_a9_final_freeze_20260625_171733/models_final/final_unsw_hierarchical.pt` |
| Rollback target | `results/audits/unsw_freeze_backups/unsw_a9_final_freeze_20260625_171733/models_final/final_unsw_hierarchical.pt` |

This freeze is an acceptance record for the existing A9 checkpoint. It did not replace the checkpoint,
promote a different checkpoint, retrain, re-evaluate, or change final metrics.

## Known A9 Metrics

| Metric | Value |
| --- | ---: |
| Binary macro-F1 | `0.894488` |
| Attack-family macro-F1 | `0.500429` |
| Rare-class macro-F1 | `0.385669` |

The metrics above are copied from existing A9 project evidence. No metric was invented, recomputed, or
tuned from test data for this freeze.

## Hash Verification

| Hash | Value |
| --- | --- |
| Checkpoint SHA256 | `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA` |
| Backup SHA256 | `5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA` |
| Hashes match | `True` |

The matching hashes document that the rollback backup is an exact copy of the current A9 final
checkpoint.

## Experiment History

- A9: accepted corrected-protocol UNSW hierarchical baseline.
- A9.6: controlled `head2_loss_weight` experiment; did not replace A9.
- A9.7: controlled Head 2 branch-capacity experiment; did not replace A9.
- A9.8: multi-seed comparison; confirmed A9 remains accepted.
- A9.9: design-only next strategy; no training was run and nothing replaced A9.

## Legacy Artifacts

Old UNSW binary centralized and FedAvg outputs are legacy/pre-correction artifacts. They are preserved
for provenance but are not the official final hierarchical model.

- `models/final/final_unsw_binary.pt`: legacy/pre-correction binary artifact.
- `models/federated/fedavg_unsw_binary.pt`: legacy/pre-correction FedAvg binary artifact.
- `models/federated/fedavg_unsw_hierarchical.pt`: not present as an official final checkpoint.

Some legacy binary/FedAvg metadata still uses `final_checkpoint=true` for its own historical artifact.
That wording is superseded for final V2 reporting by this status page and by the corrected-protocol
UNSW documentation.

## Safety Notes

- No training was run.
- No evaluation was run.
- No preprocessing rebuild was run.
- No XAI or Streamlit dashboard was launched.
- No checkpoint was modified or replaced.
- No different checkpoint was promoted.
- No CICIDS or V1 artifact was modified.
- No Git action was performed.
