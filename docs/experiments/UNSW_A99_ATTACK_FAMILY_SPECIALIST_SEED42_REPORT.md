# UNSW A9.9 Attack-Family Specialist — Seed 42 Report

Status: `single-seed screen result — NOT promotable alone; A9 remains the accepted UNSW final`
Generated: `2026-06-25` (artifacts repaired from the existing seed42 checkpoint; **no retraining**)

Specialist checkpoint: `models/experiments/unsw_a99_attack_family_specialist_seed42.pt`
Checkpoint SHA256: `E6F72328F70D498800DD62AA9853D104EA5C61F17AF292B7F9DF8E97649E3A0B`
Frozen A9 router: `models/final/final_unsw_hierarchical.pt` (loaded read-only; never retrained)
Checkpoint selection: **validation-only** (best val attack-family macro-F1 =
`0.5862711090268267`). Test was evaluated **once** for this
report and was **not** used for selection or tuning.

---

## 1. Metric views (kept strictly separate)

> Oracle = specialist on the TRUE attack rows (teacher-forced). Routed = frozen A9 Head 1 routes
> detected attacks into the specialist (deployment view, bounded by Head 1 recall). **Oracle numbers
> are not deployment/routed numbers.**

| View | Metric | Value |
| --- | --- | ---: |
| A9 binary Head 1 (router, frozen) | binary macro-F1 | 0.894488 |
| Specialist **oracle** attack-family | macro-F1 (attack rows) | 0.474716 |
| Specialist **oracle** rare-class | macro-F1 (Shellcode, Worms) | 0.285025 |
| **Routed** end-to-end | routed attack-family macro-F1 | 0.477364 |
| **Routed** end-to-end | correctly-attributed rate | 0.719315 |
| **Routed** end-to-end | missed-as-benign rate | 0.050957 |

Oracle attack rows evaluated: 45332. Routed attack total:
45332 (correctly attributed 32608,
wrong family 10414, missed as benign
2310).

## 2. Comparison vs A9 baseline (test)

| Metric | A9 baseline | A9.9 seed42 (oracle) | Δ |
| --- | ---: | ---: | ---: |
| Attack-family macro-F1 | 0.500429 | 0.474716 | -0.025713 |
| Rare-class macro-F1 | 0.385669 | 0.285025 | -0.100644 |
| Binary macro-F1 (router) | 0.894488 | 0.894488 | router frozen (unchanged by construction) |

## 3. Weak classes (reported, never hidden)

| Class | Support | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| Analysis | 677 | 0.0 | 0.0 | 0.0 |
| Backdoor | 583 | 0.06382 | 0.233276 | 0.100221 |
| DoS | 4089 | 0.338081 | 0.55148 | 0.419184 |
| Shellcode | 378 | 0.194289 | 0.828042 | 0.314731 |
| Worms | 44 | 0.24 | 0.272727 | 0.255319 |

## 4. Seed42 screen gates

- Oracle attack-family macro-F1 ≥ 0.515429: **fail**
- Rare-class macro-F1 ≥ 0.385669: **fail**
- Binary router unchanged (A9 frozen): **True**
- Oracle / routed separated: **True**
- Overall: **FAIL_SCREEN_DIAGNOSTIC_ONLY**

## 5. Promotion status

**Seed42 cannot be promoted on its own.** Promotion requires a 3-seed (42/123/999) mean ± std that
clears the ~0.0143 attack-family seed-noise band versus the A9 linear 3-seed mean (0.494965), plus the
rare-class and precision gates — and explicit main-control approval. A9 remains the accepted UNSW final
model. This document is a single-seed screen result only.
