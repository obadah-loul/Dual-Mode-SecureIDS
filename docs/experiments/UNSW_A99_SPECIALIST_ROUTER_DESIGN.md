# UNSW A9.9 — Attack-Family Specialist Router Design

Status: `design / prep only — no training, no evaluation, no checkpoint, no promotion`
Generated: `2026-06-25`
Companion: `docs/experiments/UNSW_A99_ATTACK_FAMILY_SPECIALIST_PREP_PLAN.md`,
`results/audits/unsw_a99_specialist_prep.json`,
`results/audits/unsw_a99_expected_runs.csv`.

This document is the architecture/design spec for the approved next UNSW direction. **It does not implement, train, or evaluate anything.** Code is deferred to a separately-approved build step.

---

## 1. How the specialist router works

The hierarchical IDS becomes an explicit two-component pipeline:

1. **Router = frozen A9 Head 1 (binary).** Every test flow first passes through the **existing, unchanged** A9 model. Its binary head decides Benign/Normal vs Attack at the existing threshold 0.5. The router's behaviour, weights, and metrics are exactly A9's — nothing about Head 1 is retrained or recalibrated.
2. **Specialist = a dedicated attack-only family classifier.** Flows the router calls "attack" are sent to a new specialist that predicts one of the 9 UNSW attack families (`0 Generic … 8 Worms`). The specialist is trained **only on attack rows** and is solely responsible for family attribution.

Today A9 does both jobs in one shared encoder: `encoder → gate → {binary_head, attack_head=Linear(128→9)}`. Because the binary objective is near-saturated, the shared 128-d embedding is shaped mostly by the easy benign-vs-attack task (root cause **RC3**), leaving little room to carve the overlapping `Analysis/Backdoor/DoS/Exploits` boundaries. The specialist **removes benign-vs-attack pressure from the family learner** so its entire capacity is spent on family separation.

### Two specialist variants (primary vs ablation)

- **A9.9 primary — independent specialist encoder.** A standalone classifier with its **own** encoder + attack-family head, trained from scratch on attack rows. Maximum decoupling from the binary-dominated embedding. This is the recommended variant.
- **A9.9 ablation — frozen-embedding specialist.** Reuse the **frozen** A9 `encoder+gate` embedding as fixed input features and train only a new attack head on top. Cheaper, but it inherits the binary-dominated embedding (the RC3 problem we are trying to escape), so it is expected to be weaker. Keep as a diagnostic ablation only.

## 2. How A9 Head 1 remains protected / frozen

- The A9 checkpoint `models/final/final_unsw_hierarchical.pt` is **loaded read-only** for routing. It is **never** retrained, fine-tuned, recalibrated, copied, or overwritten by A9.9.
- The specialist is a **separate** `nn.Module` saved to a **separate** path under `models/experiments/`. A9's final artifacts under `models/final/` and `results/final/` are untouched.
- Because Head 1 is frozen, **binary macro-F1, recall, FP, and the missed-as-benign count stay exactly at A9 values** by construction. The router cannot regress; only family attribution can change.
- In code terms (for the future build): the specialist trainer must `torch.load` A9 with `requires_grad=False` / `eval()` and use it **only** in the evaluation/routing path — never in the specialist's optimizer.

## 3. How the attack-only specialist is trained (train attack rows only)

- **Training data:** UNSW **train** split attack rows only — i.e. rows where `attack_family_mask == 1` (`y_attack_family ∈ {0..8}`, never the ignore index −1). Benign rows are excluded from specialist training entirely.
- **Protocol (unchanged from A9):** corrected A8.8/A9 protocol — train/val from the 175,341-row partition (local `UNSW_NB15_testing-set.csv`), final test on the 82,332-row partition (local `UNSW_NB15_training-set.csv`). Same preprocessor; **no preprocessing rebuild**.
- **Loss:** CrossEntropy over the 9 attack families with **train-only** class weights (same sqrt-inverse-frequency, mean-normalized policy as A9; computed from train attack labels only). Any sampling probabilities, if used, are computed from **train attack labels only**.
- **Selection:** **validation-only**, using the **val split attack rows** (oracle attack-family macro-F1 on val). A single final test pass after selection. The hardcoded joint `val_hierarchical_score` does not apply to the specialist; the specialist's selection metric is its own attack-family macro-F1 on validation attack rows (documented in its config/report).
- **No test labels** are ever used for training, weights, sampling, threshold/selection, or model choice.

## 4. How routed metrics differ from oracle metrics

Two clearly-separated views must always be reported side by side:

