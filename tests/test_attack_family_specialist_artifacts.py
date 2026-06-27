"""Regression tests: the A9.9 execute/artifact flow must write all outputs.

These guard against the original bug where --execute saved only the checkpoint
and never created result_dir / report. Torch-free (synthetic metric dicts).
"""

from __future__ import annotations

import dataclasses
import inspect

import pytest

from secureids.training.attack_family_specialist_config import (
    PROJECT_ROOT,
    load_attack_family_specialist_config,
)
from secureids.training.attack_family_specialist_artifacts import (
    ARTIFACT_FILE_KEYS,
    SpecialistArtifactError,
    compute_screen_gate,
    write_seed_artifacts,
)
from secureids.training.attack_family_specialist_evaluation import (
    compute_oracle_attack_family_metrics,
    compute_routed_attack_family_metrics,
)

SEED42_CONFIG = (
    PROJECT_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "unsw_a99_attack_family_specialist_seed42.yaml"
)


def _synthetic_inputs():
    y_true = [0, 1, 2, 3]
    oracle = compute_oracle_attack_family_metrics(y_true, [0, 1, 2, 3])
    routed = compute_routed_attack_family_metrics(y_true, [1, 1, 1, 0], [0, 1, 2, 3])
    binary = {"macro_f1": 0.894488, "source": "frozen_a9_head1"}
    class_weights = {"method": "sqrt_inverse_frequency_mean_normalized", "computed_from_train_only": True}
    model_summary = {"best_val_attack_family_macro_f1": 0.5, "architecture_metadata": {}}
    gate = compute_screen_gate(oracle["attack_family_macro_f1"], 0.3, binary_router_unchanged=True)
    return oracle, routed, binary, class_weights, model_summary, gate


def _config_in_tmp(tmp_path, **output_overrides):
    config = load_attack_family_specialist_config(SEED42_CONFIG, project_root=PROJECT_ROOT)
    outputs = dict(config.outputs)
    outputs.update(output_overrides)
    return dataclasses.replace(config, outputs=outputs, project_root=tmp_path)


def test_writer_creates_all_configured_outputs_and_report(tmp_path):
    oracle, routed, binary, cw, ms, gate = _synthetic_inputs()
    config = _config_in_tmp(tmp_path)
    written = write_seed_artifacts(
        config,
        oracle_metrics=oracle,
        routed_metrics=routed,
        binary_router_metrics=binary,
        class_weight_snapshot=cw,
        model_summary=ms,
        training_history_note="note",
        screen_gate=gate,
        checkpoint_sha256="DEADBEEF",
        project_root=tmp_path,
    )
    # Every configured file artifact exists (the core regression guard).
    for key in ARTIFACT_FILE_KEYS:
        assert (tmp_path / config.outputs[key]).exists(), f"missing artifact: {key}"
    assert (tmp_path / config.outputs["result_dir"]).is_dir()
    assert "artifact_manifest_json" in written
    # Report is present.
    assert (tmp_path / config.outputs["report_md"]).exists()


def test_oracle_and_routed_written_to_separate_files(tmp_path):
    oracle, routed, binary, cw, ms, gate = _synthetic_inputs()
    config = _config_in_tmp(tmp_path)
    write_seed_artifacts(
        config,
        oracle_metrics=oracle,
        routed_metrics=routed,
        binary_router_metrics=binary,
        class_weight_snapshot=cw,
        model_summary=ms,
        training_history_note="note",
        screen_gate=gate,
        checkpoint_sha256="DEADBEEF",
        project_root=tmp_path,
    )
    assert config.outputs["oracle_metrics_json"] != config.outputs["routed_metrics_json"]
    assert (tmp_path / config.outputs["oracle_metrics_json"]).exists()
    assert (tmp_path / config.outputs["routed_metrics_json"]).exists()


def test_writer_rejects_swapped_views(tmp_path):
    oracle, routed, binary, cw, ms, gate = _synthetic_inputs()
    config = _config_in_tmp(tmp_path)
    with pytest.raises(SpecialistArtifactError):
        write_seed_artifacts(
            config,
            oracle_metrics=routed,  # swapped on purpose
            routed_metrics=oracle,
            binary_router_metrics=binary,
            class_weight_snapshot=cw,
            model_summary=ms,
            training_history_note="note",
            screen_gate=gate,
            checkpoint_sha256="DEADBEEF",
            project_root=tmp_path,
        )


def test_writer_rejects_final_output_path(tmp_path):
    oracle, routed, binary, cw, ms, gate = _synthetic_inputs()
    config = _config_in_tmp(tmp_path, oracle_metrics_json="results/final/hierarchical/unsw/x.json")
    with pytest.raises(SpecialistArtifactError):
        write_seed_artifacts(
            config,
            oracle_metrics=oracle,
            routed_metrics=routed,
            binary_router_metrics=binary,
            class_weight_snapshot=cw,
            model_summary=ms,
            training_history_note="note",
            screen_gate=gate,
            checkpoint_sha256="DEADBEEF",
            project_root=tmp_path,
        )


def test_writer_refuses_overwrite_by_default(tmp_path):
    oracle, routed, binary, cw, ms, gate = _synthetic_inputs()
    config = _config_in_tmp(tmp_path)
    kwargs = dict(
        oracle_metrics=oracle,
        routed_metrics=routed,
        binary_router_metrics=binary,
        class_weight_snapshot=cw,
        model_summary=ms,
        training_history_note="note",
        screen_gate=gate,
        checkpoint_sha256="DEADBEEF",
        project_root=tmp_path,
    )
    write_seed_artifacts(config, **kwargs)
    with pytest.raises(SpecialistArtifactError):
        write_seed_artifacts(config, **kwargs)  # second time, overwrite=False -> raise


def test_execute_path_calls_artifact_writer():
    # The execute/training path must write artifacts after the checkpoint exists.
    from secureids.training import attack_family_specialist_trainer as trainer

    source = inspect.getsource(trainer._execute_training)
    assert "generate_seed_artifacts" in source, "execute path must write artifacts after checkpoint"
    assert "torch.save" in source


def test_train_hierarchical_unchanged():
    from secureids.cli import build_parser, handle_train_hierarchical

    parser = build_parser()
    args = parser.parse_args(
        ["train-hierarchical", "--config", "configs/training/unsw_nb15_hierarchical.yaml"]
    )
    assert args.func is handle_train_hierarchical
    assert args.execute is False
