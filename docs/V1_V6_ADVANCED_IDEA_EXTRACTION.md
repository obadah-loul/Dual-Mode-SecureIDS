# V1/V6 Advanced Idea Extraction

Status: `Task A2.5 complete - read-only reference review only`

## 1. Scope

Task A2.5 inspected the old V1/V6 work as read-only reference material before
real hierarchical preprocessing is implemented in V2.

This task did not copy V1/V6 code, folders, checkpoints, processed arrays, or
results into V2. It did not implement model code, run preprocessing, train,
evaluate, create checkpoints, create metrics, start security/attack/Trimmed
Mean/XAI/dashboard work, or change the locked A2 taxonomy/preprocessing YAML
configs.

## 2. V1 Read-Only Inspection Confirmation

The old V1 project was inspected at:

`C:\IDS\IDS_V1\Secure-Distributed-Intrusion-Detection`

V1 was treated as read-only reference only. No V1 file or folder was modified.

## 3. V1/V6 Files And Folders Inspected

Relevant V1/V6 files and folders inspected:

- `README.md`
- `docs/ARTIFACTS_NOT_IN_GITHUB.md`
- `results/final_v6/FINAL_MODEL_SUMMARY.md`
- `results/final_v6/attack_recall_report.txt`
- `results/final_v6/false_positive_false_negative_report.txt`
- `results/final_v6/ids_metric_summary.txt`
- `results/final_v6/model_selection_summary.txt`
- `results/final_v6/per_class_best_model_table.csv`
- `results/final_v6/validation_vs_test_gap_report.txt`
- `results/final_v6/weak_class_analysis_report.txt`
- `results/week5_dashboard_snapshot.txt`
- `scripts/v5/attack_taxonomy.py`
- `scripts/v5/hierarchy.py`
- `scripts/v5/calibration_v5.py`
- `scripts/v5/specialists_v5.py`
- `scripts/v5/train_engine.py`
- `scripts/v5/run_preprocess_v6.py`
- `scripts/v5/security_dashboard.py`
- `scripts/v5/v6_reports.py`

Name/text searches also checked for references to V6, hierarchy, rare classes,
specialists, routing, confidence, calibration, attack-family logic, reports,
XAI, SHAP, explainability, ensemble work, and thresholds.

## 4. Useful V1/V6 Ideas Found

Useful ideas found:

- Strict leakage-aware reporting: V6 documented exact-feature group splitting
  and clearly separated validation selection from untouched test reporting.
- Hierarchical IDS concept: V1 used staged Benign-vs-Attack, attack-family,
  and within-family classification.
- Attack-family taxonomy: V1 grouped CICIDS labels into families such as DDoS,
  DoS, BruteForce, WebAttack, Bot, and Infilteration.
- Validation-only calibration: probability scaling was tuned on validation
  only, with stricter acceptance requirements for low-support classes.
- Guarded routing: specialist rules were accepted only when validation macro-F1
  improved without exceeding protected class F1 budgets.
- Rare/weak-class reporting: V1 explicitly tracked weak classes, attack recall,
  false positives/false negatives, validation-vs-test gaps, and per-class
  failures.
- Honest limitation reporting: V6 preserved poor FTP-BruteForce and
  Infilteration behavior instead of hiding it behind aggregate accuracy.
- Dashboard/reporting shape: worker status, accept/reject counts, suspicion
  scores, and security-layer status can inspire later dashboard layout.

## 5. Relevance To SecureIDS-HierarchicalAdvancedNet

Relevant to the final V2 system:

- The Head 1 / Head 2 concept is aligned with the approved
  `SecureIDS-HierarchicalAdvancedNet` direction.
- Validation-only calibration and routing policies are useful future ideas, but
  should be rebuilt around V2 neural logits/probabilities rather than copied.
- Weak-class and rare-class reporting should become part of future
  hierarchical centralized/FedAvg reports.
- The final system should preserve one organized architecture family rather
  than reviving V1's model zoo and ensemble selection workflow.

## 6. Rare Attack And Attack-Family Ideas

