# UNSW_COMPATIBILITY_DECISION.md

## Decision

Official UNSW-NB15 must not be forced into the old CICIDS2018 feature
pipeline.

## Rationale

- The old CICIDS2018 model expected CICIDS-specific numeric features.
- UNSW-NB15 has a different schema and categorical fields such as
  `proto`, `service`, and `state`.
- Binary label mapping is valid.
- Direct frozen CICIDS-to-UNSW feature evaluation is invalid.

## V2 Solution

V2 uses dataset-specific adapters and dataset-specific preprocessors for
CICIDS2018 and UNSW-NB15. The project keeps one shared SecureIDSNet
architecture, but uses dataset-specific final checkpoints:

- `models/final/final_cicids_binary.pt`
- `models/final/final_unsw_binary.pt`

This keeps the binary IDS task valid without making a fake cross-dataset
generalization claim.
