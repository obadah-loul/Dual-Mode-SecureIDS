"""Read-only local integration checks. No training or full dataset evaluation."""
from pathlib import Path
import ast
import importlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def main():
    import torch
    import yaml
    from streamlit.testing.v1 import AppTest
    from secureids.training.checkpoints import load_checkpoint
    from secureids.artifacts import sha256_file
    from secureids.inference.live_demo import SCENARIO_CHOICES
    torch.set_num_threads(2)
    output = {'python': sys.version, 'checkpoints': [], 'dashboard': [], 'imports': [], 'yaml': []}
    local = ROOT / '.secureids-local.json'
    reference_root = Path(json.loads(local.read_text())['artifact_root']) if local.exists() else ROOT
    paths = sorted((ROOT / 'models').rglob('*.pt'))
    if reference_root != ROOT:
        paths += sorted((reference_root / 'results').rglob('*.pt'))
    for path in paths:
        try:
            checkpoint = load_checkpoint(path)
            state = checkpoint.get('model_state_dict', {})
            tensors = [v for v in state.values() if torch.is_tensor(v)]
            assert tensors and all(torch.isfinite(v).all() for v in tensors)
            output['checkpoints'].append({'path': str(path), 'sha256': sha256_file(path), 'restricted_load': True, 'finite_state': True})
        except Exception as error:
            output['checkpoints'].append({'path': str(path), 'error': str(error)})
    if '--checkpoints-only' in sys.argv:
        target = ROOT / 'verification/integration.json'
        existing = json.loads(target.read_text()) if target.exists() else {}
        existing['checkpoints'] = output['checkpoints']
        target.write_text(json.dumps(existing, indent=2))
        print(json.dumps({'restricted_checkpoints': len(paths),
                         'failures': sum('error' in c for c in output['checkpoints'])}))
        return
    for path in sorted((ROOT / 'secureids').rglob('*.py')):
        ast.parse(path.read_text(encoding='utf-8-sig'))
        parts = path.relative_to(ROOT).with_suffix('').parts
        name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
        try:
            importlib.import_module(name)
            output['imports'].append({'module': name, 'ok': True})
        except Exception as error:
            output['imports'].append({'module': name, 'error': str(error)})
    for path in sorted((ROOT / 'configs').rglob('*.yaml')):
        yaml.safe_load(path.read_text())
        output['yaml'].append(path.relative_to(ROOT).as_posix())
    for choice in SCENARIO_CHOICES:
        app = AppTest.from_file(str(ROOT / 'dashboard/app.py')).run(timeout=30)
        app.radio[1].set_value(choice).run(timeout=30)
        app.button[0].click().run(timeout=30)
        errors = [e.message for e in app.exception] + [e.value for e in app.error]
        assert not errors, errors
        values = {m.label: m.value for m in app.metric}
        assert values.get('Integrity status') == 'Fingerprints computed'
        assert values.get('Binary decision') in ('Attack', 'Benign')
        output['dashboard'].append({'scenario': choice, 'metrics': values, 'exceptions': errors})
    app.radio[0].set_value('Centralized reference framing').run(timeout=30)
    assert not app.exception
    output['deployment_mode_toggle'] = True
    previous = os.environ.get('SECUREIDS_ARTIFACT_ROOT')
    os.environ['SECUREIDS_ARTIFACT_ROOT'] = str(ROOT / 'verification/nonexistent-artifacts')
    try:
        import streamlit
        streamlit.cache_data.clear()
        missing = AppTest.from_file(str(ROOT / 'dashboard/app.py')).run(timeout=30)
        assert not missing.exception and len(missing.error) == 1
        output['missing_artifact_message'] = missing.error[0].value
    finally:
        if previous is None:
            os.environ.pop('SECUREIDS_ARTIFACT_ROOT', None)
        else:
            os.environ['SECUREIDS_ARTIFACT_ROOT'] = previous
    # Start a separate local HTTP instance, verify health, then stop only our PID.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    log = (ROOT / 'verification/dashboard-server.txt').open('w')
    process = subprocess.Popen([sys.executable, '-B', '-m', 'streamlit', 'run', 'dashboard/app.py',
        '--server.address=127.0.0.1', f'--server.port={port}', '--server.headless=true',
        '--browser.gatherUsageStats=false'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        for attempt in range(40):
            if process.poll() is not None:
                raise RuntimeError('Streamlit server exited before health check.')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=2) as response:
                    body = response.read().decode()
                    assert response.status == 200 and body == 'ok'
                output['http_health'] = {'status': 200, 'body': body, 'bound_address': '127.0.0.1', 'test_server_stopped': True}
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError('Streamlit health check timed out.')
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()
    (ROOT / 'verification/integration.json').write_text(json.dumps(output, indent=2))
    print(json.dumps({'restricted_checkpoints': len(output['checkpoints']),
        'checkpoint_failures': sum('error' in c for c in output['checkpoints']),
        'modules_imported': len(output['imports']), 'import_failures': sum('error' in m for m in output['imports']),
        'yaml_parsed': len(output['yaml']), 'dashboard_scenarios': len(output['dashboard']),
        'missing_resources_handled': True, 'http_health': output['http_health']}, indent=2))


if __name__ == '__main__':
    main()
