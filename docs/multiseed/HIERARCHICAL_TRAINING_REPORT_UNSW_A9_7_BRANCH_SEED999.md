> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T13:30:59.318118+00:00`

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
- Best epoch: `11` (epochs run: `17`)
- Best validation hierarchical score: `0.742842`
- Validation binary macro-F1 (best epoch): `0.9258064442332707`
- Validation attack-family macro-F1 (best epoch): `0.5598773288182564`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `530,186`

## Final test - Head 1 (binary)

- accuracy: `0.903379`
- precision: `0.888365`
- recall: `0.943020`
- f1: `0.914877`
- macro_f1: `0.901583`
- attack false negatives (attacks predicted benign): `2583`
- confusion (tn,fp,fn,tp): `31628, 5372, 2583, 42749`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.777398`
- macro-F1 on attack rows (all 9 classes): `0.493259`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9993 | 0.9623 | 0.9805 | 18871 |
| `Exploits` | 0.8272 | 0.5748 | 0.6783 | 11132 |
| `Fuzzers` | 0.8235 | 0.7303 | 0.7741 | 6062 |
| `DoS` | 0.3300 | 0.7298 | 0.4545 | 4089 |
| `Reconnaissance` | 0.7839 | 0.8415 | 0.8117 | 3496 |
| `Analysis` | 0.0462 | 0.0044 | 0.0081 | 677 |
| `Backdoor` | 0.1795 | 0.0240 | 0.0424 | 583 |
| `Shellcode` | 0.2823 | 0.7910 | 0.4161 | 378 |
| `Worms` | 0.2549 | 0.2955 | 0.2737 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.344914478262462`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.2823 | 0.7910 | 0.4161 | 378 |
| `Worms` | 0.2549 | 0.2955 | 0.2737 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `31628` (0.8548 of 37000 benign)
- attack detected and correctly attributed: `32924` (0.7263 of 45332 attacks)
- attack detected but wrong family: `9825` (0.2167)
- attack missed as benign: `2583` (0.0570)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\multiseed\unsw_a9_7_branch_seed999.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\multiseed\unsw_a9_7_branch_seed999`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\multiseed\hierarchical_training_manifest_unsw_a9_7_branch_seed999.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
