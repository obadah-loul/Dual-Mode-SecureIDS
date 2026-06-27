# CENTRALIZED_TRAINING_SMOKE_CHECK.md

## Status: NON-FINAL TECHNICAL SMOKE TEST

This is a technical smoke test of the centralized training path. It is
**not** a final training result and **not** a final model performance
claim. No final checkpoint was created and no `results/final/centralized`
outputs were created.

Markers: non_final=true, do_not_report=true, do_not_use_for_dashboard=true.

Last updated (UTC): 2026-06-23T17:35:07.707125+00:00

## Datasets Tested

### unsw_nb15 - PASS

- input_dim: 190
- train samples used: 4096
- val samples used: 2048
- test samples used: 2048
- epochs run: 1
- batches run: 4
- dataloader ok: True
- forward pass ok: True
- backward pass ok: True
- params updated: True
- loss computed: True
- logits shape [batch, 1] ok: True
- metrics computed: True
- checkpoint created: False

Non-final smoke metrics (do not report):
- val (non-final): {'accuracy': 0.7021484375, 'confusion_matrix': {'fn': 6, 'fp': 299, 'tn': 142, 'tp': 577}, 'f1': 0.7909527073337903, 'macro_f1': 0.6365629411032279, 'n_samples': 1024, 'precision': 0.658675799086758, 'recall': 0.9897084048027445, 'threshold': 0.5}

### cicids2018 - PASS

- input_dim: 77
- train samples used: 4096
- val samples used: 2048
- test samples used: 2048
- epochs run: 1
- batches run: 4
- dataloader ok: True
- forward pass ok: True
- backward pass ok: True
- params updated: True
- loss computed: True
- logits shape [batch, 1] ok: True
- metrics computed: True
- checkpoint created: False

Non-final smoke metrics (do not report):
- val (non-final): {'accuracy': 1.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0, 'macro_f1': 0.5, 'confusion_matrix': {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 1024}, 'threshold': 0.5, 'n_samples': 1024}

## Safety Confirmation

- final checkpoint created: False
- final metrics created: False
- full training run: False

## Next Recommended Step

If every dataset above is PASS, the centralized training path is
validated on tiny subsets. The next step is to seek approval to enable
full `train-centralized --execute` (Task 8B), starting with UNSW-NB15
(smaller) before CICIDS2018. If any dataset is BLOCKED, fix the cause
and re-run the smoke check before any full training.
