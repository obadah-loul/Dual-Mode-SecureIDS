# Adapter Interface And Pipeline Registry

## Purpose

This document describes the lightweight adapter interface and pipeline metadata registry for Secure IDS V2.

The registry connects the existing schema detector/router to dataset-aware adapter and artifact metadata. It does not train, preprocess full datasets, load checkpoints, run predictions, compute XAI, or launch Streamlit.

## Fit After Schema Detector/Router

The current architecture flow is:

```text
input sample/file
-> schema detector/router
-> supported adapter/pipeline metadata
-> later preprocessing artifact loading
-> later model checkpoint loading
-> Head 1 Normal vs Attack
-> Head 2 attack family/type
-> XAI
-> Streamlit dashboard output
```

The correct wording is: input schema matches a supported adapter/pipeline.

The system should not say that traffic belongs to CICIDS, UNSW, or a model. The registry reports schema compatibility and route metadata only.

## Adapter Interface Contract

`secureids/datasets/adapter_contracts.py` defines:

- `ArtifactStatus`
- `PreprocessingArtifactSet`
- `CheckpointReference`
- `AdapterPipelineMetadata`

These contracts separate registered metadata from real artifact existence. A path can be registered and still missing. Missing artifacts must be shown as missing or unconfirmed; they must not be treated as successful outputs.

## Registered CICIDS2018 Metadata

Schema ID: `cicids2018`

Adapter:

- `secureids.datasets.cicids2018.CICIDS2018Adapter`

Registered preprocessing and taxonomy configs:

- `configs/preprocessing/cicids2018_binary.yaml`
- `configs/preprocessing/cicids2018_hierarchical.yaml`
- `configs/taxonomy/cicids2018_attack_taxonomy.yaml`

Training config identifiers, metadata only:

- `configs/training/cicids2018_binary.yaml`
- `configs/training/cicids2018_hierarchical.yaml`

Checkpoint references, existence only:

- `models/final/final_cicids_hierarchical.pt`
- `models/final/final_cicids_binary.pt`
- `models/federated/fedavg_cicids_hierarchical.pt`
- `models/federated/fedavg_cicids_binary.pt`

The registry does not claim these checkpoints are final accepted evidence. It only reports whether the files exist.

## Registered UNSW-NB15 Metadata

Schema ID: `unsw_nb15`

Adapter:

- `secureids.datasets.unsw_nb15.UNSWNB15Adapter`

Registered preprocessing and taxonomy configs:

- `configs/preprocessing/unsw_nb15_binary.yaml`
- `configs/preprocessing/unsw_nb15_hierarchical.yaml`
- `configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`

Training config identifiers, metadata only:

- `configs/training/unsw_nb15_binary.yaml`
- `configs/training/unsw_nb15_hierarchical.yaml`
- `configs/training/unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml`
- `configs/training/unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml`

Checkpoint references, existence only:

- `models/final/final_unsw_hierarchical.pt`
- `models/final/final_unsw_binary.pt`
- `models/federated/fedavg_unsw_hierarchical.pt`
- `models/federated/fedavg_unsw_binary.pt`

The registry records existence only. It does not replace the A9/A9.6/A9.7/A9.8 review decisions and does not claim a checkpoint is final without evidence review.

## Metadata vs Artifacts vs Evidence

Registered pipeline metadata means the project knows which adapter, config, taxonomy, processed directory, and checkpoint family would be used later.

Preprocessing artifacts are saved files/directories such as processed arrays, preprocessing manifests, taxonomy configs, and preprocessor joblib files. They may exist or be missing.

Trained checkpoint existence means a `.pt` file is present at the expected path. Existence alone is not the same as final accepted result evidence.

Final accepted result evidence requires config snapshots, command or log evidence, saved metrics, saved artifacts, and clear reports with no test leakage.

## Unknown Or Missing Artifact Behavior

Unknown input schemas should be rejected by the schema detector/router unless the caller explicitly allows unknown routes.

Missing artifacts are reported with `exists=false` and a note. The registry should not create, delete, move, or repair artifacts.

## Why This Avoids Fake Shared Checkpoints

CICIDS2018 and UNSW-NB15 have different schemas, preprocessing artifacts, and attack taxonomies. The registry supports one professional interface while keeping dataset-specific pipeline metadata behind it.

This avoids pretending that one checkpoint or one preprocessing pipeline works across incompatible schemas.

## Future Dashboard Flow

Future Streamlit prediction flow:

1. User uploads or selects a sample.
2. Detector identifies whether the input schema matches a supported adapter/pipeline.
3. Registry returns adapter/pipeline metadata.
4. Future predictor loads saved preprocessing artifacts.
5. Future predictor loads the correct checkpoint only if available and approved.
6. UI displays Head 1, Head 2, and XAI outputs.

The current registry stops at metadata and existence checks.

## Limitations

- No model loading is implemented here.
- No preprocessing artifact loading is implemented here.
- No prediction service is implemented here.
- Checkpoint references are not final result claims.
- Model input dimensions are recorded from current metadata/config context and should be rechecked before final demo integration.

## Future Steps

- Connect a real preprocessing artifact loader.
- Connect an approved checkpoint loader.
- Create a lightweight prediction service.
- Integrate metadata and prediction into Streamlit.
- Run a final artifact verification audit before the demo.
