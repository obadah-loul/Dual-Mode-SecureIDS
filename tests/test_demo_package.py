"""Packaging-only synthetic fixtures; no training or model deserialization."""
import io
import json
from dataclasses import replace

import numpy as np
import pytest

from tools import demo_package as package
from secureids.inference import live_demo


def fixture_archive(tmp_path, *, extra=None, damage=False):
    ds = 'cicids2018'
    base = f'data/processed/{ds}/hierarchical'
    # Checkpoint bytes here test archive handling only; never loaded as a model.
    payload = {f'models/experiments/federated_security/{package.MODELS[ds]}': b'unit-test-non-model',
               'artifacts/DEMO_NOTICES.md': b'fixture'}
    for name in (*package.METADATA, *package.ARRAYS, 'demo_samples.json'):
        payload[f'{base}/{name}'] = b'fixture'
    manifest = {'format_version': 1, 'datasets': [ds], 'scenario_count': 4,
                'distribution_status': 'test_fixture',
                'files': {n: {'bytes': len(v), 'sha256': package.digest(v)} for n, v in payload.items()}}
    payload[package.MANIFEST] = package.json_bytes(manifest)
    if extra:
        payload.update(extra)
    if damage:
        payload['artifacts/DEMO_NOTICES.md'] = b'mutated'
    path = tmp_path / 'fixture.zip'
    record = package.write_zip(path, payload)
    return path, record['sha256']


def test_install_verifies_payload_and_is_idempotent(tmp_path):
    archive, digest = fixture_archive(tmp_path)
    dest = tmp_path / 'installed'
    first = package.install(archive, digest, dest)
    before = {p.relative_to(dest): p.read_bytes() for p in dest.rglob('*') if p.is_file()}
    assert package.install(archive, digest, dest) == first
    assert {p.relative_to(dest): p.read_bytes() for p in dest.rglob('*') if p.is_file()} == before
    assert len(before) == 11


def test_archive_hash_rejected_before_installation(tmp_path):
    archive, _ = fixture_archive(tmp_path)
    dest = tmp_path / 'absent'
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        package.install(archive, '0' * 64, dest)
    assert not dest.exists()


def test_existing_different_file_preserved(tmp_path):
    archive, digest = fixture_archive(tmp_path)
    dest = tmp_path / 'installed'
    p = dest / 'artifacts/DEMO_NOTICES.md'
    p.parent.mkdir(parents=True)
    p.write_bytes(b'preserve')
    with pytest.raises(FileExistsError, match='overwrite'):
        package.install(archive, digest, dest)
    assert p.read_bytes() == b'preserve'
    assert not (dest / 'models').exists()


@pytest.mark.parametrize('name', ['../escape.txt', '/absolute.txt', 'C:/escape.txt', 'data\\escape.txt'])
def test_path_traversal_is_rejected(tmp_path, name):
    archive, digest = fixture_archive(tmp_path, extra={name: b'bad'})
    # Windows zipfile may normalize a backslash before the reader sees it;
    # normalized-but-unlisted entries must still fail closed.
    with pytest.raises(ValueError, match='Unsafe|Unexpected'):
        package.verified_payload(archive, digest)


def test_unlisted_file_is_rejected(tmp_path):
    archive, digest = fixture_archive(tmp_path, extra={'.secureids-local.json': b'{}'})
    with pytest.raises(ValueError, match='Unexpected'):
        package.verified_payload(archive, digest)


def test_tampered_payload_is_rejected(tmp_path):
    archive, digest = fixture_archive(tmp_path, damage=True)
    with pytest.raises(ValueError, match='Payload hash mismatch'):
        package.verified_payload(archive, digest)


def test_zip_is_deterministic_and_never_overwritten(tmp_path):
    a = package.write_zip(tmp_path / 'a.zip', {'b': b'two', 'a': b'one'})
    b = package.write_zip(tmp_path / 'b.zip', {'a': b'one', 'b': b'two'})
    assert a['sha256'] == b['sha256']
    with pytest.raises(FileExistsError):
        package.write_zip(tmp_path / 'a.zip', {'a': b'changed'})


def test_compact_layout_keeps_original_indices_without_padding(tmp_path):
    spec = replace(live_demo.DATASET_SPECS['CICIDS2018'], data_dir=tmp_path)
    rows = np.ones((2, 77), dtype=np.float32)
    np.save(tmp_path / 'X_demo.npy', rows)
    info = {'format_version': 1, 'dataset': 'cicids2018',
            'source_test_rows': 1443773, 'source_indices': [7921, 365528]}
    (tmp_path / 'demo_samples.json').write_text(json.dumps(info))
    actual, manifest = live_demo._load_sample_layout(spec)
    assert actual.shape == (2, 77)
    assert actual.flags.writeable is False
    assert manifest['source_indices'] == [7921, 365528]
    info['source_indices'] = [7921, 7921]
    (tmp_path / 'demo_samples.json').write_text(json.dumps(info))
    with pytest.raises(ValueError, match='unique'):
        live_demo._load_sample_layout(spec)


def test_full_split_fallback_still_works(tmp_path):
    spec = replace(live_demo.DATASET_SPECS['UNSW-NB15'], data_dir=tmp_path)
    np.save(tmp_path / 'X_test.npy', np.zeros((2, 192), dtype=np.float32))
    X, manifest = live_demo._load_sample_layout(spec)
    assert manifest is None and X.shape == (2, 192)
