"""Post-training artifact + report writer for the UNSW A9.9 specialist.

The original A9.9 ``_execute_training`` saved only the checkpoint and returned;
it never wrote the result_dir/report. This module supplies the missing
artifact-writer so:

* future ``--execute`` runs call ``generate_seed_artifacts(...)`` after saving
  the checkpoint, and
* an already-trained checkpoint can be repaired into its full artifact set
  WITHOUT retraining.

``write_seed_artifacts`` is torch-free and file-driven (easy to unit test).
``generate_seed_artifacts`` adds the torch/data evaluation and is not run in
unit tests. Nothing here trains, overwrites checkpoints, or touches final trees.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - environment dependent
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from secureids.training.attack_family_specialist_config import (
    PROJECT_ROOT,
    ATTACK_FAMILY_NAMES,
    AttackFamilySpecialistConfig,
    is_final_path,
    load_attack_family_specialist_config,
)

SEED42_SCREEN_MIN_ORACLE_MACRO_F1 = 0.515429  # A9 0.500429 + 0.015 noise band
A9_BASELINE = {
    "binary_macro_f1": 0.894488,
    "attack_family_macro_f1": 0.500429,
    "rare_class_macro_f1": 0.385669,
}

# Output keys that are real files this writer must produce (everything in the
# config outputs except the pre-existing checkpoint and the result_dir itself).
ARTIFACT_FILE_KEYS = (
    "training_history_csv",
    "oracle_metrics_json",
    "routed_metrics_json",
    "per_class_attack_metrics_csv",
    "rare_class_metrics_csv",
    "attack_family_confusion_matrix_csv",
    "routing_summary_json",
    "training_config_snapshot_yaml",
    "class_weight_snapshot_json",
    "model_summary_json",
    "report_md",
)


class SpecialistArtifactError(RuntimeError):
    """Raised on unsafe paths or refusal to overwrite an existing artifact."""


def _resolve(config: AttackFamilySpecialistConfig, rel: str) -> Path:
    return config.resolve(rel)


def _guard_not_final(rel: str, label: str) -> None:
    if is_final_path(rel):
        raise SpecialistArtifactError(f"{label} resolves into a final tree: {rel!r}")


def _write_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(text, encoding="utf-8")


def _write_per_class_csv(path: Path, oracle_metrics: dict[str, Any], overwrite: bool) -> None:
    rows = oracle_metrics.get("per_class", [])
    if path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["class_id", "class_name", "precision", "recall", "f1", "support"])
        for entry in rows:
            writer.writerow(
                [
                    entry.get("class_id"),
                    entry.get("class_name"),
                    round(float(entry.get("precision", 0.0)), 6),
                    round(float(entry.get("recall", 0.0)), 6),
                    round(float(entry.get("f1", 0.0)), 6),
                    entry.get("support"),
                ]
            )


def _write_rare_csv(path: Path, oracle_metrics: dict[str, Any], overwrite: bool) -> None:
    rare = oracle_metrics.get("rare_class", {})
    if path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["class_name", "precision", "recall", "f1", "support"])
        for entry in rare.get("per_rare_class", []):
            writer.writerow(
                [
                    entry.get("class_name"),
                    entry.get("precision"),
                    entry.get("recall"),
                    entry.get("f1"),
                    entry.get("support"),
                ]
            )
        writer.writerow(["rare_class_macro_f1", "", "", rare.get("rare_class_macro_f1"), ""])


def _write_confusion_csv(path: Path, oracle_metrics: dict[str, Any], overwrite: bool) -> None:
    cm = oracle_metrics.get("confusion_matrix", [])
    names = oracle_metrics.get("class_names", list(ATTACK_FAMILY_NAMES))
    if path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true\\pred", *names])
        for index, row in enumerate(cm):
            label = names[index] if index < len(names) else f"class_{index}"
            writer.writerow([label, *row])


def _render_report_md(
    config: AttackFamilySpecialistConfig,
    oracle_metrics: dict[str, Any],
    routed_metrics: dict[str, Any],
    binary_router_metrics: dict[str, Any],
    model_summary: dict[str, Any],
    screen_gate: dict[str, Any],
    checkpoint_sha256: str,
) -> str:
    oracle_macro = oracle_metrics.get("attack_family_macro_f1")
    oracle_rare = oracle_metrics.get("rare_class", {}).get("rare_class_macro_f1")
    routed_macro = routed_metrics.get("routed_attack_family_macro_f1")
    by_name = {e["class_name"]: e for e in oracle_metrics.get("per_class", [])}

    def f1(name: str) -> Any:
        return round(float(by_name[name]["f1"]), 6) if name in by_name else "n/a"

    weak_rows = "\n".join(
        f"| {name} | {by_name.get(name, {}).get('support', 'n/a')} | "
        f"{round(float(by_name[name]['precision']), 6) if name in by_name else 'n/a'} | "
        f"{round(float(by_name[name]['recall']), 6) if name in by_name else 'n/a'} | "
        f"{f1(name)} |"
        for name in ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms")
    )

    return f"""# UNSW A9.9 Attack-Family Specialist — Seed 42 Report

