# Dual-Mode SecureIDS

A cybersecurity graduation **research prototype** for binary intrusion detection
and dataset-specific attack-family classification. It includes centralized
reference results, simulated federated learning, exploratory robustness results,
and a Streamlit demonstration running genuine pretrained inference on selected
processed benchmark records. It is **not** a production network IDS.

The local recovery is based on commit `afab2b0fe56c205201b930a99d5c999fe0489fd4`.
Read the [verification and claims report](docs/PROJECT_VERIFICATION_REPORT.md)
and [recovery corrections](docs/LOCAL_RECOVERY.md) before interpreting
historical experiment reports. Recovery preserves model bytes and numerical
results, without retraining models or repeating experiments.

## Architecture and scope

**Dual-mode** refers to centralized reference experiments versus simulated
federated experiments. The dashboard's mode selector is descriptive only;
both selections use saved federated checkpoints for replay inference.
This is not two interchangeable live deployed detection engines.

Dataset adapters and train-fitted preprocessing feed a residual/gated MLP with a
shared embedding, one binary logit, and a dataset-specific family head. Family
predictions are exposed only when the binary decision is Attack. The family
metric on true attack rows is an oracle-head diagnostic; routed outcomes also
count attacks missed by the binary head.

| Dataset | Hierarchical inputs | Family outputs | Selected live checkpoint |
|---|---:|---:|---|
| CICIDS2018 | 77 | 14 | `models/experiments/federated_security/cicids_hierarchical_clean_fedavg.pt` |
| UNSW-NB15 | 192 | 9 | `models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt` |

Centralized binary and hierarchical models provide benchmark references. The
federated runner is an in-process simulation over centrally available arrays:
clients train locally, return full states, and use sample-weighted FedAvg or
coordinate-wise Trimmed Mean. It supports full participation and
attack-family-aware IID partitioning. Unsupported execution settings are rejected.
This implementation does not establish deployment privacy, secure aggregation,
TLS transport, or differential privacy.

Modules: `secureids/datasets`, `preprocessing`, `models`, `training`, `federated`,
`security`, `inference`, and `xai`; CLI: `secureids/cli.py`; UI: `dashboard/app.py`.
Exploratory specialist and A11 paths remain available, but are not the selected
dashboard models. Legacy 190-feature UNSW binary artifacts must not be mixed
with the current 192-feature hierarchical pipeline.

## Clone and install (Python 3.12)

```powershell
git clone https://github.com/obadah-loul/Dual-Mode-SecureIDS.git
cd Dual-Mode-SecureIDS
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The owner-authorized [v0.1.0 release](https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/tag/v0.1.0)
provides the CICIDS demonstration below. On Linux use
`python3.12 -m venv .venv` and `.venv/bin/python` in place of the Windows launcher
and environment executable. The verified platform is Windows/Python3.12/CPU.
CUDA and training are not required. The full tested Windows environment snapshot
is `requirements-lock-py312-windows.txt`.

## Obtain the small demo artifacts

Git excludes model weights and dataset arrays. Download the approved
[CICIDS demonstration archive](https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/download/v0.1.0/secureids-demo-cicids-v1.zip)
to a local `downloads/` folder. Its exact identity is recorded in
[configs/demo_artifacts.json](configs/demo_artifacts.json). This GitHub Release
asset requires neither Git LFS nor full dataset downloads.

| Archive | Size | Genuine replay rows | Distribution status |
|---|---:|---:|---|
| `secureids-demo-cicids-v1.zip` | 1.81 MB | 4 CICIDS scenarios | Owner-authorized public release; attribution included |
| `secureids-demo-seven-v1.zip` | 3.72 MB | All 7 scenarios | Private review only pending UNSW republication clarification |

Both retain real pretrained model weights and processed sample values. They
contain feature names, label mappings, original row indices and provenance, not
cached predictions. The seven-scenario package has two checkpoints and seven
rows; the CICIDS candidate has one checkpoint and four rows. Neither includes
raw data, full train/validation/test arrays, joblib preprocessors, or historical
checkpoint collections. Already processed rows need no preprocessing fits.

Download and install the CICIDS demo (checks archive and payload hashes before writes):

```powershell
New-Item -ItemType Directory -Force downloads | Out-Null
Invoke-WebRequest -Uri 'https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/download/v0.1.0/secureids-demo-cicids-v1.zip' -OutFile downloads/secureids-demo-cicids-v1.zip
.\.venv\Scripts\python.exe tools/demo_package.py install downloads/secureids-demo-cicids-v1.zip --sha256 98ab04d6a311f7a3efc2f2e0c32ac8c1b0729adfc04e3656ecde7f2eb97d61b7
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

