# Schema Detector And Router

## Purpose

This document describes the clean foundation for automatic schema detection and adapter routing in Secure IDS V2.

The detector/router is metadata-only. It does not load models, run predictions, train, rebuild preprocessing outputs, run long evaluations, compute XAI, or launch Streamlit.

## Final Architecture Support

The final project should not ask the professor to manually choose a random model. The intended flow is:

```text
input sample/file
-> schema detector/router
-> correct adapter/pipeline identifier
-> later prediction pipeline
-> Head 1 Normal vs Attack
-> Head 2 attack family/type
-> XAI
-> Streamlit dashboard output
```

The correct wording is: input schema matches a supported adapter/pipeline.

The system should not claim that traffic belongs to CICIDS, UNSW, or a model. CICIDS2018 and UNSW-NB15 are benchmark schemas/datasets with different feature spaces and attack taxonomies.

## What The Detector Does

`secureids/datasets/schema_detector.py` provides:

- `SupportedSchema`
- `SchemaDetectionResult`
- `normalize_column_name(name)`
- `detect_schema(columns_or_dataframe, min_confidence=..., ambiguity_margin=...)`

The detector normalizes column names by handling case, spaces, underscores, hyphens, slashes, punctuation, and common CICIDS naming variants. It scores the input against canonical CICIDS2018 and UNSW-NB15 column profiles using multiple expected and core columns.

It intentionally avoids fragile one-column detection. Low-confidence or ambiguous partial matches return `unknown` with a clear reason rather than crashing.

Supported input forms:

- A list, tuple, set, or other non-string iterable of column names.
- A pandas DataFrame or any object with a `columns` attribute.

## What The Router Does

`secureids/datasets/router.py` provides:

- `PipelineRoute`
- `UnsupportedSchemaError`
- `route_schema(columns_or_dataframe, require_supported=True)`
- `route_from_detection(result, require_supported=True)`

The router returns adapter/pipeline metadata:

- `schema_id`
- `adapter_id`
- `preprocessing_config`
- `hierarchical_preprocessing_config`
- `taxonomy_config`
- `checkpoint_family`
- `dashboard_label`
- `confidence`
- `reason`

It does not load a checkpoint or claim a final model path. `checkpoint_family` is an identifier for later integration, not proof that a final checkpoint exists.

## Supported Schemas

Supported schema routes:

- `cicids2018`
- `unsw_nb15`
- `unknown`

CICIDS-like route metadata points to:

- Adapter: `secureids.datasets.cicids2018.CICIDS2018Adapter`
- Binary preprocessing config: `configs/preprocessing/cicids2018_binary.yaml`
- Hierarchical preprocessing config: `configs/preprocessing/cicids2018_hierarchical.yaml`
- Taxonomy config: `configs/taxonomy/cicids2018_attack_taxonomy.yaml`
- Checkpoint family identifier: `cicids2018_hierarchical_checkpoint_family`

UNSW-like route metadata points to:

- Adapter: `secureids.datasets.unsw_nb15.UNSWNB15Adapter`
- Binary preprocessing config: `configs/preprocessing/unsw_nb15_binary.yaml`
- Hierarchical preprocessing config: `configs/preprocessing/unsw_nb15_hierarchical.yaml`
- Taxonomy config: `configs/taxonomy/unsw_nb15_attack_taxonomy.yaml`
- Checkpoint family identifier: `unsw_nb15_hierarchical_checkpoint_family`

## Unknown Schema Behavior

If the schema is unknown and `require_supported=True`, the router raises `UnsupportedSchemaError` with a clear message that the input schema does not match a supported adapter/pipeline.

If `require_supported=False`, the router returns a `PipelineRoute` with `schema_id="unknown"` and empty adapter/checkpoint metadata.

## Why This Avoids Manual Professor Model Selection

The user or professor should not have to know which model to choose. The system should inspect uploaded/sample file columns, identify the supported adapter/pipeline when possible, and pass route metadata to later prediction and dashboard layers.

This gives one professional system interface while preserving scientifically valid dataset-specific preprocessing artifacts, taxonomies, and checkpoint families.

## Why This Does Not Claim Traffic Belongs To A Dataset Or Model

Real traffic does not belong to UNSW-NB15, CICIDS2018, or a model. The detector only says that the input schema matches a supported adapter/pipeline. That is a schema compatibility statement, not a claim about the true source of traffic.

## Streamlit Prediction Demo Connection

Later, the Streamlit prediction demo can use this router to:

1. Read uploaded/sample file columns.
2. Detect the supported schema route.
3. Display the route and confidence.
4. Load the correct saved preprocessing artifacts.
5. Load the correct checkpoint family after final checkpoints are approved.
6. Run Head 1 and Head 2 prediction.
7. Load or generate XAI artifacts.
8. Display prediction, explanation, and reproducibility metadata.

The current detector/router stops at route metadata.

## Limitations

- The detector is based on columns only, not full semantic validation.
- Very small or ambiguous column subsets may return `unknown`.
- The route metadata uses checkpoint-family identifiers, not final checkpoint paths.
- This foundation does not implement prediction, preprocessing execution, model loading, XAI, or dashboard integration.

## Future Integration Steps

- Connect router output to actual adapter loading.
- Connect route metadata to saved preprocessing artifacts.
- Connect route metadata to approved model checkpoint selection.
- Connect route metadata to saved XAI artifacts.
- Add dashboard UI that displays schema match evidence and rejects unknown schemas clearly.
