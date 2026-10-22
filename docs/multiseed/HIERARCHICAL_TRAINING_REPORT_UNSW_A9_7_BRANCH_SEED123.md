> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T13:30:10.359417+00:00`

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
- Best epoch: `25` (epochs run: `31`)
- Best validation hierarchical score: `0.760457`
- Validation binary macro-F1 (best epoch): `0.9297508357511989`
- Validation attack-family macro-F1 (best epoch): `0.5911622900311296`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `530,186`

## Final test - Head 1 (binary)

- accuracy: `0.901679`
- precision: `0.885916`
- recall: `0.942844`
- f1: `0.913494`
- macro_f1: `0.899810`
- attack false negatives (attacks predicted benign): `2591`
- confusion (tn,fp,fn,tp): `31496, 5504, 2591, 42741`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.773493`
- macro-F1 on attack rows (all 9 classes): `0.511542`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9996 | 0.9624 | 0.9807 | 18871 |
| `Exploits` | 0.8208 | 0.5900 | 0.6865 | 11132 |
| `Fuzzers` | 0.8382 | 0.7222 | 0.7759 | 6062 |
| `DoS` | 0.3266 | 0.6579 | 0.4365 | 4089 |
| `Reconnaissance` | 0.8100 | 0.8318 | 0.8208 | 3496 |
| `Analysis` | 0.0000 | 0.0000 | 0.0000 | 677 |
| `Backdoor` | 0.0569 | 0.0943 | 0.0710 | 583 |
| `Shellcode` | 0.3345 | 0.7381 | 0.4604 | 378 |
| `Worms` | 0.2824 | 0.5455 | 0.3721 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.41624453142988715`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.3345 | 0.7381 | 0.4604 | 378 |
| `Worms` | 0.2824 | 0.5455 | 0.3721 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `31496` (0.8512 of 37000 benign)
- attack detected and correctly attributed: `32791` (0.7234 of 45332 attacks)
- attack detected but wrong family: `9950` (0.2195)
- attack missed as benign: `2591` (0.0572)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\multiseed\unsw_a9_7_branch_seed123.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\multiseed\unsw_a9_7_branch_seed123`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\multiseed\hierarchical_training_manifest_unsw_a9_7_branch_seed123.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
