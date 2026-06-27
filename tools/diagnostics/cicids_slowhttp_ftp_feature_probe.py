"""Bounded, train/validation-only feature-separability diagnostic for the
CICIDS hierarchical DoS-SlowHTTPTest (id 4) vs FTP-BruteForce (id 8) confusion pair.

EXP04 (cicids_hierarchical_exp04_feature_confusion_diagnostic) — DIAGNOSTIC ONLY.

What this does (and does NOT do):
  * Reads the existing processed hierarchical arrays via numpy mmap and selects
    ONLY the rows of the two classes, with a configurable per-class cap.
  * Computes per-feature class means/stds and the standardized mean difference
    (SMD) between the two classes, plus a small linear-separability probe
    (logistic regression) trained on a TRAIN-split sample and evaluated on a
    held-out VAL-split sample.
  * Writes a per-feature CSV and a summary JSON under results/audits/.
  * It does NOT train the main model, does NOT create checkpoints, does NOT
    touch the test split, and does NOT tune anything on test.

The probe is a *separability indicator*, not a model. High held-out (val)
balanced accuracy => the two classes ARE distinguishable in the current 77-D
feature space (so the residual model confusion is model/loss-limited). Low
val balanced accuracy => the classes overlap in this feature space
(feature-limited; only feature engineering / a new preprocessing protocol
can help).

Manual run (PowerShell):
  Set-Location C:\\IDS\\IDS_V2\\Secure-Distributed-Intrusion-Detection_V2
  .\\.venv\\Scripts\\python.exe tools\\diagnostics\\cicids_slowhttp_ftp_feature_probe.py `
    --per-class-cap 20000 --seed 42 --run-probe
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "cicids2018" / "hierarchical"
OUT_DIR = PROJECT_ROOT / "results" / "audits"

CLASS_A_ID = 4  # DoS-SlowHTTPTest
CLASS_A_NAME = "DoS-SlowHTTPTest"
CLASS_B_ID = 8  # FTP-BruteForce
CLASS_B_NAME = "FTP-BruteForce"


def _load_feature_names() -> list[str]:
    with open(DATA_DIR / "feature_names.json", encoding="utf-8") as handle:
        return list(json.load(handle)["feature_names"])


def _sample_class_rows(
    y: np.ndarray, class_id: int, cap: int, rng: np.random.Generator
) -> np.ndarray:
    idx = np.flatnonzero(y == class_id)
    if cap > 0 and idx.size > cap:
        idx = rng.choice(idx, size=cap, replace=False)
    return np.sort(idx)  # sorted => efficient mmap reads


def _gather(split: str, cap: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    y = np.load(DATA_DIR / f"y_attack_family_{split}.npy")  # int64 vector (small)
    a_idx = _sample_class_rows(y, CLASS_A_ID, cap, rng)
    b_idx = _sample_class_rows(y, CLASS_B_ID, cap, rng)
    X = np.load(DATA_DIR / f"X_{split}.npy", mmap_mode="r")  # do NOT load fully
    Xa = np.asarray(X[a_idx], dtype=np.float64)
    Xb = np.asarray(X[b_idx], dtype=np.float64)
    return Xa, Xb


def _standardized_mean_difference(Xa: np.ndarray, Xb: np.ndarray) -> dict:
    mean_a = Xa.mean(axis=0)
    mean_b = Xb.mean(axis=0)
    std_a = Xa.std(axis=0, ddof=1)
    std_b = Xb.std(axis=0, ddof=1)
    pooled = np.sqrt((std_a**2 + std_b**2) / 2.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        smd = np.where(pooled > 0, (mean_a - mean_b) / pooled, 0.0)
    return {
        "mean_a": mean_a,
        "mean_b": mean_b,
        "std_a": std_a,
        "std_b": std_b,
        "smd": smd,
        "abs_smd": np.abs(smd),
    }


def _run_probe(
    Xtr_a: np.ndarray,
    Xtr_b: np.ndarray,
    Xva_a: np.ndarray,
    Xva_b: np.ndarray,
) -> dict | None:
    try:
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:  # pragma: no cover
        return {"available": False, "reason": f"sklearn unavailable: {exc!r}"}

    Xtr = np.vstack([Xtr_a, Xtr_b])
    ytr = np.concatenate([np.zeros(len(Xtr_a)), np.ones(len(Xtr_b))])
    Xva = np.vstack([Xva_a, Xva_b])
    yva = np.concatenate([np.zeros(len(Xva_a)), np.ones(len(Xva_b))])

    # Standardize using TRAIN statistics only; apply to VAL. Test never touched.
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd[sd == 0] = 1.0
    Xtr_s = np.nan_to_num((Xtr - mu) / sd, nan=0.0, posinf=0.0, neginf=0.0)
    Xva_s = np.nan_to_num((Xva - mu) / sd, nan=0.0, posinf=0.0, neginf=0.0)

    clf = LogisticRegression(max_iter=300, C=1.0, class_weight="balanced")
    clf.fit(Xtr_s, ytr)

    def _metrics(X, y):
        pred = clf.predict(X)
        acc = float((pred == y).mean())
        rec_a = float((pred[y == 0] == 0).mean())  # SlowHTTPTest recall
        rec_b = float((pred[y == 1] == 1).mean())  # FTP recall
        return {
            "accuracy": round(acc, 6),
            "recall_slowhttptest": round(rec_a, 6),
            "recall_ftp_bruteforce": round(rec_b, 6),
            "balanced_accuracy": round((rec_a + rec_b) / 2.0, 6),
        }

    return {
        "available": True,
        "probe_type": "logistic_regression_linear_balanced",
        "train_fit_split": "train",
        "eval_split": "val_held_out",
        "train_metrics": _metrics(Xtr_s, ytr),
        "val_metrics": _metrics(Xva_s, yva),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-class-cap", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-probe", action="store_true")
    parser.add_argument("--top-k", type=int, default=15)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_names = _load_feature_names()
    rng = np.random.default_rng(args.seed)

    Xtr_a, Xtr_b = _gather("train", args.per_class_cap, rng)
    smd = _standardized_mean_difference(Xtr_a, Xtr_b)

    # Per-feature CSV
    csv_path = OUT_DIR / "cicids_hierarchical_exp04_slowhttp_ftp_feature_diagnostics.csv"
    order = np.argsort(-smd["abs_smd"])
    lines = [
        "feature_name,mean_slowhttptest,mean_ftp_bruteforce,std_slowhttptest,"
        "std_ftp_bruteforce,standardized_mean_difference,absolute_standardized_difference,"
        "diagnostic_split,comment"
    ]
    for i in order:
        comment = "strong_separator" if smd["abs_smd"][i] >= 0.8 else (
            "moderate" if smd["abs_smd"][i] >= 0.2 else "weak_overlap")
        lines.append(
            f"{feature_names[i].replace(',', ' ')},{smd['mean_a'][i]:.6f},"
            f"{smd['mean_b'][i]:.6f},{smd['std_a'][i]:.6f},{smd['std_b'][i]:.6f},"
            f"{smd['smd'][i]:.6f},{smd['abs_smd'][i]:.6f},train,{comment}"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    probe = None
    if args.run_probe:
        Xva_a, Xva_b = _gather("val", args.per_class_cap, rng)
        probe = _run_probe(Xtr_a, Xtr_b, Xva_a, Xva_b)

    abs_smd = smd["abs_smd"]
    summary = {
        "diagnostic": "cicids_slowhttp_ftp_feature_probe",
        "note": "DIAGNOSTIC ONLY — not training metrics; train/val only; test untouched.",
        "classes": {"A": CLASS_A_NAME, "B": CLASS_B_NAME},
        "per_class_cap": args.per_class_cap,
        "seed": args.seed,
        "train_sample_sizes": {CLASS_A_NAME: int(len(Xtr_a)), CLASS_B_NAME: int(len(Xtr_b))},
        "n_features": len(feature_names),
        "smd_summary": {
            "n_strong_separators_abs_smd_ge_0p8": int((abs_smd >= 0.8).sum()),
            "n_moderate_0p2_to_0p8": int(((abs_smd >= 0.2) & (abs_smd < 0.8)).sum()),
            "n_weak_lt_0p2": int((abs_smd < 0.2).sum()),
            "max_abs_smd": round(float(abs_smd.max()), 6),
            "top_features": [
                {"feature": feature_names[int(i)], "abs_smd": round(float(abs_smd[int(i)]), 6)}
                for i in order[: args.top_k]
            ],
        },
        "linear_probe": probe,
        "feature_diagnostics_csv": str(csv_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }
    json_path = OUT_DIR / "cicids_hierarchical_exp04_slowhttp_ftp_probe.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Wrote", csv_path.relative_to(PROJECT_ROOT))
    print("Wrote", json_path.relative_to(PROJECT_ROOT))
    print(json.dumps(summary["smd_summary"], indent=2))
    if probe:
        print("PROBE:", json.dumps(probe.get("val_metrics", probe), indent=2))


if __name__ == "__main__":
    main()
