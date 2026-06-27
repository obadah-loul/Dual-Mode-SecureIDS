# Attack Taxonomy Audit

Status: `Task A1 complete; CICIDS Head 2 mapping revised in Task A4.5`

## 1. Source And Scope

The advanced direction is approved as the new final project direction: `SecureIDS-HierarchicalAdvancedNet` with Head 1 binary detection and Head 2 dataset-aware attack-family classification.

This task counted labels from actual raw data and produced taxonomy audit artifacts only. It did not implement the advanced model, train, evaluate model performance, run dry-runs, or modify baseline artifacts.

## 2. How Counts Were Obtained

- CICIDS2018: streamed `data/raw/cicids2018/*.csv` in chunks and counted the stripped `Label` column only.
- UNSW-NB15: streamed `data/raw/unsw_nb15/UNSW_NB15_training-set.csv` and `data/raw/unsw_nb15/UNSW_NB15_testing-set.csv` in chunks, counted `attack_cat` only where `label == 1`, and counted normal rows where `label == 0`.
- CICIDS support percentages use total CICIDS attack rows as denominator.
- UNSW support percentages use total UNSW attack rows as denominator.
- Audit-only rare rule: `is_rare = true` when support percent is below `1.0%` of attack rows. This threshold is not a training decision.

## 3. CICIDS2018 Summary

- Total rows inspected: 9625148
- Total benign rows: 6876913
- Total attack rows: 2748235

Benign/normal labels found:

- `Benign`: 6876913

CICIDS attack taxonomy counts and current Task A4.5 Head 2 classes:

| Raw label | Current CICIDS Head 2 class | Common superclass | Support | Support % | Rare |
| --- | --- | --- | ---: | ---: | --- |
| DDOS attack-HOIC | DDoS-HOIC | DoS/DDoS | 686012 | 24.961912 | false |
| DDoS attacks-LOIC-HTTP | DDoS-LOIC-HTTP | DoS/DDoS | 576191 | 20.965856 | false |
| DoS attacks-Hulk | DoS-Hulk | DoS/DDoS | 461912 | 16.807587 | false |
| Bot | Bot | Malware/Botnet | 286191 | 10.413629 | false |
| FTP-BruteForce | FTP-BruteForce | Brute Force | 193360 | 7.035788 | false |
| SSH-Bruteforce | SSH-Bruteforce | Brute Force | 187589 | 6.825799 | false |
| Infilteration | Infilteration / Infiltration | Exploitation | 161934 | 5.892291 | false |
| DoS attacks-SlowHTTPTest | DoS-SlowHTTPTest | DoS/DDoS | 139890 | 5.090176 | false |
| DoS attacks-GoldenEye | DoS-GoldenEye | DoS/DDoS | 41508 | 1.510351 | false |
| DoS attacks-Slowloris | DoS-Slowloris | DoS/DDoS | 10990 | 0.399893 | true |
| DDOS attack-LOIC-UDP | DDoS-LOIC-UDP | DoS/DDoS | 1730 | 0.062949 | true |
| Brute Force -Web | Web-BruteForce | Web/Injection | 611 | 0.022232 | true |
| Brute Force -XSS | Web-XSS | Web/Injection | 230 | 0.008369 | true |
| SQL Injection | SQL-Injection | Web/Injection | 87 | 0.003166 | true |

CICIDS rare classes under the audit-only `< 1%` rule:

`DoS attacks-Slowloris`, `DDOS attack-LOIC-UDP`, `Brute Force -Web`, `Brute Force -XSS`, `SQL Injection`

Task A4.5 revision:

- CICIDS Head 2 now preserves all 14 observed raw attack labels as separate
  normalized classes.
- No CICIDS rare raw label is hidden inside a broader Head 2 training class.
- Common superclasses remain reporting-only.
- `results/audits/cicids_attack_taxonomy_counts.csv` remains the support-count
  source; its historical mapped-family column is superseded by the A4.5 YAML
  mapping in `configs/taxonomy/cicids2018_attack_taxonomy.yaml`.

## 4. UNSW-NB15 Summary

- Total rows inspected: 257673
- Total normal rows: 93000
- Total attack rows: 164673

UNSW attack taxonomy counts:

| Raw label | Mapped attack family | Common superclass | Support | Support % | Rare |
| --- | --- | --- | ---: | ---: | --- |
| Generic | Generic | Generic/Other | 58871 | 35.750244 | false |
| Exploits | Exploits | Exploitation | 44525 | 27.038434 | false |
| Fuzzers | Fuzzers | Exploitation | 24246 | 14.723725 | false |
| DoS | DoS | DoS/DDoS | 16353 | 9.93059 | false |
| Reconnaissance | Reconnaissance | Reconnaissance | 13987 | 8.493803 | false |
| Analysis | Analysis | Reconnaissance | 2677 | 1.625646 | false |
| Backdoor | Backdoor | Malware/Botnet | 2329 | 1.414318 | false |
| Shellcode | Shellcode | Exploitation | 1511 | 0.917576 | true |
| Worms | Worms | Malware/Botnet | 174 | 0.105664 | true |

UNSW rare classes under the audit-only `< 1%` rule:

`Shellcode`, `Worms`

## 5. Dataset-Specific Taxonomy Decision

- CICIDS2018 Head 2 uses a raw-preserving 14-class mapping derived from the
  CICIDS `Label` field and revised in Task A4.5.
- UNSW-NB15 Head 2 should use UNSW-derived attack-family labels from `attack_cat` where `label == 1`.
- Do not force CICIDS raw labels and UNSW `attack_cat` values into one exact shared multiclass list.
- Dataset-aware attack-family heads are required because feature schemas and attack taxonomies differ.

## 6. Common Superclass Reporting Proposal

Common superclasses are allowed only for reporting/dashboard comparison, not as fake shared training labels.

Proposed common superclasses:

- DoS/DDoS
- Brute Force
- Web/Injection
- Reconnaissance
- Exploitation
- Malware/Botnet
- Generic/Other
- Rare/Unknown

Mapping notes:

- CICIDS `Infilteration` is mapped to `Exploitation` for reporting, but the raw spelling is preserved and the uncertainty should remain documented.
- UNSW `Analysis` is mapped to `Reconnaissance` for reporting because it generally represents analysis/probing behavior; this can be revisited after detailed error analysis.
- UNSW `Fuzzers` is mapped to `Exploitation` because fuzzing probes software behavior and may be grouped with exploit-discovery behavior for high-level reporting.

## 7. Rare-Class Risks

- Rare classes can have unstable per-class F1 because support is small.
- Head 1 false negatives can prevent Head 2 from ever seeing an attack at inference.
- Federated client splits may make rare classes absent from some clients.
- Class weighting or focal loss may be useful later, but must be validation-driven and not tuned on the test set.
- Poor rare-class performance must be reported honestly.

## 8. No-Fake-Results Notes

- This audit does not claim model performance.
- This audit does not create a shared CICIDS/UNSW multiclass target.
- Common superclasses are reporting-only.
- Cross-dataset attack-family training is not claimed.
- No test-set tuning is performed by this task.

## 9. Generated Audit Files

- `results/audits/cicids_attack_taxonomy_counts.csv`
- `results/audits/unsw_attack_taxonomy_counts.csv`
