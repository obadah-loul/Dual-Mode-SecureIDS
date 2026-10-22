"""Source identity guards for future preprocessing, without pickle loading."""
from pathlib import Path
from secureids.artifacts import sha256_file


def source_identities(paths):
    return [{'name': Path(p).name, 'bytes': Path(p).stat().st_size,
             'sha256': sha256_file(p)} for p in paths]


def verify_unsw_source_roles(train, test, config):
    """Validate configured canonical sizes and distributions, never filenames."""
    expected = config.get('source_verification')
    if not expected:
        return  # Small synthetic fixtures may define a different protocol.
    for name, frame in [('train', train), ('test', test)]:
        role = expected[name]
        if len(frame) != role['rows']:
            raise ValueError(f'UNSW {name} source row count does not match canonical role.')
        counts = frame[config['target_column']].value_counts().to_dict()
        if {str(k): int(v) for k, v in counts.items()} != {str(k): int(v) for k, v in role['binary_counts'].items()}:
            raise ValueError(f'UNSW {name} source binary distribution does not match canonical role.')
        if not frame['id'].is_unique:
            raise ValueError(f'UNSW {name} source has duplicate row identifiers.')
    if list(train.columns) != list(test.columns):
        raise ValueError('UNSW source schemas differ.')


def verify_reconstruction_identity(binary_dir, raw_paths, split_config):
    import json
    manifest = json.loads((binary_dir / 'preprocessing_manifest.json').read_text())
    expected = manifest.get('source_identities')
    if not expected:
        raise ValueError('Binary artifacts lack source identity hashes; cannot safely reconstruct row alignment. Preserve historical artifacts.')
    if expected != source_identities(raw_paths):
        raise ValueError('Raw source bytes or source order changed since binary preprocessing.')
    if manifest.get('config_snapshot', {}).get('split') != split_config:
        raise ValueError('Split policy changed since binary preprocessing.')
    for name, digest in manifest.get('processed_array_sha256', {}).items():
        if sha256_file(binary_dir / name) != digest:
            raise ValueError(f'Binary array identity changed: {name}')
    if not manifest.get('processed_array_sha256'):
        raise ValueError('Binary manifest lacks processed array identities.')
