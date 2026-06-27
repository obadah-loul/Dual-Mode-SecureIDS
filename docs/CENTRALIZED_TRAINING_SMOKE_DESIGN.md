# CENTRALIZED_TRAINING_SMOKE_DESIGN.md

## 1. Purpose

This document describes the centralized smoke-training mode (Task 8B-0). Smoke
training is a tiny, explicitly non-final training/evaluation pass over small
subsets of the processed arrays. Its only job is to validate the real PyTorch
training path before any full training is attempted.

It is design and usage documentation only. Running the smoke check is a separate,
manual step performed by the user.

## 2. Why Smoke Exists Before Full Training

This is the first time real PyTorch training will execute in V2. PyTorch is not
installed yet, and the full execute path (`train-centralized --execute`) is still
deliberately disabled. Jumping straight to full training on 6.7M CICIDS2018 rows
risks wasting hours on an environment or code-path problem.

Smoke training de-risks that by exercising the whole path quickly:

- config loading (smoke config + base config),
- tiny data loading from the processed arrays (mmap-sliced),
- `SecureIDSNet` construction with a config-driven `input_dim`,
- a real forward pass (single logit per sample),
- a real backward pass and optimizer step (weights actually update),
- `BCEWithLogitsLoss` computation,
- a capped evaluation pass and metric computation via the existing helpers.

If smoke passes, the path is sound and full training is a scale-up. If smoke is
blocked, the failure is found in seconds, not hours.

## 3. Smoke Is Non-Final

Smoke metrics are technical validation only. They are produced on tiny subsets
(a few thousand rows), for a single epoch, with only a handful of batches. They
are NOT model performance and must never be reported as results.

Every smoke output is marked:

- `non_final: true`
- `do_not_report: true`
- `do_not_use_for_dashboard: true`

Smoke never writes under `results/final/`, never creates a final checkpoint, and
never enables `train-centralized --execute`.

## 4. One Architecture Only

Smoke uses the single shared `SecureIDSNet` binary classifier with the
dataset-specific `input_dim` taken from config. There are no extra model
variants and no CNN/LSTM/Transformer/ensemble experiments. This matches the
locked design.

## 5. Expected Commands (run by the user, later)

First confirm the torch-free paths still work (no PyTorch required):

```bash
python -m secureids.cli --help
python -m secureids.cli train-centralized --dataset cicids --config configs/training/cicids2018_binary.yaml --dry-run
python -m secureids.cli train-centralized --dataset unsw --config configs/training/unsw_nb15_binary.yaml --dry-run
python -m secureids.cli train-centralized --dataset cicids --config configs/training/cicids2018_binary.yaml --execute
```

The `--execute` command must still refuse safely.

Then, after installing PyTorch manually (see Section 8), run smoke. Start with
UNSW-NB15 (smaller):

```bash
python -m secureids.cli smoke-train-centralized --dataset unsw --config configs/training/smoke_unsw_nb15_binary.yaml --execute
```

Optionally, after UNSW smoke passes, run CICIDS2018:

```bash
python -m secureids.cli smoke-train-centralized --dataset cicids --config configs/training/smoke_cicids2018_binary.yaml --execute
```

Compile check (any time):

```bash
python -m compileall -q secureids dashboard tests
```

## 6. Expected Outputs (only when the user runs smoke)

- `results/audits/centralized_smoke_check.json` - machine-readable smoke status,
  marked non-final. Running one dataset updates only that dataset's entry and
  preserves the other dataset's entry if present.
- `docs/CENTRALIZED_TRAINING_SMOKE_CHECK.md` - a human-readable, clearly
  non-final summary of the smoke run.

These files are produced only by running the smoke command. They are not created
during implementation (Task 8B-0).

An optional, clearly marked NON-FINAL checkpoint is written only if a smoke
config explicitly sets `save_checkpoint: true`, and then only under
`models/checkpoints/smoke/` with `NON_FINAL` / `DO_NOT_REPORT` /
`DO_NOT_USE_FOR_DASHBOARD` markers. The shipped smoke configs keep
`save_checkpoint: false`, so by default no checkpoint is written.

## 7. Safety Rules

- The smoke command requires `--execute`. Without it, it refuses:
  "Smoke training requires --execute because it runs a tiny non-final training
  check."
- On every run it prints: "This is a NON-FINAL smoke-training check. Do not
  report these metrics as final model results."
- Smoke never creates final checkpoints or final metrics.
- Smoke never writes under `results/final/centralized`.
- Smoke does not call full `train-centralized` execution and does not enable it.
- `train-centralized --execute` continues to refuse safely.
- `train-centralized --dry-run` remains torch-free.
- `smoke.py` (which imports torch) is imported only inside the smoke command
  handler, after `--execute` is confirmed - never at CLI startup.

## 8. Manual PyTorch Setup

PyTorch is not installed by this task and must be installed manually before
running smoke.

- The user should install PyTorch manually before running the smoke command.
- If the current Python version cannot install PyTorch, create or use a
  compatible Python environment first.
- Do not guess a final install command if uncertain; use the official PyTorch
  selector for the right OS/Python/CUDA combination.
- After installing, the user should verify with:

```bash
python -c "import torch; print(torch.__version__)"
```

If smoke is run without PyTorch installed, the CLI fails gracefully with a
message pointing back to this setup section, rather than crashing at startup.

## 9. How This Supports Full Training Later

A passing smoke check is the green light for full training:

- It confirms the processed arrays load and slice correctly for each dataset.
- It confirms `SecureIDSNet` builds at the correct `input_dim` (77 for
  CICIDS2018, 190 for UNSW-NB15) and emits `[batch, 1]` logits.
- It confirms forward/backward/loss/optimizer all work end to end.
- It confirms the metric helpers run on real predictions.

Once both datasets pass smoke, the recommended order for full training (a
separate, approval-gated Task 8B) is UNSW-NB15 first (smaller, faster feedback),
then CICIDS2018. Full training reuses the same `SecureIDSNet`, the same loaders,
and the same metric helpers, so smoke and full training share one code path -
smoke only caps the sizes.
