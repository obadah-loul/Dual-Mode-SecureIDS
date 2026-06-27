"""Trainer and dry-run planning for the A9.10 frozen-embedding specialist."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from secureids.training.frozen_embedding_specialist_config import (
    PROJECT_ROOT,
    FrozenEmbeddingSpecialistConfig,
    FrozenEmbeddingSpecialistConfigError,
    is_final_path,
    load_frozen_embedding_specialist_config,
)

IGNORE_INDEX = -1


class FrozenEmbeddingSpecialistError(RuntimeError):
    """Raised when A9.10 planning/training hits a safety problem."""


class FrozenEmbeddingSpecialistExecutePreconditionError(FrozenEmbeddingSpecialistError):
    """Raised before any approved A9.10 execute run can start."""


def select_attack_rows(
    y_attack_family: Any,
    attack_family_mask: Any,
    ignore_index: int = IGNORE_INDEX,
) -> np.ndarray:
    y = np.asarray(y_attack_family).reshape(-1)
    mask = np.asarray(attack_family_mask).reshape(-1)
    if y.shape[0] != mask.shape[0]:
        raise ValueError("y_attack_family and attack_family_mask must have equal length.")
    return (mask == 1) & (y != int(ignore_index))


def compute_tempered_class_weights(
    labels: Any,
    num_classes: int,
    temperature: float = 0.5,
) -> np.ndarray:
    """Train-only inverse-frequency weights tempered by ``temperature``.

    ``temperature=0`` returns all ones. ``temperature=1`` is full inverse
    frequency. The default 0.5 is sqrt-inverse frequency, mean-normalized over
    classes that appear in train.
    """

    y = np.asarray(labels).reshape(-1).astype(np.int64)
    counts = np.bincount(y, minlength=int(num_classes)).astype(np.float64)
    temp = float(temperature)
    if not 0.0 <= temp <= 1.0:
        raise ValueError("temperature must be in [0.0, 1.0].")
    if temp == 0.0:
        return np.ones(int(num_classes), dtype=np.float64)
    inverse = np.where(counts > 0, 1.0 / counts, 0.0)
    weights = np.power(inverse, temp)
    nonzero = weights[weights > 0]
    mean = float(nonzero.mean()) if nonzero.size else 1.0
    normalized = np.where(weights > 0, weights / mean, 1.0)
    return normalized.astype(np.float64)


def _resolve(config: FrozenEmbeddingSpecialistConfig, rel: str) -> Path:
    return config.resolve(rel)


def build_frozen_embedding_training_plan(
    config: FrozenEmbeddingSpecialistConfig,
) -> dict[str, Any]:
    """Dry-run plan. Validates paths and inputs; loads no arrays and writes nothing."""

    data_dir = _resolve(config, config.hierarchical_data_dir)
    expected_arrays = {
        f"{name}_{split}": data_dir / f"{name}_{split}.npy"
        for split in ("train", "val", "test")
        for name in ("X", "y_attack_family", "attack_family_mask", "y_binary")
    }
    inputs_present = {name: path.exists() for name, path in expected_arrays.items()}
    frozen_checkpoint = _resolve(config, str(config.frozen_a9["checkpoint"]))

    for key, rel in config.outputs.items():
        if is_final_path(rel):
            raise FrozenEmbeddingSpecialistError(
                f"refusing unsafe output path outputs.{key}={rel!r} (final tree)."
            )

    output_exists = {
        key: _resolve(config, rel).exists()
        for key, rel in config.outputs.items()
    }
    result_dir = _resolve(config, config.outputs["result_dir"])

    return {
        "experiment": config.experiment,
        "dataset": config.dataset,
        "task": config.task,
        "seed": config.seed,
        "input_dim": config.input_dim,
        "embedding_dim": config.embedding_dim,
        "num_attack_families": config.num_attack_families,
        "head_type": config.model["head_type"],
        "dropout": float(config.model["dropout"]),
        "weight_decay": float(config.training["weight_decay"]),
        "label_smoothing": float(config.loss.get("label_smoothing", 0.0)),
        "class_weight_temperature": float(config.class_imbalance.get("temperature", 0.5)),
        "attack_rows_only": True,
        "validation_only_selection": True,
        "no_test_tuning": True,
        "frozen_a9_checkpoint": str(config.frozen_a9["checkpoint"]),
        "frozen_a9_checkpoint_present": frozen_checkpoint.exists(),
        "frozen_a9_trainable": False,
        "embedding_source": "A9 forward()['embedding'] after encoder+gate",
        "expected_input_arrays": {name: str(path) for name, path in expected_arrays.items()},
        "expected_input_arrays_present": inputs_present,
        "all_inputs_present": all(inputs_present.values()),
        "planned_outputs": dict(config.outputs),
        "planned_outputs_exist": output_exists,
        "result_dir_exists": result_dir.exists(),
        "would_overwrite_any_output": any(output_exists.values()),
        "training_executed": False,
        "writes_in_dry_run": "none",
    }


def run_frozen_embedding_specialist_training(
    config_path: Path | str,
    execute: bool = False,
    project_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """A9.10 entry point. ``execute=False`` is a no-write dry run."""

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    config = load_frozen_embedding_specialist_config(config_path, project_root=root)
    plan = build_frozen_embedding_training_plan(config)
    if not execute:
        return {
            "executed": False,
            "mode": "dry_run",
            "wrote_checkpoint": False,
            "wrote_results": False,
            "plan": plan,
        }
    return _execute_training(config, plan, overwrite=overwrite)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _execute_training(  # pragma: no cover - not run during A9.10 prep
    config: FrozenEmbeddingSpecialistConfig,
    plan: dict[str, Any],
    overwrite: bool = False,
) -> dict[str, Any]:
    if config.safety.get("training_executed") is not False:
        raise FrozenEmbeddingSpecialistExecutePreconditionError(
            "config.safety.training_executed must be false before an approved run."
        )
    if not plan["all_inputs_present"]:
        raise FrozenEmbeddingSpecialistExecutePreconditionError("required processed arrays are missing.")
    if not plan["frozen_a9_checkpoint_present"]:
        raise FrozenEmbeddingSpecialistExecutePreconditionError("frozen A9 checkpoint is missing.")
    if plan["would_overwrite_any_output"] and not overwrite:
        existing = [key for key, exists in plan["planned_outputs_exist"].items() if exists]
        raise FrozenEmbeddingSpecialistExecutePreconditionError(
            f"planned A9.10 outputs already exist: {existing}; overwrite is refused by default."
        )

    import torch
    from torch import nn

    from secureids.models.frozen_embedding_specialist import (
        FrozenA9EmbeddingExtractor,
        FrozenEmbeddingSpecialistHead,
        extract_fixed_embeddings,
        load_frozen_a9_model,
    )
    from secureids.training.frozen_embedding_specialist_evaluation import (
        assemble_a10_report_bundle,
        compute_oracle_attack_family_metrics,
        compute_routed_attack_family_metrics,
    )
    from secureids.training.frozen_embedding_specialist_artifacts import (
        build_confusion_matrix_rows,
        build_per_class_rows,
        build_rare_class_rows,
        file_sha256,
        render_seed42_report,
    )
    from secureids.training.metrics import compute_binary_metrics

    torch.manual_seed(int(config.seed))
    np.random.seed(int(config.seed))

    data_dir = config.resolve(config.hierarchical_data_dir)
    arrays = {
        split: {
            "X": np.load(data_dir / f"X_{split}.npy"),
            "y_attack_family": np.load(data_dir / f"y_attack_family_{split}.npy").reshape(-1).astype(np.int64),
            "attack_family_mask": np.load(data_dir / f"attack_family_mask_{split}.npy").reshape(-1).astype(np.int64),
            "y_binary": np.load(data_dir / f"y_binary_{split}.npy").reshape(-1).astype(np.int64),
        }
        for split in ("train", "val", "test")
    }
    rows = {
        split: select_attack_rows(bundle["y_attack_family"], bundle["attack_family_mask"])
        for split, bundle in arrays.items()
    }

    a9_model = load_frozen_a9_model(config.resolve(str(config.frozen_a9["checkpoint"])))
    extractor = FrozenA9EmbeddingExtractor(a9_model)

    train_embed = extract_fixed_embeddings(extractor, arrays["train"]["X"][rows["train"]])
    val_embed = extract_fixed_embeddings(extractor, arrays["val"]["X"][rows["val"]])
    test_embed, test_router = extract_fixed_embeddings(
        extractor, arrays["test"]["X"][rows["test"]], return_router=True
    )
    y_train = arrays["train"]["y_attack_family"][rows["train"]]
    y_val = arrays["val"]["y_attack_family"][rows["val"]]
    y_test = arrays["test"]["y_attack_family"][rows["test"]]

    model = FrozenEmbeddingSpecialistHead(
        embedding_dim=config.embedding_dim,
        num_attack_families=config.num_attack_families,
        head_type=str(config.model["head_type"]),
        hidden_dim=int(config.model.get("hidden_dim", 64)),
        dropout=float(config.model["dropout"]),
    )
    weights = compute_tempered_class_weights(
        y_train,
        config.num_attack_families,
        temperature=float(config.class_imbalance.get("temperature", 0.5)),
    )
    criterion = nn.CrossEntropyLoss(
        weight=torch.as_tensor(weights, dtype=torch.float32),
        label_smoothing=float(config.loss.get("label_smoothing", 0.0)),
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config.training.get("learning_rate", 0.001)),
        weight_decay=float(config.training.get("weight_decay", 0.001)),
    )

    Xt = train_embed.float()
    yt = torch.as_tensor(y_train, dtype=torch.long)
    Xv = val_embed.float()
    yv = y_val.astype(np.int64)
    max_epochs = int(config.training.get("max_epochs", 40))
    batch_size = int(config.training.get("batch_size", 1024))
    patience = int(config.training.get("early_stopping_patience", 8))
    best_score = -1.0
    best_state = None
    stale_epochs = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, max_epochs + 1):
        model.train()
        permutation = torch.randperm(Xt.shape[0])
        running_loss = 0.0
        for start in range(0, Xt.shape[0], batch_size):
            idx = permutation[start : start + batch_size]
            optimizer.zero_grad()
            loss = criterion(model(Xt[idx]), yt[idx])
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * int(idx.numel())

        model.eval()
        with torch.no_grad():
            val_pred = model(Xv).argmax(dim=1).cpu().numpy().astype(np.int64)
            train_pred = model(Xt).argmax(dim=1).cpu().numpy().astype(np.int64)
        val_metrics = compute_oracle_attack_family_metrics(yv, val_pred, config.num_attack_families)
        train_metrics = compute_oracle_attack_family_metrics(y_train, train_pred, config.num_attack_families)
        val_f1 = float(val_metrics["attack_family_macro_f1"])
        train_f1 = float(train_metrics["attack_family_macro_f1"])
        gap = max(0.0, train_f1 - val_f1)
        score = val_f1 - float(config.checkpoint_selection.get("train_val_gap_penalty", 0.25)) * gap
        history.append(
            {
                "epoch": epoch,
                "train_loss": running_loss / max(1, Xt.shape[0]),
                "train_attack_family_macro_f1": train_f1,
                "val_attack_family_macro_f1": val_f1,
                "train_val_gap": gap,
                "selection_score": score,
            }
        )
        if score > best_score:
            best_score = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= patience:
            break

    model.load_state_dict(best_state or model.state_dict())
    model.eval()
    with torch.no_grad():
        test_pred = model(test_embed.float()).argmax(dim=1).cpu().numpy().astype(np.int64)
        full_test_logits = []
        for start in range(0, arrays["test"]["X"].shape[0], 8192):
            batch = torch.as_tensor(arrays["test"]["X"][start : start + 8192], dtype=torch.float32)
            output = a9_model(batch)
            full_test_logits.append(output["binary_logit"].reshape(-1).cpu().numpy())
        binary_logits = np.concatenate(full_test_logits, axis=0)

    binary_metrics = compute_binary_metrics(
        arrays["test"]["y_binary"], binary_logits, threshold=0.5, from_logits=True
    )
    oracle_metrics = compute_oracle_attack_family_metrics(y_test, test_pred, config.num_attack_families)
    routed_metrics = compute_routed_attack_family_metrics(
        y_test, test_router.numpy(), test_pred, config.num_attack_families
    )
    report_bundle = assemble_a10_report_bundle(binary_metrics, oracle_metrics, routed_metrics)

    checkpoint_path = config.resolve(config.outputs["checkpoint"])
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "architecture_metadata": model.architecture_metadata,
            "frozen_a9_checkpoint": config.frozen_a9["checkpoint"],
            "frozen_a9_identity": config.frozen_a9["identity"],
            "selection": "validation_only_generalization_aware",
            "best_val_generalization_score": best_score,
            "seed": int(config.seed),
            "experiment": config.experiment,
            "safety": {
                "a9_frozen": True,
                "test_set_used_for_tuning": False,
                "final_checkpoint": False,
            },
        },
        checkpoint_path,
    )

    result_dir = config.resolve(config.outputs["result_dir"])
    result_dir.mkdir(parents=True, exist_ok=True)
    _write_json(config.resolve(config.outputs["oracle_metrics_json"]), oracle_metrics)
    _write_json(config.resolve(config.outputs["routed_metrics_json"]), routed_metrics)
    _write_json(config.resolve(config.outputs["routing_summary_json"]), report_bundle)
    _write_json(
        config.resolve(config.outputs["class_weight_snapshot_json"]),
        {"computed_from": "train_attack_rows_only", "temperature": float(config.class_imbalance.get("temperature", 0.5)), "weights": weights.tolist()},
    )
    _write_json(config.resolve(config.outputs["model_summary_json"]), {"architecture_metadata": model.architecture_metadata, "best_score": best_score})
    _write_json(config.resolve(config.outputs["manifest_json"]), {"experiment": config.experiment, "selection": "validation_only", "checkpoint": config.outputs["checkpoint"], "test_tuning": False})

    _write_csv(
        config.resolve(config.outputs["training_history_csv"]),
        history,
        ["epoch", "train_loss", "train_attack_family_macro_f1", "val_attack_family_macro_f1", "train_val_gap", "selection_score"],
    )
    per_class_rows = build_per_class_rows("oracle", oracle_metrics) + build_per_class_rows(
        "routed", routed_metrics
    )
    _write_csv(
        config.resolve(config.outputs["per_class_attack_metrics_csv"]),
        per_class_rows,
        ["view", "class_id", "class_name", "precision", "recall", "f1", "support"],
    )
    rare_rows = build_rare_class_rows("oracle", oracle_metrics) + build_rare_class_rows(
        "routed", routed_metrics
    )
    _write_csv(
        config.resolve(config.outputs["rare_class_metrics_csv"]),
        rare_rows,
        ["view", "class_name", "present", "precision", "recall", "f1", "support"],
    )
    cm_fields, cm_rows = build_confusion_matrix_rows(oracle_metrics)
    _write_csv(
        config.resolve(config.outputs["attack_family_confusion_matrix_csv"]),
        cm_rows,
        cm_fields,
    )
    config.resolve(config.outputs["training_config_snapshot_yaml"]).write_text(
        config.path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    config.resolve(config.outputs["report_md"]).write_text(
        render_seed42_report(
            oracle=oracle_metrics,
            routed=routed_metrics,
            a10_sha256=file_sha256(config.resolve(config.outputs["checkpoint"])),
            a9_sha256=file_sha256(config.resolve(str(config.frozen_a9["checkpoint"]))),
        ),
        encoding="utf-8",
    )

    return {
        "executed": True,
        "mode": "train_frozen_embedding_head_validation_only",
        "wrote_checkpoint": True,
        "checkpoint": str(checkpoint_path),
        "best_val_generalization_score": best_score,
        "oracle_attack_family_macro_f1": oracle_metrics["attack_family_macro_f1"],
        "routed_attack_family_macro_f1": routed_metrics["routed_attack_family_macro_f1"],
    }
