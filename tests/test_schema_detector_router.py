from __future__ import annotations

import pytest

from secureids.datasets.router import UnsupportedSchemaError, route_schema
from secureids.datasets.schema_detector import SupportedSchema, detect_schema


CICIDS_COLUMNS = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Fwd Packet Length Max",
    "Bwd Packet Length Max",
    "Protocol",
    "Label",
]

UNSW_COLUMNS = [
    "dur",
    "proto",
    "service",
    "state",
    "spkts",
    "dpkts",
    "sbytes",
    "dbytes",
    "attack_cat",
    "label",
]


def test_cicids_like_columns_detect_cicids2018():
    result = detect_schema(CICIDS_COLUMNS)

    assert result.schema_id == SupportedSchema.CICIDS2018.value
    assert result.confidence >= 0.62
    assert "flow_duration" in result.matched_columns
    assert "label" in result.matched_columns


def test_unsw_like_columns_detect_unsw_nb15():
    result = detect_schema(UNSW_COLUMNS)

    assert result.schema_id == SupportedSchema.UNSW_NB15.value
    assert result.confidence >= 0.62
    assert "attack_cat" in result.matched_columns
    assert "proto" in result.matched_columns


def test_case_spacing_and_separator_variations_still_match():
    columns = [
        " DUR ",
        "Proto",
        " service ",
        " State",
        "SBytes",
        "DBytes",
        "Attack Cat",
        "LABEL",
    ]

    result = detect_schema(columns)

    assert result.schema_id == SupportedSchema.UNSW_NB15.value
    assert "attack_cat" in result.matched_columns


def test_unknown_random_columns_return_unknown():
    result = detect_schema(["alpha", "beta", "gamma", "target"])

    assert result.schema_id == SupportedSchema.UNKNOWN.value
    assert result.confidence == 0.0


def test_ambiguous_partial_columns_return_unknown():
    result = detect_schema(["Label", "Protocol", "state", "duration"])

    assert result.schema_id == SupportedSchema.UNKNOWN.value
    assert "Unsupported schema" in result.reason or "Ambiguous schema" in result.reason


def test_route_schema_returns_cicids_metadata():
    route = route_schema(CICIDS_COLUMNS)

    assert route.schema_id == SupportedSchema.CICIDS2018.value
    assert route.adapter_id == "secureids.datasets.cicids2018.CICIDS2018Adapter"
    assert route.preprocessing_config == "configs/preprocessing/cicids2018_binary.yaml"
    assert route.taxonomy_config == "configs/taxonomy/cicids2018_attack_taxonomy.yaml"
    assert route.checkpoint_family == "cicids2018_hierarchical_checkpoint_family"


def test_route_schema_returns_unsw_metadata():
    route = route_schema(UNSW_COLUMNS)

    assert route.schema_id == SupportedSchema.UNSW_NB15.value
    assert route.adapter_id == "secureids.datasets.unsw_nb15.UNSWNB15Adapter"
    assert route.preprocessing_config == "configs/preprocessing/unsw_nb15_binary.yaml"
    assert route.taxonomy_config == "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml"
    assert route.checkpoint_family == "unsw_nb15_hierarchical_checkpoint_family"


def test_route_schema_raises_for_unknown_when_required():
    with pytest.raises(UnsupportedSchemaError, match="supported adapter/pipeline"):
        route_schema(["alpha", "beta", "gamma"], require_supported=True)


def test_route_schema_returns_unknown_when_not_required():
    route = route_schema(["alpha", "beta", "gamma"], require_supported=False)

    assert route.schema_id == SupportedSchema.UNKNOWN.value
    assert route.adapter_id is None
    assert route.checkpoint_family is None


def test_detector_accepts_pandas_dataframe_when_available():
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame(columns=UNSW_COLUMNS)

    result = detect_schema(frame)

    assert result.schema_id == SupportedSchema.UNSW_NB15.value
