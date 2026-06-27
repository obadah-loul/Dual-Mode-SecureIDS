# Pre-Training HIGH Findings Resolution (Task A8.8)

Status: `RESOLVED — both A8.75 HIGH findings fixed; clean GO for UNSW A9 training`
Generated UTC: `2026-06-24`
Inputs: [PRE_TRAINING_CODE_AUDIT_REPORT.md](PRE_TRAINING_CODE_AUDIT_REPORT.md),
[UNSW_SPLIT_PROTOCOL_DECISION.md](UNSW_SPLIT_PROTOCOL_DECISION.md)
Machine-readable: `results/audits/pre_training_high_findings_resolution.json`

---

## Executive summary

A8.75 gave a **conditional** go with two HIGH findings. A8.8 resolves both:

- **F1 (UNSW split protocol):** verified the local raw file names are swapped vs the
  canonical UNSW-NB15 partition sizes, corrected the pipeline to the standard
  benchmark protocol (train on the 175,341-row partition, test on the 82,332-row
  partition), and regenerated all UNSW processed/hierarchical/readiness/class-weight
  artifacts. Old UNSW binary baselines are marked legacy/pre-correction and preserved.
- **F2 (class-weight wiring):** `compute_hierarchical_loss` now accepts and applies
  the A8.5-locked binary `pos_weight` and Head 2 `attack_class_weights`, with shape
  validation, device handling, class-id alignment, and empty-mask safety. A focused
  test suite proves the weights change the loss and that wrong shapes fail clearly.

No training was run; no final checkpoints or final metrics were created. Tests:
**102 passed**. Readiness gates: **PASS**. Recommendation: **GO** to implement and run
UNSW A9 training.

---

## F1 — UNSW split protocol (resolved)

See [UNSW_SPLIT_PROTOCOL_DECISION.md](UNSW_SPLIT_PROTOCOL_DECISION.md) for the full
verification and decision. Key points:

- Verified from the raw CSVs: local `UNSW_NB15_training-set.csv` = 82,332 rows
  (canonical test size); local `UNSW_NB15_testing-set.csv` = 175,341 rows (canonical
  train size). The file **names are swapped** vs canonical row counts.
- Decision: train/val on the 175,341-row partition; final test on the 82,332-row
  partition — the standard UNSW-NB15 benchmark protocol. Implemented by swapping
  `train_file`/`test_file` (assigned by row count) in the binary preprocessing config;
  raw files were not modified.
- Corrected split: **train 149,039 / val 26,302 / test 82,332**. Feature dim
  **190 → 192** (data-derived; all hierarchical-path configs/code updated).
- Bonus: rare-class support improved (Worms train 40→109, val 4→21), which also
  mitigates the A8.75 F3 validation-stability concern.
- Old UNSW binary/FedAvg baselines are **legacy/pre-correction**, preserved on disk,
  and must not be reported as final. Legacy preprocessor + audit snapshots archived
  under `results/audits/legacy_pre_a8_8_unsw/` and
  `models/final/preprocessors/legacy_pre_a8_8/`.

## F2 — Hierarchical class-weight wiring (resolved)

`compute_hierarchical_loss(...)` was extended (file
`secureids/models/secureids_hierarchical_advanced_net.py`):

- New optional `attack_class_weights` (Head 2) applied via `F.cross_entropy(weight=...)`
  on attack rows only; existing `pos_weight` applies to `BCEWithLogits` for Head 1.
- **Shape validation:** `attack_class_weights` length must equal `attack_head_dim`;
  a wrong length raises `ValueError` **up front**, so it fails clearly even on an
  all-benign batch.
- **Device/dtype:** both weight tensors are moved to the logits' device/dtype inside
  the loss, so callers may pass CPU tensors/lists.
- **Class-id alignment:** new `build_train_only_class_weights(dataset)` in
  `secureids/training/hierarchical_class_weights.py` returns `attack_class_weights`
  ordered by class id `0..N-1` (aligned to `id_to_class`) plus the binary
  `pos_weight`, computed from the **train split only**.
- **Empty-mask safety:** a batch with no attack rows returns a zero attack-loss tensor
  on the binary loss's device/dtype — never NaN.

Wired into the real path:

- `hierarchical_readiness.py` now builds the locked train-only weights and exercises
  the **weighted** masked loss (readiness JSON records
  `attack_class_weights_applied: true`, `class_weights_train_only: true`).
- `hierarchical_smoke.py` applies the locked weights during the non-final smoke run
  (smoke JSON records both weight-applied flags).

### Tests (`tests/test_hierarchical_weighted_loss.py`)

Covers: attack weights change the attack loss; uniform weights match unweighted; a
list aligned to class ids is accepted; binary `pos_weight` changes the binary loss;
weights are moved to the logits device (CPU + CUDA when available); all-benign,
all-attack, and mixed batches stay finite; empty attack mask produces no NaN even with
weights; wrong length (too short / too long) raises `ValueError` including on an
all-benign batch; exact length passes; `build_train_only_class_weights` never reads
val/test labels and returns capped, class-id-aligned, loss-usable weights.

## Note: obsolete A4 readiness gate adjusted

Re-running the A4 `validate-hierarchical-preprocessing` gate revealed it still required
that the advanced model code **not** exist — a one-time A4→A5 transition guard that is
anachronistic now that the model was approved and implemented at A5. It was adjusted to
treat the approved model's presence as **expected** (reported, non-blocking) while
keeping the real "no final hierarchical checkpoints/metrics, no security/attack/XAI
outputs, binary artifacts preserved" blockers. Both datasets then validate **PASS**.
This is the only behavioral change outside the F1/F2 scope and is documented here.

---

## Commands run (all safe / non-training)

| Command | Result |
| --- | --- |
| `compileall secureids tests` | clean |
| `pytest tests -q` | 102 passed |
| `pytest tests/test_hierarchical_weighted_loss.py -q` | passed |
| regenerate UNSW binary preprocessing (direct call) | feature_dim 192; train 149,039 / val 26,302 / test 82,332 |
| regenerate UNSW hierarchical preprocessing (`execute_dataset`, overwrite) | PASS, feature_dim 192, masks valid |
| `validate-hierarchical-preprocessing --dataset all` | PASS / PASS |
| `lock-hierarchical-class-weights --dataset all` | PASS / PASS (max attack weight unsw 3.95) |
| `check-hierarchical-training-readiness --dataset all` | PASS / PASS (weighted loss exercised) |
| `smoke-train-hierarchical --dataset unsw` | PASS (non-final, input_dim 192, weights applied) |

## Safety confirmation

- No full training, no final checkpoints, no final metrics.
- No hierarchical FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work.
- No Git operations; V1 not modified; CICIDS2018 not modified.
- Binary baseline checkpoints preserved (and marked legacy where the protocol changed).
- Class weights computed from train only; no validation/test labels used.

## Go / No-Go for A9

**GO** for UNSW full centralized hierarchical training (to be implemented in A9). Both
HIGH findings are resolved, the locked class weights are now actually applied (and
proven by tests), the UNSW protocol is standard and regenerated, and all readiness
gates pass. Remaining items are A9 implementation work (the trainer, final metrics, and
the `train-hierarchical` CLI command), not pre-training blockers.

Do **not** run `train-hierarchical` until A9 is implemented.
