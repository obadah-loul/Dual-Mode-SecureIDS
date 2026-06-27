# UNSW A11 Enhanced Feature Protocol Feasibility Audit

Status: `prep only - no preprocessing, no training, no evaluation`
Generated: `2026-06-25`
Protocol name: `UNSW A11 Enhanced Feature Protocol`

## 1. Purpose

A11 is a separate enhanced feature/preprocessing protocol for UNSW-NB15. It is not a same-preprocessing model-only improvement over A9.

The current accepted UNSW baseline remains frozen and visible:

- Checkpoint: `models/final/final_unsw_hierarchical.pt`
- Identity: `A9 corrected-protocol hierarchical baseline`
- Binary macro-F1: `0.894488`
- Attack-family macro-F1: `0.500429`
- Rare-class macro-F1: `0.385669`

A11 may be compared to A9 only as:

`enhanced feature protocol vs corrected A9 baseline`

It must not be presented as a same-preprocessing architecture or training-only improvement.

## 2. A9 Baseline Protocol

A9 uses the corrected official UNSW split:

- Local `UNSW_NB15_testing-set.csv` is the canonical train source: `175341` rows.
- Local `UNSW_NB15_training-set.csv` is the canonical test source: `82332` rows.
- Validation is derived only from the canonical train source.
- Final train/val/test split: `149039 / 26302 / 82332`.
- Taxonomy: fixed 9-class UNSW attack-family taxonomy.
- Held-out canonical test set is used only after validation-only selection.

A9 feature protocol:

- Input dimension: `192`
- Numeric features: `39`
- `proto` one-hot features: `133`
- `service` one-hot features: `13`
- `state` one-hot features: `7`
- Median imputation fit on train only.
- Standard scaling fit on train only.
- One-hot encoding fit on train only.

## 3. Why Earlier UNSW Attempts Did Not Solve the Weakness

A9 is honest and accepted, but attack-family attribution remains weak. The dominant failure cluster is:

`Analysis / Backdoor / DoS / Exploits`

The existing per-class evidence shows that `Analysis` and `Backdoor` remain near collapse, while `DoS` absorbs many neighboring classes. This keeps attack-family macro-F1 near `0.50` even when binary detection is acceptable.

Prior attempts did not create a promotable result:

- A9.6 increased global attack-family loss pressure, but hurt attack-family and rare-class macro-F1.
- A9.7 added Head 2 branch capacity, but did not beat A9 on the approved seed-42 screen.
- A9.8 compared A9 linear Head 2 vs A9.7 branch across seeds; the branch did not pass the approved promotion rule.
- A9.9 overfit and did not become an accepted improvement path.
- A9.10 frozen-embedding specialist did not meaningfully beat A9 and hurt rare-class macro-F1.

These outcomes suggest that simple loss pressure, simple Head 2 capacity, and a specialist trained on the frozen embedding are not sufficient. The remaining plausible lever is the input feature protocol itself.

## 4. Why Feature Protocol Is the Remaining Plausible Lever

The A9 input space is dominated by sparse categorical one-hot features, especially `proto`:

- `133 / 192` features are `proto_*` one-hot columns.
- Many protocol categories are rare.
- Current scaling treats one-hot columns as numeric columns, which can amplify sparse category spikes.

A11 therefore targets feature representation rather than another architecture-only change:

- Do train-only feature/category inventory first.
- Keep numeric scaling for numeric columns only.
- Avoid scaling one-hot categorical columns.
- Use train-only categorical grouping, especially `proto` min-frequency grouping into an explicit other bucket.
- Keep service/state grouping conservative or disabled unless train-only diagnostics justify it.

The expected upside is modest and uncertain. A realistic A11 win is a small but honest attack-family macro-F1 gain without damaging rare classes or binary detection.

## 5. Comparability Position

A11 keeps the same raw split, taxonomy, and held-out canonical test as A9. This allows a valid comparison of:

`A11 enhanced feature protocol` vs `A9 corrected-protocol baseline`

The comparison must be labeled clearly because A11 may change feature semantics and feature dimension. It is not valid to claim that A11 is a same-preprocessing model-only improvement.

A9 remains the accepted rollback/reference model unless A11 later wins honestly and main control approves a separate promotion decision.

## 6. Explicitly Rejected Shortcuts

A11 must reject the following:

- Test-set feature selection.
- Test-label feature decisions.
- Test scaler fitting.
- Taxonomy changes to inflate metrics.
- Hiding or removing weak classes.
- Silent replacement of A9.
- Random reruns.
- Test tuning.
- Fake metrics.

## 7. Feasibility Decision

A11 is feasible as a bounded final UNSW improvement attempt, but only under strict protocol separation.

Recommended next step:

Approve or reject A11 preprocessing implementation after reviewing this prep package. No preprocessing, training, evaluation, promotion, or checkpoint change is authorized by this document.