Status: `single-seed screen result — NOT promotable alone; A9 remains the accepted UNSW final`
Generated: `2026-06-25` (artifacts repaired from the existing seed42 checkpoint; **no retraining**)

Specialist checkpoint: `models/experiments/unsw_a99_attack_family_specialist_seed42.pt`
Checkpoint SHA256: `{checkpoint_sha256}`
Frozen A9 router: `models/final/final_unsw_hierarchical.pt` (loaded read-only; never retrained)
Checkpoint selection: **validation-only** (best val attack-family macro-F1 =
`{model_summary.get('best_val_attack_family_macro_f1')}`). Test was evaluated **once** for this
report and was **not** used for selection or tuning.

---

## 1. Metric views (kept strictly separate)

> Oracle = specialist on the TRUE attack rows (teacher-forced). Routed = frozen A9 Head 1 routes
> detected attacks into the specialist (deployment view, bounded by Head 1 recall). **Oracle numbers
> are not deployment/routed numbers.**

| View | Metric | Value |
| --- | --- | ---: |
| A9 binary Head 1 (router, frozen) | binary macro-F1 | {round(float(binary_router_metrics.get('macro_f1', 0.0)), 6)} |
| Specialist **oracle** attack-family | macro-F1 (attack rows) | {round(float(oracle_macro), 6) if oracle_macro is not None else 'n/a'} |
| Specialist **oracle** rare-class | macro-F1 (Shellcode, Worms) | {round(float(oracle_rare), 6) if oracle_rare is not None else 'n/a'} |
| **Routed** end-to-end | routed attack-family macro-F1 | {round(float(routed_macro), 6) if routed_macro is not None else 'n/a'} |
| **Routed** end-to-end | correctly-attributed rate | {round(float(routed_metrics.get('attack_detected_and_correctly_attributed_rate', 0.0)), 6)} |
| **Routed** end-to-end | missed-as-benign rate | {round(float(routed_metrics.get('attack_missed_as_benign_rate', 0.0)), 6)} |

Oracle attack rows evaluated: {oracle_metrics.get('attack_rows_evaluated')}. Routed attack total:
{routed_metrics.get('attack_total')} (correctly attributed {routed_metrics.get('attack_detected_and_correctly_attributed')},
wrong family {routed_metrics.get('attack_detected_wrong_family')}, missed as benign
{routed_metrics.get('attack_missed_as_benign')}).

## 2. Comparison vs A9 baseline (test)

