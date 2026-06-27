from __future__ import annotations

import pytest

from secureids.security.update_integrity import (
    make_update_integrity_record,
    sha256_update,
    verify_update_hash,
    verify_update_integrity_records,
)


torch = pytest.importorskip("torch")


def test_sha256_update_is_stable_for_same_payload():
    update = {"w": torch.tensor([1.0, 2.0]), "b": torch.tensor([0.5])}

    assert sha256_update(update) == sha256_update(update)


def test_verify_update_hash_accepts_matching_hash():
    update = {"w": torch.tensor([1.0, 2.0])}
    digest = sha256_update(update)

    assert verify_update_hash(update, digest) is True


def test_verify_update_hash_detects_tamper():
    clean = {"w": torch.tensor([1.0, 2.0])}
    tampered = {"w": torch.tensor([1.0, 2.5])}
    digest = sha256_update(clean)

    assert verify_update_hash(tampered, digest) is False


def test_integrity_records_report_tampered_update():
    clean = {"w": torch.tensor([1.0, 2.0])}
    tampered = {"w": torch.tensor([1.0, 2.5])}
    record = make_update_integrity_record(
        client_id="client_00",
        round_id=1,
        update_hash=sha256_update(clean),
    )

    result = verify_update_integrity_records([record], [tampered])

    assert result["all_verified"] is False
    assert result["records"][0]["verified"] is False
