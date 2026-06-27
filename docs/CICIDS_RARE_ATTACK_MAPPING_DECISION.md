# CICIDS Rare Attack Mapping Decision

Status: `Task A4.5 complete - CICIDS taxonomy revision decision`

## 1. Decision

Task A4 accepted the hierarchical preprocessing artifacts, but it also showed
that the old CICIDS Head 2 mapping hid two rare raw labels inside broad
families:

- `DoS attacks-Slowloris` was grouped into `DoS`.
- `DDOS attack-LOIC-UDP` was grouped into `DDoS`.

That broad family mapping was technically valid for family-level
classification, but it was not strong enough for the final advanced goal:
rare/raw attack-type detection inside `SecureIDS-HierarchicalAdvancedNet`.

Task A4.5 revises only the CICIDS2018 Head 2 taxonomy. CICIDS Head 2 now uses a
raw-preserving hybrid mapping: all 14 observed CICIDS raw attack labels remain
separate training classes with clean normalized names.

UNSW-NB15 is unchanged and continues to use the official `attack_cat`
categories.

## 2. Why Family-Level Mapping Was Not Enough

The final system needs to report more than binary attack detection and broad
attack families. It should also expose rare attack behavior, per-class
recall/F1, and future rare-class error analysis.

With the old 8-class CICIDS mapping, `DoS attacks-Slowloris` and
`DDOS attack-LOIC-UDP` were counted only as part of larger `DoS` and `DDoS`
classes. That made it impossible for Head 2 training/evaluation artifacts to
separate those rare raw attacks from the dominant DoS/DDoS traffic.

The revised mapping avoids that loss while keeping one organized final system.

## 3. Final CICIDS Head 2 Classes

Support counts come from `results/audits/cicids_attack_taxonomy_counts.csv`.
The rare rule remains the audit rule: `support_percent < 1.0`.

| Raw CICIDS label | Final Head 2 class | Support | Support % | Rare | Weak/hard flag |
| --- | --- | ---: | ---: | --- | --- |
| `DDOS attack-HOIC` | `DDoS-HOIC` | 686012 | 24.961912 | false | false |
| `DDoS attacks-LOIC-HTTP` | `DDoS-LOIC-HTTP` | 576191 | 20.965856 | false | false |
| `DDOS attack-LOIC-UDP` | `DDoS-LOIC-UDP` | 1730 | 0.062949 | true | false |
| `DoS attacks-Hulk` | `DoS-Hulk` | 461912 | 16.807587 | false | false |
| `DoS attacks-SlowHTTPTest` | `DoS-SlowHTTPTest` | 139890 | 5.090176 | false | true |
| `DoS attacks-GoldenEye` | `DoS-GoldenEye` | 41508 | 1.510351 | false | false |
| `DoS attacks-Slowloris` | `DoS-Slowloris` | 10990 | 0.399893 | true | false |
| `Bot` | `Bot` | 286191 | 10.413629 | false | false |
| `FTP-BruteForce` | `FTP-BruteForce` | 193360 | 7.035788 | false | true |
| `SSH-Bruteforce` | `SSH-Bruteforce` | 187589 | 6.825799 | false | false |
| `Infilteration` | `Infilteration / Infiltration` | 161934 | 5.892291 | false | true |
| `Brute Force -Web` | `Web-BruteForce` | 611 | 0.022232 | true | false |
| `Brute Force -XSS` | `Web-XSS` | 230 | 0.008369 | true | false |
| `SQL Injection` | `SQL-Injection` | 87 | 0.003166 | true | false |

## 4. Rare Raw Labels Preserved Separately

The following rare raw CICIDS labels are now separate Head 2 classes:

- `DoS attacks-Slowloris` -> `DoS-Slowloris`
- `DDOS attack-LOIC-UDP` -> `DDoS-LOIC-UDP`
- `Brute Force -Web` -> `Web-BruteForce`
- `Brute Force -XSS` -> `Web-XSS`
- `SQL Injection` -> `SQL-Injection`

