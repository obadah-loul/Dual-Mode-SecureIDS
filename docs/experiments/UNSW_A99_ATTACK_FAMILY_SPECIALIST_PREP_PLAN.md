# UNSW A9.9 — Attack-Family Specialist Prep Plan (A9.9-prep)

Status: `prep only — no training, no evaluation, no checkpoint, no config, no code, no promotion`
Generated: `2026-06-25`
Companion: `docs/experiments/UNSW_A99_SPECIALIST_ROUTER_DESIGN.md`,
`results/audits/unsw_a99_specialist_prep.json`,
`results/audits/unsw_a99_expected_runs.csv`.

---

## 1. Purpose and scope

Prepare the approved next UNSW direction — the **A9.9 attack-family specialist router** — as planning/scaffolding only. This phase **creates documents and an audit record**; it does **not** train, evaluate, create checkpoints, create configs, change preprocessing, replace A9, or promote anything.

- **Current baseline:** A9 corrected-protocol hierarchical (`models/final/final_unsw_hierarchical.pt`), frozen but reopened for controlled improvement. Binary macro-F1 0.894488, attack-family macro-F1 0.500429, rare-class macro-F1 0.385669.
- **Approved direction:** freeze A9 Head 1 as the binary router; later train a dedicated attack-only family classifier; report routed vs oracle metrics separately; do not replace A9 yet.
- **Why:** A9.6 (attack-loss increase) failed; A9.7 (stronger branch) did not clearly beat A9; A9.8 confirmed branch gains sit inside the seed-noise band. The specialist is the highest-value untried direction that protects the accepted binary detector while directly targeting family separation.

## 2. Were code changes needed in this prep phase? — No

**No code or config was created in this prep phase**, by design. Justification (verified from the codebase, read-only):

- The specialist (frozen A9 Head 1 router + dedicated attack-only classifier) is **not** implementable with the current CLI/trainer. The existing `train-hierarchical` subcommand trains the **joint** `SecureIDSHierarchicalAdvancedNet` (`encoder → gate → {binary_head, attack_head}`) from scratch — there is no frozen-Head-1, attack-only specialist mode.
- The `train-hierarchical` gate `_validate_train_hierarchical_cli_gate` (in `secureids/cli.py`) would **reject** a config named `unsw_a99_attack_family_specialist_seed42.yaml` for UNSW: it requires the config name to contain `hierarchical` **or** start with `unsw_a9_` (trailing underscore). `unsw_a99_` matches neither.
- Therefore a seed42 config **on its own would be non-runnable** and could mislead. Creating unapproved, unrunnable code/config also conflicts with the tightened process rule ("prep means create only approved prep files").

**Conclusion:** the specialist requires a **separately-approved code build step**. This prep produces the design + audit so that build can proceed cleanly if approved. The required build artifacts are listed in §6.

## 3. Controlled run sequence (planned, not executed)

1. **A9.9-prep (this phase):** docs + audit JSON/CSV only.
2. **A9.9-build (needs approval):** implement the isolated specialist module, trainer, evaluation, a new CLI subcommand, the seed42 config (marked NOT RUN YET), and unit tests.
3. **A9.9-screen (needs approval):** one-seed screen, **seed 42** only. De-risk the code path; get a directional oracle + routed read.
4. **A9.9-confirm (needs approval):** 3-seed confirmation **42 / 123 / 999**; promotion decided only from the aggregate.
5. **A9.9b (optional, only-if-justified-later):** one precision variant (train-only attack-row class-balancing or a rare-class weight temperature).

The user runs training **manually** and **only after** the relevant main-control approval at each gate.

## 4. Config / output naming plan (isolated paths; none created yet)

