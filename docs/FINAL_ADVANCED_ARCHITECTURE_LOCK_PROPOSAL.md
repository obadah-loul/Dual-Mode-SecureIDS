# Final Advanced Architecture Lock Proposal

Status: `PROPOSAL - PENDING REVIEW`

This document proposes the final advanced direction for the V2 project. It does
not claim implementation is complete, does not introduce new results, and does
not change existing checkpoints, metrics, preprocessing outputs, or FedAvg
artifacts.

## 1. Final System Name

The proposed final system name is:

`SecureIDS-HierarchicalAdvancedNet`

The full project title becomes:

Secure, Robust, Explainable, and Hierarchical Federated Intrusion Detection
System.

## 2. Problem Solved

The system detects whether a network sample is benign or malicious and, when
malicious, classifies the attack family or rare attack type using a
dataset-aware hierarchy.

The current binary-only work proves the V2 pipeline is clean and reproducible,
but the final professor-facing system should demonstrate more than
Benign-versus-Attack detection. It should also support attack-family reporting,
rare-class evaluation, federated learning, later Byzantine robustness, and XAI.

## 3. Why Binary-Only Is Not Enough

Binary IDS answers only:

- Is this sample benign or malicious?

The final target must also answer:

- What type of attack is this?
- Which rare classes are missed or confused?
- How does federated learning affect attack-family performance?
- Under attacks or robust aggregation, which attack families collapse or recover?
- Which features explain Head 1 and Head 2 decisions?

Binary-only results remain useful internal baselines, but they are not rich
enough for the upgraded final system.

## 4. Current V2 Foundation Results

The following accepted results are treated as foundation and pipeline
validation, not as the final advanced architecture.

| Stage | Dataset | Checkpoint | Accuracy | Macro-F1 |
| --- | --- | --- | ---: | ---: |
| Centralized | UNSW-NB15 | `models/final/final_unsw_binary.pt` | 0.8875904665765565 | 0.8792684183754923 |
| Centralized | CICIDS2018 | `models/final/final_cicids_binary.pt` | 0.9795632692951038 | 0.9746194261725205 |
| FedAvg | UNSW-NB15 | `models/federated/fedavg_unsw_binary.pt` | 0.8761327926725637 | 0.8679284268229737 |
| FedAvg | CICIDS2018 | `models/federated/fedavg_cicids_binary.pt` | 0.9793021479138341 | 0.9743010869503197 |

These results should not be deleted, overwritten, or presented as fake
hierarchical results.

## 5. System Flow

Proposed inference flow:

1. Input network sample.
2. Dataset-specific preprocessing and feature vector.
3. Dataset-specific input projection based on input dimension.
4. Advanced shared tabular encoder.
5. Head 1 predicts binary class: Benign/Normal or Attack.
6. If Head 1 predicts Attack, Head 2 predicts attack family using the
   dataset-aware attack-family head.
7. Optional common high-level superclass is used for reporting and dashboard
   comparison only.

## 6. Advanced Shared Encoder Design

The encoder should be an advanced tabular network, not artificial image or
sequence complexity.

Recommended components:

- Dataset-specific input projection for `input_dim`.
- Residual MLP blocks.
- LayerNorm or BatchNorm.
- Dropout.
- Gated feature/channel attention.
- Shared latent representation.
- Optional calibrated confidence outputs.

Avoid:

- CNN/LSTM/Transformer only for appearance.
- Ensembles as the final system.
- Many competing final models.
- Fake direct CICIDS-to-UNSW multiclass evaluation.

## 7. Head 1: Binary Detection

Head 1 is the binary IDS detection head:

- Output: one logit.
- Objective: Benign/Normal vs Attack.
- Loss concept: `BCEWithLogitsLoss`.
- Threshold: fixed at `0.5` unless a later approved calibration task changes
  this using validation data only.
- Metrics: accuracy, precision, recall, F1, macro-F1, confusion matrix.

Head 1 must remain compatible with centralized and federated training.

## 8. Head 2: Dataset-Aware Attack-Family Classification

Head 2 classifies attack families only for attack samples.

Because CICIDS2018 and UNSW-NB15 have different attack taxonomies, Head 2 must
be dataset-aware:

