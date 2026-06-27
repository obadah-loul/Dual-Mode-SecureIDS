# UNSW A9.9 — Attack-Family Specialist Code Build Report

Status: `code/config/test scaffolding only — no training, no evaluation, no checkpoint, no promotion`
Generated: `2026-06-25`
Companion: `docs/experiments/UNSW_A99_SPECIALIST_ROUTER_DESIGN.md`,
`docs/experiments/UNSW_A99_ATTACK_FAMILY_SPECIALIST_PREP_PLAN.md`,
`results/audits/unsw_a99_specialist_code_build.json`,
`results/audits/unsw_a99_specialist_build_expected_outputs.csv`.

---

## 1. What was added

**New code modules (isolated, A9.9-specific):**
- `secureids/models/attack_family_specialist.py` — `AttackFamilySpecialistNet`, an isolated attack-only 9-way classifier (own encoder, **no binary head**). Separate from `SecureIDSHierarchicalAdvancedNet`; cannot change hierarchical or CICIDS behaviour.
- `secureids/training/attack_family_specialist_config.py` — torch-free config loader/validator with output-path safety.
- `secureids/training/attack_family_specialist_trainer.py` — torch-free dry-run plan + `select_attack_rows`, plus a lazily-torch `_execute_training` path that is **not invoked** in this build.
- `secureids/training/attack_family_specialist_evaluation.py` — NumPy oracle-vs-routed metric assembly (reuses the existing `hierarchical_metrics` primitives) + lazy-torch prediction helpers.

**CLI (additive):**
- `secureids/cli.py` — new `train-attack-family-specialist` subcommand and handler. `train-hierarchical` and all other commands are unchanged.

**Config:**
- `configs/training/experiments/unsw_a99_attack_family_specialist_seed42.yaml` — `status: not_run_yet`.

**Tests:**
- `tests/test_attack_family_specialist_config.py`, `..._safety.py`, `..._cli.py`, `..._metrics.py`.

**Docs/audit:** this report, `unsw_a99_specialist_code_build.json`, `unsw_a99_specialist_build_expected_outputs.csv`.

## 2. How the specialist router works

Frozen **A9 Head 1** is the binary **router**: every flow is first classified attack-vs-benign by the unchanged A9 model. Flows it calls "attack" are sent to the **specialist** (`AttackFamilySpecialistNet`), which predicts the attack family. The specialist has no binary head and is trained only to separate attack families, so all its capacity targets the overlapping `Analysis/Backdoor/DoS/Exploits` cluster instead of the easy benign-vs-attack task.

## 3. How A9 Head 1 is protected / frozen

- The A9 checkpoint `models/final/final_unsw_hierarchical.pt` is loaded **read-only** for routing and is never retrained, recalibrated, copied, or overwritten.
- The config enforces `frozen_a9_router.trainable: false` and `safety.freeze_a9_head1: true`; the loader rejects any config that sets these otherwise.
- The specialist saves to a **separate** `models/experiments/` path. Binary macro-F1/recall/FP stay at A9 values by construction.
- The future `_execute_training` path loads A9 only inside the evaluation/routing helpers (`torch.no_grad`, `eval()`), never in the specialist optimizer.

## 4. How attack-only training is enforced

- `select_attack_rows(y_attack_family, attack_family_mask)` returns rows where `mask == 1 AND y != -1` — the single source of truth for training-data selection. Benign rows are excluded.
- The config requires `training_data.attack_rows_only: true` and `split: train`; class weights are `compute_weights_from: train_only` with `allow_test_based_weights: false`.
- Selection is validation-only (`use_validation_only: true`, `select_by_test_metrics: false`).

## 5. How oracle vs routed metrics are separated

`attack_family_specialist_evaluation.py` produces two explicitly-tagged views:
- **`oracle`** — specialist on the **true** attack rows (teacher-forced); apples-to-apples with A9's 0.500429. Tagged `is_oracle: true`, `is_routed_deployment_metric: false`.
- **`routed`** — frozen A9 Head 1 routes detected attacks into the specialist; missed-as-benign rows count as errors. Tagged `is_routed_deployment_metric: true`.

`assemble_specialist_report(...)` bundles **three** blocks (A9 binary Head 1 / specialist oracle / routed end-to-end) and **raises** if the two views are mislabeled, so oracle numbers can never be reported as routed deployment numbers. Macro-F1 is over the full fixed 9-class set, so weak classes (Analysis, Backdoor, DoS, Shellcode, Worms) remain visible; no label merging is permitted.

## 6. CLI command and dry-run behaviour

```powershell
# Dry run (no training, no writes) — validates config + prints a plan, exits 0:
.\.venv\Scripts\python.exe -m secureids.cli train-attack-family-specialist `
  --config configs\training\experiments\unsw_a99_attack_family_specialist_seed42.yaml
```

- `--config` is required; `--execute` is required to actually train; `--overwrite` exists but **must not** be used without main-control approval.
- Without `--execute`, the command runs a **torch-free** dry run and writes nothing.
- The handler refuses unsafe output paths and refuses to overwrite an existing checkpoint unless `--overwrite`.
- It does **not** reuse or alter `train-hierarchical`.

Verified dry-run output (this build): plan printed, exit code 0, **no checkpoint or results dir created**.

## 7. Config path and expected outputs

- Config: `configs/training/experiments/unsw_a99_attack_family_specialist_seed42.yaml` (`status: not_run_yet`).
- Future (only after an approved `--execute` run): checkpoint `models/experiments/unsw_a99_attack_family_specialist_seed42.pt`, results under `results/experiments/unsw_a99_attack_family_specialist_seed42/` (oracle + routed metrics, per-class, rare, confusion, routing summary, history), report `docs/experiments/UNSW_A99_ATTACK_FAMILY_SPECIALIST_SEED42_REPORT.md`. See `unsw_a99_specialist_build_expected_outputs.csv`.

## 8. Tests run

```
.\.venv\Scripts\python.exe -m pytest tests/test_attack_family_specialist_config.py `
  tests/test_attack_family_specialist_safety.py tests/test_attack_family_specialist_cli.py `
  tests/test_attack_family_specialist_metrics.py -q
=> 19 passed in 2.39s
```

Coverage: config loading/validation (incl. rejection of final paths, test-based weights, test selection, trainable router, `training_executed: true`); attack-only row selection; output-path safety; model build/forward; CLI gate (requires `--config`, dry-run does not train/write, `train-hierarchical` unchanged); oracle-vs-routed separation (routed bounded by oracle; mislabel raises).

## 9. Safety checks / no-training confirmation

- No training, no evaluation, no preprocessing rebuild, no XAI, no Streamlit, no Git, no V1 change, no CICIDS behaviour change.
- A9 final checkpoint and `results/final/` are **unmodified**; **no** A9.9 checkpoint was created under `models/experiments/`.
- `train-hierarchical` behaviour is unchanged (additive CLI only).
- No existing target deliverable was overwritten — all four target files were confirmed new before writing (honoring the tightened no-overwrite rule).
- The `_execute_training` path exists for later use but is not invoked anywhere in this build.

## 10. Next main-control decision needed

**Approve or reject the manual seed42 training run** (`approve_or_reject_manual_seed42_training_run`). Only after approval should the operator run the `--execute` command in §6/§11 of the prep plan. This build did not train, evaluate, create checkpoints, or promote anything.