| Artifact | Path |
| --- | --- |
| Config seed42 | `configs/training/experiments/unsw_a99_attack_family_specialist_seed42.yaml` |
| Config seed123 | `configs/training/experiments/unsw_a99_attack_family_specialist_seed123.yaml` |
| Config seed999 | `configs/training/experiments/unsw_a99_attack_family_specialist_seed999.yaml` |
| Checkpoint seed42 | `models/experiments/unsw_a99_attack_family_specialist_seed42.pt` |
| Checkpoint seed123 | `models/experiments/unsw_a99_attack_family_specialist_seed123.pt` |
| Checkpoint seed999 | `models/experiments/unsw_a99_attack_family_specialist_seed999.pt` |
| Results seed42 | `results/experiments/unsw_a99_attack_family_specialist_seed42/` |
| Results seed123 | `results/experiments/unsw_a99_attack_family_specialist_seed123/` |
| Results seed999 | `results/experiments/unsw_a99_attack_family_specialist_seed999/` |
| Report seed42 | `docs/experiments/UNSW_A99_ATTACK_FAMILY_SPECIALIST_SEED42_REPORT.md` |

All under `…/experiments/…`. Nothing in `models/final/` or `results/final/` is created or touched. See `results/audits/unsw_a99_expected_runs.csv` for the full run table.

> **Note on the config name vs the existing gate:** because `unsw_a99_…` would be rejected by the current `train-hierarchical` gate, the A9.9-build step must wire a **new** subcommand whose own gate accepts the specialist config — it must **not** weaken the existing `train-hierarchical` gate.

## 5. Manual seed42 command (proposed, NOT executed, NOT yet runnable)

> **Manual command is proposed but NOT runnable until config/module prep is approved/created.** The specialist subcommand, module, and seed42 config do not exist yet, and the existing `train-hierarchical` cannot run the specialist.

Proposed future command (PowerShell, from project root), using the **proposed** new subcommand:

```powershell
# DO NOT RUN YET — requires the approved A9.9-build (module + new CLI subcommand + seed42 config).
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
.\.venv\Scripts\python.exe -m secureids.cli train-attack-family-specialist `
  --config configs\training\experiments\unsw_a99_attack_family_specialist_seed42.yaml `
  --execute
```

- `--execute` mirrors the existing `train-hierarchical` convention (which requires `--execute` to actually run; without it the command must no-op/plan).
- The existing `train-hierarchical --config … --execute` form is **not** a substitute: it would train the joint model and its gate rejects the `unsw_a99_` name.

## 6. Required A9.9-build artifacts (only if approved next)

- `secureids/models/attack_family_specialist.py` — isolated specialist model (independent encoder + 9-way attack head; primary variant).
- `secureids/training/attack_family_specialist_trainer.py` — attack-rows-only trainer; train-only class weights; validation-only selection; loads frozen A9 only for routing.
- `secureids/evaluation/attack_family_specialist_evaluation.py` — computes **oracle** and **routed** metrics separately using a frozen A9 Head 1.
- New CLI subcommand `train-attack-family-specialist` in `secureids/cli.py` — **additive**; does not alter `train-hierarchical`, the schema router, CLI defaults, CICIDS, or the dashboard.
- `configs/training/experiments/unsw_a99_attack_family_specialist_seed42.yaml` — marked `status: not_run_yet`.
- `tests/test_attack_family_specialist.py` — lightweight unit tests (see §9).

## 7. Safety and no-fake-results rules (enforced)

- Do **not** tune on test. Do **not** use test labels for training, weights, sampling, threshold selection, or model selection.
- Do **not** hide weak classes; do **not** merge labels to inflate scores. Metrics over the full fixed 9-class set.
- Do **not** claim the specialist replaces A9 unless validated and main-control-approved.
- Do **not** report oracle metrics as routed deployment metrics. Always report, separately:
  1. **A9 binary Head 1** metrics (frozen, unchanged),
  2. **specialist oracle** attack-family metrics (teacher-forced on true attack rows),
  3. **routed end-to-end** metrics (frozen Head 1 routes into the specialist).
- Do **not** compare a single-seed A9.9 result against a multi-seed standard as if final. Do **not** promote on seed42 alone.
- Keep A9 frozen; isolated experiment paths; no `models/final/` or `results/final/` change.

## 8. Promotion / rejection criteria

A9.9 continues beyond seed42 and may later be promoted **only if** (all hold):

- Oracle attack-family macro-F1 improves **meaningfully** over A9 0.500429.
- Rare-class macro-F1 improves over (or at least does not drop below) A9 0.385669.
- Routed end-to-end metrics are clearly reported and not misleading.
- Binary routing remains A9-based and unchanged.
- No leakage, fake metrics, or path contamination.
- Weak classes are still shown — especially Analysis, Backdoor, DoS, Shellcode, Worms.
- No evidence of severe specialist overfit (train vs val vs test gap reported).

