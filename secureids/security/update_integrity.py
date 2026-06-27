"""SHA-256 client update integrity utilities.

These helpers provide integrity evidence for serialized client updates. They do
not implement secure aggregation, do not provide encryption, and do not modify
checkpoints or final artifacts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


class UpdateIntegrityError(ValueError):
    """Raised when update integrity records are invalid."""


def _torch():
    try:
        import torch
    except ModuleNotFoundError as error:  # pragma: no cover - environment specific
        raise UpdateIntegrityError("PyTorch is required for tensor hashing.") from error
    return torch


def _is_tensor(value: Any) -> bool:
    torch = _torch()
    return torch.is_tensor(value)


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def serialize_update_for_hash(update: Any) -> bytes:
    """Serialize an update deterministically for SHA-256 hashing."""

    if _is_tensor(update):
        tensor = update.detach().cpu().contiguous()
        header = {
            "kind": "tensor",
            "dtype": str(tensor.dtype),
            "shape": list(tensor.shape),
        }
        return _json_bytes(header) + b"\n" + tensor.numpy().tobytes(order="C")
    if isinstance(update, Mapping):
        chunks = [_json_bytes({"kind": "mapping", "keys": sorted(str(k) for k in update.keys())})]
        for key in sorted(update.keys(), key=str):
            chunks.append(_json_bytes({"key": str(key)}))
            chunks.append(serialize_update_for_hash(update[key]))
        return b"\n".join(chunks)
    if isinstance(update, (list, tuple)):
        chunks = [_json_bytes({"kind": "sequence", "length": len(update)})]
        for index, value in enumerate(update):
            chunks.append(_json_bytes({"index": index}))
            chunks.append(serialize_update_for_hash(value))
        return b"\n".join(chunks)
    if update is None or isinstance(update, (bool, int, float, str)):
        return _json_bytes({"kind": "scalar", "value": update})
    raise UpdateIntegrityError(f"Unsupported update value type: {type(update).__name__}")


def sha256_update(update: Any) -> str:
    """Return the SHA-256 hex digest for a client update."""

    return hashlib.sha256(serialize_update_for_hash(update)).hexdigest().upper()


def verify_update_hash(update: Any, expected_hash: str) -> bool:
    """Verify an update against an expected SHA-256 hex digest."""

    if not isinstance(expected_hash, str) or not expected_hash:
        raise UpdateIntegrityError("expected_hash must be a non-empty string.")
    return sha256_update(update) == expected_hash.upper()


def make_update_integrity_record(
    client_id: str | int,
    round_id: str | int,
    update_hash: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a JSON-serializable integrity record for a client update."""

    if not isinstance(update_hash, str) or len(update_hash) != 64:
        raise UpdateIntegrityError("update_hash must be a SHA-256 hex digest.")
    return {
        "client_id": str(client_id),
        "round_id": str(round_id),
        "update_hash": update_hash.upper(),
        "metadata": dict(metadata or {}),
    }


def verify_update_integrity_records(
    records: Sequence[Mapping[str, Any]],
    updates: Sequence[Any],
) -> dict[str, Any]:
    """Verify records against the corresponding update payloads."""

    if len(records) != len(updates):
        raise UpdateIntegrityError("records and updates must have the same length.")
    verification_rows: list[dict[str, Any]] = []
    for index, (record, update) in enumerate(zip(records, updates)):
        expected = record.get("update_hash")
        if not isinstance(expected, str):
            raise UpdateIntegrityError(f"record {index} missing update_hash.")
        actual = sha256_update(update)
        verified = actual == expected.upper()
        verification_rows.append(
            {
                "client_id": str(record.get("client_id", index)),
                "round_id": str(record.get("round_id", "")),
                "expected_hash": expected.upper(),
                "actual_hash": actual,
                "verified": verified,
            }
        )
    return {
        "all_verified": all(row["verified"] for row in verification_rows),
        "records": verification_rows,
    }
