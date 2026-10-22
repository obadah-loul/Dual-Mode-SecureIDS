> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (UNSW-NB15)

Status: `Task A9 complete - first real centralized hierarchical training (UNSW-NB15 only)`

Generated UTC: `2026-06-24T04:12:40.521862+00:00`

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
- Best epoch: `36` (epochs run: `40`)
- Best validation hierarchical score: `0.757317`
- Validation binary macro-F1 (best epoch): `0.9251139019877719`
- Validation attack-family macro-F1 (best epoch): `0.5895193203898301`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `513,418`

## Final test - Head 1 (binary)

- accuracy: `0.912865`
- precision: `0.903191`
- recall: `0.942800`
- f1: `0.922570`
- macro_f1: `0.911474`
- attack false negatives (attacks predicted benign): `2593`
- confusion (tn,fp,fn,tp): `32419, 4581, 2593, 42739`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.761140`
- macro-F1 on attack rows (all 9 classes): `0.485478`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9997 | 0.9632 | 0.9811 | 18871 |
| `Exploits` | 0.7224 | 0.6782 | 0.6996 | 11132 |
| `Fuzzers` | 0.8645 | 0.6506 | 0.7425 | 6062 |
| `DoS` | 0.3060 | 0.3764 | 0.3375 | 4089 |
| `Reconnaissance` | 0.8276 | 0.8295 | 0.8286 | 3496 |
| `Analysis` | 0.0066 | 0.0089 | 0.0076 | 677 |
| `Backdoor` | 0.0353 | 0.0755 | 0.0481 | 583 |
| `Shellcode` | 0.2365 | 0.8333 | 0.3684 | 378 |
| `Worms` | 0.2437 | 0.6591 | 0.3558 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.3621246367452373`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.2365 | 0.8333 | 0.3684 | 378 |
| `Worms` | 0.2437 | 0.6591 | 0.3558 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `32419` (0.8762 of 37000 benign)
- attack detected and correctly attributed: `32237` (0.7111 of 45332 attacks)
- attack detected but wrong family: `10502` (0.2317)
- attack missed as benign: `2593` (0.0572)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\final\final_unsw_hierarchical_a9_6_head2_loss_weight.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\final\hierarchical\unsw_a9_6_head2_loss_weight`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
