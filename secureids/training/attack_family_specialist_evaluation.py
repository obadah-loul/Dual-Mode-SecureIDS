"""Evaluation scaffolding for the UNSW A9.9 attack-family specialist.

Two metric VIEWS are produced and must always be reported separately:

* ``oracle``  - specialist on the TRUE attack rows (teacher-forced, perfect
  routing). Apples-to-apples with A9 attack-family macro-F1 (0.500429).
* ``routed``  - the frozen A9 Head 1 decides attack vs benign first; only rows
  the router calls "attack" reach the specialist. Rows the router calls benign
  are ``attack_missed_as_benign`` and count as errors. This is the deployment
  view and is bounded by A9 Head 1 recall.

The pure metric-assembly functions are NumPy-only and file-free so they are easy
to unit test. The torch prediction helpers are imported lazily and are NOT run
in the A9.9 build phase. Nothing here writes files or trains.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from secureids.training.attack_family_specialist_config import (
    ATTACK_FAMILY_NAMES,
    RARE_CLASSES,
)
from secureids.training.hierarchical_metrics import (
    multiclass_classification_report,
    rare_class_macro_f1,
)

ORACLE_VIEW = "oracle"
ROUTED_VIEW = "routed"


def _names(num_classes: int, class_names: list[str] | None) -> list[str]:
    if class_names is not None:
        return [str(name) for name in class_names]
    if int(num_classes) == len(ATTACK_FAMILY_NAMES):
        return list(ATTACK_FAMILY_NAMES)
    return [f"class_{i}" for i in range(int(num_classes))]


def compute_oracle_attack_family_metrics(
    y_true_attack: Any,
    y_pred_attack: Any,
    num_classes: int = len(ATTACK_FAMILY_NAMES),
    class_names: list[str] | None = None,
    rare_class_names: list[str] | None = None,
) -> dict[str, Any]:
    """Oracle view: specialist predictions on the TRUE attack rows.

    Macro-F1 is over the FULL fixed class set, so collapsed/never-predicted
    families (e.g. Analysis, Backdoor) keep scoring 0 and remain visible.
    """

    names = _names(num_classes, class_names)
    rare = list(rare_class_names) if rare_class_names is not None else list(RARE_CLASSES)
    report = multiclass_classification_report(
        y_true_attack, y_pred_attack, int(num_classes), class_names=names
    )
    rare_block = rare_class_macro_f1(report, rare)
    return {
        "view": ORACLE_VIEW,
        "is_oracle": True,
        "is_routed_deployment_metric": False,
        "note": "Teacher-forced on true attack rows; assumes perfect routing. NOT a deployment metric.",
        "attack_rows_evaluated": int(report["n_samples"]),
        "attack_family_accuracy": report["accuracy"],
        "attack_family_macro_f1": report["macro_f1"],
        "per_class": report["per_class"],
        "confusion_matrix": report["confusion_matrix"],
        "class_names": report["class_names"],
        "rare_class": rare_block,
    }


def compute_routed_attack_family_metrics(
    y_true_attack: Any,
    router_calls_attack: Any,
    specialist_pred_attack: Any,
    num_classes: int = len(ATTACK_FAMILY_NAMES),
    class_names: list[str] | None = None,
    rare_class_names: list[str] | None = None,
) -> dict[str, Any]:
    """Routed end-to-end view over the true attack rows.

    Parameters
    ----------
    y_true_attack:
        True attack-family ids for the attack rows (length ``N_attack``).
    router_calls_attack:
        Frozen A9 Head 1 decision per attack row: 1 = routed to specialist,
        0 = missed as benign (Head 1 false negative).
    specialist_pred_attack:
        Specialist family prediction per attack row (only meaningful where the
        router said attack; ignored where the router said benign).

    A row is ``correctly_attributed`` only if the router routed it AND the
    specialist family is correct. Missed rows count as false negatives for
    their true family. Attribution accuracy is bounded by router recall;
    macro-F1 has no universal ordering against the oracle view.
    """

    yt = np.asarray(y_true_attack).reshape(-1)
    routed = np.asarray(router_calls_attack).reshape(-1)
    sp = np.asarray(specialist_pred_attack).reshape(-1)
    if not (yt.shape[0] == routed.shape[0] == sp.shape[0]):
        raise ValueError("routed metric arrays must have the same length.")
    if not np.isin(routed, [0, 1]).all():
        raise ValueError('Router decisions must be binary.')
    if not np.isin(yt, np.arange(num_classes)).all() or not np.isin(sp[routed == 1], np.arange(num_classes)).all():
        raise ValueError('Family labels must belong to the fixed taxonomy.')

    names = _names(num_classes, class_names)
    rare = list(rare_class_names) if rare_class_names is not None else list(RARE_CLASSES)

    attack_total = int(yt.shape[0])
    routed_mask = routed == 1
    missed_as_benign = int(np.sum(~routed_mask))

    # Effective routed prediction: -1 (no family) where the router missed it.
    effective_pred = np.where(routed_mask, sp, -1).astype(np.int64)
    correctly_attributed = int(np.sum(routed_mask & (effective_pred == yt)))
    wrong_family = int(np.sum(routed_mask & (effective_pred != yt)))

    # Include an explicit missed column. The old confusion primitive discarded
    # -1 predictions entirely, omitting those false negatives from recall.
    report = multiclass_classification_report(
        yt, np.where(routed_mask, sp, num_classes), int(num_classes) + 1,
        class_names=names + ['Missed-as-benign'])
    report['per_class'] = report['per_class'][:num_classes]
    report['macro_f1'] = float(np.mean([p['f1'] for p in report['per_class']]))
    rare_block = rare_class_macro_f1(report, rare)

    return {
        "view": ROUTED_VIEW,
        "is_oracle": False,
        "is_routed_deployment_metric": True,
        "note": "Frozen A9 Head 1 routes attacks into the specialist; bounded by Head 1 recall.",
        "attack_total": attack_total,
        "attack_detected_and_correctly_attributed": correctly_attributed,
        "attack_detected_and_correctly_attributed_rate": (
            correctly_attributed / attack_total if attack_total else 0.0
        ),
        "attack_detected_wrong_family": wrong_family,
        "attack_missed_as_benign": missed_as_benign,
        "attack_missed_as_benign_rate": (missed_as_benign / attack_total if attack_total else 0.0),
        "routed_attack_family_macro_f1": report["macro_f1"],
        "per_class": report["per_class"],
        "confusion_matrix": report["confusion_matrix"],
        "class_names": report["class_names"],
        "rare_class": rare_block,
    }


def assemble_specialist_report(
    a9_binary_head1_metrics: dict[str, Any],
    oracle_metrics: dict[str, Any],
    routed_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Bundle the three metric blocks with explicit separation guarantees.

    Raises if the oracle/routed views are mislabeled, so oracle numbers can
    never be silently reported as routed deployment numbers.
    """

    if oracle_metrics.get("view") != ORACLE_VIEW or oracle_metrics.get("is_oracle") is not True:
        raise ValueError("oracle_metrics must be the oracle view.")
    if routed_metrics.get("view") != ROUTED_VIEW or routed_metrics.get("is_routed_deployment_metric") is not True:
        raise ValueError("routed_metrics must be the routed deployment view.")

    return {
        "metric_views_are_separated": True,
        "do_not_report_oracle_as_routed": True,
        "weak_classes_must_remain_visible": list(
            ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms")
        ),
        "a9_binary_head1": dict(a9_binary_head1_metrics),
        "specialist_oracle_attack_family": dict(oracle_metrics),
        "routed_end_to_end": dict(routed_metrics),
    }