| Metric | A9 baseline | A9.9 seed42 (oracle) | Δ |
| --- | ---: | ---: | ---: |
| Attack-family macro-F1 | {A9_BASELINE['attack_family_macro_f1']} | {round(float(oracle_macro), 6) if oracle_macro is not None else 'n/a'} | {round(float(oracle_macro) - A9_BASELINE['attack_family_macro_f1'], 6) if oracle_macro is not None else 'n/a'} |
| Rare-class macro-F1 | {A9_BASELINE['rare_class_macro_f1']} | {round(float(oracle_rare), 6) if oracle_rare is not None else 'n/a'} | {round(float(oracle_rare) - A9_BASELINE['rare_class_macro_f1'], 6) if oracle_rare is not None else 'n/a'} |
| Binary macro-F1 (router) | {A9_BASELINE['binary_macro_f1']} | {round(float(binary_router_metrics.get('macro_f1', 0.0)), 6)} | router frozen (unchanged by construction) |

## 3. Weak classes (reported, never hidden)

| Class | Support | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
{weak_rows}

## 4. Seed42 screen gates

- Oracle attack-family macro-F1 ≥ {SEED42_SCREEN_MIN_ORACLE_MACRO_F1}: **{screen_gate['oracle_attack_family_gate']}**
- Rare-class macro-F1 ≥ {A9_BASELINE['rare_class_macro_f1']}: **{screen_gate['rare_class_gate']}**
- Binary router unchanged (A9 frozen): **{screen_gate.get('binary_router_unchanged')}**
- Oracle / routed separated: **{screen_gate.get('oracle_routed_separation')}**
- Overall: **{screen_gate['overall_seed42_screen']}**

## 5. Promotion status

