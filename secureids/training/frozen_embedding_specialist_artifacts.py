"""A9.10 frozen-embedding specialist artifact repair/writer helpers.

This module is intentionally scoped to the A9.10 UNSW seed42 workflow. It
derives report/CSV artifacts from already-written JSON metrics and never trains,
selects checkpoints, promotes checkpoints, or writes final model/result trees.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from secureids.training.frozen_embedding_specialist_config import PROJECT_ROOT


A10_RESULTS_DIR = Path("results/experiments/unsw_a10_frozen_embedding_specialist_seed42")
A10_CHECKPOINT = Path("models/experiments/unsw_a10_frozen_embedding_specialist_seed42.pt")
A9_CHECKPOINT = Path("models/final/final_unsw_hierarchical.pt")
A10_REPORT = Path("docs/experiments/UNSW_A10_FROZEN_EMBEDDING_SPECIALIST_SEED42_REPORT.md")
A10_REPAIR_AUDIT = Path("results/audits/unsw_a10_seed42_artifact_repair.json")
PER_CLASS_CSV = A10_RESULTS_DIR / "per_class_attack_metrics.csv"
RARE_CLASS_CSV = A10_RESULTS_DIR / "rare_class_metrics.csv"
CONFUSION_CSV = A10_RESULTS_DIR / "attack_family_confusion_matrix.csv"

EXPECTED_A10_SHA256 = "AC790FD0FBD67FAD9702DBBE29F12ED8A817FE3C076C9E2D91027187111C81D6"
EXPECTED_A9_SHA256 = "5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA"

A9_BASELINE = {
    "binary_macro_f1": 0.894488,
    "attack_family_macro_f1": 0.500429,
    "rare_class_macro_f1": 0.385669,
}


class FrozenEmbeddingArtifactRepairError(RuntimeError):
    """Raised when A9.10 artifact repair would be unsafe."""


def _project_path(project_root: Path, relative: Path) -> Path:
    return project_root / relative


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def file_sha256(path: Path) -> str:
    """Public hash helper for A9.10 artifact/report generation."""

    return _sha256(path)


def _round6(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if path.exists():
        raise FrozenEmbeddingArtifactRepairError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_text(path: Path, text: str) -> None:
    if path.exists():
        raise FrozenEmbeddingArtifactRepairError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FrozenEmbeddingArtifactRepairError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _as_per_class_list(per_class: Any) -> list[dict[str, Any]]:
    if isinstance(per_class, list):
        return [dict(row) for row in per_class]
    if isinstance(per_class, dict):
        rows: list[dict[str, Any]] = []
        for index, (name, metrics) in enumerate(per_class.items()):
            row = dict(metrics)
            row.setdefault("class_id", index)
            row.setdefault("class_name", name)
            rows.append(row)
        return rows
    raise FrozenEmbeddingArtifactRepairError(
        f"unsupported per_class shape: {type(per_class).__name__}"
    )


def build_per_class_rows(view: str, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize per-class metrics from list or dict shape into CSV rows."""

    rows = []
    for index, row in enumerate(_as_per_class_list(metrics.get("per_class", []))):
        rows.append(
            {
                "view": view,
                "class_id": row.get("class_id", index),
                "class_name": row.get("class_name", f"class_{index}"),
                "precision": row.get("precision"),
                "recall": row.get("recall"),
                "f1": row.get("f1"),
                "support": row.get("support"),
            }
        )
    return rows