Open `http://localhost:8501`. Select one of the four CICIDS scenarios and click
**Run IDS Replay**. Inference and Gradient × Input run locally on the
model. UNSW selections report missing artifacts with the CICIDS-only package.
Installation refuses different existing files; use a clean clone for a different
bundle. Rerunning installation of the same archive is safe.

Authorized private reviewers who received the full bundle instead install:

```powershell
.\.venv\Scripts\python.exe tools/demo_package.py install downloads/secureids-demo-seven-v1.zip --sha256 3844534c2ff5d7618424e5fbc129702c0bf754553012f40942cf37ed03815b2f
```

Then run the same Streamlit command; all seven scenarios are available. These
hashes are local artifact identities, not signatures or independent assurances
of original dataset authenticity. [SHA256SUMS-demo.txt](SHA256SUMS-demo.txt) records
them separately. The installer has no network activity and never loads pickle.

[Dataset rights and citations](docs/DATASET_RIGHTS.md) explain UNB's redistribution
terms, UNSW's academic-use grant and the outstanding republication question.
Do not publish the complete bundle until the required rights are established.
Eligible academic users can obtain authorized matching artifacts and build the
same compact package locally; see [distribution instructions](docs/DEMO_DISTRIBUTION.md).
The repository has no owner-selected blanket code/model license; no third-party
data or checkpoint is implicitly relicensed as open source.

## What the demo verifies

The dashboard replays selected genuine test rows; it does not capture packets,
execute attacks, accept unknown raw traffic, or benchmark the full dataset.
Original test indices remain visible even though only four/seven rows are stored.
Both deployment-mode selections use the selected federated model; the radio
control explains deployment framing. Explainability uses real model gradients.

`configs/selected_models.json` identifies selected reference models and their
training snapshots. The promoted centralized CICIDS model uses EXP03 attack loss
weight1.25 and seed999; the base CICIDS YAML is the earlier loss1.0/seed42 recipe.
Centralized and archival weights are not required for the replay and are excluded
from the small demo archives. Compact bundles are deliberately insufficient for
training or historical full-split evaluation.

Optional development checks:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m secureids.cli --help
.\.venv\Scripts\python.exe -m pytest -q tests/test_demo_package.py
```

The final consistency integration passed 393 automated tests with no failures
or skips. Earlier 377-test and 35-packaging-test records are retained separately.
Clean compact-bundle inference, XAI and dashboard checks also passed; no research
experiment or original-model training was repeated. Full-suite tests requiring recovered
historical artifacts may be unavailable in a fresh minimal demo clone.
Configuration PASS differs from execution readiness. Older audit/preprocessing
commands can write reports and must not overwrite preserved scientific evidence.
No training/preprocessing command is needed for the demonstration.

## Evidence and limitations

The authoritative public-facing summary of implementation, test evidence,
unsupported claims and remaining blockers is
[the project verification report](docs/PROJECT_VERIFICATION_REPORT.md).

Phase A compares clean FedAvg, attacked FedAvg, and attacked Trimmed Mean for
both datasets. Historical `signflip25` filenames describe a requested 25% setting
that selected **one of five clients: 20% realized**. The nominal 50% archive used
two of five: 40%. SignFlip inverted absolute floating model states, rather than
parameter deltas. Historical protocols and numerical outputs remain unchanged.

SHA-256 identifies sample, prediction, checkpoint, and schema bytes. Self-created
hashes are fingerprints, not independent integrity assurance or origin
authentication. The UI states this. Supplied reference hashes can detect changed
updates; the simulator does not authenticate senders.

Within each run validation selected checkpoints. Across development, observed
test results informed later experiments and model choices, so performance is
exploratory rather than an untouched confirmatory estimate. CICIDS uses random
row splitting, not a temporal/site holdout. Raw identity and flow-level overlap
remain unverified without raw data. Rare supports are small. Single-seed
federated evidence does not establish general robustness; UNSW defense improved
macro-F1 while worsening the missed-attack rate.

Read the [historical evidence index](docs/experiments/FINAL_EVIDENCE_REPORT_INDEX.md)
with the [recovery corrections](docs/LOCAL_RECOVERY.md). Local verification covers
compatibility, sample inference, numerical guards, and tests; it is not a fresh
full benchmark evaluation.
