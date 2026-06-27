# Train-Hierarchical CLI Gate Fix

Status: `focused CLI gate resolution complete`

Generated on: `2026-06-24`

## Purpose

This task resolves the focused blocker in `secureids/cli.py` where
`train-hierarchical` accepted only UNSW-NB15 and refused CICIDS2018 before the
trainer could perform its normal safety checks.

The change is limited to CLI dataset alias and config pairing validation. It
does not change model code, training logic, preprocessing, checkpoint writing,
metrics, dashboard behavior, FedAvg, security, attacks, Trimmed Mean, or XAI.

## Previous Blocker

The blocker was in `handle_train_hierarchical` in `secureids/cli.py`.

After loading a hierarchical config, the handler explicitly checked:

`config.dataset != "unsw_nb15"`

and rejected everything else with an A9 UNSW-only message. That meant
`configs/training/cicids2018_hierarchical.yaml` could pass config-level
validation but still be refused by the CLI before training preconditions were
reached.

## New Allowed Dataset Aliases

UNSW-NB15 aliases:

- `unsw`
- `unsw_nb15`
- `unsw-nb15`

CICIDS2018 aliases:

- `cicids`
- `cicids2018`
- `cicids-2018`

## Canonical Dataset IDs

- `unsw`, `unsw_nb15`, `unsw-nb15` -> `unsw_nb15`
- `cicids`, `cicids2018`, `cicids-2018` -> `cicids2018`

## Config Pairing Rules

`train-hierarchical` now validates the requested dataset alias, the config
dataset, the config task, expected input dimension, and the config filename
family before importing the trainer.

Rules:

- `unsw_nb15` must use a UNSW hierarchical training config.
- UNSW A9/A9.6/A9.7/A9.8 variant configs are allowed when the loaded config is
  hierarchical and the filename clearly belongs to UNSW, including `unsw_a9_*`
  variant names.
- `cicids2018` must use `configs/training/cicids2018_hierarchical.yaml`.
- Config task must be `hierarchical`.
- Expected input dims are still enforced: UNSW-NB15 `192`, CICIDS2018 `77`.

## Rejected Unsafe Cases

The gate rejects:

- unsupported dataset aliases;
- CICIDS dataset aliases with UNSW configs;
- UNSW dataset aliases with CICIDS configs;
- binary configs;
- smoke configs;
- unrelated YAML configs;
- config task values other than `hierarchical`;
- wrong dataset-specific input dimensions.

## Safety Boundaries

This task did not run training, full preprocessing, long evaluation, XAI,
Streamlit, FedAvg, security, attacks, Trimmed Mean, or dashboard work. It did
not modify checkpoints, create final metrics, delete/archive/move files, run
Git, fake predictions, fake metrics, or claim training happened.

The actual hierarchical trainer still owns:

- leakage checks;
- train-only class weights;
- validation-only checkpoint selection;
- one final test after best validation selection;
- checkpoint overwrite protection;
- final output writing.

## Manual Verification Command

Tests were not run by this task. To verify manually:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_train_hierarchical_cli_gate.py tests/test_adapter_registry.py tests/test_schema_detector_router.py -q
```

Audit JSON validation:

```powershell
Get-Content "results\audits\train_hierarchical_cli_gate_fix.json" -Raw | .\.venv\Scripts\python.exe -m json.tool
```

## Next Step

Rerun the CICIDS hierarchical readiness audit after this gate fix. Then return
to the project controller for explicit approval before any manual CICIDS
hierarchical training command is run.
