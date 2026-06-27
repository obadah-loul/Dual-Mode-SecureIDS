# UNSW A11 Preprocessing Implementation Build Report

Status: `IMPLEMENTED_NOT_RUN`
Generated: `2026-06-25`
Protocol name: `UNSW A11 Enhanced Feature Protocol`

## 1. Build Scope

This task implemented code/config/test/docs/audit scaffolding for UNSW A11 preprocessing support only.

No A11 preprocessing was executed. No training, evaluation, checkpoint creation, promotion, XAI, Streamlit, Git action, final result modification, or A9 artifact modification was performed.

## 2. Code Added Or Changed

Added:

- `secureids/preprocessing/unsw_a11_config.py`
- `secureids/preprocessing/unsw_a11_preprocessor.py`
- `tests/test_unsw_a11_preprocessing_config.py`
- `tests/test_unsw_a11_preprocessor.py`
- `tests/test_unsw_a11_cli.py`

Changed:

- `secureids/cli.py`
- `configs/preprocessing/experiments/unsw_a11_enhanced_feature_protocol.yaml`

The A11 config was updated only to make the approved protocol executable later: it now has an explicit train-only proto `min_frequency: 10` and an A11-specific preprocessor artifact path.

## 3. CLI Command Added

Added CLI command:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli prepare-unsw-a11 --config configs\preprocessing\experiments\unsw_a11_enhanced_feature_protocol.yaml
```

Without `--execute`, the command validates the A11 config and prints planned outputs only. It writes nothing.

Future manual execution command, not run now:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
.\.venv\Scripts\python.exe -m secureids.cli prepare-unsw-a11 --config configs\preprocessing\experiments\unsw_a11_enhanced_feature_protocol.yaml --execute
```

## 4. Config Validation Behavior

The A11 validator checks:

- `status` remains `not_run_yet`.
- Dataset is `unsw_nb15` only.
- Corrected UNSW canonical split is preserved.
- Validation is derived only from the canonical train source.
- Target/drop/categorical columns match the approved UNSW protocol.
- Train-only fitting flags are enabled.
- No test fitting, no test-label feature selection, and no test tuning are enabled.
- Numeric-only scaling is enabled.
- One-hot categorical columns are not scaled.
- Proto grouping uses a train-only other-bucket rule.
- Planned processed data paths stay under `data/processed/unsw_a11_enhanced/`.
- Preprocessor artifacts stay under `models/experiments/preprocessors/unsw_a11_enhanced/`.
- Audit outputs stay under `results/audits/` with `unsw_a11` filenames.
- No output path targets `models/final` or `results/final`.
- A9 remains a frozen reference, not a target.
- Overwrite is refused by default.

## 5. Preprocessor Behavior

The A11 preprocessor supports the future approved execution path:

- Load corrected UNSW train/test raw sources.
- Split validation from the canonical train source only.
- Fit numeric median imputer on train only.
- Fit numeric standard scaler on train numeric columns only.
- Fit categorical grouping on train only.
- Group rare proto categories into an explicit other bucket.
- Apply the same grouping to train/val/test.
- Map validation/test unknown proto categories to the other bucket.
- Fit one-hot encoder on train grouped categories only.
- Keep one-hot outputs unscaled.
- Preserve consistent feature order across train/val/test.
- Save A11-specific arrays, feature names, mappings, preprocessor artifact, manifest, and audit files only when `--execute` is later used.

## 6. Leakage Guards

Implemented guards reject:

- validation/test fitting
- test-label feature decisions
- unsafe processed output paths
- `models/final` or `results/final` paths
- A9 processed-data overwrite
- existing A11 output paths by default
- missing required UNSW columns
- leakage columns in feature names
- unsafe config status or safety flags

The dry-run path validates and returns planned output existence, but writes nothing.

## 7. Tests Run

Targeted lightweight tests only:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_unsw_a11_preprocessing_config.py tests/test_unsw_a11_preprocessor.py tests/test_unsw_a11_cli.py -q
```

Result:

`13 passed in 3.76s`

The first targeted run exposed an overly strict A11 audit-path prefix check. The validator was corrected to accept approved `results/audits/unsw_a11...` filenames while still rejecting `results/final` and non-A11 audit targets.

## 8. Expected Future Outputs

The expected future outputs are listed in:

- `results/audits/unsw_a11_preprocessing_expected_outputs.csv`

No future output was created by this build except the requested code, tests, docs, and audit scaffolding.

## 9. Safety Confirmation

Confirmed:

- A11 preprocessing was not run.
- Existing preprocessing was not rebuilt.
- Training was not run.
- Evaluation was not run.
- XAI was not run.
- Streamlit was not launched.
- Git actions were not used.
- V1 was not modified.
- No checkpoints were created or modified.
- `models/final/` was not modified.
- `results/final/` was not modified.
- A9 was not replaced or promoted.
- No final metrics were created.

## 10. Exact Next Decision Needed

`approve_or_reject_manual_a11_preprocessing_run`

A11 preprocessing support is now runnable behind the explicit `--execute` gate, but the manual run has not been approved or executed by this task.
