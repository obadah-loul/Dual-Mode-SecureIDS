"""Trainer scaffolding for the UNSW A9.9 attack-family specialist.

Safety contract for this build phase:
* ``run_attack_family_specialist_training(..., execute=False)`` performs a
  torch-free DRY RUN: it validates the config, checks output-path safety, and
  returns a plan. It loads no arrays, trains nothing, and writes nothing.
* ``execute=True`` would run the real attack-only training; it is implemented
  with a lazy torch import and is NOT invoked anywhere in the A9.9 build phase.
* Checkpoints are only ever written under ``models/experiments/`` and results
  under ``results/experiments/``. Existing checkpoints are never overwritten
  unless ``overwrite=True`` (which must not be used without main-control
  approval). No final model/result is read for tuning or ever written.
"""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly

from pathlib import Path
from typing import Any

import numpy as np

from secureids.training.attack_family_specialist_config import (
    PROJECT_ROOT,
    AttackFamilySpecialistConfig,
    AttackFamilySpecialistConfigError,
    is_final_path,
    load_attack_family_specialist_config,
)

IGNORE_INDEX = -1


class AttackFamilySpecialistError(RuntimeError):
    """Raised when a specialist run hits a safety/precondition problem."""


class AttackFamilySpecialistExecutePreconditionError(AttackFamilySpecialistError):
    """Raised when an ``execute=True`` run fails a safety precondition."""


def select_attack_rows(
    y_attack_family: Any,
    attack_family_mask: Any,
    ignore_index: int = IGNORE_INDEX,
) -> np.ndarray:
    """Return a boolean mask of attack rows (mask==1 AND label != ignore_index).

    Torch-free and file-free. This is the single source of truth for "attack
    rows only" training-data selection, so benign rows are never used to train
    the specialist.
    """

    y = np.asarray(y_attack_family).reshape(-1)
    mask = np.asarray(attack_family_mask).reshape(-1)
    if y.shape[0] != mask.shape[0]:
        raise ValueError("y_attack_family and attack_family_mask must have equal length.")
    return (mask == 1) & (y != int(ignore_index))


def _resolve(config: AttackFamilySpecialistConfig, rel: str) -> Path:
    return config.resolve(rel)


def build_specialist_training_plan(
    config: AttackFamilySpecialistConfig,
) -> dict[str, Any]:
    """Torch-free dry-run plan. Validates paths/inputs; loads & writes nothing."""

    data_dir = _resolve(config, config.hierarchical_data_dir)
    expected_arrays = {
        "X_train": data_dir / "X_train.npy",
        "y_attack_family_train": data_dir / "y_attack_family_train.npy",
        "attack_family_mask_train": data_dir / "attack_family_mask_train.npy",
        "X_val": data_dir / "X_val.npy",
        "y_attack_family_val": data_dir / "y_attack_family_val.npy",
        "attack_family_mask_val": data_dir / "attack_family_mask_val.npy",
    }
    inputs_present = {name: path.exists() for name, path in expected_arrays.items()}

    router_ckpt = _resolve(config, str(config.frozen_a9_router["checkpoint"]))

    # Re-assert output safety (defensive; config loader already validated).
    for key, rel in config.outputs.items():
        if is_final_path(rel):
            raise AttackFamilySpecialistError(
                f"refusing unsafe output path outputs.{key}={rel!r} (final tree)."
            )

    checkpoint_rel = config.outputs["checkpoint"]
    checkpoint_exists = _resolve(config, checkpoint_rel).exists()

    return {
        "experiment": config.experiment,
        "dataset": config.dataset,
        "task": config.task,
        "seed": config.seed,
        "input_dim": config.input_dim,
        "num_attack_families": config.num_attack_families,
        "attack_rows_only": True,
        "validation_only_selection": True,
        "no_test_tuning": True,
        "frozen_a9_router_checkpoint": str(config.frozen_a9_router["checkpoint"]),
        "frozen_a9_router_present": router_ckpt.exists(),
        "frozen_a9_router_trainable": False,
        "expected_input_arrays": {name: str(path) for name, path in expected_arrays.items()},
        "expected_input_arrays_present": inputs_present,
        "all_inputs_present": all(inputs_present.values()),
        "planned_outputs": dict(config.outputs),
        "checkpoint_already_exists": checkpoint_exists,
        "would_overwrite_checkpoint": False,
        "training_executed": False,
        "writes_in_dry_run": "none",
    }


