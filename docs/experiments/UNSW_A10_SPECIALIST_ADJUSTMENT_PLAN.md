> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# UNSW A9.10 — Adjusted Specialist Plan

Status: `deep analysis / planning only — no training, no code, no config, no implementation`
Generated: `2026-06-25`
Companion: `docs/experiments/UNSW_A99_SPECIALIST_FAILURE_REVIEW.md`,
`results/audits/unsw_a99_specialist_failure_review.json`,
`results/audits/unsw_a10_specialist_adjustment_plan.json`,
`results/audits/unsw_a10_candidate_matrix.csv`.

---

## 1. Is A9.10 worth attempting?

**Yes — but exactly ONE bounded seed42 screen of the corrected design, with a hard stop if it fails.**

A9.9 failed for two identifiable, fixable reasons: the independent encoder **overfit** (val 0.5863 → test
0.4747) and it **discarded the shared representation** that the joint A9 model learned from all 149,039 rows
(incl. benign) — regressing Fuzzers/Shellcode/Worms. There is one untried variant that addresses **both**
at low cost. It deserves a single fair test.

**Honest caveat:** A9.6 (loss weight), A9.7/A9.8 (branch capacity), and A9.9 (independent specialist) have
**all** failed to beat A9. The attack-family ceiling (~0.50–0.60) is dominated by intrinsic
Analysis/Backdoor/DoS/Exploits overlap (RC1). So the prior probability of clearing the gate is modest, and
A9.10 is explicitly the **last** specialist attempt: if its seed42 screen fails, stop and keep A9.

## 2. Recommended A9.10 idea (one design only)

**`A9.10` — frozen-A9-embedding regularized head.**

- **Freeze the entire A9 encoder + gate**; use its 128-d embedding as **fixed features** for attack rows.
- Train **only** a small, strongly-regularized attack-family head (linear, or one shallow GELU layer).
- **Strong regularization:** higher dropout, weight decay, and **label smoothing**.
- **Tempered class weights:** flatter (less aggressive) than sqrt-inverse-frequency, to protect rare-class
  precision and stop the Shellcode over-prediction seen in A9.9.
- **Generalization-aware selection / earlier stopping** to close the val→test gap.
- Keep **A9 Head 1 as the frozen binary router** (binary metrics unchanged by construction).

## 3. What A9.10 changes from A9.9

| Aspect | A9.9 (failed) | A9.10 (proposed) |
| --- | --- | --- |
| Encoder | new, trained from scratch on attack rows | **frozen A9 encoder reused** (shared representation kept) |
| Head | `[256,128]` encoder + head | **linear or one shallow layer** (tiny, less to overfit) |
| Regularization | dropout 0.2, wd 1e-4 | **higher dropout + wd + label smoothing** |
| Class weights | sqrt-inverse-freq (aggressive) | **tempered/flatter** (protect rare precision) |
| Selection | best val macro-F1 | **generalization-aware / earlier stop** |
| Router | frozen A9 Head 1 | frozen A9 Head 1 (unchanged) |

## 4. Codex implementation or config-only?

**Requires Codex implementation (code), not config-only.** Freezing and extracting the A9 embedding,
label smoothing, class-weight tempering, and a generalization-aware selection criterion are new behaviors
not exposed by the current config. (A purely config-only fallback — `A10b`: smaller `hidden_dims` + dropout
0.4 + weight_decay 1e-3 + earlier stopping on the existing independent specialist — is possible but is
**lower value** because it does **not** restore the shared representation, which was the deeper A9.9 failure.)

## 5. Expected number of manual runs

**1** — a single seed42 screen first. A 3-seed (42/123/999) confirmation runs **only if** seed42 clears the
gates. No single-seed promotion; no confirmation for a failed screen.

## 6. Expected benefit / risk

- **Benefit:** addresses both A9.9 failure modes; realistic oracle attack-family macro-F1 ~**0.50–0.53**, a
  fair chance to recover rare-class macro toward A9's 0.385669 by protecting Shellcode/Worms precision;
  binary unchanged.
- **Risk:** modest. A9.7/A9.8 showed Head-2 capacity on the shared embedding gives only +0.0045 (within the
  ~0.0143 seed-noise band), so A9.10 may also land below the gate. If so, the specialist direction is
  exhausted.

## 7. Promotion / rejection criteria (pre-registered)

**Seed42 screen — proceed only if all hold:**
- Oracle attack-family macro-F1 ≥ **0.515429** (A9 0.500429 + 0.015 noise band) **and** > A9 on test.
- Rare-class macro-F1 ≥ **0.385669** (no regression vs A9).
- Shellcode/Worms precision floors not breached (no A9.9-style precision collapse).
- Binary router unchanged (frozen A9 — holds by construction).
- Val→test gap materially smaller than A9.9's 0.1116 (evidence the fix worked).

**Promotion (later):** only on a 3-seed mean ± std that clears the noise band vs the A9 linear 3-seed mean
(0.494965), with rare and precision gates met, and explicit main-control approval. Never from one seed.

**Reject / stop:** if the seed42 screen fails any gate, **reject A9.10 and stop specialist work**; keep A9.

## 8. Why this avoids the A9.9 failure mode

Freezing the A9 encoder **retains** the benign-informed, full-data representation that A9.9 threw away (the
direct cause of the Fuzzers/Shellcode/Worms regressions), and a **tiny regularized head** has far less
capacity to overfit (the cause of the 0.1116 val→test gap). Tempered weights stop the rare-class precision
collapse. It is the smallest change that targets the measured causes.

## 9. What to avoid

- No test tuning; validation-only selection/calibration; single final test.
- No hiding/merging weak classes; report Analysis/Backdoor/DoS/Shellcode/Worms in full.
- Do not report oracle metrics as routed/deployment metrics.
- No random reruns; no fishing for a lucky seed; no 3-seed confirmation of a failed screen; no single-seed
  promotion; no fake improvements.
- Do not enlarge or re-run the A9.9 independent specialist (proven failure mode).

## 10. Exact next main-control decision needed

**Approve Codex A9.10-prep (frozen-A9-embedding regularized head), or stop UNSW specialist work and move to
federated/security** with A9 frozen as the final UNSW model. If A9.10-prep is approved, it is **code build +
seed42 config preparation only** — training remains a separate, later approval; and a failed seed42 screen
auto-stops the specialist direction.