| View | What is fed to the specialist | Compares against | Meaning |
| --- | --- | --- | --- |
| **Oracle attack-family** | the **true** attack rows (teacher-forced, perfect routing) | A9 attack-family macro-F1 **0.500429** | upper-bound family-separation quality; apples-to-apples with A9's teacher-forced Head 2 |
| **Routed end-to-end** | only rows the **frozen A9 Head 1** labels "attack" | A9 correct-attribution rate **0.7208** and missed-as-benign **0.0510** | deployment reality; capped by Head 1 recall |

Key consequence: **routed performance is bounded by A9 Head 1.** Head 1 misses 2,310 attacks (5.1%) as benign; the specialist can never recover those. So routed correctly-attributed ≈ (specialist oracle accuracy) × (Head 1 attack recall 0.949). Benign flows Head 1 wrongly flags as attack (6,186) are already counted as binary false positives and are **not** attack rows, so they are not given a family label in the headline attack-family metric.

## 5. What will and will not be claimed

**Will claim (only after training + evaluation):**
- Oracle attack-family macro-F1 vs A9 0.500429, as a 3-seed mean ± std.
- Rare-class macro-F1 vs A9 0.385669.
- Routed end-to-end correct-attribution and missed-as-benign, clearly labelled as routed (not oracle).
- Per-class movement for Analysis / Backdoor / DoS / Shellcode / Worms.

**Will NOT claim:**
- That the specialist replaces A9 — not unless it passes the multi-seed gates **and** main control approves.
- Oracle numbers presented as routed/deployment numbers, or vice versa.
- Any single-seed result as final.
- Attack-family macro-F1 **> 0.9** as realistic for this setup (see §9).
- Improvement from hiding, merging, or relabelling weak classes.

## 6. Why this does not replace A9 yet

- Nothing is trained or evaluated in this prep phase; there are no A9.9 metrics yet.
- Even once trained, replacement requires passing the predefined multi-seed promotion gates (§7 of the prep plan) **and** explicit main-control approval, executed through a separate backup-gated promotion plan. A9 stays the official UNSW final until then.

## 7. How this avoids test tuning

- Validation-only model selection and any calibration; the **test split is touched once**, after every choice is frozen.
- Class weights / sampling from **train attack labels only**; no val/test labels for weights, sampling, or preprocessing.
- Promotion gates and all artifact paths are **predefined** (this document + the expected-runs CSV) before any run.
- Isolated experiment paths; A9 final artifacts never read for tuning and never written.

## 8. How weak classes remain visible (not hidden)

- Metrics are computed over the **full fixed 9-class set**; collapsed classes (Analysis, Backdoor) keep scoring ~0 and continue to drag macro-F1 — they are never dropped to inflate the average.
- Per-class precision/recall/F1 and the attack-family confusion matrix are reported for **all 9 families** every run.
- The `Analysis/Backdoor/DoS/Exploits` cluster is reported explicitly; an optional **grouped/super-class view** may be added only as a **diagnostic** companion, never as a replacement for the 9-class metric.
- Rare-class precision floors (Shellcode, Worms) are hard gates so we do not repeat the A9.6 recall-for-precision collapse.

## 9. Why macro-F1 > 0.9 is not realistic here

On the corrected official UNSW-NB15 split, `Analysis/Backdoor/DoS/Exploits` overlap in the 192-feature flow space **by construction**: 70.8% of true Analysis and 70.2% of true Backdoor fall into DoS, and Exploits↔DoS leak both ways. Published 9-class UNSW work routinely reports near-zero Analysis/Backdoor F1 and macro-F1 in the ~0.45–0.60 band (high weighted-F1 ~0.75–0.80 is dominated by Generic/Exploits). A macro-F1 > 0.9 would require near-perfect separation of intrinsically-entangled families and is not achievable from these features without changing the problem (merging families or adding richer data). **Realistic A9.9 target: oracle attack-family macro-F1 0.52–0.58 (3-seed mean), stretch ~0.60.**

## 10. Integration boundaries (for the future build step)

- New code lives in **new, isolated** files/modules named with `attack_family_specialist` / `a99`. It must **not** change `train-hierarchical`, the schema router, the CLI defaults, CICIDS, or dashboard behaviour unless the new mode is explicitly invoked.
- A **new** CLI subcommand (e.g. `train-attack-family-specialist`) is required. The existing `train-hierarchical` is unsuitable: it trains the joint model, and its gate `_validate_train_hierarchical_cli_gate` would reject a `unsw_a99_…` config name (UNSW configs must contain `hierarchical` or start with `unsw_a9_`).
- New code ships with **lightweight unit tests** (shape/freeze/oracle-vs-routed-separation/leakage-guard) before any training run.
- No final checkpoint or final result is touched at any point.
