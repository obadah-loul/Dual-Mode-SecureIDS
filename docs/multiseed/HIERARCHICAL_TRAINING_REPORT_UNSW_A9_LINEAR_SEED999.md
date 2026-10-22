> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T13:27:39.529513+00:00`

## Scope and protocol

- This is the **corrected UNSW-NB15 benchmark protocol** (A8.8): train/val on the
  175,341-row canonical training partition, final test on the 82,332-row canonical
  testing partition.
- The old UNSW binary centralized/FedAvg baselines are **legacy / pre-correction**
  and are NOT final hierarchical results.
- Corrected `input_dim` = **192**; `attack_head_dim` = **9**.
- Model: `SecureIDSHierarchicalAdvancedNet` (shared encoder + binary Head 1 +
  dataset-aware attack-family Head 2).
- Checkpoint selected by **validation only**
  (`val_hierarchical_score = 0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1`).
- Test evaluated **once** after the best validation checkpoint was selected.
- Class weights computed from the **train split only** (no validation/test labels);
  no test-set tuning.
- Not started yet: hierarchical FedAvg, security/SHA-256, Byzantine attacks,
  Trimmed Mean, XAI, dashboard. CICIDS hierarchical training has NOT been run.

## Training

- Device: `cuda`
- Best epoch: `18` (epochs run: `24`)
- Best validation hierarchical score: `0.752012`
- Validation binary macro-F1 (best epoch): `0.9272225264644265`
- Validation attack-family macro-F1 (best epoch): `0.5768019107522804`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `513,418`

## Final test - Head 1 (binary)

- accuracy: `0.898241`
- precision: `0.877128`
- recall: `0.947984`
- f1: `0.911180`
- macro_f1: `0.896035`
- attack false negatives (attacks predicted benign): `2358`
- confusion (tn,fp,fn,tp): `30980, 6020, 2358, 42974`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.773229`
- macro-F1 on attack rows (all 9 classes): `0.505731`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9998 | 0.9622 | 0.9806 | 18871 |
| `Exploits` | 0.8141 | 0.5997 | 0.6907 | 11132 |
| `Fuzzers` | 0.8637 | 0.6857 | 0.7645 | 6062 |
| `DoS` | 0.3268 | 0.6850 | 0.4425 | 4089 |
| `Reconnaissance` | 0.8048 | 0.8304 | 0.8174 | 3496 |
| `Analysis` | 0.0000 | 0.0000 | 0.0000 | 677 |
| `Backdoor` | 0.0498 | 0.0617 | 0.0551 | 583 |
| `Shellcode` | 0.2678 | 0.7963 | 0.4008 | 378 |
| `Worms` | 0.3443 | 0.4773 | 0.4000 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.40039946737683085`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.2678 | 0.7963 | 0.4008 | 378 |
| `Worms` | 0.3443 | 0.4773 | 0.4000 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `30980` (0.8373 of 37000 benign)
- attack detected and correctly attributed: `32955` (0.7270 of 45332 attacks)
- attack detected but wrong family: `10019` (0.2210)
- attack missed as benign: `2358` (0.0520)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\multiseed\unsw_a9_linear_seed999.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\multiseed\unsw_a9_linear_seed999`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\multiseed\hierarchical_training_manifest_unsw_a9_linear_seed999.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
