"""Read-only recovery inventory; never deserializes artifacts or runs experiments."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / 'SecureIDS_Demo_Package'
OUTPUT = ROOT / 'verification'


def sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=True)
    inventory = {p.relative_to(ORIGINAL).as_posix(): {
        'bytes': p.stat().st_size, 'sha256': sha256(p)
    } for p in ORIGINAL.rglob('*') if p.is_file()}
    (OUTPUT / 'original_inventory.json').write_text(json.dumps(inventory, indent=2))
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    differences = []
    for name in tracked:
        ref = ORIGINAL / name
        if not ref.exists() or sha256(ROOT / name) != inventory.get(name, {}).get('sha256'):
            differences.append(name)
    models = {}
    for name, item in inventory.items():
        if name.endswith(('.pt', '.pth')):
            p = ORIGINAL / name
            record = dict(item)
            if zipfile.is_zipfile(p):
                with zipfile.ZipFile(p) as archive:
                    record['zip_members'] = len(archive.infolist())
                    record['unsafe_zip_paths'] = [n for n in archive.namelist() if '..' in Path(n).parts]
                    record['expanded_bytes'] = sum(i.file_size for i in archive.infolist())
            models[name] = record
    summary = {'original_root': str(ORIGINAL), 'files': len(inventory),
               'bytes': sum(v['bytes'] for v in inventory.values()),
               'baseline': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'tracked_differences': differences, 'checkpoints': models,
               'raw_csvs': [n for n in inventory if n.endswith('.csv') and n.startswith('data/raw/')]}
    (OUTPUT / 'recovery_inventory.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != 'checkpoints'}, indent=2))
    print('Checkpoints:', len(models))


if __name__ == '__main__':
    main()
