"""Build genuine compact replay bundles, or verify/install an owner-supplied ZIP.

No downloads, preprocessing fits, checkpoint deserialization, or training.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'artifacts/demo-manifest.json'
MAX_BYTES = 16 * 1024 * 1024
METADATA = ('feature_names.json', 'binary_label_mapping.json', 'attack_family_label_mapping.json')
ARRAYS = ('X_demo.npy', 'y_binary_demo.npy', 'y_attack_family_demo.npy', 'attack_family_mask_demo.npy')
MODELS = {'cicids2018': 'cicids_hierarchical_clean_fedavg.pt',
          'unsw_nb15': 'unsw_hierarchical_clean_fedavg.pt'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def write_zip(output, payload):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Refusing to replace existing archive: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o100644 << 16
            archive.writestr(member, data, compresslevel=9)
    return {'file': output.name, 'bytes': output.stat().st_size,
            'sha256': digest(output.read_bytes()), 'payload_files': len(payload)}


def build(artifact_root, models_root, output, datasets):
    import numpy as np
    # Constants only; this import does not run inference or deserialize weights.
    sys.path.insert(0, str(ROOT))
    from secureids.inference.live_demo import DATASET_SPECS, SCENARIO_SPECS
    source = Path(artifact_root).resolve()
    model_root = Path(models_root).resolve()
    payload = {}
    scenarios = []
    identities = json.loads((ROOT / 'configs/selected_models.json').read_text())
    for spec in DATASET_SPECS.values():
        if spec.key not in datasets:
            continue
        relative = f'data/processed/{spec.key}/hierarchical'
        folder = source / relative
        selected = [s for s in SCENARIO_SPECS.values() if DATASET_SPECS[s.dataset_name].key == spec.key]
        indices = [s.sample_index for s in selected]
        X = np.load(folder / 'X_test.npy', mmap_mode='r', allow_pickle=False)
        if X.ndim != 2 or X.shape[1] != spec.input_dim:
            raise ValueError('Source feature schema does not match selected model.')
        for name in METADATA:
            payload[f'{relative}/{name}'] = (folder / name).read_bytes()
        rows = np.array(X[indices], copy=True)
        if rows.dtype != np.float32 or not np.isfinite(rows).all():
            raise ValueError('Expected original finite float32 processed samples.')
        arrays = {'X_demo.npy': rows}
        for prefix in ('y_binary', 'y_attack_family', 'attack_family_mask'):
            labels = np.load(folder / f'{prefix}_test.npy', mmap_mode='r', allow_pickle=False)
            if labels.ndim != 1 or len(labels) != len(X):
                raise ValueError('Source labels do not align with feature rows.')
            arrays[f'{prefix}_demo.npy'] = np.array(labels[indices], copy=True)
        if not np.array_equal(arrays['y_binary_demo.npy'], arrays['attack_family_mask_demo.npy']):
            raise ValueError('Source family masks differ from binary labels.')
        for name, array in arrays.items():
            stream = io.BytesIO()
            np.save(stream, array, allow_pickle=False)
            payload[f'{relative}/{name}'] = stream.getvalue()
        row_hashes = [digest(np.ascontiguousarray(row).tobytes()) for row in rows]
        payload[f'{relative}/demo_samples.json'] = json_bytes({
            'format_version': 1, 'dataset': spec.key, 'source_split': 'test',
            'source_test_rows': int(X.shape[0]), 'source_indices': indices,
            'row_sha256_float32': row_hashes, 'preprocessing': 'already processed; no refit or transform',
            'source_feature_file': f'{relative}/X_test.npy'})
        name = f'models/experiments/federated_security/{MODELS[spec.key]}'
        checkpoint = (model_root / name).read_bytes()
        if digest(checkpoint) != identities[f'{spec.key}_federated']['sha256']:
            raise ValueError('Selected checkpoint differs from the reviewed recovery identity.')
        payload[name] = checkpoint
        scenarios += [{'name': s.name, 'dataset': spec.key, 'source_index': s.sample_index,
                       'row_sha256_float32': h} for s, h in zip(selected, row_hashes)]
    if not scenarios:
        raise ValueError('No supported datasets selected.')
    payload['artifacts/DEMO_NOTICES.md'] = (ROOT / 'docs/DATASET_RIGHTS.md').read_bytes()
    manifest = {'format_version': 1, 'datasets': list(datasets), 'scenario_count': len(scenarios),
        'distribution_status': 'private_review_only_pending_unsw_permission' if 'unsw_nb15' in datasets else 'cicids_candidate_subject_to_owner_model_rights_and_release_approval',
        'scenarios': scenarios, 'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(payload.items())},
        'hash_scope': 'local recovery fingerprints; not signatures or dataset authenticity proof',
        'models_retrained': False, 'samples_synthetic': False}
    payload[MANIFEST] = json_bytes(manifest)
    if sum(map(len, payload.values())) > MAX_BYTES:
        raise ValueError('Compact bundle exceeds the 16 MiB safety limit.')
    summary = write_zip(output, payload)
    summary.update({'scenarios': len(scenarios), 'datasets': list(datasets),
                    'distribution_status': manifest['distribution_status']})
    return summary


def verified_payload(archive_path, expected_sha256):
    path = Path(archive_path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Archive exceeds 16 MiB.')
    data = path.read_bytes()
    if len(expected_sha256) != 64 or digest(data) != expected_sha256.lower():
        raise ValueError('Archive SHA-256 mismatch. Obtain the expected hash separately from the owner.')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > MAX_BYTES:
            raise ValueError('Duplicate members or oversized expanded archive.')
        for item in archive.infolist():
            parts = PurePosixPath(item.filename)
            if parts.is_absolute() or '..' in parts.parts or '\\' in item.filename or ':' in item.filename or item.is_dir() or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe archive member.')
        manifest = json.loads(archive.read(MANIFEST))
        datasets = manifest.get('datasets', [])
        if manifest.get('format_version') != 1 or not datasets or len(set(datasets)) != len(datasets) or any(ds not in MODELS for ds in datasets):
            raise ValueError('Unsupported demo bundle manifest.')
        allowed = {MANIFEST, 'artifacts/DEMO_NOTICES.md'}
        for ds in datasets:
            allowed.add(f'models/experiments/federated_security/{MODELS[ds]}')
            allowed.update(f'data/processed/{ds}/hierarchical/{n}' for n in (*METADATA, *ARRAYS, 'demo_samples.json'))
        if set(names) != allowed or set(manifest['files']) != allowed - {MANIFEST}:
            raise ValueError('Unexpected or missing demo files.')
        payload = {name: archive.read(name) for name in names}
        for name, record in manifest['files'].items():
            if len(payload[name]) != record['bytes'] or digest(payload[name]) != record['sha256']:
                raise ValueError(f'Payload hash mismatch: {name}')
    return payload, manifest


def install(archive, expected_sha256, destination):
    payload, manifest = verified_payload(archive, expected_sha256)
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    targets = {}
    for name, data in payload.items():
        target = root / name
        if not target.resolve().is_relative_to(root):
            raise ValueError('Installation path escapes destination (including symlinks).')
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise FileExistsError(f'Refusing to overwrite different existing file: {name}')
        targets[name] = target
    with tempfile.TemporaryDirectory(prefix='.demo-install-', dir=root) as temp:
        for name, data in payload.items():
            staged = Path(temp) / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(data)
        for name, target in targets.items():
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(Path(temp) / name), str(target))
    return {'installed_files': len(payload), 'scenario_count': manifest['scenario_count'],
            'distribution_status': manifest['distribution_status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    builder = commands.add_parser('build', help='Extract real replay rows from authorized matching processed artifacts.')
    builder.add_argument('--artifact-root', required=True, type=Path)
    builder.add_argument('--models-root', type=Path, default=ROOT)
    builder.add_argument('--output', required=True, type=Path)
    builder.add_argument('--datasets', choices=['all', 'cicids2018'], default='all')
    installer = commands.add_parser('install', help='Verify and install a locally obtained bundle; no network access.')
    installer.add_argument('archive', type=Path)
    installer.add_argument('--sha256', required=True)
    installer.add_argument('--destination', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            result = build(args.artifact_root, args.models_root, args.output,
                           ('cicids2018', 'unsw_nb15') if args.datasets == 'all' else ('cicids2018',))
        else:
            result = install(args.archive, args.sha256, args.destination)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Demo package rejected: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
