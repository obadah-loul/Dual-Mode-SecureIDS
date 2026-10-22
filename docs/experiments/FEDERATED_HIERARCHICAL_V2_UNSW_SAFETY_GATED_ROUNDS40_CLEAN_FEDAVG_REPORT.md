> **Recovery clarification:** The hash result below was an internal self-check and does not establish independent sender authentication or an untampered transport channel. Saved metrics remain unchanged.

# Hierarchical Federated Experiment Report

Dataset: `unsw_nb15`
Protocol: `unsw_hierarchical_clean_fedavg_rounds40_safety_gated`
Aggregation: `fedavg`
Attack: `none`
Malicious fraction: `0.0`
Selected malicious clients: `[]`

Status: historical run recorded as completed; not rerun during final integration.

Safety notes:

- Centralized final checkpoint was reference-only.
- Initialization was from scratch.
- No `models/final/` or `results/final/` path was written.
- This FL checkpoint is experimental and not promoted.

Results:

- Best round: `1`
- Rounds run: `40`
- Test metrics path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\federated_hierarchical_v2\unsw_safety_gated_rounds40_clean_fedavg\test_metrics.json`
- Manifest path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\federated_hierarchical_v2_unsw_safety_gated_rounds40_clean_fedavg_manifest.json`
- Historical SHA-256 self-check reported: `True` (not independent origin authentication or externally anchored integrity proof)

Selection:

- Strategy: `safety_gated_hierarchical_score`
- Safety metric: `val_attack_missed_as_benign_rate`
- Relative margin: `0.005`
- Absolute missed-as-benign max: `0.067097`
- Selected round: `1`
- Safety gate satisfied: `True`
- Eligible rounds: `1`
- Selected round missed-as-benign rate: `0.06306557926488661`
- Selected round binary recall: `0.9369344207351133`
- Per-round checkpoints saved: `True`
- Per-round checkpoint folder: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\federated_hierarchical_v2\unsw_safety_gated_rounds40_clean_fedavg\round_checkpoints`