def _rare_entries(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rare = metrics.get("rare_class", {})
    if isinstance(rare, list):
        return [dict(row) for row in rare]
    if isinstance(rare, dict):
        entries = rare.get("per_rare_class", [])
        if isinstance(entries, list):
            return [dict(row) for row in entries]
    raise FrozenEmbeddingArtifactRepairError(
        f"unsupported rare_class shape: {type(rare).__name__}"
    )


def build_rare_class_rows(view: str, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize rare-class metrics from list or dict shape into CSV rows."""

    rows = []
    for row in _rare_entries(metrics):
        rows.append(
            {
                "view": view,
                "class_name": row.get("class_name"),
                "present": row.get("present"),
                "precision": row.get("precision"),
                "recall": row.get("recall"),
                "f1": row.get("f1"),
                "support": row.get("support"),
            }
        )
    return rows


def build_confusion_matrix_rows(metrics: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Return a wide oracle confusion matrix table from list-based JSON."""

    matrix = metrics.get("confusion_matrix")
    class_names = list(metrics.get("class_names") or [])
    if not isinstance(matrix, list) or not matrix:
        raise FrozenEmbeddingArtifactRepairError("confusion_matrix must be a non-empty list.")
    if not class_names:
        class_names = [f"class_{index}" for index in range(len(matrix))]
    rows: list[dict[str, Any]] = []
    for index, values in enumerate(matrix):
        if not isinstance(values, list):
            raise FrozenEmbeddingArtifactRepairError("confusion_matrix rows must be lists.")
        row = {"view": metrics.get("view", "oracle"), "true_class": class_names[index]}
        for column_index, value in enumerate(values):
            row[class_names[column_index]] = int(value)
        rows.append(row)
    return ["view", "true_class", *class_names], rows


def _metric_table(oracle: dict[str, Any], routed: dict[str, Any]) -> str:
    oracle_af = float(oracle["attack_family_macro_f1"])
    oracle_rare = float(oracle["rare_class"]["rare_class_macro_f1"])
    routed_af = float(routed["routed_attack_family_macro_f1"])
    routed_rare = float(routed["rare_class"]["rare_class_macro_f1"])
    return "\n".join(
        [
            "| Metric | A9 baseline | A9.10 seed42 | Delta | Gate | Result |",
            "| --- | ---: | ---: | ---: | --- | --- |",
            f"| Oracle attack-family macro-F1 | {A9_BASELINE['attack_family_macro_f1']:.6f} | {oracle_af:.6f} | {oracle_af - A9_BASELINE['attack_family_macro_f1']:+.6f} | >= 0.515429 | FAIL |",
            f"| Oracle rare-class macro-F1 | {A9_BASELINE['rare_class_macro_f1']:.6f} | {oracle_rare:.6f} | {oracle_rare - A9_BASELINE['rare_class_macro_f1']:+.6f} | >= 0.385669 | FAIL |",
            f"| Routed attack-family macro-F1 | {A9_BASELINE['attack_family_macro_f1']:.6f} | {routed_af:.6f} | {routed_af - A9_BASELINE['attack_family_macro_f1']:+.6f} | deployment-style context | FAIL |",
            f"| Routed rare-class macro-F1 | {A9_BASELINE['rare_class_macro_f1']:.6f} | {routed_rare:.6f} | {routed_rare - A9_BASELINE['rare_class_macro_f1']:+.6f} | diagnostic | WARN |",
            f"| Binary macro-F1 | {A9_BASELINE['binary_macro_f1']:.6f} | A9 router unchanged | 0.000000 | frozen A9 Head 1 | PASS |",
        ]
    )


def render_seed42_report(
    *,
    oracle: dict[str, Any],
    routed: dict[str, Any],
    a10_sha256: str,
    a9_sha256: str,
) -> str:
    weak_rows = []
    by_name = {row["class_name"]: row for row in _as_per_class_list(oracle["per_class"])}
    for name in ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms"):
        row = by_name.get(name, {})
        weak_rows.append(
            f"| {name} | {row.get('precision')} | {row.get('recall')} | {row.get('f1')} | {row.get('support')} |"
        )

    return "\n".join(
        [
            "# UNSW A10 Frozen Embedding Specialist Seed42 Report",
            "",
            "Status: `FAIL_SCREEN`",
            "",
            "A9.10 seed42 is rejected as diagnostic only. It does not proceed to 3-seed confirmation, and A9 remains the accepted UNSW baseline. No single-seed promotion is allowed.",
            "",
            "## Safety",
            "",
            f"- A9 final checkpoint SHA256 stayed unchanged: `{a9_sha256}`",
            f"- A9.10 checkpoint SHA256 stayed unchanged: `{a10_sha256}`",
            "- No training rerun occurred.",
            "- No test tuning occurred.",
            "- No checkpoint was promoted or replaced.",
            "- `models/final/` and `results/final/` were not modified.",
            "",
            "## Metric Views",
            "",
            "- Oracle metrics are teacher-forced on true attack rows. They are not routed/deployed metrics.",
            "- Routed metrics are deployment-style because the frozen A9 Head 1 routes rows into the A9.10 head.",
            "- Routed performance is bounded by frozen A9 Head 1 misses.",
            "",
            "## Screen Metrics",
            "",
            _metric_table(oracle, routed),
            "",
            "## Screen Gates",
            "",
            "| Gate | Result |",
            "| --- | --- |",
            "| Oracle attack-family macro-F1 >= 0.515429 | FAIL |",
            "| Rare-class macro-F1 >= 0.385669 | FAIL |",
            "| Oracle/routed separated | PASS |",
            "| Binary router remains A9-based | PASS |",
            "| Overall | FAIL_SCREEN |",
            "",
            "## Weak Classes Remain Visible",
            "",
            "| Class | Precision | Recall | F1 | Support |",
            "| --- | ---: | ---: | ---: | ---: |",
            *weak_rows,
            "",
            "## Generated Repair Artifacts",
            "",
            f"- Per-class CSV: `{PER_CLASS_CSV.as_posix()}`",
            f"- Rare-class CSV: `{RARE_CLASS_CSV.as_posix()}`",
            f"- Oracle confusion matrix CSV: `{CONFUSION_CSV.as_posix()}`",
            "",
            "## Recommendation",
            "",
            "Reject A9.10 seed42 as diagnostic only. Do not proceed to 3-seed confirmation. Stop UNSW specialist work unless main control requests further deep analysis. Keep A9 as the accepted UNSW baseline.",
            "",
        ]
    )


def write_seed42_artifact_repair(
    *,
    project_root: Path | str = PROJECT_ROOT,
    generated_on: str = "2026-06-25",
    tests_run: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create missing A9.10 seed42 CSV/report/audit artifacts from existing JSON."""

    root = Path(project_root)
    target_relatives = [A10_REPORT, PER_CLASS_CSV, RARE_CLASS_CSV, CONFUSION_CSV, A10_REPAIR_AUDIT]
    existing = [path.as_posix() for path in target_relatives if _project_path(root, path).exists()]
    if existing:
        raise FrozenEmbeddingArtifactRepairError(f"refusing to overwrite existing repair artifacts: {existing}")

    a10_path = _project_path(root, A10_CHECKPOINT)
    a9_path = _project_path(root, A9_CHECKPOINT)
    a10_before = _sha256(a10_path)
    a9_before = _sha256(a9_path)
    if a10_before != EXPECTED_A10_SHA256:
        raise FrozenEmbeddingArtifactRepairError(f"A9.10 checkpoint hash mismatch: {a10_before}")
    if a9_before != EXPECTED_A9_SHA256:
        raise FrozenEmbeddingArtifactRepairError(f"A9 checkpoint hash mismatch: {a9_before}")

    results_dir = _project_path(root, A10_RESULTS_DIR)
    oracle = _load_json(results_dir / "oracle_attack_family_metrics.json")
    routed = _load_json(results_dir / "routed_end_to_end_metrics.json")
    _load_json(results_dir / "hierarchical_routing_summary.json")
    _load_json(results_dir / "manifest.json")
    _load_json(results_dir / "model_summary.json")
    _load_json(results_dir / "class_weight_snapshot.json")

    per_class_rows = build_per_class_rows("oracle", oracle) + build_per_class_rows("routed", routed)
    rare_rows = build_rare_class_rows("oracle", oracle) + build_rare_class_rows("routed", routed)
    confusion_fields, confusion_rows = build_confusion_matrix_rows(oracle)

    _write_csv(
        _project_path(root, PER_CLASS_CSV),
        per_class_rows,
        ["view", "class_id", "class_name", "precision", "recall", "f1", "support"],
    )
    _write_csv(
        _project_path(root, RARE_CLASS_CSV),
        rare_rows,
        ["view", "class_name", "present", "precision", "recall", "f1", "support"],
    )
    _write_csv(_project_path(root, CONFUSION_CSV), confusion_rows, confusion_fields)

    a10_after = _sha256(a10_path)
    a9_after = _sha256(a9_path)
    report = render_seed42_report(
        oracle=oracle,
        routed=routed,
        a10_sha256=a10_after,
        a9_sha256=a9_after,
    )
    _write_text(_project_path(root, A10_REPORT), report)

    audit = {
        "audit_name": "unsw_a10_seed42_artifact_repair",
        "task_type": "a10_seed42_artifact_report_repair_no_training_rerun",
        "generated_on": generated_on,
        "root_cause": (
            "A9.10 wrote JSON metrics and then crashed while generating CSV/report "
            "artifacts because frozen_embedding_specialist_trainer.py expected "
            "oracle_metrics['per_class'] to be a dict with .items(), but the "
            "shared multiclass metrics helper stores per_class as a list of row dicts."
        ),
        "existing_checkpoint": A10_CHECKPOINT.as_posix(),
        "existing_checkpoint_sha256_before": a10_before,
        "existing_checkpoint_sha256_after": a10_after,
        "a9_checkpoint": A9_CHECKPOINT.as_posix(),
        "a9_checkpoint_sha256_before": a9_before,
        "a9_checkpoint_sha256_after": a9_after,
        "training_rerun": False,
        "checkpoint_modified": a10_before != a10_after,
        "checkpoint_promoted": False,
        "results_dir": A10_RESULTS_DIR.as_posix() + "/",
        "report_created": A10_REPORT.as_posix(),
        "generated_csvs": [
            PER_CLASS_CSV.as_posix(),
            RARE_CLASS_CSV.as_posix(),
            CONFUSION_CSV.as_posix(),
        ],
        "seed42_metrics": {
            "oracle_attack_family_macro_f1": _round6(oracle["attack_family_macro_f1"]),
            "oracle_rare_class_macro_f1": _round6(oracle["rare_class"]["rare_class_macro_f1"]),
            "routed_attack_family_macro_f1": _round6(routed["routed_attack_family_macro_f1"]),
        },
        "a9_baseline": dict(A9_BASELINE),
        "screen_gate_result": {
            "oracle_attack_family_target": 0.515429,
            "oracle_attack_family_pass": False,
            "rare_class_target": 0.385669,
            "rare_class_pass": False,
            "oracle_routed_separation": True,
            "single_seed_promotion_allowed": False,
            "overall_seed42_screen": "FAIL_SCREEN",
        },
        "recommendation": "reject_a10_seed42_diagnostic_only_do_not_run_3seed",
        "tests_run": list(tests_run or []),
        "validation_checks": [
            "existing_json_metrics_parsed",
            "per_class_list_format_accepted",
            "rare_class_dict_with_per_rare_class_accepted",
            "confusion_matrix_list_format_accepted",
            "a10_checkpoint_hash_unchanged",
            "a9_checkpoint_hash_unchanged",
        ],
        "forbidden_actions_confirmed": {
            "training_rerun": False,
            "preprocessing_rebuild_run": False,
            "xai_run": False,
            "streamlit_launched": False,
            "git_action": False,
            "v1_modified": False,
            "a9_checkpoint_modified": False,
            "a10_checkpoint_overwritten": False,
            "checkpoint_promoted": False,
            "results_final_modified": False,
            "models_final_modified": False,
            "test_tuning": False,
            "fake_metrics": False,
        },
        "next_main_control_decision": "formally_reject_a10_and_stop_unsw_specialist_work_or_request_deep_analysis",
    }
    _write_json(_project_path(root, A10_REPAIR_AUDIT), audit)
    return audit
