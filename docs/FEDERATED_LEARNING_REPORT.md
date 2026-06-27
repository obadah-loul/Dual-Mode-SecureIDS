# Federated Learning Report

Status: `UNSW FedAvg completed; CICIDS FedAvg completed`

## CICIDS2018 FedAvg

- Config: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\configs\federated\cicids2018_fedavg.yaml`
- Algorithm: `FedAvg`
- Model: `SecureIDSNet`
- Input dimension: `77`
- Clients: `5`
- Best round by validation macro-F1: `20`
- Final test accuracy: `0.9793021479138341`
- Final test macro-F1: `0.9743010869503197`

## Client Setup

- `client_00`: total=1347521, class_0=962768, class_1=384753
- `client_01`: total=1347521, class_0=962768, class_1=384753
- `client_02`: total=1347521, class_0=962768, class_1=384753
- `client_03`: total=1347521, class_0=962768, class_1=384753
- `client_04`: total=1347519, class_0=962767, class_1=384752

## Confusion Matrix

- TP: `388494`
- FP: `6141`
- FN: `23742`
- TN: `1025396`

## Centralized Reference Comparison

- Centralized CICIDS2018 accuracy: `0.9795632692951038`
- Centralized CICIDS2018 macro-F1: `0.9746194261725205`
- FedAvg CICIDS2018 accuracy: `0.9793021479138341`
- FedAvg CICIDS2018 macro-F1: `0.9743010869503197`

## Output Artifacts

- checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\federated\fedavg_cicids_binary.pt`
- round_history: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\cicids\fedavg_round_history.csv`
- client_distribution: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\cicids\fedavg_client_distribution.csv`
- client_logs: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\cicids\fedavg_client_logs.csv`
- test_metrics: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\cicids\fedavg_test_metrics.json`
- confusion_matrix: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\cicids\fedavg_confusion_matrix.csv`
- manifest: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\audits\fedavg_manifest_cicids2018.json`
- report: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\docs\FEDERATED_LEARNING_REPORT.md`

## Safety Confirmation

- UNSW FedAvg outputs were not rerun or overwritten.
- No centralized checkpoint, metric, history, confusion matrix, or manifest was modified.
- Test data was evaluated once after selecting the best validation round.
- No security, attack simulation, Trimmed Mean, XAI, or dashboard model demo was run.

- UNSW FedAvg was previously completed and remains a separate preserved result.
## Scope Limitations

- TLS/security, SHA-256 integrity, attack simulation, Trimmed Mean, XAI, and dashboard integration remain future work.

## UNSW FedAvg Preserved Result

- Checkpoint: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\models\federated\fedavg_unsw_binary.pt`
- Metrics: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\results\federated\unsw\fedavg_test_metrics.json`
- Accuracy: `0.8761327926725637`
- Macro-F1: `0.8679284268229737`
- This result was not rerun or overwritten by CICIDS FedAvg training.