**Seed42 screen gates (pass to proceed to 3-seed confirmation):**

- Oracle attack-family macro-F1 ≥ **0.500429 + 0.015 = 0.515429** (A9.8 showed ~±0.0143 seed noise, so a smaller lift is indistinguishable from noise).
- Rare-class macro-F1 **not below** 0.385669.
- Binary metrics reported from the **frozen A9 Head 1** and unchanged.
- The Analysis / Backdoor / DoS cluster shows at least some improvement or cleaner attribution.
- If gains are **oracle-only** while routed metrics fail, mark the run **diagnostic, not a promotion candidate**.

**Promotion comparison basis:** the 3-seed (42/123/999) mean ± std vs the **A9 linear 3-seed mean (0.494965)** — not vs the favorable A9 seed-42 point (0.500429) — to keep the bar fair, and the gain must clear the noise band.

## 9. Tests plan (for the future A9.9-build; none added in this prep)

When the specialist code is built, add `tests/test_attack_family_specialist.py` with lightweight unit tests:

- **Frozen-router test:** loading A9 and stepping the specialist optimizer leaves all A9 Head 1 parameters unchanged (`requires_grad=False`, params byte-identical before/after a step).
- **Attack-rows-only test:** the specialist trainer consumes only `attack_family_mask == 1` rows; a synthetic all-benign batch yields no specialist gradient.
- **Oracle≠routed test:** the evaluator returns distinct oracle and routed metric dicts and never overwrites one with the other.
- **Leakage guard:** class weights / sampling are computed from train labels only (val/test label arrays are never read in the weight path).
- **Shape/contract test:** specialist outputs `(batch, 9)` logits; 9-class macro-F1 includes all families.

Run only the new tests, e.g.:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_attack_family_specialist.py -q
```

No tests were added or run in this prep phase (no code was added).

## 10. Post-run validation plan for seed42 (for later, after an approved run)

After the manual seed42 run (once built and approved), validate **without** any test tuning:

1. Confirm isolated outputs exist (`models/experiments/unsw_a99_attack_family_specialist_seed42.pt`, `results/experiments/unsw_a99_attack_family_specialist_seed42/…`) and that `models/final/` + `results/final/` are **unchanged** (size + timestamp + hash of `final_unsw_hierarchical.pt`).
2. Read the seed42 `test_metrics` and confirm the three metric views are reported separately (A9 binary / specialist oracle / routed).
3. Check the seed42 screen gates (§8). Confirm rare-class precision did not collapse (Shellcode/Worms).
4. Confirm the run used validation-only selection (`checkpoint_not_selected_by_test_metrics: true`) and train-only weights (no val/test labels).
5. Confirm reproducibility metadata (seed 42, config path, protocol = corrected A8.8/A9, input_dim 192, attack_head_dim 9).
6. Record a seed42 audit JSON + the seed42 report; **do not** promote and **do not** start seed123/999 until main control approves confirmation.

## 11. Risks

- Specialist **overfitting** on fewer attack rows (train vs val vs test gap) — mitigate with validation-only selection, dropout, and reporting the gap.
- Class-balancing / weighting can distort priors and **rare precision** — gate on precision floors (avoid the A9.6 pattern).
- **Routed** end-to-end remains capped by A9 Head 1's 2,310 missed attacks — oracle gains may not fully transfer to routed numbers.
- **Oracle-vs-routed confusion** in reporting — enforce separate, clearly-labelled metric blocks.
- Added specialist artifact increases **model-management** complexity — isolated paths + naming discipline.
- **Intrinsic ceiling** (~0.60) from RC1 overlap — do not over-promise; a within-noise "win" is not a promotion.

## 12. Next main-control decision needed

**Approve or reject the A9.9 specialist code build** (isolated module + new `train-attack-family-specialist` CLI subcommand + seed42 config marked "not run yet" + unit tests). Only after that build is approved and created can the **manual seed42 training run** be separately approved (`approve_or_reject_manual_seed42_training_run`). No training, checkpoint, config, or code is produced without explicit approval at each gate.
