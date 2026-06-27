# V2 Final Architecture Reset

## 1. Purpose and Scope

This document is a design-only architecture reset for V2 of the graduation project:

Secure, Robust, Explainable, and Hierarchical Federated Intrusion Detection System.

It does not approve coding, training, deletion, cleanup, refactor, preprocessing rebuilds, full evaluation, XAI computation, Streamlit execution, GitHub push, or checkpoint modification.

Only these three design/audit files are created by this task:

- `docs/V2_FINAL_ARCHITECTURE_RESET.md`
- `docs/V2_FINAL_DESIGN_LOCK_DECISION.md`
- `results/audits/v2_final_architecture_reset.json`

All existing implementation files, configs, results, checkpoints, tests, docs, V1 reference files, and V2 experiment artifacts remain untouched.

## 2. Final Architecture Recommendation

The final project should continue inside the current V2 workspace, not start a new V3. V2 already contains useful package structure, configs, docs, results, tests, dashboard code, preprocessing work, hierarchical model work, and experiment evidence.

The recommended final architecture is one automatic multi-schema IDS system:

input sample/file -> schema detector/router -> dataset/source adapter -> dataset-specific preprocessing pipeline -> hierarchical IDS -> XAI explanation -> Streamlit dashboard output.

The final system should use one professional user-facing interface and one consistent architecture family where possible, but it must not force one fake shared checkpoint onto incompatible CICIDS2018 and UNSW-NB15 schemas. CICIDS2018 and UNSW-NB15 have different feature schemas, preprocessing needs, and attack taxonomies. A single checkpoint should only be claimed if the code and evidence genuinely prove schema and taxonomy compatibility. Until then, the scientifically valid design is dataset-specific adapters, dataset-specific preprocessing artifacts, and dataset-specific checkpoint/head configurations behind one automatic system interface.

The correct professional story is:

input schema matches a supported adapter/pipeline.

The incorrect story is:

traffic belongs to a dataset/model.

## 3. Final System Flow

The accepted architecture flow is:

```text
input sample/file
-> schema detector/router
-> adapter/pipeline
-> Head 1 Normal vs Attack
-> Head 2 Attack family/type if attack
-> XAI
-> dashboard output
```

## 4. Dataset/Source Adapter Design

Each supported dataset/source adapter should be responsible for:

- Schema validation.
- Column normalization.
- Missing and infinite value policy.
- Feature selection.
- Categorical encoding.
- Numeric scaling.
- Binary label mapping.
- Attack-family mapping.
- Preprocessing artifact loading and saving.
- Audit logging.
- Leakage-safe fit/transform behavior.

Adapters must separate fitting from transformation. Scalers, encoders, selectors, class weights, and sampling policies must be fitted only on training data. Validation and test data must only be transformed by already-fitted artifacts.

## 5. Schema Detector/Router Design

The schema detector/router should inspect uploaded files or sample columns and match them to canonical schema fingerprints. Supported routes should include:

- `cicids2018_like`
- `unsw_nb15_like`

Unknown schemas should be rejected with a clear error that explains which required columns or schema features were missing. The final demo should not require manual professor model selection. The router should identify the adapter, preprocessing artifact set, checkpoint family, taxonomy, and dashboard label.

Router output should include:

- `schema_id`
- `adapter_id`
- `preprocessing_artifact_set`
- `checkpoint_family`
- `taxonomy_id`
- `dashboard_label`

## 6. Two-Head / Two-Stage IDS Design

The final IDS must stay hierarchical and must not become binary-only.

Head 1 predicts Normal vs Attack. Head 2 predicts attack family/type and is meaningful only for attacks or for the attack-probability path of the system. Head 2 must use a dataset-aware attack-family taxonomy unless a scientifically valid shared taxonomy is created and validated.

Rare classes should be reported honestly. They should not be hidden, merged, or overclaimed without clear justification. If rare-class metrics are weak, the final report should show the weakness and explain it.

Metrics must include both binary metrics and attack-family metrics. A strong binary result alone is not enough to support the final hierarchical IDS claim.

## 7. Model Strategy Decision

Option A: one forced shared model/checkpoint.

This is rejected unless future evidence proves true compatibility. CICIDS2018 and UNSW-NB15 have incompatible schemas and taxonomies, so forcing one checkpoint would be scientifically unsafe.