- CICIDS2018 checkpoint: CICIDS attack-family output dimension.
- UNSW-NB15 checkpoint: UNSW attack-family output dimension.

This is not multiple competing final models. It is one architecture family with
dataset-specific input dimensions and dataset-specific attack-family heads.

## 9. Head 2 Support For CICIDS2018

CICIDS2018 Head 2 should train on attack labels derived from the CICIDS `Label`
field after excluding benign rows from the attack-family loss.

Known CICIDS attack labels from current raw files:

- Bot
- Brute Force -Web
- Brute Force -XSS
- DDOS attack-HOIC
- DDOS attack-LOIC-UDP
- DDoS attacks-LOIC-HTTP
- DoS attacks-GoldenEye
- DoS attacks-Hulk
- DoS attacks-SlowHTTPTest
- DoS attacks-Slowloris
- FTP-BruteForce
- Infilteration
- SQL Injection
- SSH-Bruteforce

The spelling `Infilteration` should be preserved if that is the actual dataset
label, while documentation may note the likely intended meaning is
Infiltration.

## 10. Head 2 Support For UNSW-NB15

UNSW-NB15 Head 2 should train on `attack_cat` for attack rows only.

Known UNSW attack categories:

- Analysis
- Backdoor
- DoS
- Exploits
- Fuzzers
- Generic
- Reconnaissance
- Shellcode
- Worms

If future audit confirms different spelling or extra classes, the mapping must
be updated from the data audit. Do not invent unverified UNSW labels.

## 11. Common High-Level Superclass Reporting

Common high-level attack superclasses should be used for dashboard/reporting
comparison, not as fake exact training labels.

Proposed superclasses:

- DoS/DDoS
- Brute Force
- Web/Injection
- Reconnaissance
- Exploitation
- Malware/Botnet
- Generic/Other
- Rare/Unknown

### CICIDS2018 To Common Superclass

| CICIDS label | Proposed superclass | Note |
| --- | --- | --- |
| DDOS attack-HOIC | DoS/DDoS | Volumetric DDoS |
| DDOS attack-LOIC-UDP | DoS/DDoS | UDP DDoS |
| DDoS attacks-LOIC-HTTP | DoS/DDoS | HTTP DDoS |
| DoS attacks-GoldenEye | DoS/DDoS | DoS family |
| DoS attacks-Hulk | DoS/DDoS | DoS family |
| DoS attacks-SlowHTTPTest | DoS/DDoS | Slow HTTP DoS |
| DoS attacks-Slowloris | DoS/DDoS | Slow HTTP DoS |
| FTP-BruteForce | Brute Force | Credential attack |
| SSH-Bruteforce | Brute Force | Credential attack |
| Brute Force -Web | Web/Injection | Web application brute force; could also be reported as Brute Force in detailed view |
| Brute Force -XSS | Web/Injection | Web/XSS attack |
| SQL Injection | Web/Injection | Injection attack |
| Bot | Malware/Botnet | Bot behavior |
| Infilteration | Exploitation | Uncertain label spelling; consider Rare/Unknown if audit shows very low support |

### UNSW-NB15 To Common Superclass

| UNSW attack_cat | Proposed superclass | Note |
| --- | --- | --- |
| DoS | DoS/DDoS | Denial of service |
| Reconnaissance | Reconnaissance | Scanning/probing |
| Exploits | Exploitation | Exploit behavior |
| Shellcode | Exploitation | Payload/exploit behavior |
| Backdoor | Malware/Botnet | Also related to exploitation; use Malware/Botnet for reporting clarity |
| Worms | Malware/Botnet | Self-propagating malware |
| Fuzzers | Exploitation | Could also support Reconnaissance; document choice |
| Analysis | Reconnaissance | Could also support Generic/Other; document choice |
| Generic | Generic/Other | Broad UNSW category |

## 12. Rare Attack Handling

Rare attacks must be visible, not hidden by aggregate accuracy.

Required rare-class handling:

- Report support counts per attack family.
- Report per-class precision, recall, and F1.
- Report macro-F1 and rare-class F1.
- Include attack-family confusion matrices.
- Include rare-class error analysis.
- Avoid test-set tuning.

Possible later strategies:

- Class weighting.
- Focal loss.
- Balanced client sampling.
- Rare-class grouping for common reporting.
- Calibration/confidence thresholds based on validation data only.

