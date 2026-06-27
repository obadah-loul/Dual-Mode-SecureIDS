# FedAvg Dry-Run Report

This report is generated only by `federated-dry-run`. It records dry-run validation status without training, checkpoint creation, final metric generation, or test evaluation.

## UNSW-NB15

Status: `PASS`
- Config: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\configs\federated\unsw_nb15_fedavg.yaml`
- Algorithm: `FedAvg`
- Clients: `5`
- Feature count: `190`
- Train labels: `69982`
- Failed checks: `0`

## CICIDS2018

Status: `PASS`
- Config: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\configs\federated\cicids2018_fedavg.yaml`
- Algorithm: `FedAvg`
- Clients: `5`
- Feature count: `77`
- Train labels: `6737603`
- Failed checks: `0`

## Safety Confirmation

- No federated training is run by dry-run validation.
- No federated checkpoints are created.
- No final federated metrics are generated.
- No test evaluation is run.
- No security, attack, robust aggregation, XAI, or dashboard work is triggered.
