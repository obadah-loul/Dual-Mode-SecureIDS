# UNSW A9.9 Attack-Family Specialist — Formal Failure Review

Status: `deep analysis / audit only — no training, no evaluation, no code, no config`
Generated: `2026-06-25`
Companion: `results/audits/unsw_a99_specialist_failure_review.json`,
`docs/experiments/UNSW_A10_SPECIALIST_ADJUSTMENT_PLAN.md`,
`results/audits/unsw_a10_specialist_adjustment_plan.json`,
`results/audits/unsw_a10_candidate_matrix.csv`.

---

## 1. A9.9 seed42 status

**FAIL_SCREEN.** The A9.9 attack-family specialist (independent encoder, trained on UNSW train attack
rows only, behind the frozen A9 Head 1 router) failed both pre-registered seed42 screen gates on test.
A9 remains the accepted UNSW final baseline; the A9 final checkpoint was never modified. The specialist
checkpoint exists and its artifacts were repaired from that checkpoint with no retraining.

## 2. Metrics summary (test split; selection was validation-only)

| Metric | A9.9 seed42 | Gate / A9 | Result |
| --- | ---: | --- | --- |
| Oracle attack-family macro-F1 | **0.474716** | ≥ 0.515429 (A9 0.500429) | **FAIL** (below gate AND below A9) |
| Oracle accuracy | 0.754015 | — | — |
| Rare-class macro-F1 (Shellcode, Worms) | **0.285025** | ≥ 0.385669 | **FAIL** |
| Routed attack-family macro-F1 (routed rows) | 0.477364 | — | — |
| Routed correctly-attributed rate | 0.719315 | A9 0.7208 | slightly below A9 |
| Missed-as-benign | 2,310 / 0.050957 | A9 2,310 / 0.0510 | identical (router frozen) |
| Binary router macro-F1 | 0.894488 | A9 0.894488 | **identical** (router frozen) |
| Validation oracle macro-F1 | 0.5863 | — | vs test 0.4747 → gap **0.1116** |

## 3. Comparison vs A9 (per-class oracle F1)

| Class | A9 F1 | A9.9 F1 | Δ | Read |
| --- | ---: | ---: | ---: | --- |
| Generic | 0.9808 | 0.9808 | +0.0000 | unchanged (easy) |
| Reconnaissance | 0.8227 | 0.8237 | +0.0010 | unchanged |
| Exploits | 0.6907 | 0.6862 | −0.0045 | ~flat |
| **DoS** | 0.3877 | 0.4192 | **+0.0315** | small gain (overlap class) |
| **Backdoor** | 0.0704 | 0.1002 | **+0.0298** | small gain (still ~0.1) |
| Analysis | 0.0123 | 0.0000 | −0.0123 | **fully collapses (0 predicted)** |
| **Fuzzers** | 0.7679 | 0.6923 | **−0.0756** | regressed |
| **Worms** | 0.3314 | 0.2553 | **−0.0761** | regressed (recall 0.66→0.27) |
| **Shellcode** | 0.4399 | 0.3147 | **−0.1252** | regressed (precision 0.31→0.19) |

**Net:** marginal gains on the already-overlapping **DoS/Backdoor** were paid for by clear regressions on
**Fuzzers, Shellcode, Worms** → attack-family macro **−0.0257** and rare macro **−0.1006** vs A9.

## 4. Screen-gate result

- Oracle attack-family macro-F1 ≥ 0.515429 → **FAIL** (0.474716).
- Rare-class macro-F1 ≥ 0.385669 → **FAIL** (0.285025).
- Binary router unchanged → PASS (0.894488 = A9, by construction).
- Oracle / routed separated → PASS.
- **Overall: FAIL_SCREEN.**

## 5. Validation-to-test gap (overfitting evidence)

Validation oracle macro-F1 **0.5863** → test oracle macro-F1 **0.4747**, a **0.1116** drop. The specialist
selected the best validation epoch but that epoch did not generalize to the harder, prior-shifted test
partition. This is the classic overfitting signature, amplified by the official-partition prior shift
(RC4: train/val benign 31.9% vs test 44.9%).