**Seed42 cannot be promoted on its own.** Promotion requires a 3-seed (42/123/999) mean ± std that
clears the ~0.0143 attack-family seed-noise band versus the A9 linear 3-seed mean (0.494965), plus the
rare-class and precision gates — and explicit main-control approval. A9 remains the accepted UNSW final
model. This document is a single-seed screen result only.
"""


def write_seed_artifacts(
    config: AttackFamilySpecialistConfig,
    *,
    oracle_metrics: dict[str, Any],
    routed_metrics: dict[str, Any],
    binary_router_metrics: dict[str, Any],
    class_weight_snapshot: dict[str, Any],
    model_summary: dict[str, Any],
    training_history_note: str,
    screen_gate: dict[str, Any],
    checkpoint_sha256: str,
    project_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, str]:
    """Write ALL configured seed artifacts + the report. Torch-free.

    Creates ``result_dir`` and writes every file in :data:`ARTIFACT_FILE_KEYS`
    plus an artifact manifest. Refuses any path that resolves into a final tree
    and refuses to overwrite an existing file unless ``overwrite=True``.
    """

    if oracle_metrics.get("view") != "oracle":
        raise SpecialistArtifactError("oracle_metrics must be the oracle view.")
    if routed_metrics.get("view") != "routed":
        raise SpecialistArtifactError("routed_metrics must be the routed view.")

    root = Path(project_root) if project_root is not None else config.project_root
    outputs = config.outputs

    result_dir_rel = outputs["result_dir"]
    _guard_not_final(result_dir_rel, "outputs.result_dir")
    result_dir = root / result_dir_rel
    result_dir.mkdir(parents=True, exist_ok=True)

    for key in ARTIFACT_FILE_KEYS:
        _guard_not_final(outputs[key], f"outputs.{key}")
        (root / outputs[key]).parent.mkdir(parents=True, exist_ok=True)

    written: dict[str, str] = {}

    # training history (not persisted by the original run) -> clear note CSV.
    hist_path = root / outputs["training_history_csv"]
    if hist_path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {hist_path}")
    with hist_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "value", "note"])
        writer.writerow(
            [
                "best_val_attack_family_macro_f1",
                model_summary.get("best_val_attack_family_macro_f1"),
                training_history_note,
            ]
        )
    written["training_history_csv"] = outputs["training_history_csv"]

    _write_json(root / outputs["oracle_metrics_json"], oracle_metrics, overwrite)
    written["oracle_metrics_json"] = outputs["oracle_metrics_json"]

    _write_json(root / outputs["routed_metrics_json"], routed_metrics, overwrite)
    written["routed_metrics_json"] = outputs["routed_metrics_json"]

    _write_per_class_csv(root / outputs["per_class_attack_metrics_csv"], oracle_metrics, overwrite)
    written["per_class_attack_metrics_csv"] = outputs["per_class_attack_metrics_csv"]

    _write_rare_csv(root / outputs["rare_class_metrics_csv"], oracle_metrics, overwrite)
    written["rare_class_metrics_csv"] = outputs["rare_class_metrics_csv"]

    _write_confusion_csv(
        root / outputs["attack_family_confusion_matrix_csv"], oracle_metrics, overwrite
    )
    written["attack_family_confusion_matrix_csv"] = outputs["attack_family_confusion_matrix_csv"]

    routing_summary = {
        "view": "routed",
        "definitions": {
            "attack_detected_and_correctly_attributed": "true attack routed by A9 Head 1 AND specialist family correct",
            "attack_detected_wrong_family": "true attack routed by A9 Head 1 but specialist family wrong",
            "attack_missed_as_benign": "true attack predicted benign by frozen A9 Head 1 (never reaches specialist)",
        },
        "a9_binary_head1_router": binary_router_metrics,
        "routed_end_to_end": routed_metrics,
        "oracle_is_not_routed": True,
    }
    _write_json(root / outputs["routing_summary_json"], routing_summary, overwrite)
    written["routing_summary_json"] = outputs["routing_summary_json"]

    snapshot_path = root / outputs["training_config_snapshot_yaml"]
    if snapshot_path.exists() and not overwrite:
        raise SpecialistArtifactError(f"refusing to overwrite existing artifact: {snapshot_path}")
    if yaml is not None:
        snapshot_path.write_text(yaml.safe_dump(config.raw, sort_keys=False), encoding="utf-8")
    else:  # pragma: no cover
        snapshot_path.write_text(json.dumps(config.raw, indent=2), encoding="utf-8")
    written["training_config_snapshot_yaml"] = outputs["training_config_snapshot_yaml"]

    _write_json(root / outputs["class_weight_snapshot_json"], class_weight_snapshot, overwrite)
    written["class_weight_snapshot_json"] = outputs["class_weight_snapshot_json"]

    _write_json(root / outputs["model_summary_json"], model_summary, overwrite)
    written["model_summary_json"] = outputs["model_summary_json"]

    report_md = _render_report_md(
        config,
        oracle_metrics,
        routed_metrics,
        binary_router_metrics,
        model_summary,
        screen_gate,
        checkpoint_sha256,
    )
    _write_text(root / outputs["report_md"], report_md, overwrite)
    written["report_md"] = outputs["report_md"]

    manifest = {
        "experiment": config.experiment,
        "seed": config.seed,
        "checkpoint": outputs["checkpoint"],
        "checkpoint_sha256": checkpoint_sha256,
        "generated_by": "attack_family_specialist_artifacts.write_seed_artifacts",
        "retraining": False,
        "metric_views_separated": True,
        "oracle_attack_family_macro_f1": oracle_metrics.get("attack_family_macro_f1"),
        "routed_attack_family_macro_f1": routed_metrics.get("routed_attack_family_macro_f1"),
        "rare_class_macro_f1": oracle_metrics.get("rare_class", {}).get("rare_class_macro_f1"),
        "binary_router_macro_f1": binary_router_metrics.get("macro_f1"),
        "a9_baseline": A9_BASELINE,
        "screen_gate": screen_gate,
        "artifacts": dict(written),
    }
    manifest_rel = f"{result_dir_rel}/unsw_a99_seed42_artifact_manifest.json"
    _write_json(root / manifest_rel, manifest, overwrite)
    written["artifact_manifest_json"] = manifest_rel

    # Regression guard: every configured file artifact must now exist.
    missing = [key for key in ARTIFACT_FILE_KEYS if not (root / outputs[key]).exists()]
    if missing:  # pragma: no cover - defensive
        raise SpecialistArtifactError(f"artifact writer did not produce: {missing}")

    return written


def compute_screen_gate(
    oracle_attack_family_macro_f1: float,
    rare_class_macro_f1: float,
    binary_router_unchanged: bool,
    oracle_routed_separation: bool = True,
) -> dict[str, Any]:
    """Evaluate the seed42 screen gates from TEST oracle metrics (reporting only)."""

    oracle_gate = (
        "pass" if float(oracle_attack_family_macro_f1) >= SEED42_SCREEN_MIN_ORACLE_MACRO_F1 else "fail"
    )
    rare_gate = (
        "pass" if float(rare_class_macro_f1) >= A9_BASELINE["rare_class_macro_f1"] else "fail"
    )
    if oracle_gate == "pass" and rare_gate == "pass" and binary_router_unchanged:
        overall = "PASS_SCREEN"
    elif oracle_gate == "fail" and rare_gate == "fail":
        overall = "FAIL_SCREEN_DIAGNOSTIC_ONLY"
    else:
        overall = "NEEDS_INVESTIGATION"
    return {
        "oracle_attack_family_gate": oracle_gate,
        "rare_class_gate": rare_gate,
        "binary_router_unchanged": bool(binary_router_unchanged),
        "oracle_routed_separation": bool(oracle_routed_separation),
        "single_seed_promotion_allowed": False,
        "overall_seed42_screen": overall,
    }


def generate_seed_artifacts(  # pragma: no cover - torch/data path, not unit tested
    config_path: Path | str,
    project_root: Path | None = None,
    checkpoint_path: Path | str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Load the existing checkpoint + frozen A9 router, evaluate test once, write artifacts.

    No training. No checkpoint write/overwrite. Test is evaluated a single time
    for reporting only (selection already done on validation during training).
    """

    import hashlib

    import numpy as np
    import torch

    from secureids.models.attack_family_specialist import AttackFamilySpecialistNet
    from secureids.models.secureids_hierarchical_advanced_net import (
        SecureIDSHierarchicalAdvancedNet,
    )
    from secureids.training.attack_family_specialist_evaluation import (
        compute_oracle_attack_family_metrics,
        compute_routed_attack_family_metrics,
    )
    from secureids.training.attack_family_specialist_trainer import (
        _compute_attack_class_weights,
        select_attack_rows,
    )
    from secureids.training.metrics import compute_binary_metrics

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    config = load_attack_family_specialist_config(config_path, project_root=root)

    ckpt_rel = checkpoint_path if checkpoint_path is not None else config.outputs["checkpoint"]
    ckpt_file = root / str(ckpt_rel)
    if not ckpt_file.exists():
        raise SpecialistArtifactError(f"specialist checkpoint not found: {ckpt_file}")
    checkpoint_sha256 = hashlib.sha256(ckpt_file.read_bytes()).hexdigest().upper()

    spec_ckpt = torch.load(ckpt_file, map_location="cpu", weights_only=False)
    meta = spec_ckpt["architecture_metadata"]
    specialist = AttackFamilySpecialistNet(
        input_dim=int(meta["input_dim"]),
        num_attack_families=int(meta["num_attack_families"]),
        hidden_dims=meta.get("hidden_dims"),
        dropout=float(meta.get("dropout", 0.2)),
        normalization=str(meta.get("normalization", "layernorm")),
    )
    specialist.load_state_dict(spec_ckpt["model_state_dict"])
    specialist.eval()

    router_file = root / str(config.frozen_a9_router["checkpoint"])
    a9_ckpt = torch.load(router_file, map_location="cpu", weights_only=False)
    a9_meta = a9_ckpt["architecture_metadata"]
    router = SecureIDSHierarchicalAdvancedNet(
        input_dim=int(a9_ckpt["input_dim"]),
        attack_head_dim=int(a9_ckpt["attack_head_dim"]),
        hidden_dims=a9_meta.get("hidden_dims"),
        dropout=float(a9_meta.get("dropout", 0.2)),
        normalization=str(a9_meta.get("normalization", "layernorm")),
        residual_expansion=int(a9_meta.get("residual_expansion", 2)),
    )
    router.load_state_dict(a9_ckpt["model_state_dict"])
    router.eval()

    data_dir = root / config.hierarchical_data_dir
    X_test = np.load(data_dir / "X_test.npy")
    y_bin_test = np.load(data_dir / "y_binary_test.npy").reshape(-1).astype(np.int64)
    y_af_test = np.load(data_dir / "y_attack_family_test.npy").reshape(-1).astype(np.int64)
    m_test = np.load(data_dir / "attack_family_mask_test.npy").reshape(-1).astype(np.int64)

    def _forward(model, X, head):
        outs = []
        with torch.no_grad():
            for start in range(0, X.shape[0], 8192):
                xb = torch.as_tensor(X[start : start + 8192], dtype=torch.float32)
                out = model(xb)
                outs.append(head(out))
        return np.concatenate(outs, axis=0)

    binary_logits = _forward(router, X_test, lambda o: o["binary_logit"].reshape(-1).cpu().numpy())
    binary_router = compute_binary_metrics(y_bin_test, binary_logits, threshold=0.5, from_logits=True)
    router_attack_pred_full = (1.0 / (1.0 + np.exp(-binary_logits)) >= 0.5).astype(np.int64)

    attack_rows = select_attack_rows(y_af_test, m_test)
    X_attack = X_test[attack_rows]
    y_attack = y_af_test[attack_rows]
    spec_logits = _forward(specialist, X_attack, lambda o: o.cpu().numpy())
    spec_pred = spec_logits.argmax(axis=1).astype(np.int64)

    oracle_metrics = compute_oracle_attack_family_metrics(y_attack, spec_pred, config.num_attack_families)
    routed_metrics = compute_routed_attack_family_metrics(
        y_attack, router_attack_pred_full[attack_rows], spec_pred, config.num_attack_families
    )

    y_af_train = np.load(data_dir / "y_attack_family_train.npy").reshape(-1).astype(np.int64)
    m_train = np.load(data_dir / "attack_family_mask_train.npy").reshape(-1).astype(np.int64)
    train_attack = select_attack_rows(y_af_train, m_train)
    weights = _compute_attack_class_weights(y_af_train[train_attack], config.num_attack_families)
    class_weight_snapshot = {
        "attack_family_class_weights_by_name": {
            ATTACK_FAMILY_NAMES[i]: round(float(weights[i]), 6) for i in range(len(weights))
        },
        "method": "sqrt_inverse_frequency_mean_normalized",
        "source_split": "train",
        "computed_from_train_only": True,
        "test_labels_used": False,
        "validation_labels_used": False,
    }
    model_summary = {
        "architecture_metadata": meta,
        "best_val_attack_family_macro_f1": spec_ckpt.get("best_val_attack_family_macro_f1"),
        "selection": spec_ckpt.get("selection"),
        "seed": spec_ckpt.get("seed"),
        "checkpoint": config.outputs["checkpoint"],
        "checkpoint_sha256": checkpoint_sha256,
    }
    screen_gate = compute_screen_gate(
        oracle_metrics["attack_family_macro_f1"],
        oracle_metrics["rare_class"]["rare_class_macro_f1"],
        binary_router_unchanged=True,
        oracle_routed_separation=True,
    )

    written = write_seed_artifacts(
        config,
        oracle_metrics=oracle_metrics,
        routed_metrics=routed_metrics,
        binary_router_metrics=binary_router,
        class_weight_snapshot=class_weight_snapshot,
        model_summary=model_summary,
        training_history_note=(
            "Reconstructed from checkpoint metadata; full per-epoch training history was not "
            "persisted by the original A9.9 seed42 run."
        ),
        screen_gate=screen_gate,
        checkpoint_sha256=checkpoint_sha256,
        project_root=root,
        overwrite=overwrite,
    )
    return {
        "written": written,
        "checkpoint_sha256": checkpoint_sha256,
        "oracle_metrics": oracle_metrics,
        "routed_metrics": routed_metrics,
        "binary_router_metrics": binary_router,
        "screen_gate": screen_gate,
    }
