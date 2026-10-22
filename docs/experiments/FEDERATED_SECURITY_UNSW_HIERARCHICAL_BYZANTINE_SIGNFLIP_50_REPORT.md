> **Recovery clarification:** The hash result below was an internal self-check and does not establish independent sender authentication or an untampered transport channel. Saved metrics remain unchanged.

# Hierarchical Federated Experiment Report

Dataset: `unsw_nb15`
Protocol: `unsw_a9_hierarchical_byzantine_signflip_50_reference_frozen_baseline`
Aggregation: `fedavg`
Attack: `sign_flip`
Requested malicious fraction: `0.5` (actual: **2 of 5 = 40%**); archive-only full-state SignFlip
Selected malicious clients: `['client_00', 'client_04']`

Status: historical run recorded as completed; not rerun during final integration.

Safety notes:

- Centralized final checkpoint was reference-only.
- Initialization was from scratch.
- No `models/final/` or `results/final/` path was written.
- This FL checkpoint is experimental and not promoted.

Results:

- Best round: `1`
- Rounds run: `20`
- Test metrics path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\federated_security\unsw_hierarchical_byzantine_signflip_50\test_metrics.json`
- Manifest path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\federated_security_unsw_hierarchical_byzantine_signflip_50_manifest.json`
- Historical SHA-256 self-check reported: `True` (not independent origin authentication or externally anchored integrity proof)
