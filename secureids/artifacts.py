"""Explicit read-only access to externally stored processed arrays.

Only readers use this resolver. Output paths must always stay in the working
copy; no links, writable maps, or automatic writes to external storage exist.
"""
from pathlib import Path
import hashlib
import json
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: str | Path) -> str:
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read_artifact_path(path: str | Path, project_root: Path = PROJECT_ROOT) -> Path:
    path = Path(path)
    local = path if path.is_absolute() else project_root / path
    if local.exists():
        return local
    try:
        relative = local.resolve().relative_to(project_root.resolve())
    except ValueError:
        return local
    if relative.parts[:2] != ('data', 'processed'):
        return local
    config_path = project_root / '.secureids-local.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    external = os.environ.get('SECUREIDS_ARTIFACT_ROOT') or config.get('artifact_root')
    if not external:
        return local
    root = Path(external).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('Artifact path escapes configured root.')
    return candidate if candidate.exists() else local


def load_numpy_readonly(path, mmap_mode=None, *, allow_pickle=False):
    """Load numeric arrays with external fallback and no writable mappings."""
    import numpy as np
    if allow_pickle or mmap_mode not in (None, 'r'):
        raise ValueError('Only numeric read-only array loading is supported.')
    return np.load(read_artifact_path(path), mmap_mode=mmap_mode, allow_pickle=False)
