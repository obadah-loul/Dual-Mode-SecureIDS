# Advanced Direction Decision

Status: `DECISION PROPOSAL - PENDING REVIEW`

## 1. Source Direction Update

The project source direction has been updated. The final target is no longer a
simple binary-only IDS.

Updated final project direction:

`Secure, Robust, Explainable, and Hierarchical Federated Intrusion Detection System`

Proposed final system:

`SecureIDS-HierarchicalAdvancedNet`

## 2. Decision Summary

The project should move from binary-only final IDS framing to one organized
advanced hierarchical IDS:

- Advanced shared tabular encoder.
- Head 1: binary Benign/Normal vs Attack detection.
- Head 2: dataset-aware attack-family and rare-attack classification.
- Federated learning support.
- Later security, Byzantine attack, robust aggregation, XAI, and dashboard
  layers.

This is a design decision proposal only. No coding or training is approved by
this document.

## 3. Current Work Remains Valid

The completed V2 binary centralized and FedAvg work remains valid as:

- Clean engineering foundation.
- Pipeline validation.
- Internal baseline.
- Reproducibility evidence.

It should not be deleted, replaced, or presented as fake hierarchical results.

## 4. Final Target

The final target is one organized advanced system, not many competing models.

Allowed:

- One architecture family with dataset-specific input dimensions.
- Dataset-specific checkpoints for incompatible schemas.
- Dataset-aware attack-family heads.

Not allowed:

- Multiple unrelated final models.
- A direct messy V1/V6 merge.
- Fake exact shared multiclass labels across CICIDS2018 and UNSW-NB15.
- Old V1/V6 results presented as new V2 results.

## 5. Head 2 Dataset-Aware Requirement

Head 2 must support both datasets:

- CICIDS2018 attack labels/families from the CICIDS `Label` field.
- UNSW-NB15 attack families from `attack_cat`.

Because the taxonomies differ, the model must not force a fake exact shared
label list. Dataset-aware Head 2 output dimensions are required.

## 6. Common Superclass Reporting

A common high-level attack superclass layer is allowed for reporting and
dashboard comparison if documented clearly.

Example superclasses:

- DoS/DDoS
- Brute Force
- Web/Injection
- Reconnaissance
- Exploitation
- Malware/Botnet
- Generic/Other
- Rare/Unknown

This layer is not a substitute for dataset-specific attack-family training.

## 7. V1/V6 Use Policy

V1/V6 are read-only reference sources for ideas only.

Safe ideas:

- Hierarchical routing.
- Rare-class handling.
- Confidence and calibration.
- Specialist insight.
- Error analysis.
- Reporting style.

Do not copy:

- Old messy scripts.
- Old checkpoints.
- Old result files.
- Old V6 ensemble as the final system.
- Old CICIDS-only assumptions.
- Old pipelines directly into V2.

## 8. Paused Work

The following work is paused until this advanced direction is reviewed and
approved:

- Task 9E.
- Security/TLS.
- SHA-256 update integrity.
- Gradient trust/audit logging.
- Byzantine attack simulation.
- Trimmed Mean.
- XAI.
- Dashboard model demo.
- Any hierarchical coding or training.

## 9. Required Review Before Coding

Before implementation, review and approve:

- Final architecture name.
- Dataset-aware Head 2 plan.
- Attack taxonomy mapping plan.
- Rare-class evaluation plan.
- Masked multi-task training recommendation.
- New hierarchical preprocessing outputs.
- Centralized and FedAvg hierarchical training sequence.
- How current binary baselines will be presented as foundation results.

## 10. Decision Statement

Pending review, the project should adopt:

`SecureIDS-HierarchicalAdvancedNet`

as the final advanced architecture direction, with a binary detection head and
dataset-aware attack-family head. The current binary centralized/FedAvg work
remains valid foundation work, while future professor-facing results should be
produced by the approved hierarchical architecture.

No implementation, training, security, attack, XAI, dashboard, or GitHub push
should proceed until this direction is approved.
