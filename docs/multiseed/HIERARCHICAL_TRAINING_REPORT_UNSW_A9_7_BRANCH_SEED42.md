# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T13:28:46.593564+00:00`

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
- Best epoch: `17` (epochs run: `23`)
- Best validation hierarchical score: `0.752137`
- Validation binary macro-F1 (best epoch): `0.9275356293301599`
- Validation attack-family macro-F1 (best epoch): `0.5767386198904179`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `530,186`

## Final test - Head 1 (binary)

- accuracy: `0.900318`
- precision: `0.883024`
- recall: `0.944013`
- f1: `0.912501`
- macro_f1: `0.898348`
- attack false negatives (attacks predicted benign): `2538`
- confusion (tn,fp,fn,tp): `31331, 5669, 2538, 42794`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.767537`
- macro-F1 on attack rows (all 9 classes): `0.493667`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9991 | 0.9608 | 0.9796 | 18871 |
| `Exploits` | 0.7884 | 0.6053 | 0.6848 | 11132 |
| `Fuzzers` | 0.8477 | 0.7077 | 0.7714 | 6062 |
| `DoS` | 0.3217 | 0.5596 | 0.4085 | 4089 |
| `Reconnaissance` | 0.7771 | 0.8518 | 0.8128 | 3496 |
| `Analysis` | 0.0000 | 0.0000 | 0.0000 | 677 |
| `Backdoor` | 0.0534 | 0.1372 | 0.0769 | 583 |
| `Shellcode` | 0.3120 | 0.6852 | 0.4288 | 378 |
| `Worms` | 0.1779 | 0.6591 | 0.2802 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.35450059186742167`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.3120 | 0.6852 | 0.4288 | 378 |
| `Worms` | 0.1779 | 0.6591 | 0.2802 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `31331` (0.8468 of 37000 benign)
- attack detected and correctly attributed: `32593` (0.7190 of 45332 attacks)
- attack detected but wrong family: `10201` (0.2250)
- attack missed as benign: `2538` (0.0560)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\multiseed\unsw_a9_7_branch_seed42.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\multiseed\unsw_a9_7_branch_seed42`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\multiseed\hierarchical_training_manifest_unsw_a9_7_branch_seed42.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
