"""Column-based schema detection for supported SecureIDS V2 adapters.

This module is intentionally metadata-only. It inspects column names and returns
schema-match evidence; it does not load data, preprocess datasets, train, load
models, or run predictions.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SupportedSchema(str, Enum):
    """Supported input schema identifiers."""

    CICIDS2018 = "cicids2018"
    UNSW_NB15 = "unsw_nb15"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SchemaDetectionResult:
    """Evidence returned by column-based schema detection."""

    schema_id: str
    confidence: float
    matched_columns: list[str]
    missing_expected_columns: list[str]
    unexpected_columns_count: int
    score_by_schema: dict[str, float]
    reason: str
    normalized_input_columns: list[str]


@dataclass(frozen=True, slots=True)
class _SchemaProfile:
    schema_id: SupportedSchema
    expected_columns: frozenset[str]
    core_columns: frozenset[str]


MIN_EXPECTED_MATCHES = 5
MIN_CORE_MATCHES = 3
DEFAULT_MIN_CONFIDENCE = 0.62
DEFAULT_AMBIGUITY_MARGIN = 0.15


_COLUMN_ALIASES = {
    "dst_port": "destination_port",
    "dest_port": "destination_port",
    "destination_port": "destination_port",
    "src_port": "source_port",
    "source_port": "source_port",
    "dst_ip": "destination_ip",
    "dest_ip": "destination_ip",
    "destination_ip": "destination_ip",
    "src_ip": "source_ip",
    "source_ip": "source_ip",
    "tot_fwd_pkts": "total_fwd_packets",
    "total_fwd_pkts": "total_fwd_packets",
    "total_fwd_packets": "total_fwd_packets",
    "tot_bwd_pkts": "total_backward_packets",
    "total_bwd_pkts": "total_backward_packets",
    "total_backward_packets": "total_backward_packets",
    "totlen_fwd_pkts": "total_length_fwd_packets",
    "total_len_fwd_pkts": "total_length_fwd_packets",
    "total_length_of_fwd_packets": "total_length_fwd_packets",
    "totlen_bwd_pkts": "total_length_bwd_packets",
    "total_len_bwd_pkts": "total_length_bwd_packets",
    "total_length_of_bwd_packets": "total_length_bwd_packets",
    "fwd_pkt_len_max": "fwd_packet_len_max",
    "fwd_packet_length_max": "fwd_packet_len_max",
    "fwd_pkt_len_min": "fwd_packet_len_min",
    "fwd_packet_length_min": "fwd_packet_len_min",
    "fwd_pkt_len_mean": "fwd_packet_len_mean",
    "fwd_packet_length_mean": "fwd_packet_len_mean",
    "fwd_pkt_len_std": "fwd_packet_len_std",
    "fwd_packet_length_std": "fwd_packet_len_std",
    "bwd_pkt_len_max": "bwd_packet_len_max",
    "bwd_packet_length_max": "bwd_packet_len_max",
    "bwd_pkt_len_min": "bwd_packet_len_min",
    "bwd_packet_length_min": "bwd_packet_len_min",
    "bwd_pkt_len_mean": "bwd_packet_len_mean",
    "bwd_packet_length_mean": "bwd_packet_len_mean",
    "bwd_pkt_len_std": "bwd_packet_len_std",
    "bwd_packet_length_std": "bwd_packet_len_std",
    "flow_byts_s": "flow_bytes_s",
    "flow_bytes_s": "flow_bytes_s",
    "flow_pkts_s": "flow_packets_s",
    "flow_packets_s": "flow_packets_s",
    "fwd_pkts_s": "fwd_packets_s",
    "bwd_pkts_s": "bwd_packets_s",
    "pkt_len_min": "min_packet_length",
    "packet_length_min": "min_packet_length",
    "pkt_len_max": "max_packet_length",
    "packet_length_max": "max_packet_length",
    "pkt_len_mean": "packet_length_mean",
    "pkt_len_std": "packet_length_std",
    "pkt_len_var": "packet_length_variance",
    "avg_pkt_size": "average_packet_size",
    "fwd_seg_size_avg": "avg_fwd_segment_size",
    "bwd_seg_size_avg": "avg_bwd_segment_size",
    "subflow_fwd_pkts": "subflow_fwd_packets",
    "subflow_bwd_pkts": "subflow_bwd_packets",
    "init_fwd_win_byts": "init_win_bytes_forward",
    "init_bwd_win_byts": "init_win_bytes_backward",
    "fwd_act_data_pkts": "act_data_pkt_fwd",
    "fwd_seg_size_min": "min_seg_size_forward",
    "attack_category": "attack_cat",
}


_CICIDS_EXPECTED = frozenset(
    {
        "flow_id",
        "source_ip",
        "source_port",
        "destination_ip",
        "destination_port",
        "protocol",
        "timestamp",
        "flow_duration",
        "total_fwd_packets",
        "total_backward_packets",
        "total_length_fwd_packets",
        "total_length_bwd_packets",
        "fwd_packet_len_max",
        "fwd_packet_len_min",
        "fwd_packet_len_mean",
        "fwd_packet_len_std",
        "bwd_packet_len_max",
        "bwd_packet_len_min",
        "bwd_packet_len_mean",
        "bwd_packet_len_std",
        "flow_bytes_s",
        "flow_packets_s",
        "flow_iat_mean",
        "flow_iat_std",
        "flow_iat_max",
        "flow_iat_min",
        "fwd_iat_total",
        "fwd_iat_mean",
        "fwd_iat_std",
        "fwd_iat_max",
        "fwd_iat_min",
        "bwd_iat_total",
        "bwd_iat_mean",
        "bwd_iat_std",
        "bwd_iat_max",
        "bwd_iat_min",
        "fwd_psh_flags",
        "bwd_psh_flags",
        "fwd_urg_flags",
        "bwd_urg_flags",
        "fwd_header_length",
        "bwd_header_length",
        "fwd_packets_s",
        "bwd_packets_s",
        "min_packet_length",
        "max_packet_length",
        "packet_length_mean",
        "packet_length_std",
        "packet_length_variance",
        "fin_flag_count",
        "syn_flag_count",
        "rst_flag_count",
        "psh_flag_count",
        "ack_flag_count",
        "urg_flag_count",
        "cwe_flag_count",
        "ece_flag_count",
        "down_up_ratio",
        "average_packet_size",
        "avg_fwd_segment_size",
        "avg_bwd_segment_size",
        "fwd_header_length_1",
        "subflow_fwd_packets",
        "subflow_fwd_bytes",
        "subflow_bwd_packets",
        "subflow_bwd_bytes",
        "init_win_bytes_forward",
        "init_win_bytes_backward",
        "act_data_pkt_fwd",
        "min_seg_size_forward",
        "active_mean",
        "active_std",
        "active_max",
        "active_min",
        "idle_mean",
        "idle_std",
        "idle_max",
        "idle_min",
        "label",
    }
)

_CICIDS_CORE = frozenset(
    {
        "flow_duration",
        "total_fwd_packets",
        "total_backward_packets",
        "flow_bytes_s",
        "flow_packets_s",
        "fwd_packet_len_max",
        "bwd_packet_len_max",
        "protocol",
        "label",
    }
)

_UNSW_EXPECTED = frozenset(
    {
        "id",
        "dur",
        "proto",
        "service",
        "state",
        "spkts",
        "dpkts",
        "sbytes",
        "dbytes",
        "rate",
        "sttl",
        "dttl",
        "sload",
        "dload",
        "sloss",
        "dloss",
        "sinpkt",
        "dinpkt",
        "sjit",
        "djit",
        "swin",
        "stcpb",
        "dtcpb",
        "dwin",
        "tcprtt",
        "synack",
        "ackdat",
        "smean",
        "dmean",
        "trans_depth",
        "response_body_len",
        "ct_srv_src",
        "ct_state_ttl",
        "ct_dst_ltm",
        "ct_src_dport_ltm",
        "ct_dst_sport_ltm",
        "ct_dst_src_ltm",
        "is_ftp_login",
        "ct_ftp_cmd",
        "ct_flw_http_mthd",
        "ct_src_ltm",
        "ct_srv_dst",
        "is_sm_ips_ports",
        "attack_cat",
        "label",
    }
)

_UNSW_CORE = frozenset(
    {
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
    }
)

_PROFILES = (
    _SchemaProfile(
        schema_id=SupportedSchema.CICIDS2018,
        expected_columns=_CICIDS_EXPECTED,
        core_columns=_CICIDS_CORE,
    ),
    _SchemaProfile(
        schema_id=SupportedSchema.UNSW_NB15,
        expected_columns=_UNSW_EXPECTED,
        core_columns=_UNSW_CORE,
    ),
)


def normalize_column_name(name: object) -> str:
    """Normalize a column name for schema matching."""

    text = str(name).replace("\ufeff", "").strip().lower()
    text = re.sub(r"[^0-9a-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return _COLUMN_ALIASES.get(text, text)


def detect_schema(
    columns_or_dataframe: Any,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ambiguity_margin: float = DEFAULT_AMBIGUITY_MARGIN,
) -> SchemaDetectionResult:
    """Detect whether input columns match a supported adapter/pipeline schema."""

    normalized_columns = sorted(set(_extract_normalized_columns(columns_or_dataframe)))
    normalized_set = set(normalized_columns)
    if not normalized_set:
        return _unknown_result(
            normalized_columns=[],
            score_details={},
            reason="No input columns were provided.",
        )

    details = {
        profile.schema_id.value: _score_profile(profile, normalized_set)
        for profile in _PROFILES
    }
    score_by_schema = {
        schema_id: round(detail["confidence"], 6)
        for schema_id, detail in details.items()
    }
    ranked = sorted(
        details.items(),
        key=lambda item: item[1]["confidence"],
        reverse=True,
    )
    best_schema, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else {"confidence": 0.0}
    margin = best["confidence"] - second["confidence"]

    if best["matched_expected_count"] < MIN_EXPECTED_MATCHES:
        return _unknown_result(
            normalized_columns=normalized_columns,
            score_details=details,
            reason=(
                "Unsupported schema: too few expected columns matched any "
                "supported adapter/pipeline."
            ),
        )

    if best["matched_core_count"] < MIN_CORE_MATCHES:
        return _unknown_result(
            normalized_columns=normalized_columns,
            score_details=details,
            reason=(
                "Unsupported schema: not enough distinctive core columns "
                "matched a supported adapter/pipeline."
            ),
        )

    if best["confidence"] < min_confidence:
        return _unknown_result(
            normalized_columns=normalized_columns,
            score_details=details,
            reason=(
                f"Unsupported schema: best confidence {best['confidence']:.3f} "
                f"is below threshold {min_confidence:.3f}."
            ),
        )

    if margin < ambiguity_margin:
        return _unknown_result(
            normalized_columns=normalized_columns,
            score_details=details,
            reason=(
                f"Ambiguous schema: best margin {margin:.3f} is below "
                f"required margin {ambiguity_margin:.3f}."
            ),
        )

    return SchemaDetectionResult(
        schema_id=best_schema,
        confidence=round(best["confidence"], 6),
        matched_columns=best["matched_columns"],
        missing_expected_columns=best["missing_expected_columns"],
        unexpected_columns_count=best["unexpected_columns_count"],
        score_by_schema=score_by_schema,
        reason=(
            "Input schema matches a supported adapter/pipeline: "
            f"{best_schema}."
        ),
        normalized_input_columns=normalized_columns,
    )


def _extract_normalized_columns(columns_or_dataframe: Any) -> list[str]:
    if hasattr(columns_or_dataframe, "columns"):
        return [
            normalize_column_name(column)
            for column in getattr(columns_or_dataframe, "columns")
        ]

    if isinstance(columns_or_dataframe, (list, tuple, set, frozenset)):
        return [normalize_column_name(column) for column in columns_or_dataframe]

    if isinstance(columns_or_dataframe, Iterable) and not isinstance(
        columns_or_dataframe,
        (str, bytes, dict),
    ):
        return [normalize_column_name(column) for column in columns_or_dataframe]

    raise TypeError(
        "detect_schema expects a column iterable or an object with a columns attribute."
    )


def _score_profile(
    profile: _SchemaProfile,
    normalized_input: set[str],
) -> dict[str, Any]:
    matched_expected = normalized_input & profile.expected_columns
    matched_core = normalized_input & profile.core_columns
    unexpected = normalized_input - profile.expected_columns

    precision = len(matched_expected) / max(len(normalized_input), 1)
    core_ratio = len(matched_core) / max(len(profile.core_columns), 1)
    signal_count_ratio = min(len(matched_expected) / 10.0, 1.0)
    confidence = (0.35 * precision) + (0.45 * core_ratio) + (0.20 * signal_count_ratio)

    return {
        "confidence": confidence,
        "matched_columns": sorted(matched_expected),
        "missing_expected_columns": sorted(profile.expected_columns - normalized_input),
        "unexpected_columns_count": len(unexpected),
        "matched_expected_count": len(matched_expected),
        "matched_core_count": len(matched_core),
    }


def _unknown_result(
    *,
    normalized_columns: list[str],
    score_details: dict[str, dict[str, Any]],
    reason: str,
) -> SchemaDetectionResult:
    best: dict[str, Any] = {
        "matched_columns": [],
        "missing_expected_columns": [],
        "unexpected_columns_count": len(normalized_columns),
        "confidence": 0.0,
    }
    if score_details:
        best = max(score_details.values(), key=lambda detail: detail["confidence"])

    return SchemaDetectionResult(
        schema_id=SupportedSchema.UNKNOWN.value,
        confidence=0.0,
        matched_columns=list(best["matched_columns"]),
        missing_expected_columns=list(best["missing_expected_columns"]),
        unexpected_columns_count=int(best["unexpected_columns_count"]),
        score_by_schema={
            schema_id: round(detail["confidence"], 6)
            for schema_id, detail in score_details.items()
        },
        reason=reason,
        normalized_input_columns=normalized_columns,
    )


__all__ = [
    "SchemaDetectionResult",
    "SupportedSchema",
    "detect_schema",
    "normalize_column_name",
]