Option B: fully separate models with manual selection.

This is also rejected as the final story. It may be easier to implement, but it creates a weak demo where the professor or user must know which model to choose manually.

Option C: automatic schema-router system with dataset-specific adapters/checkpoints and a shared architecture family.

This is the recommended option. It gives one professional system while avoiding false compatibility claims. The user uploads or selects input, the system detects the supported schema, routes to the correct adapter/pipeline, loads the correct artifact/checkpoint family, predicts with Head 1 and Head 2, generates explanations, and displays results in one dashboard.

## 8. Current V2 Reuse Plan

The current V2 workspace should be reused rather than replaced.

Reusable or likely reusable areas:

- `secureids/datasets`: useful foundation for dataset loading and adapter behavior; should be reviewed before final router work.
- `secureids/preprocessing`: useful foundation for preprocessing pipelines and artifact handling; must remain leakage-safe.
- `secureids/models`: useful hierarchical model foundation; final model family should remain two-head/two-stage.
- `secureids/training`: useful training foundation and evidence of controlled experiment structure; future changes require approval.
- `secureids/federated`: useful or partial foundation for federated learning; classify readiness before final claims.
- `configs/preprocessing`: useful configuration foundation and evidence; do not modify without approval.
- `configs/taxonomy`: useful dataset-aware taxonomy foundation.
- `configs/training`: useful as evidence and possible foundation; existing configs must not be treated as all final.
- `configs/federated`: useful for federated design and experiment planning.
- `docs`: evidence, design history, and thesis material foundation; some docs may become final, some experiment evidence, some archive candidates.
- `results/audits`: audit evidence and decision trail; classify carefully.
- `results/final/hierarchical/unsw`: valid UNSW hierarchical result evidence candidate, especially A9 corrected-protocol baseline.
- `tests`: safety foundation; later test expansion may be needed after explicit implementation approval.

Partial or evidence-only areas:

- Security, attack, aggregation, XAI, and dashboard modules may be skeletons or partial until proven by artifacts and reports.
- Smoke and dry-run outputs are diagnostic unless supported by full experiment evidence.
- Federated dry-run outputs are readiness evidence, not final experiment evidence by default.

## 9. Current V2 File Classification Rules

Existing files should be classified before any cleanup or archive move. No files should be deleted now.

Recommended categories:

- Final architecture source: docs/configs/code that define the accepted final system after approval.
- Final accepted evidence: results with config snapshot, command/log evidence, metrics, artifacts, and report.
- Experiment evidence: controlled experiments that may have succeeded or failed but are scientifically useful.
- Diagnostic evidence: smoke runs, dry runs, readiness checks, partial outputs, or debugging evidence.
- Legacy/archive candidate: older results or pre-correction artifacts that should remain visible but not drive final claims.
- Implementation skeleton: partial code that expresses intended structure but is not yet proven complete.
- Future work: planned modules or folders not ready for final claims.

Files should be moved or archived later only after explicit approval. They should not be deleted during this reset.

## 10. Existing Result Classification Guidance

UNSW A9 corrected-protocol hierarchical baseline is a valid evidence candidate.

UNSW A9.6, A9.7, and A9.8 are controlled improvement experiments. They must remain visible and honest, but they do not automatically replace A9.

`legacy_pre_a8_8_unsw` is a legacy evidence/archive candidate.

CICIDS binary centralized/FedAvg baselines are useful legacy or baseline evidence, but they are not enough for a final hierarchical CICIDS claim.

Smoke and dry-run outputs are diagnostic only.

Federated dry-run outputs are diagnostic/readiness evidence unless full experiment artifacts, metrics, logs, and reports prove otherwise.

## 11. Final Streamlit UI Story

The final Streamlit dashboard should load saved artifacts and reports. It should not train live.

Recommended pages:

- Project Overview.
- Dataset / Schema Audit.
- Prediction Demo.
- Federated Security Results.
- Byzantine Attack Defense.
- Robust Aggregation Results.
- XAI Explanation.
- Reproducibility / Logs.

The prediction demo should let the user upload or select a sample/file. The system should inspect the schema, route to the correct supported adapter/pipeline, load saved preprocessing and model artifacts, run Head 1 and Head 2 where appropriate, generate/load explanations, and display the result clearly.