No CICIDS raw attack label remains grouped inside another Head 2 training
class after A4.5.

## 5. Weak Or Hard Classes Preserved Separately

The following classes are also preserved separately because earlier review
identified them as security-important or potentially hard/weak classes:

- `FTP-BruteForce`
- `Infilteration / Infiltration`
- `DoS-SlowHTTPTest`

The weak/hard flag is a reporting and monitoring note only. It is not a model
performance claim and does not create a different training target.

## 6. Common Superclass Mapping

Common superclasses remain reporting-only. They are not Head 2 training
targets and they do not create a fake shared CICIDS/UNSW multiclass label list.

| Final CICIDS Head 2 class | Reporting-only common superclass |
| --- | --- |
| `DDoS-HOIC` | `DoS/DDoS` |
| `DDoS-LOIC-HTTP` | `DoS/DDoS` |
| `DDoS-LOIC-UDP` | `DoS/DDoS` |
| `DoS-Hulk` | `DoS/DDoS` |
| `DoS-SlowHTTPTest` | `DoS/DDoS` |
| `DoS-GoldenEye` | `DoS/DDoS` |
| `DoS-Slowloris` | `DoS/DDoS` |
| `Bot` | `Malware/Botnet` |
| `FTP-BruteForce` | `Brute Force` |
| `SSH-Bruteforce` | `Brute Force` |
| `Infilteration / Infiltration` | `Exploitation` |
| `Web-BruteForce` | `Web/Injection` |
| `Web-XSS` | `Web/Injection` |
| `SQL-Injection` | `Web/Injection` |

## 7. One Final System, Not Multiple Models

This mapping revision does not create multiple competing final models. It only
changes the CICIDS Head 2 label space for the same final architecture family:

`SecureIDS-HierarchicalAdvancedNet`

Head 1 remains binary for every dataset. Head 2 remains dataset-aware:

- CICIDS2018 uses the revised 14-class raw-preserving Head 2 taxonomy.
- UNSW-NB15 continues to use its 9 official `attack_cat` categories.

Dataset-specific checkpoints are still allowed later because CICIDS and UNSW
have different feature spaces and different Head 2 label spaces. They remain
instances of one final system design.

## 8. Compatibility With Masked Multi-Task Training

The revised mapping keeps the existing masked multi-task contract:

- Head 1 binary loss applies to all rows.
- Head 2 attack-type loss applies only where `attack_family_mask == 1`.
- Benign rows keep `y_attack_family = -1`.
- Benign rows keep `attack_family_mask = 0`.
- Attack rows keep `attack_family_mask = 1`.

Only CICIDS attack-family IDs change from the old 8-class family mapping to
the revised 14-class raw-preserving mapping.

## 9. Compatibility With Later Project Layers

The revision remains compatible with future stages:

- Centralized hierarchical training can use the same processed feature
  matrices with a 14-class CICIDS Head 2.
- FedAvg can aggregate same-dataset CICIDS hierarchical model instances with
  the same 14-class head.
- Byzantine attacks can be evaluated against both binary and attack-type
  behavior.
- Trimmed Mean can compare recovery on rare CICIDS classes against FedAvg.
- XAI can explain Head 1 and Head 2 decisions, including rare attack classes.
- The dashboard can show both detailed CICIDS Head 2 classes and
  reporting-only common superclasses.

## 10. UNSW-NB15 Unchanged

UNSW-NB15 taxonomy and hierarchical outputs are unchanged by Task A4.5.

UNSW continues to use official `attack_cat` categories:

- `Generic`
- `Exploits`
- `Fuzzers`
- `DoS`
- `Reconnaissance`
- `Analysis`
- `Backdoor`
- `Shellcode`
- `Worms`

Common superclass mapping remains reporting-only for UNSW as well.

## 11. No-Fake-Results Statement

Task A4.5 does not implement model code, train, evaluate model performance,
create checkpoints, create model metrics, start security/attack/Trimmed
Mean/XAI/dashboard work, modify V1, or create a fake shared CICIDS/UNSW
multiclass label list.
