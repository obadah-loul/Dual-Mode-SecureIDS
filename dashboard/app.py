"""Streamlit live demonstration dashboard for SecureIDS V2."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secureids.inference.live_demo import (  # noqa: E402
    get_dataset_shape,
    get_dataset_spec,
    get_scenario_choices,
    get_scenario_spec,
    load_phase_a_matrix_rows,
    run_live_inference,
    short_hash,
)
from secureids.xai.local_attribution import format_attribution_rows  # noqa: E402


st.set_page_config(
    page_title="Dual-Mode SecureIDS Research Replay",
    layout="wide",
)

st.title("Dual-Mode SecureIDS Research Replay")
st.caption(
    "Research prototype: genuine pretrained inference on saved processed benchmark rows."
)

st.info(
    "Safety mode: this dashboard performs live one-sample inference only. It does "
    "not run training, preprocessing, full evaluation, federated experiments, or "
    "attack/defense experiments."
)

st.markdown(
    """
**Demonstration Flow**
1. Deployment Mode
2. Attack Scenario Playback
3. Automatic Model Routing
4. Run IDS Replay
5. Detection Result
6. Attack Family Classification
7. Explainability
8. SHA-256 Fingerprints
9. Federated Robustness Evidence
"""
)


@st.cache_data(show_spinner=False)
def cached_dataset_shape(dataset_name: str) -> dict[str, int]:
    return get_dataset_shape(dataset_name)


@st.cache_data(show_spinner=False)
def cached_phase_a_rows() -> list[dict[str, str]]:
    return load_phase_a_matrix_rows()


def format_probability(value: float | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:.4f}"


def status_text(value: bool | None) -> str:
    if value is None:
        return "Not available"
    return "Correct" if value else "Mismatch"


st.subheader("Deployment Mode")
deployment_mode = st.radio(
    "Deployment mode",
    (
        "Centralized reference framing",
        "Simulated federated framing",
    ),
    index=1,
)

if deployment_mode.startswith("Centralized"):
    st.info(
        "Centralized results are historical benchmark references. This descriptive "
        "mode selector does not change the checkpoint: replay uses the selected "
        "hierarchical federated model."
    )
else:
    st.success(
        "Federated experiments were single-process simulations with centrally "
        "available arrays. Replay uses their selected checkpoints; no distributed "
        "clients, raw-data secrecy, secure aggregation, or TLS is demonstrated."
    )

st.subheader("Attack Scenario Playback")
scenario_name = st.radio(
    "Select a saved benchmark attack traffic scenario",
    get_scenario_choices(),
    index=0,
)
scenario = get_scenario_spec(scenario_name)
dataset_name = scenario.dataset_name
dataset_spec = get_dataset_spec(dataset_name)
try:
    shape = cached_dataset_shape(dataset_name)
except (FileNotFoundError, ValueError, OSError) as error:
    st.error(f'Demo artifacts unavailable or incompatible: {error}')
    st.info('Restore the documented artifact bundle before running detection.')
    st.stop()
model_checkpoint = dataset_spec.checkpoint_path.relative_to(PROJECT_ROOT).as_posix()
processed_data_path = dataset_spec.data_dir.relative_to(PROJECT_ROOT).as_posix()

st.caption(
    "The dashboard replays one processed benchmark traffic record and routes it "
    "to the matching IDS model using known scenario metadata and processed feature schema. "
    "It does not execute real offensive attacks or infer unknown raw dataset schema."
)

st.subheader("Automatic Model Routing")
st.table(
    [
        {
            "Selected scenario": scenario.name,
            "Source schema": dataset_name,
            "Feature count": int(shape["features"]),
            "Routed IDS model": scenario.routed_model_label,
            "Traffic family": scenario.traffic_family,
        }
    ]
)

with st.expander("Technical Reproducibility Details"):
    st.caption(
        "These details are read-only and shown only for reproducibility. The live "
        "demonstration uses preselected benchmark attack scenarios and does not "
        "require manual row entry."
    )
    st.table(
        [
            {
                "Scenario identifier": scenario.name,
                "Source schema": dataset_name,
                "Original test row": int(scenario.sample_index),
                "Available replay rows": int(shape['rows']),
                "Feature count": int(shape["features"]),
                "Model checkpoint": model_checkpoint,
                "Processed data path": processed_data_path,
            }
        ]
    )

run_clicked = st.button("Run IDS Replay", type="primary")

if run_clicked:
    with st.spinner("Running one-sample IDS inference and local attribution..."):
        try:
            result = run_live_inference(dataset_name, int(scenario.sample_index), top_k=8)
        except Exception as error:
            st.error(f'Inference could not complete: {error}')
            st.stop()

    st.subheader("Detection Result")
    decision_col, probability_col, label_col, status_col = st.columns(4)
    decision_col.metric("Binary decision", result["binary_prediction"])
    probability_col.metric(
        "Attack probability",
        format_probability(result["binary_probability"]),
    )
    label_col.metric("True label", result["true_binary"] or "Not available")
    status_col.metric("Decision status", status_text(result["binary_correct"]))

    st.subheader("Attack Family Classification")
    family_col, confidence_col, reference_col, family_status_col = st.columns(4)
    family_col.metric(
        "Predicted attack family",
        result["attack_family_prediction"] or "Not available",
    )
    confidence_col.metric(
        "Family confidence",
        format_probability(result["attack_family_probability"]),
    )
    reference_col.metric(
        "Reference family",
        result["true_attack_family"] or "Not available",
    )
    family_status_col.metric(
        "Family status",
        status_text(result["attack_family_correct"]),
    )

    if result["binary_correct"] is False or result["attack_family_correct"] is False:
        st.warning(
            "This scenario is displayed honestly: the model output does not match "
            "the reference label for every task."
        )

    st.subheader("Explainability: Local Feature Attribution")
    st.markdown("**Method:** Gradient x Input")
    st.caption(
        "This local explanation highlights processed input features that most influenced "
        "this specific prediction. Gradient x Input is a lightweight local attribution "
        "method. It is not SHAP/LIME and does not prove real-world causality. Feature "
        "values are normalized/encoded model inputs."
    )

    binary_attr = result["attribution"]["binary"]
    family_attr = result["attribution"].get("family")
    attack_top3 = format_attribution_rows(binary_attr["top_positive"], limit=3)
    family_top3 = (
        format_attribution_rows(family_attr["top_positive"], limit=3)
        if family_attr
        else []
    )

    attack_xai_col, family_xai_col = st.columns(2)
    with attack_xai_col:
        st.markdown("**Top 3 features supporting Attack**")
        st.dataframe(attack_top3, hide_index=True, use_container_width=True)
    with family_xai_col:
        st.markdown("**Top 3 features supporting predicted attack family**")
        if family_top3:
            st.dataframe(family_top3, hide_index=True, use_container_width=True)
        else:
            st.info("Attack-family attribution is available when the prediction is Attack.")

    with st.expander("Full attribution details"):
        full_positive_col, full_negative_col = st.columns(2)
        with full_positive_col:
            st.markdown("**Features supporting Attack**")
            st.dataframe(
                format_attribution_rows(binary_attr["top_positive"]),
                hide_index=True,
                use_container_width=True,
            )
        with full_negative_col:
            st.markdown("**Features supporting Benign**")
            st.dataframe(
                format_attribution_rows(binary_attr["top_negative"]),
                hide_index=True,
                use_container_width=True,
            )
        if family_attr:
            st.markdown("**Features supporting predicted attack family**")
            st.dataframe(
                format_attribution_rows(family_attr["top_positive"]),
                hide_index=True,
                use_container_width=True,
            )

    st.subheader("SHA-256 Fingerprints")
    integrity_col, sample_hash_col, record_hash_col = st.columns(3)
    integrity_col.metric("Integrity status", "Fingerprints computed")
    sample_hash_col.metric(
        "Sample fingerprint",
        short_hash(result["sample_row_sha256"]),
    )
    record_hash_col.metric(
        "Prediction fingerprint",
        short_hash(result["prediction_record_sha256"]),
    )
    st.caption(
        "Current SHA-256 fingerprints identify the sample and prediction record. "
        "No independent trusted reference was compared. Trimmed Mean "
        "is the robust aggregation defense used in the federated robustness evidence."
    )

    with st.expander("Full SHA-256 fingerprints"):
        st.markdown("**Sample SHA-256 fingerprint**")
        st.code(result["sample_row_sha256"])
        st.markdown("**Prediction record SHA-256 fingerprint**")
        st.code(result["prediction_record_sha256"])

    with st.expander("Federated Robustness Evidence"):
        st.caption(
            "This section displays saved report evidence. It does not execute live "
            "federated attacks, training, or attack/defense experiments."
        )
        st.markdown(
            """
- Byzantine attack scenario: full-state SignFlip; requested 25%, realized 1/5 = 20%
- Baseline aggregation: FedAvg
- Robust aggregation defense: Trimmed Mean
- Datasets: CICIDS2018 and UNSW-NB15

Gaussian Noise and Scaling are additional Byzantine attack types considered as
future extensions. Historical filenames retain the nominal SignFlip25 label.
"""
        )
        phase_a_rows = cached_phase_a_rows()
        if phase_a_rows:
            # This view relabels the recorded configuration; the CSV is immutable.
            display_rows = [
                {('requested_malicious_fraction' if key == 'malicious_fraction' else key): value
                 for key, value in row.items()}
                for row in phase_a_rows
            ]
            st.dataframe(display_rows, hide_index=True, use_container_width=True)
        else:
            st.info("Phase A matrix file was not found.")

else:
    st.subheader("Ready for IDS Replay")
    st.write(
        "Select an attack scenario and run one-sample detection to view the binary "
        "decision, attack-family classification, local feature attribution, and "
        "integrity fingerprints."
    )
