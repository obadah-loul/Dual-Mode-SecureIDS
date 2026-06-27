# CICIDS Hierarchical EXP01 Plan

Generated on: `2026-06-25`

Status: `prepared_only_not_run`

## Experiment ID

`cicids_hierarchical_exp01_head2_mlp_capacity`

## Selected Improvement Idea

Use a modest non-linear MLP attack-family Head 2 while preserving the shared
encoder, binary Head 1, loss weights, class weights, data protocol, and
validation-only selection.

Selected controlled variable:

```yaml
model:
  attack_head_type: mlp
  attack_head_hidden_dim: 128
  attack_head_norm: true
  attack_head_dropout: 0.20
```

## Why This Idea Was Chosen

The current code already supports a backward-compatible Head 2 MLP option. The
trainer passes the option through to `SecureIDSHierarchicalAdvancedNet`, and the
forward/loss contract remains unchanged.

This is the safest first CICIDS improvement because the accepted baseline's main
weakness is Head 2 attack-family classification, while Head 1 is already strong.
The experiment adds capacity where the weakness lives without changing the
binary head or increasing global attack loss pressure.

## Baseline Metrics To Beat

| Metric | Accepted CICIDS baseline |
| --- | ---: |
| Binary Head 1 macro-F1 | `0.972167` |
| Binary accuracy | `0.977486` |
| Binary precision | `0.974214` |
| Binary recall | `0.946193` |
| Binary F1 | `0.960000` |
| Attack-family Head 2 macro-F1 | `0.849111` |
| Attack-family accuracy on attack rows | `0.961306` |
| Rare-class macro-F1 | `0.716987` |
| End-to-end attack detected and correctly attributed rate | `0.909008` |
| Attack missed as benign rate | `0.053807` |
| Benign false alarm rate | `0.010008` |

## Weak Classes Targeted

- `Web-BruteForce`: F1 `0.3636`, support `96`
- `Web-XSS`: F1 `0.6182`, support `38`
- `DoS-SlowHTTPTest`: F1 `0.5535`, support `20941`
- `FTP-BruteForce`: F1 `0.7787`, support `28928`
- `SQL-Injection`: F1 `0.8000`, support `12`

## Exact Paths

- Config: `configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml`
- Future checkpoint: `models/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.pt`
- Future results folder: `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/`
- Future report: `docs/experiments/CICIDS_HIERARCHICAL_EXP01_HEAD2_MLP_CAPACITY_REPORT.md`
- Future manifest: `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp01_head2_mlp_capacity.json`

## Variables Deliberately Unchanged

- Dataset: `cicids2018`
- Task: `hierarchical`
- Input dimension: `77`
- Attack-family Head 2 dimension: `14`
- Processed train/validation/test artifact paths
- Shared encoder hidden dimensions: `[256, 128, 128]`
- Shared encoder dropout: `0.20`
- Normalization: `layernorm`
- Binary head: unchanged
- Binary loss weight: `1.0`
- Attack loss weight: `1.0`
- Train-only class weights
- No oversampling
- Batch size: `4096`
- Max epochs: `30`
- Optimizer: `adamw`
- Learning rate: `0.001`
- Weight decay: `0.0001`
- Early-stopping patience: `5`
- Threshold: `0.5`
- Checkpoint selection: validation only
- Final test: once after best validation checkpoint

## Training Safety Rules

- Do not overwrite the accepted baseline checkpoint.
- Do not use `--overwrite`.
- Do not tune on the test set.
- Do not use validation or test labels to compute class weights.
- Do not change taxonomy to improve metrics.
- Do not claim improvement unless a real future run creates real outputs.
- Keep this as one controlled factor.

## No-Test-Tuning Rule

The test set is used once after the best validation checkpoint is selected. It
must not be used to choose the architecture, threshold, class weights, epoch, or
promotion decision before the run is complete.

## Manual Training Command

Prepare only. Run manually after main-control approval:

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.yaml --execute
```

Do not include `--overwrite`.

## Expected Outputs

- `models/experiments/cicids_hierarchical_exp01_head2_mlp_capacity.pt`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/training_history.csv`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/test_metrics.json`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/binary_confusion_matrix.csv`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/attack_family_confusion_matrix.csv`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/per_class_attack_metrics.csv`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/rare_class_metrics.csv`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/hierarchical_routing_summary.json`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/training_config_snapshot.yaml`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/class_weight_snapshot.json`
- `results/experiments/cicids_hierarchical_exp01_head2_mlp_capacity/model_summary.json`
- `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp01_head2_mlp_capacity.json`
- `docs/experiments/CICIDS_HIERARCHICAL_EXP01_HEAD2_MLP_CAPACITY_REPORT.md`

## Promotion Criteria

Promote EXP01 only if it beats the accepted baseline honestly:

- Attack-family macro-F1 improves meaningfully over `0.849111`, preferably by
  at least `0.01` absolute.
- Rare-class macro-F1 improves over `0.716987` or at least does not collapse.
- Binary Head 1 macro-F1 remains strong, preferably at least `0.965`.
- End-to-end correct attribution does not drop badly from `0.909008`.
- Benign false alarm rate does not materially worsen from `0.010008`.
- Attack missed-as-benign rate does not materially worsen from `0.053807`.
- No evidence of test tuning, path overwrite, fake metrics, or leakage.

## Rejection Criteria

Reject or mark diagnostic only if:

- Head 2 macro-F1 does not improve meaningfully.
- Head 1 drops badly.
- Rare-class macro-F1 collapses.
- False alarms or missed attacks worsen materially.
- Output paths overwrite baseline.
- Any test leakage or fake-metric issue appears.

## Risks

- Extra Head 2 capacity may overfit rare classes.
- Gains may be small because the current CICIDS baseline is already strong.
- DoS-SlowHTTPTest may reflect feature overlap rather than capacity alone.
- A single seed is not final proof of superiority.
- Runtime may be similar to the large accepted CICIDS run.

## Next Decision Needed

Main control must approve the manual EXP01 training command. After real outputs
exist, compare EXP01 against the accepted CICIDS baseline and decide whether to
promote, reject, or run a later controlled experiment.