# --------------------------------------------------------------------------- #
# Torch prediction helpers (lazy import). NOT executed in the A9.9 build phase.
# These will be used later, only after a manual, main-control-approved run.
# --------------------------------------------------------------------------- #
def predict_specialist_logits(model: Any, features: Any) -> "np.ndarray":  # pragma: no cover
    """Return specialist family predictions for ``features`` (eval mode)."""

    import torch  # lazy

    model.eval()
    with torch.no_grad():
        x = torch.as_tensor(np.asarray(features), dtype=torch.float32)
        logits = model(x)
        return logits.argmax(dim=1).cpu().numpy().astype(np.int64)


def route_with_frozen_a9_head1(a9_model: Any, features: Any, threshold: float = 0.5) -> "np.ndarray":  # pragma: no cover
    """Return frozen A9 Head 1 attack/benign decisions (1=attack) for ``features``."""

    import torch  # lazy

    a9_model.eval()
    with torch.no_grad():
        x = torch.as_tensor(np.asarray(features), dtype=torch.float32)
        out = a9_model(x)
        binary_logit = out["binary_logit"] if isinstance(out, dict) else out
        probs = torch.sigmoid(binary_logit.reshape(-1))
        return (probs >= float(threshold)).cpu().numpy().astype(np.int64)