Relevant ideas for rare attack / attack-family classification:

- Keep per-class precision, recall, F1, and support visible.
- Report attack recall separately from attack-family attribution errors.
- Track false negatives to benign because Head 1 false negatives prevent Head 2
  from classifying the attack.
- Track weak classes separately from rare-by-support classes.
- Keep rare-class support counts and rare-class F1 in future reports.
- Consider validation-driven class weighting, focal loss, or sampling later,
  but do not tune them on test data.

Important distinction:

- A1/A2 define `is_rare` by support percent below `1.0%`.
- V1's `WEAK_CLASSES` also included hard classes that were not rare by support,
  such as `FTP-BruteForce`, `Infilteration`, and
  `DoS attacks-SlowHTTPTest`.

This suggests a future reporting concept named weak/hard class tracking, not a
revision to the rare-class definition.

## 7. Confidence, Calibration, And Routing Ideas

Relevant ideas:

- Calibration should be validation-only.
- Any confidence threshold or routing threshold must be frozen before test
  evaluation.
- Routing must have guardrails so improving rare recall does not silently
  damage benign precision or other important classes.
- Accepted and rejected threshold/routing rules should be logged.
- If confidence/routing is added later, it should be a reviewed task after the
  basic hierarchical model and metrics exist.

No A2/A3 preprocessing change is needed for these ideas.

## 8. Reporting, Dashboard, And XAI Ideas

Relevant reporting/dashboard ideas:

- Show binary detection metrics separately from attack-family metrics.
- Show attack recall as "any attack detected" separately from family accuracy.
- Show false positives and false negatives per class.
- Show validation-vs-test gaps.
- Show weak/rare class tables.
- Show security worker status, accepted/rejected updates, and suspicion scores
  later when the security layer is actually implemented.

XAI-specific evidence was not found as a mature V1/V6 implementation. Future
V2 XAI should follow the approved V2 plan: permutation importance required, with
Integrated Gradients or SHAP optional later if stable.

## 9. Safe Ideas To Rebuild Cleanly In V2

Safe ideas to rebuild:

- Dataset-aware hierarchical routing concept.
- Validation-only calibration policy.
- Frozen threshold policy with no test-set tuning.
- Guarded routing logs and accepted/rejected rule reports.
- Rare-class and weak-class reporting.
- Per-class recall/F1/support reports.
- Head 1 false-negative analysis for attacks missed as benign/normal.
- Attack-family confusion matrices.
- Validation-vs-test gap reports.
- Leakage and split-integrity evidence where applicable.
- Dashboard sections that read artifacts instead of inventing live claims.

These should be rebuilt using V2 modules, configs, manifests, and dataset-aware
CICIDS/UNSW logic.

## 10. Unsafe V1/V6 Parts Not To Reuse Directly

Do not copy or directly reuse:

- V1/V6 scripts as implementation source.
- V1/V6 processed `.pt` chunks.
- V1/V6 joblib models, checkpoints, cached probabilities, or predictors.
- The V1 model zoo, voting ensemble, and specialist pipeline as the final V2
  architecture.
- CICIDS-only label indices or hard-coded specialist pairs as general V2 logic.
- V1 dashboard claims that are not backed by current V2 artifacts.
- Old V1/V6 metrics as V2 hierarchical metrics.
- Any V1 folder merge that would recreate multiple competing final systems.

## 11. CICIDS Taxonomy Revision Decision

Historical A2.5 decision:

A1/A2 CICIDS taxonomy mappings were initially judged sufficient for A3 family-level preprocessing.

Task A4.5 update:

- A4 readiness review showed that the old family-level mapping hid
  `DoS attacks-Slowloris` inside `DoS` and `DDOS attack-LOIC-UDP` inside
  `DDoS`.
- CICIDS Head 2 is now revised to a raw-preserving 14-class mapping before
  model implementation.
- The raw spelling `Infilteration` remains preserved in the normalized class
  name `Infilteration / Infiltration`.
