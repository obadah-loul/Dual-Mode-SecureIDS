from __future__ import annotations

from pathlib import Path

import pytest
import torch

from secureids.federated.hierarchical_training import (
    HierarchicalFedAvgTrainingError,
    run_hierarchical_fedavg_dry_run,
    validate_aggregation_with_integrity,
    verify_client_update_integrity,
)
from secureids.security.update_integrity import (
    make_update_integrity_record,
    sha256_update,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/federated/experiments/unsw_hierarchical_clean_fedavg.yaml"


def test_hierarchical_fedavg_dry_run_lists_outputs_and_writes_nothing():
    outcome = run_hierarchical_fedavg_dry_run(CONFIG, project_root=PROJECT_ROOT)

    assert outcome["status"] == "PASS"
    assert outcome["dataset"] == "unsw_nb15"
    assert outcome["initialization"] == "from_scratch"
    assert outcome["writes_outputs"] is False
    assert outcome["training_run"] is False
    assert outcome["checkpoint_created"] is False
    assert outcome["metrics_created"] is False
    assert outcome["expected_outputs"]["checkpoint"].endswith(
        "models\\experiments\\federated_security\\unsw_hierarchical_clean_fedavg.pt"
    ) or outcome["expected_outputs"]["checkpoint"].endswith(
        "models/experiments/federated_security/unsw_hierarchical_clean_fedavg.pt"
    )


def test_weighted_fedavg_state_dict_aggregation_has_audit():
    client_updates = [
        {"layer.weight": torch.tensor([1.0, 3.0])},
        {"layer.weight": torch.tensor([5.0, 7.0])},
    ]

    outcome = validate_aggregation_with_integrity(
        client_updates,
        sample_counts=[1, 3],
        client_ids=["client_00", "client_01"],
        round_id=2,
    )

    assert torch.allclose(
        outcome["aggregated_state_dict"]["layer.weight"],
        torch.tensor([4.0, 6.0]),
    )
    assert outcome["verification"]["all_verified"] is True
    audit = outcome['aggregation_audit']
    assert {k: audit[k] for k in ('round', 'algorithm', 'client_ids', 'sample_counts', 'total_samples', 'integrity_verified')} == {
        "round": 2,
        "algorithm": "fedavg",
        "client_ids": ["client_00", "client_01"],
        "sample_counts": [1, 3],
        "total_samples": 4,
        "integrity_verified": False,
    }
    assert audit['integrity_scope'] == 'local_fingerprint_self_check'
    assert audit['fingerprints_match'] is True
    assert audit['strategy'] == 'fedavg'
    assert audit['sample_count_weighted'] is True


def test_runner_integrity_hook_rejects_tampered_update():
    clean_update = {"layer.weight": torch.tensor([1.0, 2.0])}
    records = [
        make_update_integrity_record(
            client_id="client_00",
            round_id=1,
            update_hash=sha256_update(clean_update),
        )
    ]
    tampered_update = {"layer.weight": torch.tensor([1.0, 9.0])}

    with pytest.raises(HierarchicalFedAvgTrainingError, match="hash verification"):
        verify_client_update_integrity(records, [tampered_update])
