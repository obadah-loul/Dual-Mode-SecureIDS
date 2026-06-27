# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T13:25:20.560722+00:00`

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
- Best epoch: `35` (epochs run: `40`)
- Best validation hierarchical score: `0.762364`
- Validation binary macro-F1 (best epoch): `0.9330895845116535`
- Validation attack-family macro-F1 (best epoch): `0.5916384802502117`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `513,418`

## Final test - Head 1 (binary)

- accuracy: `0.896808`
- precision: `0.874289`
- recall: `0.949043`
- f1: `0.910133`
- macro_f1: `0.894488`
- attack false negatives (attacks predicted benign): `2310`
- confusion (tn,fp,fn,tp): `30814, 6186, 2310, 43022`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.766478`
- macro-F1 on attack rows (all 9 classes): `0.500429`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9981 | 0.9641 | 0.9808 | 18871 |
| `Exploits` | 0.7784 | 0.6208 | 0.6907 | 11132 |
| `Fuzzers` | 0.8368 | 0.7095 | 0.7679 | 6062 |
| `DoS` | 0.3241 | 0.4825 | 0.3877 | 4089 |
| `Reconnaissance` | 0.8031 | 0.8432 | 0.8227 | 3496 |
| `Analysis` | 0.0373 | 0.0074 | 0.0123 | 677 |
| `Backdoor` | 0.0449 | 0.1630 | 0.0704 | 583 |
| `Shellcode` | 0.3079 | 0.7698 | 0.4399 | 378 |
| `Worms` | 0.2214 | 0.6591 | 0.3314 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.3856689342403628`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.3079 | 0.7698 | 0.4399 | 378 |
| `Worms` | 0.2214 | 0.6591 | 0.3314 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `30814` (0.8328 of 37000 benign)
- attack detected and correctly attributed: `32674` (0.7208 of 45332 attacks)
- attack detected but wrong family: `10348` (0.2283)
- attack missed as benign: `2310` (0.0510)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\multiseed\unsw_a9_linear_seed42.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\multiseed\unsw_a9_linear_seed42`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\multiseed\hierarchical_training_manifest_unsw_a9_linear_seed42.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
