> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Full Training Readiness Report

Status: `Task A8 readiness/pre-run gate - no full training run`

Generated UTC: `2026-06-24T02:13:07.953488+00:00`

## Dataset Readiness

- cicids2018: `PASS` (ready=true, blocking=0, warnings=1)
- unsw_nb15: `PASS` (ready=true, blocking=0, warnings=1)

## Direct Answers

1. CICIDS ready: `true`.
2. UNSW ready: `true`.
3. Train first: `UNSW-NB15`. UNSW is smaller and faster, so it is the safer first real centralized hierarchical run when there are no blockers.
4. Blocking issues: `none`.
5. Warnings: `present`; mainly rare-class/class-weight caution.
6. Rare classes: represented in train/val/test for inspected datasets; keep per-class and rare-class reporting.
7. Class weights: raw inverse-frequency Head 2 weights are risky where noted; use capped, sqrt, or log-smoothed train-only weighting before real training.
8. Checkpoint/output paths: checked for overwrite risk; no A8 final outputs were created.
9. CUDA available: `true`.
10. First real training command for later approval: `python -m secureids.cli train-hierarchical --dataset unsw --config configs/training/unsw_nb15_hierarchical.yaml --execute`.

## Per-Dataset Notes

### cicids2018

- status: `PASS`
- ready_for_full_hierarchical_training: `true`
- blocking issues: `0`
- warnings: `1`
- input_dim: `77`
- attack_head_dim: `14`
- class-weight risk: `WARNING` (raw max Head 2 weight `2181.138322`)
- rare classes safe/documented: `true`
- planned checkpoint exists: `false`
- result dir contains files: `false`
- device recommendation: `cuda` (cuda_available=true)
- later command: `python -m secureids.cli train-hierarchical --dataset cicids --config configs/training/cicids2018_hierarchical.yaml --execute`

Warnings:

- Raw inverse-frequency Head 2 weights are extreme for: DDoS-LOIC-UDP, Web-BruteForce, Web-XSS, SQL-Injection; use capped, sqrt, or log-smoothed weighting before real training.

### unsw_nb15

- status: `PASS`
- ready_for_full_hierarchical_training: `true`
- blocking issues: `0`
- warnings: `1`
- input_dim: `192`
- attack_head_dim: `9`
- class-weight risk: `WARNING` (raw max Head 2 weight `103.40367`)
- rare classes safe/documented: `true`
- planned checkpoint exists: `false`
- result dir contains files: `false`
- device recommendation: `cuda` (cuda_available=true)
- later command: `python -m secureids.cli train-hierarchical --dataset unsw --config configs/training/unsw_nb15_hierarchical.yaml --execute`

Warnings:

- Raw inverse-frequency Head 2 weights are extreme for: Worms; use capped, sqrt, or log-smoothed weighting before real training.

## A8 Safety Confirmation

- No full hierarchical training was run.
- No optimizer training loop or full epoch was run.
- No final hierarchical checkpoint was created.
- No final hierarchical metrics, histories, or confusion matrices were created.
- No hierarchical FedAvg, TLS/security, attacks, Trimmed Mean, XAI, or dashboard work was started.
- Existing binary checkpoints/results were checked and preserved.
- V1 files were not modified by this readiness command.
- No scaler/encoder refit on test was performed.
- No test-set tuning or test-based class weights were used.
