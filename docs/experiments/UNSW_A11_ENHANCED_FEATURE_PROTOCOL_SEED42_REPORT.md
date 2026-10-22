> **Historical record — correction dated 22 October 2026.** Current scope is defined by the
> [project verification report](../PROJECT_VERIFICATION_REPORT.md). Original task-scoped claims of no test tuning
> do not establish an untouched test set across development: test feedback informed later
> choices. Old plans/status statements are not evidence of current functionality.
> Federation was simulated; privacy, TLS, and authenticated origins were not demonstrated.
> Original measurements below are retained.

# Hierarchical Training Report (UNSW-NB15)

Status: `Real centralized hierarchical training (UNSW-NB15, A8.8 corrected benchmark protocol)`

Generated UTC: `2026-06-25T18:36:11.176746+00:00`

## Scope and protocol

- This is the **corrected UNSW-NB15 benchmark protocol** (A8.8): train/val on the
  175,341-row canonical training partition, final test on the 82,332-row canonical
  testing partition.
- The old UNSW binary centralized/FedAvg baselines are **legacy / pre-correction**
  and are NOT final hierarchical results.
- `input_dim` = **192**; `attack_head_dim` = **9**.
- Model: `SecureIDSHierarchicalAdvancedNet` (shared encoder + binary Head 1 +
  dataset-aware attack-family Head 2).
- Checkpoint selected by **validation only**
  (`val_hierarchical_score = 0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1`).
- Test evaluated **once** after the best validation checkpoint was selected.
- Class weights computed from the **train split only** (no validation/test labels);
  no test-set tuning.
- Not started yet: hierarchical FedAvg, security/SHA-256, Byzantine attacks,
  Trimmed Mean, XAI, dashboard.

## Training

- Device: `cuda`
- Best epoch: `23` (epochs run: `29`)
- Best validation hierarchical score: `0.757436`
- Validation binary macro-F1 (best epoch): `0.9330801615926818`
- Validation attack-family macro-F1 (best epoch): `0.5817916211132313`
- Train class distribution (binary): `{'0': 47600, '1': 101439}`
- Model parameters: `513,418`

## Final test - Head 1 (binary)

- accuracy: `0.899104`
- precision: `0.872208`
- recall: `0.956962`
- f1: `0.912621`
- macro_f1: `0.896630`
- attack false negatives (attacks predicted benign): `1951`
- confusion (tn,fp,fn,tp): `30644, 6356, 1951, 43381`
- n_samples: `82332`

## Final test - Head 2 (attack-family, attack rows only)

- accuracy on attack rows: `0.760964`
- macro-F1 on attack rows (all 9 classes): `0.494685`
- attack rows evaluated: `45332`

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Generic` | 0.9999 | 0.9621 | 0.9806 | 18871 |
| `Exploits` | 0.8299 | 0.5921 | 0.6911 | 11132 |
| `Fuzzers` | 0.8439 | 0.6467 | 0.7322 | 6062 |
| `DoS` | 0.3237 | 0.6175 | 0.4248 | 4089 |
| `Reconnaissance` | 0.8284 | 0.8284 | 0.8284 | 3496 |
| `Analysis` | 0.0594 | 0.0739 | 0.0658 | 677 |
| `Backdoor` | 0.0353 | 0.0583 | 0.0440 | 583 |
| `Shellcode` | 0.2172 | 0.7831 | 0.3400 | 378 |
| `Worms` | 0.2339 | 0.6591 | 0.3452 | 44 |

## Final test - rare classes

- rare-class macro-F1 (Shellcode, Worms): `0.34263627909521066`

| Rare class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `Shellcode` | 0.2172 | 0.7831 | 0.3400 | 378 |
| `Worms` | 0.2339 | 0.6591 | 0.3452 | 44 |

## Final test - end-to-end routing

- benign correctly stopped: `30644` (0.8282 of 37000 benign)
- attack detected and correctly attributed: `32871` (0.7251 of 45332 attacks)
- attack detected but wrong family: `10510` (0.2318)
- attack missed as benign: `1951` (0.0430)

## Output artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\experiments\unsw_a11_enhanced_feature_protocol_seed42.pt`
- result dir: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\unsw_a11_enhanced_feature_protocol_seed42`
- training manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\experiments\unsw_a11_enhanced_feature_protocol_seed42\manifest.json`

## Safety confirmation

- Checkpoint selected by validation only; test evaluated once after selection.
- No test-set tuning; class weights from train split only.
- Old UNSW pre-correction baselines preserved as legacy, not used as final.
- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.
- CICIDS hierarchical training not run. V1 not modified. No Git operations.
