> **Recovery clarification:** The hash result below was an internal self-check and does not establish independent sender authentication or an untampered transport channel. Saved metrics remain unchanged.

# Hierarchical Federated Experiment Report

Dataset: `unsw_nb15`
Protocol: `unsw_hierarchical_clean_fedavg_rounds40_improvement`
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

- Best round: `38`
- Rounds run: `40`
- Test metrics path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\federated_hierarchical_v2\unsw_improved_rounds40_clean_fedavg\test_metrics.json`
- Manifest path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\federated_hierarchical_v2_unsw_improved_rounds40_clean_fedavg_manifest.json`
- Historical SHA-256 self-check reported: `True` (not independent origin authentication or externally anchored integrity proof)
