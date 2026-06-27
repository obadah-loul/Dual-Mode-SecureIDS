import warnings

import numpy as np

from secureids.training.metrics import compute_binary_metrics, sigmoid


def test_sigmoid_extreme_logits_do_not_raise_runtime_warning():
    logits = np.array(
        [-1e6, -1000.0, -100.0, -10.0, 0.0, 10.0, 100.0, 1000.0, 1e6],
        dtype=np.float64,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        probabilities = sigmoid(logits)

    runtime_warnings = [
        warning for warning in caught if issubclass(warning.category, RuntimeWarning)
    ]
    assert runtime_warnings == []
    assert np.all(np.isfinite(probabilities))
    assert np.all(probabilities >= 0.0)
    assert np.all(probabilities <= 1.0)
    assert probabilities[0] == 0.0
    assert probabilities[1] == 0.0
    assert probabilities[2] < 1e-40
    assert probabilities[4] == 0.5
    assert probabilities[6] > 1.0 - 1e-12
    assert probabilities[7] == 1.0
    assert probabilities[8] == 1.0


def test_sigmoid_preserves_nan_model_outputs():
    probabilities = sigmoid(np.array([-1.0, np.nan, 1.0], dtype=np.float64))

    assert np.isfinite(probabilities[0])
    assert np.isnan(probabilities[1])
    assert np.isfinite(probabilities[2])


def test_compute_binary_metrics_still_uses_existing_threshold_logic():
    y_true = np.array([0, 1, 1, 0], dtype=np.int64)
    logits = np.array([-4.0, 4.0, 2.0, -2.0], dtype=np.float64)

    metrics = compute_binary_metrics(y_true, logits, threshold=0.5, from_logits=True)

    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["threshold"] == 0.5
    assert metrics["n_samples"] == 4
    assert metrics["confusion_matrix"] == {
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "tn": 2,
    }