- V1's weak-class idea remains useful as reporting context only; it does not
  change the rare threshold.

## 12. UNSW Taxonomy Revision Decision

A1/A2 UNSW taxonomy mappings do not need revision.

Reason:

- V1/V6 evidence is CICIDS2018-only and does not provide a better UNSW
  `attack_cat` mapping.
- UNSW must keep its dataset-specific Head 2 taxonomy.
- No V1/V6 insight justifies changing the locked UNSW labels or mappings.

## 13. Common Superclass Revision Decision

The common superclass mapping does not need revision.

Reason:

- V1's WebAttack grouping supports the current `Web/Injection` superclass for
  `Brute Force -Web`, `Brute Force -XSS`, and `SQL Injection`.
- V1's DoS/DDoS and BruteForce concepts align with the current A1/A2 mapping.
- `Infilteration` can remain a dataset-specific family mapped to the reporting
  superclass `Exploitation`.
- Common superclasses should remain reporting-only.

## 14. Rare-Class Definition Revision Decision

The A1/A2 rare-class definition does not need revision.

Keep:

- `is_rare = true` when support percent is below `1.0%` of attack rows.

Add later, if approved:

- Separate weak/hard class reporting based on validation/test performance.

This avoids mixing a data-support definition with a model-performance
definition.

## 15. Masked Multi-Task Training Revision Decision

The masked multi-task training design does not need revision.

V1's staged hierarchy is useful conceptually, but the approved V2 design should
remain:

- Binary loss applies to every row.
- Attack-family loss applies only to attack rows.
- Benign/normal rows use Head 2 ignore index `-1`.
- Benign/normal rows use Head 2 mask value `0`.
- Attack rows use Head 2 mask value `1`.

Confidence routing can be reviewed later as an inference/calibration layer, not
as a reason to change A3 preprocessing.

## 16. Final Architecture Proposal Revision Decision

The final architecture proposal does not need revision before A3.

The V1/V6 review supports the approved direction:

- one organized final system,
- dataset-aware Head 2,
- common superclasses for reporting only,
- rare/weak-class visibility,
- validation-only tuning,
- and no fake shared CICIDS/UNSW multiclass target.

## 17. CICIDS-Only V6 Ideas And Generalization

V6 ideas that are CICIDS-only:

- Exact CICIDS label order and label indices.
- The `WEAK_CLASSES` list.
- Pair specialists such as Benign vs Infilteration.
- FTP-BruteForce vs DoS attacks-SlowHTTPTest routing.
- Web-group specialist for CICIDS web attack labels.
- V6 82-feature engineered CICIDS representation.
- 15-class CICIDS multiclass probability matrix including benign.

How to handle them in V2:

- Rebuild the general pattern only.
- Keep CICIDS and UNSW taxonomies separate.
- Generate label indices from dataset-specific taxonomy configs.
- Use future validation data to identify weak classes per dataset.
- Do not apply CICIDS specialist rules to UNSW.

## 18. Keeping One Final System

To avoid recreating V1 confusion:

- Keep `SecureIDS-HierarchicalAdvancedNet` as the final architecture family.
- Treat existing binary SecureIDSNet centralized/FedAvg work as foundation
  baselines.
- Train dataset-specific checkpoints only because CICIDS and UNSW have
  incompatible feature spaces and Head 2 taxonomies.
- Do not introduce a separate V6 ensemble final model.
- Do not copy old scripts into V2.
- Keep later calibration, routing, security, attack, robust aggregation, XAI,
  and dashboard layers as extensions around the approved final architecture.

## 19. Final Recommendation

Proceed to A3 as planned.

No taxonomy/config revision is required before A3.

Recommended A3 framing:

- Implement real hierarchical preprocessing using the locked A2 configs.
- Preserve current feature dimensions: CICIDS2018 `77`, UNSW-NB15 `190`.
- Produce binary labels, attack-family labels, masks, mappings, feature names,
  split summaries, and manifests.
- Do not implement confidence routing, calibration, model code, training, or
  dashboard work in A3 unless explicitly approved later.
