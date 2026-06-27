"""A9.10 artifact repair tests from existing JSON metrics only."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from secureids.training import frozen_embedding_specialist_artifacts as artifacts


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _oracle_metrics() -> dict:
    return {
        "view": "oracle",
        "attack_family_macro_f1": 0.5011550605016061,
        "attack_rows_evaluated": 6,
        "per_class": [
            {"class_id": 0, "class_name": "Generic", "precision": 1.0, "recall": 1.0, "f1": 1.0, "support": 3},
            {"class_id": 1, "class_name": "Shellcode", "precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 2},
            {"class_id": 2, "class_name": "Worms", "precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 1},
        ],
        "confusion_matrix": [[3, 0, 0], [0, 1, 1], [0, 1, 0]],
        "class_names": ["Generic", "Shellcode", "Worms"],
        "rare_class": {
            "rare_classes": ["Shellcode", "Worms"],
            "rare_class_macro_f1": 0.25,
            "per_rare_class": [
                {"class_name": "Shellcode", "present": True, "precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 2},
                {"class_name": "Worms", "present": True, "precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 1},
            ],
        },
    }


def _routed_metrics() -> dict:
    routed = _oracle_metrics()
    routed["view"] = "routed"
    routed["routed_attack_family_macro_f1"] = 0.49
    routed["rare_class"]["rare_class_macro_f1"] = 0.24
    return routed


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_tmp_project(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    root = tmp_path
    results = root / "results/experiments/a10"
    _write_json(results / "oracle_attack_family_metrics.json", _oracle_metrics())
    _write_json(results / "routed_end_to_end_metrics.json", _routed_metrics())
    _write_json(results / "hierarchical_routing_summary.json", {"metric_views_are_separated": True})
    _write_json(results / "manifest.json", {"test_tuning": False})
    _write_json(results / "model_summary.json", {"architecture_metadata": {}})
    _write_json(results / "class_weight_snapshot.json", {"weights": [1.0]})
    (results / "training_history.csv").write_text("epoch,loss\n1,1.0\n", encoding="utf-8")

    a10 = root / "models/experiments/a10.pt"
    a9 = root / "models/final/a9.pt"
    a10.parent.mkdir(parents=True, exist_ok=True)
    a9.parent.mkdir(parents=True, exist_ok=True)
    a10.write_bytes(b"a10-checkpoint")
    a9.write_bytes(b"a9-checkpoint")

    monkeypatch.setattr(artifacts, "A10_RESULTS_DIR", Path("results/experiments/a10"))
    monkeypatch.setattr(artifacts, "A10_CHECKPOINT", Path("models/experiments/a10.pt"))
    monkeypatch.setattr(artifacts, "A9_CHECKPOINT", Path("models/final/a9.pt"))
    monkeypatch.setattr(artifacts, "A10_REPORT", Path("docs/experiments/a10_report.md"))
    monkeypatch.setattr(artifacts, "A10_REPAIR_AUDIT", Path("results/audits/a10_repair.json"))
    monkeypatch.setattr(artifacts, "PER_CLASS_CSV", Path("results/experiments/a10/per_class_attack_metrics.csv"))
    monkeypatch.setattr(artifacts, "RARE_CLASS_CSV", Path("results/experiments/a10/rare_class_metrics.csv"))
    monkeypatch.setattr(artifacts, "CONFUSION_CSV", Path("results/experiments/a10/attack_family_confusion_matrix.csv"))
    monkeypatch.setattr(artifacts, "EXPECTED_A10_SHA256", _hash(a10))
    monkeypatch.setattr(artifacts, "EXPECTED_A9_SHA256", _hash(a9))
    return a10, a9


def test_list_metric_shapes_are_accepted_for_csv_rows():
    oracle = _oracle_metrics()
    per_class = artifacts.build_per_class_rows("oracle", oracle)
    rare = artifacts.build_rare_class_rows("oracle", oracle)
    fields, confusion = artifacts.build_confusion_matrix_rows(oracle)
    assert per_class[0]["view"] == "oracle"
    assert rare[0]["class_name"] == "Shellcode"
    assert fields == ["view", "true_class", "Generic", "Shellcode", "Worms"]
    assert confusion[0]["Generic"] == 3


def test_rare_class_list_shape_is_accepted():
    metrics = {"rare_class": [{"class_name": "Shellcode", "present": True, "f1": 0.5, "support": 2}]}
    rows = artifacts.build_rare_class_rows("routed", metrics)
    assert rows == [
        {
            "view": "routed",
            "class_name": "Shellcode",
            "present": True,
            "precision": None,
            "recall": None,
            "f1": 0.5,
            "support": 2,
        }
    ]


def test_repair_generates_csv_report_and_audit_without_checkpoint_overwrite(tmp_path, monkeypatch):
    a10, a9 = _seed_tmp_project(tmp_path, monkeypatch)
    a10_before = _hash(a10)
    a9_before = _hash(a9)

    audit = artifacts.write_seed42_artifact_repair(project_root=tmp_path)

    assert audit["training_rerun"] is False
    assert _hash(a10) == a10_before
    assert _hash(a9) == a9_before
    report = tmp_path / "docs/experiments/a10_report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "Oracle metrics are teacher-forced" in text
    assert "Routed metrics are deployment-style" in text
    assert "FAIL_SCREEN" in text

    per_class = list(csv.DictReader((tmp_path / "results/experiments/a10/per_class_attack_metrics.csv").open()))
    rare = list(csv.DictReader((tmp_path / "results/experiments/a10/rare_class_metrics.csv").open()))
    confusion = list(csv.DictReader((tmp_path / "results/experiments/a10/attack_family_confusion_matrix.csv").open()))
    assert {row["view"] for row in per_class} == {"oracle", "routed"}
    assert {row["view"] for row in rare} == {"oracle", "routed"}
    assert confusion[0]["true_class"] == "Generic"


def test_repair_refuses_to_overwrite_existing_targets(tmp_path, monkeypatch):
    _seed_tmp_project(tmp_path, monkeypatch)
    existing_report = tmp_path / "docs/experiments/a10_report.md"
    existing_report.parent.mkdir(parents=True, exist_ok=True)
    existing_report.write_text("existing", encoding="utf-8")
    try:
        artifacts.write_seed42_artifact_repair(project_root=tmp_path)
    except artifacts.FrozenEmbeddingArtifactRepairError as error:
        assert "refusing to overwrite" in str(error)
    else:  # pragma: no cover
        raise AssertionError("repair should refuse existing targets")