def run_attack_family_specialist_training(
    config_path: Path | str,
    execute: bool = False,
    project_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Entry point. ``execute=False`` is a torch-free dry run (default).

    The A9.9 build phase only ever calls this with ``execute=False``.
    """

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    config = load_attack_family_specialist_config(config_path, project_root=root)
    plan = build_specialist_training_plan(config)

    if not execute:
        return {
            "executed": False,
            "mode": "dry_run",
            "wrote_checkpoint": False,
            "wrote_results": False,
            "plan": plan,
        }

    # execute=True path: real training. Implemented with a lazy torch import and
    # NOT invoked during the A9.9 build phase. Requires explicit approval to run.
    return _execute_training(config, plan, overwrite=overwrite)


def _compute_attack_class_weights(labels: np.ndarray, num_classes: int) -> np.ndarray:
    """sqrt-inverse-frequency, mean-normalized weights from TRAIN labels only."""

    counts = np.bincount(labels.astype(np.int64), minlength=int(num_classes)).astype(np.float64)
    inverse = np.where(counts > 0, 1.0 / counts, 0.0)
    sqrt_inverse = np.sqrt(inverse)
    nonzero = sqrt_inverse[sqrt_inverse > 0]
    mean = float(nonzero.mean()) if nonzero.size else 1.0
    normalized = np.where(sqrt_inverse > 0, sqrt_inverse / mean, 1.0)
    return normalized.astype(np.float64)


def _execute_training(  # pragma: no cover - never run in the A9.9 build phase
    config: AttackFamilySpecialistConfig,
    plan: dict[str, Any],
    overwrite: bool = False,
) -> dict[str, Any]:
    """Real attack-only training. Lazy torch. Not invoked in this build phase."""

    if config.safety.get("training_executed") is not False:
        raise AttackFamilySpecialistExecutePreconditionError(
            "config.safety.training_executed must be false before an approved run flips it."
        )
    if not plan["all_inputs_present"]:
        raise AttackFamilySpecialistExecutePreconditionError(
            "required processed UNSW attack-family arrays are missing."
        )
    if not plan["frozen_a9_router_present"]:
        raise AttackFamilySpecialistExecutePreconditionError(
            "frozen A9 router checkpoint is missing; routing cannot be evaluated."
        )

    checkpoint_path = config.resolve(config.outputs["checkpoint"])
    if is_final_path(config.outputs["checkpoint"]):
        raise AttackFamilySpecialistExecutePreconditionError("refusing to write into the final tree.")
    if checkpoint_path.exists() and not overwrite:
        raise AttackFamilySpecialistExecutePreconditionError(
            f"checkpoint already exists: {checkpoint_path} (pass overwrite=True only after approval)."
        )

    import torch  # lazy
    from torch import nn

    from secureids.models.attack_family_specialist import AttackFamilySpecialistNet

    data_dir = config.resolve(config.hierarchical_data_dir)
    seed = int(config.seed)
    torch.manual_seed(seed)
    np.random.seed(seed)

    X_train = load_numpy_readonly(data_dir / "X_train.npy")
    y_train = load_numpy_readonly(data_dir / "y_attack_family_train.npy")
    m_train = load_numpy_readonly(data_dir / "attack_family_mask_train.npy")
    X_val = load_numpy_readonly(data_dir / "X_val.npy")
    y_val = load_numpy_readonly(data_dir / "y_attack_family_val.npy")
    m_val = load_numpy_readonly(data_dir / "attack_family_mask_val.npy")

    train_rows = select_attack_rows(y_train, m_train)
    val_rows = select_attack_rows(y_val, m_val)
    Xt = torch.as_tensor(X_train[train_rows], dtype=torch.float32)
    yt = torch.as_tensor(y_train[train_rows].astype(np.int64), dtype=torch.long)
    Xv = torch.as_tensor(X_val[val_rows], dtype=torch.float32)
    yv = y_val[val_rows].astype(np.int64)

    weights = _compute_attack_class_weights(y_train[train_rows], config.num_attack_families)
    weight_tensor = torch.as_tensor(weights, dtype=torch.float32)

    model_cfg = config.model
    model = AttackFamilySpecialistNet(
        input_dim=config.input_dim,
        num_attack_families=config.num_attack_families,
        hidden_dims=model_cfg.get("hidden_dims"),
        dropout=float(model_cfg.get("dropout", 0.2)),
        normalization=str(model_cfg.get("normalization", "layernorm")),
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config.raw.get("training", {}).get("learning_rate", 1e-3)),
        weight_decay=float(config.raw.get("training", {}).get("weight_decay", 1e-4)),
    )
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)

    from secureids.training.attack_family_specialist_evaluation import (
        compute_oracle_attack_family_metrics,
    )

    max_epochs = int(config.raw.get("training", {}).get("max_epochs", 40))
    batch_size = int(config.raw.get("training", {}).get("batch_size", 1024))
    best_score = -1.0
    best_state = None
    for _epoch in range(max_epochs):
        model.train()
        perm = torch.randperm(Xt.shape[0])
        for start in range(0, Xt.shape[0], batch_size):
            idx = perm[start : start + batch_size]
            optimizer.zero_grad()
            loss = criterion(model(Xt[idx]), yt[idx])
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            val_pred = model(Xv).argmax(dim=1).cpu().numpy()
        val_metrics = compute_oracle_attack_family_metrics(yv, val_pred, config.num_attack_families)
        score = float(val_metrics["attack_family_macro_f1"])  # validation-only selection
        if score > best_score:
            best_score = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": best_state,
            "architecture_metadata": model.architecture_metadata,
            "best_val_attack_family_macro_f1": best_score,
            "seed": seed,
            "selection": "validation_only_attack_family_macro_f1",
            "experiment": config.experiment,
        },
        checkpoint_path,
    )

    # Post-training artifact writer: evaluate the test split ONCE (reporting only;
    # selection above was validation-only) and write the full result_dir + report.
    # This guarantees an --execute run never leaves only a bare checkpoint behind.
    from secureids.training.attack_family_specialist_artifacts import generate_seed_artifacts

    artifacts = generate_seed_artifacts(
        config.path, project_root=config.project_root, checkpoint_path=config.outputs["checkpoint"]
    )
    return {
        "executed": True,
        "mode": "train_validation_only_then_write_artifacts",
        "wrote_checkpoint": True,
        "checkpoint": str(checkpoint_path),
        "best_val_attack_family_macro_f1": best_score,
        "wrote_artifacts": True,
        "artifacts": artifacts["written"],
        "note": "Test evaluated once after validation-only selection, for reporting only.",
    }