## 6. Class-level failure analysis (from the specialist oracle confusion matrix)

- **Analysis (F1 0.000):** the specialist **never predicts Analysis** (0/677). 426→DoS, 128→Backdoor,
  118→Exploits. Worse than A9 (which had 5 correct).
- **Backdoor (precision 0.064):** a low-precision dumping ground — 2,131 rows predicted Backdoor, only
  136 correct (DoS→Backdoor 717, Exploits→Backdoor 764).
- **Shellcode (precision 0.194):** massively over-predicted — 1,611 predicted, 313 correct; **Fuzzers→
  Shellcode 704**, Exploits→Shellcode 347. Class weighting bought recall (0.836) at a steep precision cost.
- **Worms (recall 0.273):** collapsed from A9's 0.659 — tiny support (44), overfit; 23 Worms→Exploits.
- **Fuzzers (recall 0.575):** down from A9's 0.710 — leaks into DoS (842) and Shellcode (704).

## 7. Root-cause hypotheses

1. **Overfitting of the independent encoder** (val 0.5863 → test 0.4747). [256,128] capacity on attack-only
   rows with only modest dropout/weight-decay memorized validation-specific structure.
2. **Lost shared representation.** A9's joint encoder is shaped by all 149,039 train rows (incl. benign) and
   the binary task, which regularizes the representation and helped Fuzzers/Shellcode/Worms. The attack-only
   specialist discarded this and learned a narrower representation → those classes regressed.
3. **Class-weight over-pressure on rare classes** (RC5 pattern). sqrt-inverse-frequency weights over-pushed
   Shellcode predictions (precision collapse) and did not rescue Worms recall → rare macro fell to 0.285.
4. **Intrinsic RC1 overlap unchanged.** Analysis/Backdoor/DoS/Exploits remain mutually confused; a separate
   classifier cannot separate families that overlap in the 192-feature space by construction.
5. **Official-partition prior shift (RC4)** amplifies the val→test gap.

**Oracle vs routed:** the frozen A9 router reproduces A9 exactly (0.894488), so the routed cap is the
**specialist**, not the router. Oracle (0.4747) is reported separately and is not a deployment number; the
routed deployment view (correctly-attributed 0.7193) is slightly below A9's 0.7208.

## 8. Should A9.9 be rejected? Should 3-seed confirmation run?

- **Reject A9.9 as configured: YES.** It underperforms A9 on attack-family and rare-class on a clean seed,
  and fails both gates.
- **Run 3-seed confirmation: NO.** Multi-seeding a configuration that is below A9 on a clean seed would
  waste compute and risk fishing for a lucky seed — a methodology violation. Promotion is never from one
  seed, and confirmation is only for a configuration that *passed* the seed42 screen.
- **Keep A9 as the accepted baseline: YES.** A9 remains stronger.
- **A9.9 is diagnostic-only: YES.** Its value is the lesson it provides for A9.10 (the independent encoder
  overfits and loses the shared representation).

## 9. Safety and anti-overclaiming notes

- No training, evaluation, preprocessing, XAI, Streamlit, Git, code, or config in this review.
- Weak classes (Analysis, Backdoor, DoS, Shellcode, Worms) are reported in full, never hidden or merged.
- Oracle metrics are not presented as routed/deployment metrics.
- No seed was cherry-picked; the single clean seed42 result is reported as-is. No fake improvements.

## 10. Exact main-control decision needed

**Approve or reject the A9.10 adjusted-specialist plan** (see
`docs/experiments/UNSW_A10_SPECIALIST_ADJUSTMENT_PLAN.md`). The recommendation there is **one** bounded
seed42 screen of a frozen-A9-embedding regularized head (which addresses both A9.9 failure modes), with a
hard stop if it fails — or, alternatively, stop UNSW specialist work now and move to federated/security
with A9 frozen as the final UNSW model.
