# V2 Final Design Lock Decision

## 1. Decision Status

Status: proposed design lock, pending main-control acceptance after review.

This document is not implementation approval. It does not approve coding, training, cleanup, deletion, refactor, preprocessing rebuilds, full evaluation, XAI computation, dashboard execution, or GitHub activity.

## 2. Locked Recommendation

Continue in the current V2 workspace.

Use an automatic schema-router system with dataset-specific adapters and preprocessing artifacts. Use dataset-specific checkpoints/heads behind one final system interface where scientifically required. Keep the hierarchical IDS design with Head 1 and Head 2.

The final system should be one professional interface, not one fake shared checkpoint.

## 3. Accepted Architecture Flow

```text
input sample/file
-> schema detector/router
-> adapter/pipeline
-> Head 1 Normal vs Attack
-> Head 2 Attack family/type if attack
-> XAI
-> dashboard output
```

## 4. Accepted Design Rules

- No binary-only final project.
- No fake shared CICIDS/UNSW checkpoint.
- No manual professor model selection in the final demo.
- No random model zoo with no router.
- No validation/test leakage.
- No fake metrics.
- No dry-run result presented as final.
- No hidden failed experiments.

## 5. Rejected Directions

- Starting a new V3 now.
- Reducing the final system to binary-only IDS.
- Forcing one CICIDS/UNSW pipeline despite incompatible schemas.
- Using random separate final models with no schema router.
- Treating all experiment folders as final.
- Hiding failed or weak experiments.

## 6. Current V2 Evidence Treatment

Reusable implementation foundation:

- Dataset loading/adapters and preprocessing foundation.
- Hierarchical preprocessing, model, and training foundation.
- Taxonomy, training, preprocessing, and federated configs.
- Tests as safety foundation.
- Dashboard foundation if later proven and completed.

Valid evidence candidate:

- UNSW A9 corrected-protocol hierarchical baseline.

Experiment evidence:

- UNSW A9.6, A9.7, and A9.8 controlled improvement experiments.

Diagnostic evidence:

- Smoke runs, dry runs, readiness outputs, and partial module outputs.

Legacy/archive candidates:

- `legacy_pre_a8_8_unsw`.
- Binary-only results that do not support final hierarchical claims.

Future implementation gaps:

- Schema detector/router.
- Final adapter interface cleanup.
- CICIDS final hierarchical training confirmation.
- Final security/attacks/aggregation/XAI/dashboard integration.

## 7. Immediate Next Phase After Approval

After main-control approval, prepare an implementation prompt for schema detector/router and adapter interface cleanup.

No training should start before that decision. No CICIDS or UNSW training should start before architecture implementation approval.

## 8. Required Main Control Chat Update

After this design-only task, the user must receive a concise update prompt for the main control chat before any next phase begins.

The next phase must be approved explicitly before coding, training, cleanup, deletion, or refactor.