## 13. Rare Attack Evaluation

Evaluation should include:

- Head 1 binary metrics.
- Head 2 attack-family metrics on attack samples.
- Rare-class support table.
- Rare-class F1 table.
- Macro-F1 over attack-family classes.
- Confusion matrix for attack-family prediction.
- Error analysis for common misroutes: Head 1 false negatives and Head 2
  attack-family confusion.

No poor rare-class performance should be hidden behind high binary accuracy.

## 14. Avoiding Fake Cross-Dataset Multiclass Claims

The design avoids fake claims by:

- Keeping CICIDS and UNSW feature spaces dataset-specific.
- Keeping Head 2 taxonomies dataset-aware.
- Not forcing one exact shared multiclass label list.
- Using common superclasses only for reporting, not as a false training target.
- Reporting CICIDS and UNSW hierarchical metrics separately.

No direct frozen CICIDS-to-UNSW multiclass evaluation should be claimed unless a
formal common feature space and label ontology are designed later.

## 15. Dataset-Specific Feature Compatibility

The model remains compatible with different feature dimensions by using a
dataset-specific input projection:

- Current CICIDS binary pipeline: `input_dim = 77`.
- Current UNSW binary pipeline: `input_dim = 190`.

If hierarchical preprocessing changes feature counts, input dimensions must be
recomputed from processed `feature_names.json`, not hardcoded.

## 16. Centralized Training Compatibility

Centralized hierarchical training should run separately per dataset:

- UNSW hierarchical centralized checkpoint.
- CICIDS hierarchical centralized checkpoint.

Both use the same architecture family but dataset-specific input dimensions and
attack-family heads.

Recommended training strategy:

`Masked multi-task training`

Rationale:

- One coherent final architecture.
- Binary loss applies to every row.
- Attack-family loss applies only to attack rows.
- Benign rows are excluded from Head 2 loss.
- The same forward pass can produce both heads.
- It is easier to preserve one final model story than separate unrelated
  two-stage models.

If masked multi-task training is unstable, a clearly documented two-stage
training fallback may be reviewed later.

## 17. FedAvg Compatibility

FedAvg should run separately per dataset:

- UNSW hierarchical FedAvg.
- CICIDS hierarchical FedAvg.

Reasons:

- Feature dimensions differ.
- Attack-family heads differ.
- Attack taxonomies differ.

FedAvg aggregates parameters for the same dataset-specific model instance. The
future federated reports should include binary metrics, attack-family metrics,
rare-class metrics, client distributions, round histories, and manifests.

## 18. Byzantine Attack Compatibility

Later attack simulations can target the full hierarchical model update:

- Sign-flip attack.
- Gaussian noise attack.
- Scaling attack.

Reports should evaluate:

- Binary macro-F1 under attack.
- Attack-family macro-F1 under attack.
- Rare-class F1 under attack.
- Collapse and recovery behavior.
- Which head is more sensitive to malicious updates.

## 19. Trimmed Mean Compatibility

Trimmed Mean robust aggregation can replace FedAvg aggregation under attack.

The same hierarchical update structure is aggregated, but the aggregation rule
changes from mean-by-sample-count to coordinate-wise trimming. Results should be
compared against clean FedAvg and attacked FedAvg.

## 20. XAI For Both Heads

XAI must answer two questions:

- Why did Head 1 predict Benign or Attack?
- If attack, why did Head 2 predict a specific attack family?

Required method:

- Permutation importance.

Optional later methods:

- Integrated Gradients.
- SHAP.

Required XAI outputs should include binary global importance, attack-family
global importance, local benign explanations, local attack explanations, and
rare-attack explanations.

## 21. Dashboard Plan

The Streamlit dashboard should present:

- Project overview.
- Dataset audit and schema compatibility.
- Hierarchical IDS prediction demo.
- Head 1 binary prediction and confidence.
- Head 2 attack-family prediction and confidence when Head 1 predicts attack.
- Rare attack detection.
- Centralized and federated results.
- Byzantine defense and robust aggregation results.
- XAI explanations.
- Reproducibility logs and manifests.

The dashboard must read artifacts only. It must not train live.

## 22. Current V2 Files Reusable Safely

