# Hierarchical Smoke Training Check

Status: `Task A7 smoke-only execution report`

This report contains NON-FINAL smoke diagnostics only. It is a
technical validation of data loading, forward/loss/optimizer plumbing,
and small evaluation diagnostics. It is not final model performance.

Last updated UTC: `2026-06-24T02:13:50.815850+00:00`

## Safety Markers

- smoke_only: `true`
- non_final: `true`
- do_not_report_as_final: `true`
- checkpoint_created: `false`
- final_metrics_created: `false`
- full_training_run: `false`
- final_checkpoint: `false`
- final_results: `false`

## Dataset Results

### cicids2018 - PASS

- output JSON: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_smoke_training_cicids2018.json`
- train samples selected: `4096`
- val samples selected: `2048`
- test samples selected: `2048`
- batches run: `4`
- forward pass ok: `True`
- backward pass ok: `True`
- masked loss finite: `True`
- binary loss finite: `True`
- attack loss finite or zero: `True`
- optimizer updated parameters: `True`
- smoke binary validation F1: `0.9236234458259325`
- smoke attack rows evaluated: `520`

### unsw_nb15 - PASS

- output JSON: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_smoke_training_unsw_nb15.json`
- train samples selected: `4096`
- val samples selected: `2048`
- test samples selected: `2048`
- batches run: `4`
- forward pass ok: `True`
- backward pass ok: `True`
- masked loss finite: `True`
- binary loss finite: `True`
- attack loss finite or zero: `True`
- optimizer updated parameters: `True`
- smoke binary validation F1: `0.9015691868758916`
- smoke attack rows evaluated: `700`

## What Was Not Done

- No full hierarchical training was run.
- No final hierarchical checkpoint was created.
- No final hierarchical metrics, histories, or confusion matrices were created.
- No hierarchical FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work was started.
