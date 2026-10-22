"""Boundary and integration regressions. Synthetic fixtures only; no training."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
import torch

from secureids.artifacts import read_artifact_path
from secureids.training.metrics import compute_binary_metrics, binary_confusion_matrix
from secureids.training.hierarchical_metrics import multiclass_confusion_matrix
from secureids.federated.robust_aggregation import aggregate_fedavg, AggregationValidationError
from secureids.federated.hierarchical_training import (
    validate_aggregation_with_integrity, HierarchicalFedAvgTrainingError,
    _apply_attack_to_client_updates, run_hierarchical_fedavg_dry_run)
from secureids.security.update_integrity import make_update_integrity_record, sha256_update
from secureids.training.checkpoints import load_checkpoint
from secureids.preprocessing.pipeline import guard_preprocessing_outputs
from secureids.preprocessing.identity import source_identities, verify_reconstruction_identity, verify_unsw_source_roles
from secureids.xai.local_attribution import gradient_x_input_attribution


@pytest.mark.parametrize('scores,logits', [([np.nan], True), ([np.inf], True), ([-0.1], False), ([1.1], False)])
def test_metrics_reject_invalid_scores(scores, logits):
    with pytest.raises(ValueError):
        compute_binary_metrics([0], scores, from_logits=logits)


@pytest.mark.parametrize('label', [2, -1, 0.5, np.nan])
def test_metrics_reject_invalid_labels(label):
    with pytest.raises(ValueError):
        binary_confusion_matrix([label], [0])
    with pytest.raises(ValueError):
        multiclass_confusion_matrix([label], [0], 2)


@pytest.mark.parametrize('mapping', [True, False])
def test_nonfinite_updates_rejected(mapping):
    x = torch.tensor([float('nan')])
    with pytest.raises(AggregationValidationError, match='finite'):
        aggregate_fedavg([{'w': x}] if mapping else [x])


def test_supplied_reference_rejects_mutation_and_wrong_identity():
    u = {'w': torch.tensor([1.0])}
    records = [make_update_integrity_record('a', 2, sha256_update(u))]
    good = validate_aggregation_with_integrity([u], [1], ['a'], 2, expected_records=records)
    assert good['aggregation_audit']['integrity_verified'] is True
    assert good['verification']['independent_origin_authenticated'] is False
    with pytest.raises(HierarchicalFedAvgTrainingError, match='hash verification'):
        validate_aggregation_with_integrity([{'w': torch.tensor([3.0])}], [1], ['a'], 2, expected_records=records)
    with pytest.raises(HierarchicalFedAvgTrainingError, match='identity'):
        validate_aggregation_with_integrity([u], [1], ['b'], 2, expected_records=records)


def test_full_state_attack_reports_requested_and_realized_rates():
    cfg = {'enabled': True, 'type': 'sign_flip', 'configured_type': 'sign_flip',
           'malicious_fraction': 0.25, 'seed': 42, 'parameters': {'scale': -1.0}}
    updates = [{'w': torch.tensor([2.0])} for _ in range(5)]
    attacked, audit = _apply_attack_to_client_updates(updates, list('abcde'), cfg, [0], 1)
    assert attacked[0]['w'].item() == -2.0
    assert audit['realized_malicious_fraction'] == 0.2
    assert audit['requested_malicious_fraction'] == 0.25
    assert audit['attack_target'] == 'absolute_model_state'


def test_checkpoint_load_fails_closed_on_custom_objects(tmp_path):
    path = tmp_path / 'unsafe.pt'
    torch.save({'unexpected': Path('not-executed')}, path)
    with pytest.raises(Exception, match='Weights only load failed'):
        load_checkpoint(path)


def test_external_artifact_resolution_is_explicit_and_read_only(tmp_path):
    project = tmp_path / 'work'; project.mkdir()
    external = tmp_path / 'original'; external.mkdir()
    (project / '.secureids-local.json').write_text(json.dumps({'artifact_root': str(external)}))
    p = external / 'data/processed/a/X_test.npy'; p.parent.mkdir(parents=True)
    np.save(p, np.ones((1, 2)))
    assert read_artifact_path(project / 'data/processed/a/X_test.npy', project) == p
    assert read_artifact_path(project / 'models/new.pt', project) == project / 'models/new.pt'
    a = np.load(read_artifact_path(project / 'data/processed/a/X_test.npy', project), mmap_mode='r')
    assert a.flags.writeable is False


def test_preprocessing_guards_existing_preprocessor_before_writes(tmp_path):
    artifact = tmp_path / 'pre.joblib'; artifact.write_bytes(b'original')
    with pytest.raises(FileExistsError):
        guard_preprocessing_outputs(tmp_path / 'new', artifact)
    assert artifact.read_bytes() == b'original'
    assert not (tmp_path / 'new').exists()


def test_row_identity_detects_same_labels_different_source(tmp_path):
    raw = tmp_path / 'source.csv'; raw.write_text('x,label\n1,0\n2,1\n')
    arr = tmp_path / 'X_train.npy'; np.save(arr, [[1], [2]])
    from secureids.artifacts import sha256_file
    policy = {'seed': 42}
    m = {'source_identities': source_identities([raw]), 'config_snapshot': {'split': policy},
         'processed_array_sha256': {'X_train.npy': sha256_file(arr)}}
    (tmp_path / 'preprocessing_manifest.json').write_text(json.dumps(m))
    verify_reconstruction_identity(tmp_path, [raw], policy)
    raw.write_text('x,label\n2,0\n1,1\n')
    with pytest.raises(ValueError, match='source'):
        verify_reconstruction_identity(tmp_path, [raw], policy)


def test_unsw_role_check_rejects_swapped_partitions():
    import pandas as pd
    cfg = {'target_column': 'label', 'source_verification': {
        'train': {'rows': 2, 'binary_counts': {0: 1, 1: 1}},
        'test': {'rows': 1, 'binary_counts': {0: 1}}}}
    a = pd.DataFrame({'id': [1, 2], 'label': [0, 1]})
    b = pd.DataFrame({'id': [1], 'label': [0]})
    verify_unsw_source_roles(a, b, cfg)
    with pytest.raises(ValueError, match='row count'):
        verify_unsw_source_roles(b, a, cfg)


def test_gradient_x_input_matches_known_linear_contributions():
    model = torch.nn.Linear(2, 1, bias=False)
    with torch.no_grad():
        model.weight.copy_(torch.tensor([[2.0, -3.0]]))
    r = gradient_x_input_attribution(model, torch.tensor([[4.0, 1.0]]), ['a', 'b'])
    assert r['binary']['top_positive'][0]['attribution'] == pytest.approx(8.0)
    assert r['binary']['top_negative'][0]['attribution'] == pytest.approx(-3.0)


def test_routed_misses_reduce_recall_for_a_partly_detected_family():
    from secureids.training.attack_family_specialist_evaluation import compute_routed_attack_family_metrics
    result = compute_routed_attack_family_metrics([0, 0], [1, 0], [0, 0],
        num_classes=1, class_names=['A'], rare_class_names=['A'])
    assert result['per_class'][0]['support'] == 2
    assert result['per_class'][0]['recall'] == 0.5
    assert result['routed_attack_family_macro_f1'] == pytest.approx(2 / 3)
    assert np.asarray(result['confusion_matrix']).sum() == 2


def test_rare_labels_resolve_to_canonical_families():
    from secureids.training.hierarchical_metrics import rare_family_names
    assert rare_family_names({'rare_raw_labels': ['raw A', 'raw B'],
        'raw_label_to_attack_family': {'raw A': 'A', 'raw B': 'B'}}) == ['A', 'B']


@pytest.mark.parametrize('field,value,reason', [('client_fraction', 0.5, 'full participation'),
                                              ('client_split', 'stratified_iid', 'attack_family_aware_iid')])
def test_unsupported_participation_is_an_execution_blocker(tmp_path, field, value, reason):
    import yaml
    from secureids.federated.hierarchical_plan import load_hierarchical_federated_plan
    from secureids.federated.hierarchical_training import execution_readiness_errors
    root = Path(__file__).resolve().parents[1]
    config = root / 'configs/federated/experiments/unsw_hierarchical_byzantine_signflip.yaml'
    raw = yaml.safe_load(config.read_text()); raw['federation'][field] = value
    p = tmp_path / 'config.yaml'; p.write_text(yaml.safe_dump(raw))
    plan = load_hierarchical_federated_plan(p, project_root=root)
    assert any(reason in e for e in execution_readiness_errors(plan, root))


def test_benign_prediction_suppresses_family(monkeypatch, tmp_path):
    from secureids.inference import live_demo as demo
    model = torch.nn.Module()
    model.forward = lambda x: {'binary_logit': x[:, :1] * 0 - 9,
                               'attack_logits': x[:, :2] * 0 + 2}
    spec = replace(demo.DATASET_SPECS['UNSW-NB15'], input_dim=2, attack_head_dim=2, data_dir=tmp_path,
                   checkpoint_path=tmp_path / 'checkpoint.pt', default_sample_index=0)
    spec.checkpoint_path.write_bytes(b'fixture')
    (tmp_path / 'feature_names.json').write_text('{}')
    (tmp_path / 'attack_family_label_mapping.json').write_text('{}')
    monkeypatch.setattr(demo, 'get_dataset_spec', lambda _: spec)
    monkeypatch.setattr(demo, '_load_model', lambda _: model)
    monkeypatch.setattr(demo, '_load_metadata', lambda _: {'feature_names': ['a', 'b'],
        'attack_mapping': {'id_to_class': {'0': 'A', '1': 'B'}},
        'binary_mapping': {'id_to_class': {'0': 'Benign', '1': 'Attack'}}})
    np.save(tmp_path / 'X_test.npy', [[1.0, 2.0]])
    np.save(tmp_path / 'y_binary_test.npy', [1])
    np.save(tmp_path / 'y_attack_family_test.npy', [0])
    np.save(tmp_path / 'attack_family_mask_test.npy', [1])
    r = demo.run_live_inference('UNSW-NB15')
    assert r['binary_prediction'] == 'Benign'
    assert r['attack_family_prediction'] is None
    assert r['attack_family_probability'] is None
    assert r['attack_family_correct'] is False
    assert r['attribution'].get('family') is None
