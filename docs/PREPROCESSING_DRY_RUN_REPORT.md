# PREPROCESSING_DRY_RUN_REPORT.md

## Purpose

This report records preprocessing dry-run validation only. It
inspects configs, raw input paths, CSV headers, and tiny samples. It does
not create processed arrays, model artifacts, checkpoints, training
outputs, or performance metrics.

## cicids2018

- Status: `ok`
- Config path: `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\configs\preprocessing\cicids2018_binary.yaml`
- Files found: 14
- Detected column count: 79
- Target column status: `present`
- Processed outputs created: `false`
- Artifact created: `true`

Raw input paths checked:

- `C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2\data\raw\cicids2018`

Configured drop-column status:

- `Flow ID`: not present
- `Src IP`: not present
- `Dst IP`: not present
- `Dst Port`: present
- `Destination Port`: not present
- `Dest Port`: not present
- `Src Port`: not present
- `Source Port`: not present
- `Sport`: not present
- `Dport`: not present
- `Timestamp`: not present
- `Label`: present

Detected columns:

`Dst Port`, `Protocol`, `Flow Duration`, `Tot Fwd Pkts`, `Tot Bwd Pkts`, `TotLen Fwd Pkts`, `TotLen Bwd Pkts`, `Fwd Pkt Len Max`, `Fwd Pkt Len Min`, `Fwd Pkt Len Mean`, `Fwd Pkt Len Std`, `Bwd Pkt Len Max`, `Bwd Pkt Len Min`, `Bwd Pkt Len Mean`, `Bwd Pkt Len Std`, `Flow Byts/s`, `Flow Pkts/s`, `Flow IAT Mean`, `Flow IAT Std`, `Flow IAT Max`, `Flow IAT Min`, `Fwd IAT Tot`, `Fwd IAT Mean`, `Fwd IAT Std`, `Fwd IAT Max`, `Fwd IAT Min`, `Bwd IAT Tot`, `Bwd IAT Mean`, `Bwd IAT Std`, `Bwd IAT Max`, `Bwd IAT Min`, `Fwd PSH Flags`, `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `Fwd Header Len`, `Bwd Header Len`, `Fwd Pkts/s`, `Bwd Pkts/s`, `Pkt Len Min`, `Pkt Len Max`, `Pkt Len Mean`, `Pkt Len Std`, `Pkt Len Var`, `FIN Flag Cnt`, `SYN Flag Cnt`, `RST Flag Cnt`, `PSH Flag Cnt`, `ACK Flag Cnt`, `URG Flag Cnt`, `CWE Flag Count`, `ECE Flag Cnt`, `Down/Up Ratio`, `Pkt Size Avg`, `Fwd Seg Size Avg`, `Bwd Seg Size Avg`, `Fwd Byts/b Avg`, `Fwd Pkts/b Avg`, `Fwd Blk Rate Avg`, `Bwd Byts/b Avg`, `Bwd Pkts/b Avg`, `Bwd Blk Rate Avg`, `Subflow Fwd Pkts`, `Subflow Fwd Byts`, `Subflow Bwd Pkts`, `Subflow Bwd Byts`, `Init Fwd Win Byts`, `Init Bwd Win Byts`, `Fwd Act Data Pkts`, `Fwd Seg Size Min`, `Active Mean`, `Active Std`, `Active Max`, `Active Min`, `Idle Mean`, `Idle Std`, `Idle Max`, `Idle Min`, `Label`

Next step recommendation:

Review this dry-run report, then approve the preprocessing implementation phase before running real preprocessing.
