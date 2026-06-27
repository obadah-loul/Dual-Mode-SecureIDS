"""Schema router metadata for SecureIDS V2 supported adapters.

The router returns adapter and artifact identifiers only. It does not load
models, run preprocessing, run predictions, or create metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from secureids.datasets.schema_detector import (
    SchemaDetectionResult,
    SupportedSchema,
    detect_schema,
)


@dataclass(frozen=True, slots=True)
class PipelineRoute:
    """Metadata needed by later prediction/dashboard integration."""

    schema_id: str
    adapter_id: str | None
    preprocessing_config: str | None
    hierarchical_preprocessing_config: str | None
    taxonomy_config: str | None
    checkpoint_family: str | None
    dashboard_label: str
    confidence: float
    reason: str


class UnsupportedSchemaError(ValueError):
    """Raised when input columns do not match a supported adapter/pipeline."""


_ROUTES: dict[str, dict[str, str]] = {
    SupportedSchema.CICIDS2018.value: {
        "adapter_id": "secureids.datasets.cicids2018.CICIDS2018Adapter",
        "preprocessing_config": "configs/preprocessing/cicids2018_binary.yaml",
        "hierarchical_preprocessing_config": "configs/preprocessing/cicids2018_hierarchical.yaml",
        "taxonomy_config": "configs/taxonomy/cicids2018_attack_taxonomy.yaml",
        "checkpoint_family": "cicids2018_hierarchical_checkpoint_family",
        "dashboard_label": "CICIDS2018-like supported schema",
    },
    SupportedSchema.UNSW_NB15.value: {
        "adapter_id": "secureids.datasets.unsw_nb15.UNSWNB15Adapter",
        "preprocessing_config": "configs/preprocessing/unsw_nb15_binary.yaml",
        "hierarchical_preprocessing_config": "configs/preprocessing/unsw_nb15_hierarchical.yaml",
        "taxonomy_config": "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        "checkpoint_family": "unsw_nb15_hierarchical_checkpoint_family",
        "dashboard_label": "UNSW-NB15-like supported schema",
    },
}


def route_schema(
    columns_or_dataframe: Any,
    require_supported: bool = True,
) -> PipelineRoute:
    """Detect the input schema and return the matching route metadata."""

    return route_from_detection(
        detect_schema(columns_or_dataframe),
        require_supported=require_supported,
    )


def route_from_detection(
    result: SchemaDetectionResult,
    require_supported: bool = True,
) -> PipelineRoute:
    """Build route metadata from a previous schema detection result."""

    if result.schema_id == SupportedSchema.UNKNOWN.value:
        if require_supported:
            raise UnsupportedSchemaError(
                "Unsupported input schema: "
                f"{result.reason} The input schema does not match a supported "
                "adapter/pipeline."
            )
        return PipelineRoute(
            schema_id=SupportedSchema.UNKNOWN.value,
            adapter_id=None,
            preprocessing_config=None,
            hierarchical_preprocessing_config=None,
            taxonomy_config=None,
            checkpoint_family=None,
            dashboard_label="Unknown / unsupported schema",
            confidence=result.confidence,
            reason=result.reason,
        )

    route = _ROUTES.get(result.schema_id)
    if route is None:
        if require_supported:
            raise UnsupportedSchemaError(
                f"No route metadata exists for detected schema: {result.schema_id}"
            )
        return PipelineRoute(
            schema_id=SupportedSchema.UNKNOWN.value,
            adapter_id=None,
            preprocessing_config=None,
            hierarchical_preprocessing_config=None,
            taxonomy_config=None,
            checkpoint_family=None,
            dashboard_label="Unknown / unsupported schema",
            confidence=result.confidence,
            reason=f"No route metadata exists for detected schema: {result.schema_id}",
        )

    return PipelineRoute(
        schema_id=result.schema_id,
        adapter_id=route["adapter_id"],
        preprocessing_config=route["preprocessing_config"],
        hierarchical_preprocessing_config=route["hierarchical_preprocessing_config"],
        taxonomy_config=route["taxonomy_config"],
        checkpoint_family=route["checkpoint_family"],
        dashboard_label=route["dashboard_label"],
        confidence=result.confidence,
        reason=result.reason,
    )


__all__ = [
    "PipelineRoute",
    "UnsupportedSchemaError",
    "route_from_detection",
    "route_schema",
]
