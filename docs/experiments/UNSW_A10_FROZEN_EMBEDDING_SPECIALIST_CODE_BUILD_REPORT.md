# UNSW A10 Frozen Embedding Specialist Code Build Report

Generated on: 2026-06-25

Status: code/config/test/docs/audit scaffolding only. No A9.10 training was run, no full evaluation was run, no checkpoint was created, and no promotion/replacement of A9 occurred.

## What Was Added

- A9.10 frozen-embedding head module: `secureids/models/frozen_embedding_specialist.py`
- A9.10 config validator: `secureids/training/frozen_embedding_specialist_config.py`
- A9.10 dry-run/training entry point: `secureids/training/frozen_embedding_specialist_trainer.py`
- A9.10 oracle/routed metric helpers: `secureids/training/frozen_embedding_specialist_evaluation.py`
- CLI command: `train-frozen-embedding-specialist`
- Seed42 scaffold config: `configs/training/experiments/unsw_a10_frozen_embedding_specialist_seed42.yaml`
- Targeted tests for config, CLI, frozen/no-gradient behavior, metric separation, class-weight tempering, and label smoothing.

## Frozen A9 Embedding Design

A9.10 loads the accepted A9 hierarchical checkpoint:

`models/final/final_unsw_hierarchical.pt`

The A9 model is reconstructed from checkpoint metadata as `SecureIDSHierarchicalAdvancedNet`, all A9 parameters are frozen, and the existing forward output key `embedding` is used as the fixed feature representation. This is the 128-dimensional representation after the A9 encoder and gated representation block.

Only the A9.10 specialist head is trainable. A9 Head 1 remains the binary router, A9 Head 2 is not updated, and the accepted A9 checkpoint is not modified.

## A9.10 Head

The new head supports:

- `linear`
- `shallow_mlp`

The seed42 config uses `shallow_mlp`, dropout `0.35`, weight decay `0.001`, label smoothing `0.05`, and train-only tempered class weights with temperature `0.5`.

## CLI Behavior

Dry-run command:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli train-frozen-embedding-specialist --config configs\training\experiments\unsw_a10_frozen_embedding_specialist_seed42.yaml
```

Dry-run result:

- validates config
- prints planned outputs
- confirms frozen A9 checkpoint is present
- confirms processed input arrays are present
- writes nothing
- creates no checkpoint, results directory, or seed42 report

Manual training command, not run yet:

```powershell
.\.venv\Scripts\python.exe -m secureids.cli train-frozen-embedding-specialist --config configs\training\experiments\unsw_a10_frozen_embedding_specialist_seed42.yaml --execute
```

## Expected Future Outputs

- Checkpoint: `models/experiments/unsw_a10_frozen_embedding_specialist_seed42.pt`
- Results: `results/experiments/unsw_a10_frozen_embedding_specialist_seed42/`
- Report: `docs/experiments/UNSW_A10_FROZEN_EMBEDDING_SPECIALIST_SEED42_REPORT.md`

These are planned future outputs only. They were not created during this prep task.

## Oracle vs Routed Reporting

A9.10 preserves two separate metric views:

- Oracle attack-family metrics: specialist evaluated on true attack rows only.
- Routed metrics: frozen A9 Head 1 routes rows into the specialist.

Oracle metrics must not be reported as deployed/routed metrics. Weak classes remain visible: Analysis, Backdoor, DoS, Shellcode, and Worms.

## Future Seed42 Screen Gates

A9.10 seed42 should pass only if:

- Oracle attack-family macro-F1 improves meaningfully over A9 `0.500429`, preferably at least `0.515429`.
- Rare-class macro-F1 does not drop below A9 `0.385669`.
- Validation-to-test gap is not extreme like A9.9.
- Routed and oracle metrics remain clearly separated.
- Binary routing remains A9-based and unchanged.
- No leakage, fake metrics, path contamination, or test tuning occurs.
- No single-seed promotion occurs.

## Tests Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frozen_embedding_specialist_config.py tests/test_frozen_embedding_specialist_cli.py tests/test_frozen_embedding_specialist_model.py tests/test_frozen_embedding_specialist_metrics.py tests/test_attack_family_specialist_cli.py tests/test_attack_family_specialist_config.py tests/test_train_hierarchical_cli_gate.py -q
```

Result: `41 passed in 2.31s`.

## Safety Confirmation

- No training run.
- No full evaluation run.
- No preprocessing rebuild.
- No XAI or Streamlit launch.
- No Git action.
- No final checkpoint modification.
- No checkpoint creation.
- No checkpoint promotion.
- No `models/final/` modification.
- No `results/final/` modification.
- No CICIDS behavior modification.
- Existing A9.9 tests passed.
- Existing `train-hierarchical` CLI gate tests passed.

## Next Main-Control Decision

Approve or reject the manual A9.10 seed42 training run. If approved, run only the explicit `--execute` command above and treat it as a screen, not a promotion.

