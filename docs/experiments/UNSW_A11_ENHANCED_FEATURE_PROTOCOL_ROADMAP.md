# UNSW A11 Enhanced Feature Protocol Roadmap

Status: `prep only - no preprocessing, no training, no evaluation`
Generated: `2026-06-25`
Protocol name: `UNSW A11 Enhanced Feature Protocol`

## 1. Current Position

A9 remains the frozen accepted UNSW baseline and rollback reference:

- Checkpoint: `models/final/final_unsw_hierarchical.pt`
- Binary macro-F1: `0.894488`
- Attack-family macro-F1: `0.500429`
- Rare-class macro-F1: `0.385669`

A11 is a separate enhanced feature protocol. It must use separate configs, processed data, audits, experiment checkpoints, and experiment results.

No preprocessing or training is being run now.

## 2. Phase Plan

### Phase 1: Train-Only Feature Inventory And Diagnostics

Goal: quantify the current feature/category problem before changing preprocessing.

Required diagnostics:

- Feature inventory.
- Category support inventory for `proto`, `service`, and `state`.
- Train-only min-frequency decisions.
- Train-only separability diagnostics for weak classes.
- Documentation of any fixed thresholds before model training.

This phase must not use test labels for feature decisions.

### Phase 2: Preprocessing Implementation After Main-Control Approval

Implement the A11 preprocessing protocol only after separate approval.

Core design:

- Corrected A9 raw split.
- Same taxonomy.
- Same held-out canonical test.
- Numeric-only scaling.
- One-hot columns not scaled.
- Median imputation fit on train only.
- Categorical encoders fit on train only.
- Proto min-frequency grouping / other bucket fit on train only.
- Service/state grouping disabled or conservative unless train-only diagnostics justify it.
- A11-specific processed data paths.
- A11-specific preprocessor paths.
- A11-specific audit paths.
- No overwrite by default.

### Phase 3: Seed-42 Training After Main-Control Approval

Seed-42 training may occur only after A11 preprocessing implementation is approved and completed.

Seed-42 screen gates:

- Attack-family macro-F1 is approximately `>= 0.515`.
- Rare-class macro-F1 is not below A9 `0.385669`.
- Binary macro-F1 is not damaged.
- Weak classes remain visible.
- No leakage or test tuning is introduced.
- No single-seed promotion.

If the seed-42 screen fails, stop UNSW optimization, keep A9 as the accepted UNSW baseline, and move to federated/security work.

### Phase 4: Three-Seed Confirmation Only If Seed 42 Passes

Three-seed confirmation is allowed only if seed 42 passes the screen.

Required seeds:

- `42`
- `123`
- `999`

Promotion must use mean plus standard deviation across seeds. A within-noise result is not a promotion.

## 3. Promotion And Rejection Criteria

Promote A11 only if all are true:

- A11 honestly improves attack-family macro-F1 beyond the approved noise-aware gate.
- Rare-class macro-F1 is not below A9 `0.385669`.
- Binary macro-F1 is not materially damaged.
- Analysis, Backdoor, DoS, Shellcode, and Worms remain visible in reporting.
- No taxonomy changes, hidden weak classes, test tuning, or fake metrics are used.
- Main control explicitly approves promotion.

Reject A11 if:

- Seed 42 fails the screen.
- Three-seed gains are within noise.
- Rare-class macro-F1 regresses.
- Binary macro-F1 is damaged.
- The improvement depends on unsafe shortcuts.

## 4. Rollback And Reference Plan

A9 remains the accepted baseline and rollback reference throughout A11.

A11 must not overwrite:

- `models/final/final_unsw_hierarchical.pt`
- `results/final/hierarchical/unsw/`
- A9/A9.6/A9.7/A9.8/A9.9/A9.10 artifacts

All A11 checkpoints and reports must remain under experiment paths unless a later explicit promotion is approved.

## 5. Future Dashboard And Final-Doc Representation

If later dashboard/final-doc updates are approved, represent the project as:

- CICIDS: final/promoted with documented warnings.
- UNSW: A9 accepted baseline.
- A11: shown only if it honestly wins and is approved.

If A11 does not win, show it as an attempted enhanced feature protocol that was not promoted.

## 6. Next Decision

Exact next main-control decision:

`approve_or_reject_a11_preprocessing_implementation`

This prep package does not authorize preprocessing, training, evaluation, promotion, XAI, Streamlit, or Git actions.
