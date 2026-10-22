# Dual-Mode SecureIDS — Verified Scope and Scientific Limitations

**Status:** owner-authorized public source and CICIDS release v0.1.0; UNSW compact bundle private
**Evidence reviewed:** local-recovery report and test artifacts dated 22 October 2026
**Reference source baseline:** `afab2b0fe56c205201b930a99d5c999fe0489fd4`

## 1. Accurate project description

Dual-Mode SecureIDS is a **cybersecurity research prototype** that explores
centralized-reference and **simulated federated** intrusion detection using
CICIDS2018 and UNSW-NB15. It includes dataset-specific preprocessing pipelines,
a PyTorch hierarchical classifier with binary and attack-family outputs,
FedAvg and Trimmed Mean aggregation implementations, simulated full-state
SignFlip experiments, SHA-256 fingerprinting, and local Gradient × Input
attributions. A Streamlit dashboard **replays preselected processed test records**
through original pretrained hierarchical federated checkpoints. It does not
capture live traffic, implement secure multi-site deployment, or certify new
unseen examples.

## 2. What is verified versus merely recorded

| Component / claim | Evidence and status | Limitation |
|---|---|---|
| Source code and config | Owner-authorized repaired source published with tests and targeted checks | Publication does not independently reproduce the historical research |
| Unit/integration tests | Final integration executed 393 tests: all passed, no errors/skips. Prior 377-test, six-CLI-check and 35-packaging-test records are retained separately | Automated tests are not full benchmark reproduction or independent research replication |
| Dashboard | Current clean-directory seven-row and CICIDS-only checks executed real CPU inference and XAI, matching prior row/prediction/attribution evidence; both descriptive modes checked | Saved rows only, not a general raw-flow or network IDS |
| Model recovery | 76 original checkpoints passed restricted local loading; two selected centralized checkpoint digests matched frozen references | Selected federated digests are current recovery fingerprints, without original third-party anchors |
| Processed arrays | Original backup's nine hierarchical splits reported checked for shapes, finite values and labels/masks | Raw CSVs unavailable; source identity and train/test session leakage cannot be verified retrospectively |
| Federated execution | Code contains local client-training and aggregation simulation; repairs reject unsupported settings | No deployed clients, network privacy guarantees or secure aggregation |
| SHA-256 functionality | Hashes computed and recorded; supplied pre-existing records can be compared to detect changed bytes | Self-computed historical hashes do not authenticate senders or establish untampered origin |
| Full experimental performance | Historical metric JSON/CSV and selected checkpoints were preserved | No new full-dataset evaluations; test feedback influenced model development |
| Reproducibility | Python 3.12 Windows tested; compact replay can run without raw datasets | Historical raw-source/provenance incomplete; raw preprocessor version compatibility unverified |

The final 393-test pass was executed locally for this integration. Earlier counts
refer to preserved verification records, not additional independent experiments.
The clean replay checks do not independently replicate the historical research.

### Reading historical saved summaries

The saved JSON/CSV measurements and checkpoint bytes are unchanged. Historical
`all_rounds_verified` or similar true flags record local hash self-checks, not
authenticated client origin. Historical `no_test_tuning` safety flags are author
assertions about task/run scope, not proof that later research choices ignored
test results. Status strings such as `not_run_yet` in saved config snapshots
record their preparation stage, not current execution readiness. Historical
machine paths identify the old environment and are not installation commands.
Original absent rare-class summaries remain absent; the
[derived supplement](recovery/rare_class_supplement.csv) is explicitly a mean of
saved class scores, not a new evaluation. Current preflight/readiness outputs
separate supported execution and resources from configuration validation.

## 3. Scientific meaning of the attack/defense comparison

The historical `signflip25` labels refer to `malicious_fraction: 0.25`
**requested**, but actual selection floor-rounded five clients to **one
malicious client, or 20% realized**. Likewise nominal `0.50` over five clients
selected two (40%). Original filenames and numerical results remain unchanged.

Historical SignFlip multiplied the **absolute floating client model state**;
it did **not** invert only the locally learned update delta. The evidence
therefore applies to that specific simulated protocol only.

Phase A includes clean FedAvg, attacked FedAvg and attacked Trimmed Mean for
both datasets. It does not provide a clean Trimmed Mean control, independent
replication across seeds, or an untouched confirmatory test set. Macro-F1 and
missed-as-benign should be reported together, especially on UNSW-NB15, where
Trimmed Mean increased the latter despite improving macro-F1. Attack-family
macro-F1 measured on true attack rows is an **oracle-head diagnostic**, not a
complete routed deployment F1 measure. Refer to the saved matrix and the
[risk-qualified Phase A explanation](experiments/PHASE_A_SIGNFLIP25_ATTACK_DEFENSE_SUMMARY.md).

## 4. Release and demonstration boundaries

- The **public candidate** contains source, reports, plus a separate compact
  CICIDS-only package with one original checkpoint and four selected genuine
  processed samples, subject to owner/model rights and proper attribution.
- The **seven-scenario** CICIDS/UNSW bundle adds a second original checkpoint and
  three UNSW test samples. Keep it **private** until the right to redistribute
  UNSW-derived records has been established.
- Both replay bundles contain actual processed rows and compute fresh model
  inference and gradient attributions, not stored predictions. Neither can run
  arbitrary raw traffic, a full benchmark, or a complete federated training run.
- No large raw datasets, original full processed splits or 76-checkpoint archive
  are part of the publication candidate.
- The full local original backup is separate and must remain unchanged.
- The project owner has not yet selected a blanket license for source/model reuse.
  See [distribution notices](DATASET_RIGHTS.md) and
  [demo distribution](DEMO_DISTRIBUTION.md).

## 5. Final truth/consistency rules

The README, dashboard, figures, reports, and GitHub repository description
must consistently state:

1. **Research prototype**, not a production-ready IDS.
2. **Simulated federation**, not demonstrated multi-site secrecy or TLS.
3. **Saved processed-record replay** with real inference, not packet capture.
4. **20% realized** for nominal SignFlip25; no 25%-realized result.
5. **Full-model-state sign inversion**, not generic gradient-delta poisoning.
6. **SHA-256 fingerprints**, not independent sender authentication.
7. **Saved exploratory metrics**, not an untouched confirmatory benchmark.
8. **Preserved, unmodified historical numeric evidence**, including failures,
   absent rare metrics, and UNSW missed-attack tradeoffs.
9. **Explicit dataset/model redistribution boundaries**, with private UNSW bundle.
10. **Evidence-qualified testing**, stating which exact checks executed and
    which cannot be independently reproduced without the raw original data.

## 6. Release decision

**Engineering candidate:** locally repaired and demo-verified according to the
supplied audit, test XML and compact-bundle integration evidence.
**Scientific evidence:** useful as an honestly qualified graduation research
prototype; not sufficient to claim generalizable robustness or strong privacy.
**Publication:** the owner separately authorized the public source and CICIDS
demonstration in [v0.1.0](https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/tag/v0.1.0).
The seven-scenario UNSW bundle remains private pending redistribution clearance.
No blanket code/model reuse license is granted by public visibility.

**GitHub repository description:**

> Research prototype for centralized and simulated federated intrusion detection, with hierarchical classification and an explainable pretrained replay demo.
