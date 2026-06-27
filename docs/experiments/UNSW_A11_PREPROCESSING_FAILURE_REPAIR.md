# UNSW A11 Preprocessing Failure Repair

Status: `bug fixed - preprocessing not rerun`
Generated: `2026-06-25`

## Root Cause

The manual A11 preprocessing run failed in `build_a11_split_summary` with `KeyError: 0`.

The cause was a key-type mismatch:

- `secureids.preprocessing.hierarchical.build_taxonomy_info` creates `id_to_class` with string keys such as `"0"`.
- A11 split-summary counts are produced from NumPy arrays and use integer class IDs such as `0`.
- The old A11 code indexed `taxonomy_info["id_to_class"][0]`, which fails when the mapping has `"0"` instead.

The partial `attack_family_label_mapping.json` confirms JSON-loaded mapping keys are strings.

## Code Fix

Added an A11-local helper:

`resolve_class_name(id_to_class, class_id)`

It resolves class names from integer-key, string-key, or mixed mappings. It is now used by:

- `build_a11_split_summary`
- `write_separability_placeholder`

The fix is narrow and isolated to A11 preprocessing.

## Partial Output Classification

Existing A11 output directory:

`data/processed/unsw_a11_enhanced/`

Classification: `incomplete`

Reason:

- A11 arrays and mapping JSON files exist.
- `split_summary.json` is missing.
- `hierarchical_preprocessing_manifest.json` is missing.
- `results/audits/unsw_a11_enhanced_feature_protocol_preprocessing_audit.json` is missing.
- A11 preprocessor `.joblib` is missing.

These partial outputs are not valid A11 processed data and are not safe for training.

No cleanup, deletion, overwrite, or repair of the partial output directory was performed.

## Future Rerun Behavior

A11 dry-run now reports the partial state:

`partial_outputs: detected=True, classification=incomplete, safe_to_use_for_training=False`

A11 `--execute` now refuses to run if an incomplete A11 output directory is present. Cleanup or overwrite approval must come from main control before any manual rerun.

## Tests

Targeted lightweight tests only:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_unsw_a11_preprocessing_config.py tests/test_unsw_a11_preprocessor.py tests/test_unsw_a11_cli.py -q
```

Result:

`21 passed in 3.69s`

## Safety Confirmation

- No preprocessing rerun.
- No training.
- No evaluation.
- No checkpoint creation or modification.
- No `models/final/` modification.
- No `results/final/` modification.
- No partial outputs deleted.
- No partial outputs overwritten.
- No V1 modification.
- No Git action.
- No XAI or Streamlit.
- No test tuning or fake metrics.

## Next Main-Control Decision

`approve_partial_output_cleanup_or_manual_a11_preprocessing_rerun_after_cleanup`