## 12. Final XAI Plan

The final XAI plan should include:

- Global feature importance.
- Local benign explanation.
- Local attack explanation.
- Head 1 explanation.
- Head 2 explanation.
- Permutation importance baseline.
- Integrated gradients if practical.
- SHAP only if practical.

XAI must not use test labels for tuning. XAI outputs should be generated from saved models and preprocessing artifacts, and dashboard pages should load saved XAI artifacts rather than recompute heavy analysis live.

## 13. Federated/Security/Attack/Aggregation Integration

The final architecture should remain compatible with:

- Centralized training.
- Local simulated federated training.
- FedAvg.
- Trimmed Mean.
- TLS evidence.
- SHA-256 gradient integrity verification.
- Byzantine attacks: sign-flip, Gaussian noise, and scaling if stable.
- Attack fractions such as 25% and 50%.
- Security and communication overhead reporting.

These components must be reported according to their evidence level. Dry runs and skeletons should not be marketed as full final experiments.

## 14. Correct Training/Evaluation Order After Design Lock

No coding or training should begin until the main-control update is approved.

Recommended order after approval:

1. Main-control update and approval.
2. Implement or clean the schema detector/router.
3. Finalize adapter interfaces.
4. Train or finish the CICIDS hierarchical model.
5. Decide whether UNSW needs more improvement only after reviewing current evidence.
6. Clean the federated training layer.
7. Implement TLS/SHA-256 evidence.
8. Implement Byzantine attacks.
9. Compare FedAvg vs Trimmed Mean.
10. Generate the final experiment grid.
11. Generate XAI artifacts.
12. Build the final Streamlit dashboard.
13. Generate final figures/tables.
14. Write README, reproducibility, and thesis material.

## 15. Clean Final Folder Organization

The current V2 structure should be kept. Missing folders may be added later only after approval.

Possible future folders:

- `configs/security`
- `configs/attacks`
- `configs/dashboard`
- `results/experiments`
- `models/archive`
- `docs/final`
- `docs/design`
- `docs/experiments`

These folders are not created by this reset.

## 16. Final Accepted Results vs Failed/Diagnostic Experiments

Strict acceptance rules:

- A final result must have config snapshot, command/log evidence, saved metrics, saved artifacts, and a clear report.
- A diagnostic result must not be marketed as final.
- Failed or weak experiments should remain visible and honest.
- Metrics not recorded must be marked `NOT_RECORDED`.
- Placeholder metrics are not allowed.
- No result should be called final unless the artifact evidence supports it.

## 17. Leakage and No-Fake-Results Rules

The final project must follow these rules:

- No scaler, encoder, feature selector, sampler, or class-weight fitting on validation/test data.
- No tuning on test data.
- No UNSW test data for model selection.
- No forcing CICIDS and UNSW into one incompatible pipeline.
- No claiming one checkpoint works across schemas unless proven.
- No hiding weak Head 2 performance.
- No presenting dry runs as full final experiments.
- No fake metrics.
- No placeholder metrics.

## 18. V2 vs V3 Recommendation

The recommendation is to continue in current V2.

Reasons:

- V2 already has useful package structure.
- V2 has docs, configs, tests, and results.
- V2 includes useful preprocessing/adapters, hierarchical training/model work, and audit evidence.
- Creating V3 now would create another fork and increase confusion.
- The cleaner path is to lock the design, then perform controlled refactor/archive work inside V2 only after approval.

Risk:

- V2 is not a Git repository based on the provided/current snapshot, so later edits need a backup/Git safety decision before any large cleanup or implementation work.

## 19. Risks and Assumptions

Risks and assumptions:

- V2 is not currently a Git repository based on the provided/current snapshot.
- Some files may be partial or outdated.
- Result folders may mix final, experiment, diagnostic, and legacy evidence.
- CICIDS final hierarchical results still need confirmation.
- The schema detector/router is not implemented yet.
- XAI likely is not complete yet.
- The dashboard appears early/minimal until proven otherwise.
- No implementation approval is granted by this design reset.
- V1 is read-only reference and must not be modified.

## 20. Post-Reset Control Rule

After these three files are created, the working chat must prepare a concise update for the main control chat before any coding, training, cleanup, deletion, or refactor starts.

This reset is a design lock proposal, not implementation approval.
