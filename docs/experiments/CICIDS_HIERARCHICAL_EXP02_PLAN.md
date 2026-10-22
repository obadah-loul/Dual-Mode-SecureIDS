> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# CICIDS Hierarchical EXP02 — Plan (design only)

Status: `Plan only — NOT implemented, NOT trained`. No EXP02 config, checkpoint, or metrics were
created. Requires main-control approval before preparation/training.

Generated: `2026-06-25`

Companion: `results/audits/cicids_hierarchical_exp02_plan.json`,
`results/audits/cicids_hierarchical_advanced_improvement_roadmap.csv`,
`docs/experiments/CICIDS_HIERARCHICAL_EXP01_FAILURE_ANALYSIS.md`.

---

## 1. Selected EXP02

**`cicids_hierarchical_exp02_attack_loss_weight`** — a **moderate attack-family loss-weight increase**
(`attack_loss_weight` 1.0 → 1.5), on the **baseline linear Head 2** (revert EXP01's MLP). One
controlled factor vs the accepted baseline; **config-only** (no code, no preprocessing, no taxonomy,
no model change).

## 2. Why this idea (it follows directly from EXP01's failure)

EXP01 proved Head-2 **capacity** is not the lever. The failure analysis shows two things the encoder
is doing wrong: (a) it leaves the **DoS-SlowHTTPTest ↔ FTP-BruteForce** pair entangled (~96% of error
mass), and (b) the selected epoch drifted to a **binary-conservative** Head 1 (more missed attacks),
because binary is near-ceiling and the `0.5/0.5` selection rewards it.

The one untested **training** lever that changes *what the shared encoder optimizes for* — rather than
how big the head is — is the **loss balance**. Increasing `attack_loss_weight` gives the
attack-family objective more gradient in the shared encoder, pushing it to (i) carve apart the
confused pair that capacity alone could not, and (ii) resist drifting to a binary-conservative point.
This is the most **controlled, config-only, reproducible** single-factor next step.

## 3. Why better than repeating EXP01 / making Head 2 bigger now

- Repeating EXP01 or enlarging Head 2 attacks a bottleneck that EXP01 **disproved** (the hard pair did
  not move; the embedding lacks the separating information, so a bigger head cannot help).
- `attack_loss_weight` changes the **shared encoder's** optimization, which is where the
  SlowHTTPTest/FTP separation must come from — exactly what a head-only change cannot reach.
- It is cheaper and cleaner: one scalar in YAML, no new code paths, fully reproducible, train-only.

## 4. Exact target metrics

- **Primary:** test **attack-family macro-F1** (vs baseline 0.849111), judged on the **reliable**
  signal — specifically **DoS-SlowHTTPTest F1/recall** (baseline 0.553 / 0.437) and **FTP-BruteForce
  precision** (baseline 0.688). These are the only large-support, low-noise classes with headroom.
- **Guardrails (must not regress beyond tolerance):** rare-class macro-F1 (baseline 0.716987; treat
  as guardrail not target — it is noisy at 12–96 samples), binary macro-F1 (≥ ~0.965), end-to-end
  correct attribution (baseline 0.909008), attack-missed-as-benign rate (baseline 0.053807).
- **Do NOT** optimize rare-class macro-F1 directly (noise) and **do NOT** tune any threshold on test.

## 5. Expected benefit and risk (honest)

- **Expected benefit:** small and **uncertain** — roughly +0.00 to +0.02 attack-family macro-F1 if the
  pressure helps the SlowHTTPTest/FTP pair; the real win would be SlowHTTPTest recall rising from
  0.437.
- **Risk:** (a) **A9.6 precedent** — on UNSW, `attack_loss_weight` 1.5 *hurt* Head 2 and rare
  precision; it is a blunt, global lever. (b) The SlowHTTPTest/FTP overlap may be **feature-limited**,
  in which case no loss trick fixes it (parallels UNSW Analysis/Backdoor). (c) Rare-class precision
  could dip. These risks are why EXP02 is a **controlled test with explicit rejection criteria**, not
  a presumed win.

## 6. Implementation scope (if approved)

- **Config-only.** Copy `configs/training/cicids2018_hierarchical.yaml`; change exactly two things vs
  baseline: `loss.attack_loss_weight: 1.0 → 1.5`, and keep Head 2 **linear** (omit/disable
  `attack_head_type: mlp`). Everything else (encoder, binary head, train-only class weights, cap,
  optimizer, batch, epochs, early stopping, `0.5/0.5` validation selection, seed) unchanged.
- **No code change.** `attack_loss_weight` is already wired through `compute_hierarchical_loss`.
- **Strongly recommended:** run **≥3 seeds** (42, 43, 44) and compare 3-seed means; single-seed deltas
  are within noise.

## 7. Proposed paths (create only after approval)

- Config: `configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight.yaml`
- Checkpoint: `models/experiments/cicids_hierarchical_exp02_attack_loss_weight.pt`
- Results dir: `results/experiments/cicids_hierarchical_exp02_attack_loss_weight/`
- Manifest: `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp02_attack_loss_weight.json`
- Report: `docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_REPORT.md`

Must **not** write to `models/final/final_cicids_hierarchical.pt`,
`results/final/hierarchical/cicids/`, the baseline manifest/report, or any EXP01 path.

## 8. Files that would be modified/created if approved

- Created: the EXP02 config + all EXP02 output artifacts above; a prep doc/JSON (mirroring EXP01).
- Modified: **none** in production code (config-only). A small EXP02 prep test may be added (mirroring
  `tests/test_cicids_exp01_preparation.py`) asserting one-factor change + isolated paths.

## 9. Promotion criteria (3-seed mean unless noted)

Promote EXP02 over baseline only if **all** hold:
- Attack-family macro-F1 ≥ **0.855** (baseline 0.849 + a margin beyond the ~±0.003 noise band).
- **DoS-SlowHTTPTest F1 improves** materially (e.g., ≥ 0.62, recall ≥ 0.55) — the reliable signal.
- Rare-class macro-F1 ≥ 0.700 (no collapse; allow noise tolerance, no rare class drops to ~0).
- Binary macro-F1 ≥ 0.965 and end-to-end correct attribution ≥ 0.905.
- Attack-missed-as-benign rate ≤ 0.057.
- No baseline/EXP01 overwrite; validation-only selection; train-only weights; single final test.

## 10. Rejection criteria

- Attack-family macro-F1 not beyond the noise band, or DoS-SlowHTTPTest unchanged (the pair did not
  separate).
- Rare-class precision collapse (the A9.6 pattern), or any rare class → ~0.
- Binary macro-F1 < 0.965, or missed-attack rate materially worse, or end-to-end attribution worse.
- Any protocol/model/preprocessing/taxonomy change beyond the single `attack_loss_weight` factor;
  any test-set tuning; unstable/NaN training; baseline or EXP01 artifacts overwritten.

## 11. Safety constraints

Config-only; train-only class weights; validation-only checkpoint selection; one final test after
selection; no test tuning; no taxonomy/preprocessing change; no model-zoo (single accepted final
model + isolated experiment checkpoints); no UNSW/A8.8 wording (H2 fix); baseline preserved.

## 12. Manual training command template (run only after approval)

```powershell
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m secureids.cli train-hierarchical --dataset cicids --config configs/training/experiments/cicids_hierarchical_exp02_attack_loss_weight.yaml --execute
```
(Repeat with seed 43 and 44 via per-seed config copies for the 3-seed mean.)

## 13. EXP03–EXP10 roadmap

- **EXP03 — Head-2 focal loss (gamma ~1.5–2.0), attack rows only, linear head** *(recommend_after_exp02;
  code change)*: if EXP02's global pressure is too blunt, focal down-weights the 10 ceiling classes and
  concentrates gradient on the hard SlowHTTPTest/FTP examples. Gate on rare-class precision floors
  (focal+class-weights can collapse rare precision — see UNSW A9.7-design).
- **EXP04 — targeted train-only class-weight emphasis on the confused pair / weak_hard_classes**
  *(needs_main_control_decision; per-class weighting risks model-zoo-style hacking)*.
- **EXP05 — two-stage fine-tuning** (joint warmup → partial encoder fine-tune for attack-family)
  *(possible_later; code change, medium risk; frozen encoder can't separate an entangled pair)*.
- **EXP06 — validation-only Head-1 threshold calibration** to recover the missed-attack rate
  *(possible_later; helps routing/recall, not Head-2 macro; validation-only, never test)*.
- **EXP07 — feature engineering to separate SlowHTTPTest/FTP** (timing/port/protocol features)
  *(needs_main_control_decision; NEW preprocessing protocol, breaks comparability — not a quick
  experiment; only if EXP02/03 prove the gap is feature-limited)*.
- **EXP08 — attack-only balanced sampler** *(possible_later; the hard pair is not rare, so limited
  upside; rare-class oversampling risks overfit/leakage-style optimism)*.
- **EXP09 — class-balanced (effective-number) loss** *(possible_later; similar to weighting, unlikely
  to break the pair)*.
- **EXP10 — accept baseline and stop CICIDS attack-family tuning** *(recommend if EXP02/03 do not beat
  baseline beyond noise: 0.849 macro / 0.972 binary is already strong and largely ceiling-bound)*.

Cross-cutting rule for all experiments: **≥3 seeds, mean ± std**, decisions on the reliable
(large-support) classes, rare-class macro-F1 as a guardrail, baseline frozen, isolated paths, no test
tuning.

## 14. Next main-control decision

Approve or reject **preparing EXP02** (`attack_loss_weight` 1.0→1.5, linear Head 2, config-only,
≥3 seeds). No config or training has been created/run.
