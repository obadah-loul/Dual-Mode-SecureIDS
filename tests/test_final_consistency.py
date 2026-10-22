"""Final claim/report regressions; no model training or research execution."""
from pathlib import Path
import tomllib

import pytest

from secureids.federated.hierarchical_plan import load_hierarchical_federated_plan
from secureids.federated.hierarchical_training import _validate_attack_config, _write_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('suffix,fraction,count', [('', 0.25, 1), ('_50', 0.50, 2)])
def test_future_reports_keep_requested_and_realized_rates_separate(tmp_path, suffix, fraction, count):
    plan = load_hierarchical_federated_plan(
        f'configs/federated/experiments/unsw_hierarchical_byzantine_signflip{suffix}.yaml', project_root=ROOT)
    attack = _validate_attack_config(plan)
    assert attack['requested_malicious_fraction'] == fraction
    assert attack['realized_malicious_fraction'] == count / 5
    assert attack['attack_target'] == 'absolute_model_state'
    attack['malicious_client_ids'] = [f'client_{i:02d}' for i in range(count)]
    outcome = {'attack': attack, 'aggregation': {'strategy': 'fedavg'},
               'best_round': 1, 'rounds_run': 1, 'metrics_path': 'synthetic-test-only.json',
               'manifest_path': 'synthetic-test-only-manifest.json', 'integrity_verified': False}
    path = tmp_path / 'fixture-report.md'
    _write_report(path, plan, outcome)
    text = path.read_text()
    assert f'Realized malicious fraction: `{count / 5}` ({count} of 5)' in text
    assert 'Requested malicious fraction' in text
    assert 'in-process simulation' in text
    assert 'not parameter deltas' in text
    assert 'local fingerprint self-checks' in text
    assert 'Supplied-reference comparisons passed: `False`' in text
    assert 'SHA-256 update integrity verified' not in text
    assert 'future actual run' not in text


def test_local_project_description_matches_evidence_report():
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    description = metadata['project']['description']
    assert metadata['tool']['pytest']['ini_options']['testpaths'] == ['tests']
    assert description.startswith('Research prototype')
    assert 'simulated federated' in description
    assert description in (ROOT / 'docs/PROJECT_VERIFICATION_REPORT.md').read_text(encoding='utf-8')


def test_readme_and_dashboard_name_replay_and_fingerprint_scope():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    ui = (ROOT / 'dashboard/app.py').read_text(encoding='utf-8')
    assert '**Run IDS Replay**' in readme
    assert 'st.button("Run IDS Replay"' in ui
    assert 'SHA-256 Fingerprints' in ui
    assert 'Simulated federated framing' in ui
    assert 'privacy-preserving' not in ui