Reusable categories:

- Dataset adapters.
- Preprocessing modules and audit style.
- Training infrastructure.
- Metrics helpers.
- Manifest/reporting style.
- Centralized binary baseline outputs.
- FedAvg binary baseline outputs.
- No-fake-results rules.
- Config layout.
- Dashboard shell if present.

These are foundation components, not final hierarchical claims.

## 23. Current V2 Files/Configs Needing Changes After Approval

Likely changes:

- Hierarchical preprocessing configs.
- Attack taxonomy mapping docs/configs.
- Processed attack-family labels.
- Hierarchical model module.
- Hierarchical centralized training configs.
- Hierarchical centralized training runner.
- Hierarchical FedAvg runner/configs.
- Hierarchical reports and manifests.
- Dashboard updates later.

Do not modify these until the proposal is reviewed and approved.

## 24. V1/V6 Ideas Safe To Reuse

Safe ideas:

- Hierarchical routing.
- Rare-class handling.
- Confidence/calibration.
- Specialist logic as an idea, not as copied ensemble code.
- Error analysis.
- Attack-family reporting.
- Robustness evidence style.
- Reporting style, if cleaned for V2.

## 25. V1/V6 Parts Not To Copy

Do not copy:

- Old messy scripts.
- Old checkpoints.
- Old results as V2 results.
- Old V6 ensemble as the final system.
- Old CICIDS-only assumptions.
- Old pipelines directly into V2.
- Any workflow that recreates multiple competing final models.

## 26. New Expected Files If Approved

Possible new files after approval:

- `docs/FINAL_ADVANCED_ARCHITECTURE_LOCK.md`
- `docs/ATTACK_TAXONOMY_MAPPING.md`
- `docs/RARE_ATTACK_EVALUATION.md`
- `configs/preprocessing/cicids2018_hierarchical.yaml`
- `configs/preprocessing/unsw_nb15_hierarchical.yaml`
- `configs/training/cicids2018_hierarchical.yaml`
- `configs/training/unsw_nb15_hierarchical.yaml`
- `configs/federated/cicids2018_hierarchical_fedavg.yaml`
- `configs/federated/unsw_nb15_hierarchical_fedavg.yaml`
- `secureids/models/secureids_hierarchical_advanced_net.py`
- Hierarchical centralized and federated reports/manifests.

## 27. Training Stages After Approval

Proposed stages:

1. Taxonomy audit/design.
2. Hierarchical preprocessing design.
3. Hierarchical preprocessing dry-run.
4. Real hierarchical preprocessing.
5. Hierarchical model implementation.
6. Smoke hierarchical training.
7. Centralized hierarchical UNSW.
8. Centralized hierarchical CICIDS.
9. Hierarchical validation.
10. Hierarchical FedAvg dry-run.
11. Hierarchical FedAvg UNSW.
12. Hierarchical FedAvg CICIDS.
13. Security, attacks, Trimmed Mean, XAI, and dashboard.

## 28. Risks

Key risks:

- Rare-class imbalance.
- Inconsistent attack taxonomies.
- Head 1 errors propagating to Head 2.
- Attack labels missing or meaningless for benign rows.
- Federated class imbalance per client.
- Increased training complexity.
- Professor confusion if baseline and final systems are not documented clearly.
- Temptation to copy V1/V6 mess.
- Fake cross-dataset claims.

## 29. No-Confusion Implementation Plan

Cleanest plan:

1. Freeze this proposal for review.
2. Approve one final advanced architecture direction.
3. Create taxonomy and rare-class docs before coding.
4. Extend preprocessing to preserve both binary labels and attack-family labels.
5. Implement one hierarchical model class.
6. Validate with smoke runs.
7. Train centralized hierarchical baselines per dataset.
8. Train hierarchical FedAvg per dataset.
9. Add security and attacks only after hierarchical FedAvg is stable.
10. Add Trimmed Mean.
11. Add XAI.
12. Add dashboard.

## 30. Decision Required

Before implementation starts, the project owner should approve or revise:

- Final system name.
- Masked multi-task training recommendation.
- Dataset-aware Head 2 design.
- Common superclass reporting map.
- New file/config plan.
- Training stage order.

Until approved, do not implement the advanced model.
