"""Safe CLI entry point for the SecureIDS V2 rebuild."""

from __future__ import annotations

import argparse
from pathlib import Path

from secureids.datasets.cicids2018 import CICIDS2018Adapter
from secureids.datasets.unsw_nb15 import UNSWNB15Adapter
from secureids.preprocessing.pipeline import (
    run_preprocessing_dry_run,
    run_preprocessing_execute,
)
from secureids.preprocessing.hierarchical import (
    HierarchicalPreprocessingError,
    run_hierarchical_preprocessing,
)
from secureids.preprocessing.hierarchical_validation import (
    HierarchicalReadinessError,
    run_hierarchical_readiness_validation,
)
from secureids.reporting.dataset_audit import (
    MISSING_RAW_DATA_NOTE,
    write_dataset_audit_outputs,
)

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "datasets.yaml"


def default_dataset_config() -> dict[str, dict[str, object]]:
    return {
        "cicids2018": {"raw_dir": "data/raw/cicids2018"},
        "unsw_nb15": {"raw_dir": "data/raw/unsw_nb15"},
    }


def load_dataset_config() -> dict[str, dict[str, object]]:
    if not CONFIG_PATH.exists() or yaml is None:
        return default_dataset_config()

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secureids",
        description=(
            "SecureIDS V2: dataset tools, read-only planning, and explicitly "
            "gated preprocessing/training commands. Use --help for each command."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="secureids 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command")

    audit_parser = subparsers.add_parser(
        "audit-data",
        help="Audit raw dataset CSV headers and small samples only.",
        description=(
            "Inspect raw dataset CSV files safely. This command does not train, "
            "preprocess, write processed arrays, create checkpoints, or produce "
            "performance metrics."
        ),
    )
    audit_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to audit. Defaults to all.",
    )
    audit_parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Optional raw directory override for a single dataset audit.",
    )
    audit_parser.set_defaults(func=handle_audit_data)

    preprocess_parser = subparsers.add_parser(
        "preprocess",
        help="Run preprocessing validation or approved execution.",
        description=(
            "Validate preprocessing configs with --dry-run or create approved "
            "processed artifacts with --execute. This command does not train or "
            "evaluate models."
        ),
    )
    preprocess_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to validate. Defaults to all.",
    )
    preprocess_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation only.",
    )
    preprocess_parser.add_argument(
        "--execute",
        action="store_true",
        help="Run real preprocessing and create approved processed artifacts.",
    )
    preprocess_parser.set_defaults(func=handle_preprocess)

    unsw_a11_parser = subparsers.add_parser(
        "prepare-unsw-a11",
        help="Validate or run approved UNSW A11 enhanced feature preprocessing.",
        description=(
            "Validate the UNSW A11 Enhanced Feature Protocol preprocessing "
            "config. Without --execute this is a dry-run and writes nothing. "
            "With --execute it creates only A11-specific preprocessing outputs "
            "after main-control approval. It does not train, evaluate, create "
            "checkpoints, promote models, or touch final artifacts."
        ),
    )
    unsw_a11_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to configs/preprocessing/experiments/unsw_a11_enhanced_feature_protocol.yaml.",
    )
    unsw_a11_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required to create A11 preprocessing outputs. Omit for dry-run validation.",
    )
    unsw_a11_parser.set_defaults(func=handle_prepare_unsw_a11)

    hierarchical_preprocess_parser = subparsers.add_parser(
        "preprocess-hierarchical",
        help="Run approved A3 hierarchical preprocessing only.",
        description=(
            "Create hierarchical preprocessing artifacts from accepted binary "
            "processed arrays and locked A2 taxonomy configs. This command does "
            "not create model code, train, evaluate, create checkpoints, or "
            "start security/XAI/dashboard work."
        ),
    )
    hierarchical_preprocess_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to process. Defaults to all.",
    )
    hierarchical_preprocess_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required. Runs real hierarchical preprocessing execution.",
    )
    hierarchical_preprocess_parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Allow overwriting only the selected dataset's existing "
            "hierarchical preprocessing output files."
        ),
    )
    hierarchical_preprocess_parser.set_defaults(func=handle_preprocess_hierarchical)

    hierarchical_validation_parser = subparsers.add_parser(
        "validate-hierarchical-preprocessing",
        help="Validate A3 hierarchical preprocessing outputs for A4 readiness.",
        description=(
            "Read hierarchical preprocessing artifacts, mappings, manifests, "
            "and safety targets, then write A4 readiness JSON/report outputs. "
            "This command does not create arrays, train, evaluate, create "
            "checkpoints, or implement model/security/XAI/dashboard code."
        ),
    )
    hierarchical_validation_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to validate. Defaults to all.",
    )
    hierarchical_validation_parser.set_defaults(func=handle_validate_hierarchical_preprocessing)

    train_parser = subparsers.add_parser(
        "train-centralized",
        help="Validate (dry-run) or run full centralized training for one dataset.",
        description=(
            "Validate a centralized training config and its processed artifacts "
            "with --dry-run, or run real full centralized training with --execute. "
            "Execution is enabled for UNSW-NB15 and CICIDS2018; existing final "
            "outputs are protected unless --overwrite is passed."
        ),
    )
    train_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15"],
        default=None,
        help="Dataset to train. Optional; cross-checked against the config.",
    )
    train_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the training config YAML for this dataset.",
    )
    train_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and processed artifact availability only.",
    )
    train_parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Run full centralized training. Enabled for UNSW-NB15 and CICIDS2018."
        ),
    )
    train_parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Allow overwriting existing final outputs/checkpoint for the selected "
            "dataset. Default is to refuse if they already exist."
        ),
    )
    train_parser.set_defaults(func=handle_train_centralized)

    smoke_parser = subparsers.add_parser(
        "smoke-train-centralized",
        help="Run a tiny NON-FINAL smoke-training check for one dataset.",
        description=(
            "Run a tiny, explicitly non-final training/eval pass on small subsets "
            "to validate the PyTorch training path before any full training. "
            "Requires --execute. Produces only non-final smoke outputs; never "
            "creates final checkpoints, final metrics, or results/final outputs."
        ),
    )
    smoke_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15"],
        default=None,
        help="Dataset to smoke-test. Optional; cross-checked against the config.",
    )
    smoke_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the smoke-training config YAML for this dataset.",
    )
    smoke_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required. Runs the tiny non-final smoke-training check.",
    )
    smoke_parser.set_defaults(func=handle_smoke_train_centralized)

    hierarchical_smoke_parser = subparsers.add_parser(
        "smoke-train-hierarchical",
        help="Run a tiny NON-FINAL hierarchical smoke-training check.",
        description=(
            "Run a tiny, explicitly non-final hierarchical training/eval pass "
            "on capped subsets. This command refuses non-smoke configs, refuses "
            "checkpoint saving/final metrics, and never writes final outputs."
        ),
    )
    hierarchical_smoke_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15"],
        default=None,
        help="Dataset to smoke-test. Optional; cross-checked against the config.",
    )
    hierarchical_smoke_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the hierarchical smoke-training config YAML.",
    )
    hierarchical_smoke_parser.set_defaults(func=handle_smoke_train_hierarchical)

    hierarchical_readiness_parser = subparsers.add_parser(
        "check-hierarchical-training-readiness",
        help="Run the A8 full hierarchical training readiness gate only.",
        description=(
            "Validate full centralized hierarchical training readiness without "
            "training, backpropagation, checkpoint creation, or final metric "
            "creation. Writes only A8 audit JSON files and the readiness report."
        ),
    )
    hierarchical_readiness_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to check. Defaults to all.",
    )
    hierarchical_readiness_parser.set_defaults(
        func=handle_check_hierarchical_training_readiness
    )

    hierarchical_class_weights_parser = subparsers.add_parser(
        "lock-hierarchical-class-weights",
        help="Lock and audit A8.5 hierarchical class-weight strategy only.",
        description=(
            "Compute train-only binary and Head 2 class-weight previews using "
            "the locked A8.5 smoothing/cap strategy. Writes audit JSONs and "
            "the strategy document only; does not train, evaluate, save "
            "checkpoints, or create final metrics."
        ),
    )
    hierarchical_class_weights_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15", "all"],
        default="all",
        help="Dataset to audit. Defaults to all.",
    )
    hierarchical_class_weights_parser.set_defaults(
        func=handle_lock_hierarchical_class_weights
    )

    train_hierarchical_parser = subparsers.add_parser(
        "train-hierarchical",
        help="Run approved real centralized hierarchical training for UNSW-NB15 or CICIDS2018.",
        description=(
            "Run real centralized hierarchical training for SecureIDSHierarchicalAdvancedNet. "
            "Approved datasets are UNSW-NB15 and CICIDS2018. Requires --execute. "
            "Selects the best checkpoint by validation only and evaluates the test split "
            "once after selection. Existing final outputs are protected unless --overwrite."
        ),
    )
    train_hierarchical_parser.add_argument(
        "--dataset",
        choices=[
            "cicids",
            "cicids2018",
            "cicids-2018",
            "unsw",
            "unsw_nb15",
            "unsw-nb15",
        ],
        default=None,
        help="Dataset to train. Optional; cross-checked against the hierarchical config.",
    )
    train_hierarchical_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the hierarchical training config YAML for this dataset.",
    )
    train_hierarchical_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required. Runs the real centralized hierarchical training.",
    )
    train_hierarchical_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing final hierarchical outputs/checkpoint.",
    )
    train_hierarchical_parser.set_defaults(func=handle_train_hierarchical)

    specialist_parser = subparsers.add_parser(
        "train-attack-family-specialist",
        help="Run the approved UNSW A9.9 attack-family specialist (behind frozen A9 Head 1).",
        description=(
            "Train a dedicated attack-only family specialist behind the frozen A9 "
            "Head 1 binary router (UNSW-NB15 only). Requires --execute to train. "
            "Without --execute it prints a torch-free dry-run summary and exits "
            "without training. This does NOT affect train-hierarchical."
        ),
    )
    specialist_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the A9.9 attack-family specialist config YAML.",
    )
    specialist_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required to actually train. Without it, only a dry-run summary is printed.",
    )
    specialist_parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Allow overwriting an existing specialist checkpoint under "
            "models/experiments/. Must NOT be used without main-control approval."
        ),
    )
    specialist_parser.set_defaults(func=handle_train_attack_family_specialist)

    frozen_specialist_parser = subparsers.add_parser(
        "train-frozen-embedding-specialist",
        help="Run the approved UNSW A9.10 frozen-A9-embedding attack-family specialist.",
        description=(
            "Train a tiny attack-family head over the frozen A9 128-dimensional "
            "embedding (UNSW-NB15 only). Requires --execute to train. Without "
            "--execute it validates the config, prints a dry-run plan, and writes "
            "nothing. This does NOT affect train-hierarchical or A9.9."
        ),
    )
    frozen_specialist_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the A9.10 frozen-embedding specialist config YAML.",
    )
    frozen_specialist_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required to actually train. Without it, only a dry-run summary is printed.",
    )
    frozen_specialist_parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Allow overwriting existing A9.10 experiment outputs. Refused by "
            "default and must NOT be used without main-control approval."
        ),
    )
    frozen_specialist_parser.set_defaults(func=handle_train_frozen_embedding_specialist)

    validation_parser = subparsers.add_parser(
        "validate-centralized-baselines",
        help="Validate finalized centralized baseline artifacts without training.",
        description=(
            "Read existing finalized centralized baseline artifacts and manifests "
            "only. This command does not train, retrain, evaluate models, load "
            "full arrays, or modify checkpoints/metrics/histories/confusion "
            "matrices/training manifests."
        ),
    )
    validation_parser.set_defaults(func=handle_validate_centralized_baselines)

    federated_dry_run_parser = subparsers.add_parser(
        "federated-dry-run",
        help="Validate FedAvg config and client split planning only.",
        description=(
            "Validate a FedAvg design config, existing processed artifacts, "
            "centralized references, and deterministic client distribution "
            "planning. This command does not train, evaluate on the test set, "
            "create federated checkpoints, or create final federated metrics."
        ),
    )
    federated_dry_run_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15"],
        required=True,
        help="Dataset alias to validate against the FedAvg config.",
    )
    federated_dry_run_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the FedAvg federated config YAML.",
    )
    federated_dry_run_parser.set_defaults(func=handle_federated_dry_run)

    federated_plan_parser = subparsers.add_parser(
        "federated-plan",
        help="Validate future hierarchical federated/security configs without writes.",
        description=(
            "Validate a future hierarchical federated/security config for safe "
            "experiment-only paths, final checkpoint references, aggregation, "
            "attack, and SHA-256 integrity settings. This command is scaffold "
            "validation only: without --execute it writes nothing, and with "
            "--execute it refuses because real runs are future manual work."
        ),
    )
    federated_plan_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a configs/federated/experiments/*.yaml config.",
    )
    federated_plan_parser.add_argument(
        "--execute",
        action="store_true",
        help="Future execution gate. Refused by this scaffold command.",
    )
    federated_plan_parser.set_defaults(func=handle_federated_plan)

    federated_train_hierarchical_parser = subparsers.add_parser(
        "federated-train-hierarchical",
        help="Dry-run or run approved hierarchical FedAvg training.",
        description=(
            "Validate a hierarchical FedAvg config and list expected "
            "experiment-only outputs. Without --execute this command writes "
            "nothing and starts no training. With --execute it uses the guarded "
            "future real-run path after explicit main-control approval."
        ),
    )
    federated_train_hierarchical_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a clean hierarchical FedAvg config YAML.",
    )
    federated_train_hierarchical_parser.add_argument(
        "--execute",
        action="store_true",
        help="Future approval gate. Runs real hierarchical FedAvg training only when approved.",
    )
    federated_train_hierarchical_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting planned experiment-only outputs during a future approved run.",
    )
    federated_train_hierarchical_parser.set_defaults(
        func=handle_federated_train_hierarchical
    )

    federated_train_parser = subparsers.add_parser(
        "federated-train",
        help="Run approved real FedAvg training for UNSW-NB15 or CICIDS2018.",
        description=(
            "Run real FedAvg training for approved datasets after explicit "
            "--execute approval. UNSW-NB15 and CICIDS2018 use separate configs "
            "and guarded output paths."
        ),
    )
    federated_train_parser.add_argument(
        "--dataset",
        choices=["cicids", "cicids2018", "unsw", "unsw_nb15"],
        required=True,
        help="Dataset alias for the approved FedAvg training config.",
    )
    federated_train_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the UNSW FedAvg federated config YAML.",
    )
    federated_train_parser.add_argument(
        "--execute",
        action="store_true",
        help="Required. Runs real UNSW FedAvg training.",
    )
    federated_train_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing UNSW FedAvg outputs only.",
    )
    federated_train_parser.set_defaults(func=handle_federated_train)
    return parser


def resolve_raw_dir(
    config: dict[str, dict[str, object]],
    dataset_key: str,
    override: Path | None,
) -> Path:
    if override is not None:
        return override
    configured = config.get(dataset_key, {}).get("raw_dir")
    return Path(str(configured)) if configured else Path("data/raw") / dataset_key


def selected_dataset_keys(selection: str) -> list[str]:
    if selection in {"cicids", "cicids2018"}:
        return ["cicids2018"]
    if selection in {"unsw", "unsw_nb15"}:
        return ["unsw_nb15"]
    return ["cicids2018", "unsw_nb15"]


def handle_audit_data(args: argparse.Namespace) -> int:
    if args.dataset == "all" and args.raw_dir is not None:
        raise SystemExit("--raw-dir can only be used with a single dataset audit.")

    config = load_dataset_config()
    file_audits = []
    schema_audits = {"cicids2018": [], "unsw_nb15": []}

    for dataset_key in selected_dataset_keys(args.dataset):
        raw_dir = resolve_raw_dir(config, dataset_key, args.raw_dir)
        if dataset_key == "cicids2018":
            adapter = CICIDS2018Adapter(raw_dir=raw_dir)
        else:
            adapter = UNSWNB15Adapter(raw_dir=raw_dir)

        dataset_file_audits, dataset_schema_audits = adapter.audit_schema()
        file_audits.extend(dataset_file_audits)
        schema_audits[dataset_key].extend(dataset_schema_audits)

    write_dataset_audit_outputs(
        project_root=PROJECT_ROOT,
        file_audits=file_audits,
        schema_audits=schema_audits,
    )

    print("SecureIDS V2 dataset audit completed safely.")
    print("No training, preprocessing, checkpoints, or performance metrics were created.")

    inspected_files = sum(1 for audit in file_audits if audit.is_csv and audit.exists)
    if inspected_files == 0:
        print(MISSING_RAW_DATA_NOTE)
    else:
        print(f"CSV files inspected: {inspected_files}")

    print("Audit outputs written:")
    print("- docs/DATASET_SCHEMA_AUDIT.md")
    print("- docs/UNSW_COMPATIBILITY_DECISION.md")
    print("- results/audits/dataset_file_inventory.csv")
    print("- results/audits/cicids_schema_audit.csv")
    print("- results/audits/unsw_schema_audit.csv")
    return 0


def handle_preprocess(args: argparse.Namespace) -> int:
    if args.dry_run and args.execute:
        print("Choose either --dry-run or --execute, not both.")
        return 1
    if not args.dry_run and not args.execute:
        print("Full preprocessing requires --execute. Use --dry-run for validation only.")
        return 1

    if args.dry_run:
        reports = run_preprocessing_dry_run(
            dataset=args.dataset,
            project_root=PROJECT_ROOT,
        )
        print("SecureIDS V2 preprocessing dry-run completed safely.")
        print("No processed arrays, joblib preprocessors, checkpoints, training, or metrics were created.")
        for report in reports:
            print(
                f"- {report['dataset']}: status={report['status']}, "
                f"files_found={report['file_count']}, "
                f"target={report['target_column_status']['status']}, "
                f"processed_outputs_created={str(report['processed_outputs_created']).lower()}"
            )
        print("Dry-run outputs written:")
        for report in reports:
            print(f"- results/audits/preprocessing_dry_run_{report['dataset']}.json")
        print("- docs/PREPROCESSING_DRY_RUN_REPORT.md")
        return 0

    reports = run_preprocessing_execute(
        dataset=args.dataset,
        project_root=PROJECT_ROOT,
    )
    print("SecureIDS V2 preprocessing execution completed safely.")
    print("Processed arrays and train-fitted preprocessor artifacts were created.")
    print("No model training, checkpoints, or model performance metrics were created.")
    for report in reports:
        print(
            f"- {report['dataset']}: features={report['feature_count']}, "
            f"train={report['split_summary']['train']['rows']}, "
            f"val={report['split_summary']['val']['rows']}, "
            f"test={report['split_summary']['test']['rows']}"
        )
    print("Preprocessing outputs written:")
    for report in reports:
        print(f"- {report['output_dir']}")
        print(f"- {report['artifact_path']}")
    print("- docs/PREPROCESSING_REPORT.md")
    return 0


def handle_prepare_unsw_a11(args: argparse.Namespace) -> int:
    """UNSW A11 enhanced feature preprocessing. Dry-run unless --execute."""

    from secureids.preprocessing.unsw_a11_config import UNSWA11ConfigError
    from secureids.preprocessing.unsw_a11_preprocessor import (
        UNSWA11PreprocessingError,
        run_unsw_a11_preprocessing,
    )

    try:
        outcome = run_unsw_a11_preprocessing(
            args.config,
            execute=args.execute,
            project_root=PROJECT_ROOT,
        )
    except (UNSWA11ConfigError, UNSWA11PreprocessingError, FileNotFoundError, ValueError) as error:
        print(f"UNSW A11 preprocessing request rejected: {error}")
        print("No preprocessing, training, evaluation, checkpoints, or final outputs were created.")
        return 1

    if not args.execute:
        print("UNSW A11 Enhanced Feature Protocol DRY RUN (no --execute): writes nothing.")
        print(f"- config: {outcome['config_path']}")
        print(f"- dataset: {outcome['dataset']}")
        print(f"- protocol: {outcome['protocol_name']}")
        print("- planned outputs:")
        for key, path in outcome["planned_outputs"].items():
            exists = outcome["planned_outputs_exist"][key]
            print(f"  - {key}: {path} (exists={exists})")
        partial = outcome["partial_outputs"]
        print(
            "- partial_outputs: "
            f"detected={partial['detected']}, "
            f"classification={partial['classification']}, "
            f"safe_to_use_for_training={partial['safe_to_use_for_training']}"
        )
        if partial["detected"]:
            print("- rerun requires main-control cleanup/overwrite approval before --execute.")
        print("- preprocessing_run: False")
        print("- training_run: False")
        print("- evaluation_run: False")
        print("- checkpoint_created: False")
        print("Pass --execute only after main-control approval to create A11 preprocessing outputs.")
        return 0

    print("UNSW A11 Enhanced Feature Protocol preprocessing completed.")
    print("Only A11-specific preprocessing outputs were created; no training or evaluation was run.")
    print(f"- feature_count: {outcome['feature_count']}")
    print(f"- processed outputs: {outcome['outputs']['processed_data_dir']}")
    print(f"- preprocessing audit: {outcome['outputs']['preprocessing_audit']}")
    return 0


def handle_preprocess_hierarchical(args: argparse.Namespace) -> int:
    if not args.execute:
        print("Hierarchical preprocessing requires --execute. No outputs were created.")
        return 1

    try:
        outcomes = run_hierarchical_preprocessing(
            dataset=args.dataset,
            project_root=PROJECT_ROOT,
            execute=args.execute,
            overwrite=args.overwrite,
        )
    except (HierarchicalPreprocessingError, FileNotFoundError, ValueError) as error:
        print(f"Hierarchical preprocessing failed: {error}")
        print("No model code, training, evaluation, checkpoints, or final metrics were created.")
        return 1

    print("SecureIDS V2 hierarchical preprocessing execution completed safely.")
    print("No model code, training, evaluation, checkpoints, or model metrics were created.")
    for outcome in outcomes:
        split = outcome["split_summary"]
        print(
            f"- {outcome['dataset']}: status={outcome['status']}, "
            f"features={outcome['feature_dim']}, "
            f"train={split['train']['y_binary_shape'][0]}, "
            f"val={split['val']['y_binary_shape'][0]}, "
            f"test={split['test']['y_binary_shape'][0]}"
        )
        print(f"  output_dir: {outcome['output_dir']}")
    print("Hierarchical preprocessing outputs written:")
    for outcome in outcomes:
        print(f"- {outcome['output_dir']}")
        print(f"- {CONFIGS_AUDIT_PATH(outcome['dataset'])}")
    print("- docs/HIERARCHICAL_PREPROCESSING_EXECUTION_REPORT.md")
    return 0


def CONFIGS_AUDIT_PATH(dataset: str) -> str:
    if dataset == "cicids2018":
        return "results/audits/hierarchical_preprocessing_audit_cicids2018.json"
    return "results/audits/hierarchical_preprocessing_audit_unsw_nb15.json"


def handle_validate_hierarchical_preprocessing(args: argparse.Namespace) -> int:
    try:
        outcomes = run_hierarchical_readiness_validation(
            dataset=args.dataset,
            project_root=PROJECT_ROOT,
        )
    except (HierarchicalReadinessError, FileNotFoundError, ValueError) as error:
        print(f"Hierarchical preprocessing readiness validation failed: {error}")
        print("No arrays, model code, training, evaluation, checkpoints, or model metrics were created.")
        return 1

    print("SecureIDS V2 hierarchical preprocessing readiness validation completed.")
    print("No arrays, model code, training, evaluation, checkpoints, or model metrics were created.")
    for outcome in outcomes:
        print(
            f"- {outcome['dataset']}: status={outcome['status']}, "
            f"ready={outcome['ready_for_hierarchical_model_implementation']}, "
            f"blocking_issues={len(outcome['blocking_issues'])}, "
            f"warnings={len(outcome['warnings'])}"
        )
    print("Readiness outputs written:")
    print("- results/audits/hierarchical_preprocessing_readiness_cicids2018.json")
    print("- results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json")
    print("- docs/HIERARCHICAL_PREPROCESSING_READINESS_REPORT.md")
    return 0 if all(outcome["status"] == "PASS" for outcome in outcomes) else 1


TRAIN_HIERARCHICAL_ALLOWED_ALIASES = {
    "unsw_nb15": ("unsw", "unsw_nb15", "unsw-nb15"),
    "cicids2018": ("cicids", "cicids2018", "cicids-2018"),
}
TRAIN_HIERARCHICAL_EXPECTED_INPUT_DIMS = {
    "unsw_nb15": 192,
    "cicids2018": 77,
}
TRAIN_HIERARCHICAL_EXPECTED_ATTACK_HEAD_DIMS = {
    "unsw_nb15": 9,
    "cicids2018": 14,
}
CICIDS_HIERARCHICAL_EXPERIMENT_CONFIG_PREFIX = "cicids_hierarchical_exp"


def normalized_dataset_name(selection: str | None) -> str | None:
    if selection is None:
        return None
    normalized = str(selection).strip().lower()
    for canonical, aliases in TRAIN_HIERARCHICAL_ALLOWED_ALIASES.items():
        if normalized in aliases:
            return canonical
    return None


def _format_train_hierarchical_aliases() -> str:
    return ", ".join(
        alias
        for aliases in TRAIN_HIERARCHICAL_ALLOWED_ALIASES.values()
        for alias in aliases
    )


def _is_cicids_hierarchical_experiment_config_path(config_path: Path | str) -> bool:
    path = Path(config_path)
    parts = tuple(part.lower() for part in path.parts)
    config_name = path.name.lower().replace("-", "_")
    return (
        len(parts) >= 4
        and parts[-4:-1] == ("configs", "training", "experiments")
        and config_name.startswith(CICIDS_HIERARCHICAL_EXPERIMENT_CONFIG_PREFIX)
        and config_name.endswith((".yaml", ".yml"))
    )


def _validate_train_hierarchical_cli_gate(
    dataset_selection: str | None,
    config_path: Path | str,
    config_dataset: str,
    config_input_dim: int,
    config_attack_head_dim: int | None = None,
    config_task: str = "hierarchical",
) -> str:
    """Validate train-hierarchical dataset aliases and config pairing.

    This is intentionally torch-free and side-effect free. The actual trainer
    still owns all data, checkpoint, leakage, and overwrite safety checks.
    """

    requested = normalized_dataset_name(dataset_selection)
    if dataset_selection is not None and requested is None:
        raise ValueError(
            f"unsupported dataset alias {dataset_selection!r}; supported aliases: "
            f"{_format_train_hierarchical_aliases()}."
        )

    canonical_config_dataset = normalized_dataset_name(config_dataset)
    if canonical_config_dataset is None:
        raise ValueError(f"unsupported config dataset {config_dataset!r}.")
    if str(config_task) != "hierarchical":
        raise ValueError(
            f"train-hierarchical requires task 'hierarchical', got {config_task!r}."
        )

    canonical = requested or canonical_config_dataset
    if requested is not None and requested != canonical_config_dataset:
        raise ValueError(
            f"--dataset {dataset_selection!r} does not match config dataset "
            f"{canonical_config_dataset!r}."
        )

    expected_dim = TRAIN_HIERARCHICAL_EXPECTED_INPUT_DIMS[canonical]
    if int(config_input_dim) != expected_dim:
        raise ValueError(
            f"{canonical} hierarchical input_dim must be {expected_dim}, "
            f"got {config_input_dim}. Fix the config before training."
        )
    if config_attack_head_dim is not None:
        expected_attack_dim = TRAIN_HIERARCHICAL_EXPECTED_ATTACK_HEAD_DIMS[canonical]
        if int(config_attack_head_dim) != expected_attack_dim:
            raise ValueError(
                f"{canonical} hierarchical attack_head_dim must be {expected_attack_dim}, "
                f"got {config_attack_head_dim}. Fix the config before training."
            )

    config_name = Path(config_path).name.lower().replace("-", "_")
    if not config_name.endswith((".yaml", ".yml")):
        raise ValueError("train-hierarchical config must be a YAML file.")
    if "binary" in config_name or "smoke" in config_name:
        raise ValueError(
            f"train-hierarchical refuses non-final or binary config: {Path(config_path).name!r}."
        )

    if canonical == "unsw_nb15":
        is_unsw_hierarchical_name = "hierarchical" in config_name or config_name.startswith(
            "unsw_a9_"
        ) or config_name == (
            "unsw_a11_enhanced_feature_protocol_seed42.yaml"
        )
        if (
            "unsw" not in config_name
            or "cicids" in config_name
            or not is_unsw_hierarchical_name
        ):
            raise ValueError(
                "UNSW-NB15 train-hierarchical requires a UNSW hierarchical config."
            )
        return "UNSW-NB15"

    if config_name == "cicids2018_hierarchical.yaml":
        return "CICIDS2018"
    if _is_cicids_hierarchical_experiment_config_path(config_path):
        return "CICIDS2018"
    raise ValueError(
        "CICIDS2018 train-hierarchical requires "
        "configs/training/cicids2018_hierarchical.yaml or an approved "
        "configs/training/experiments/cicids_hierarchical_exp*.yaml config."
    )


def _run_train_centralized_execute(args: argparse.Namespace) -> int:
    """Gate and run full centralized training. UNSW-NB15 and CICIDS2018 enabled."""

    # Resolve the config's dataset torch-free so config errors and unsupported
    # datasets are handled without importing torch or touching any GPU.
    from secureids.training.config import TrainingConfigError, load_training_config

    try:
        config = load_training_config(args.config, project_root=PROJECT_ROOT)
    except (TrainingConfigError, FileNotFoundError) as error:
        print(f"Centralized training failed to load config: {error}")
        return 1

    config_dataset = config.dataset
    requested = normalized_dataset_name(args.dataset)
    if requested is not None and requested != config_dataset:
        print(
            f"--dataset {args.dataset!r} does not match config dataset "
            f"{config_dataset!r}."
        )
        return 1

    enabled_datasets = {"unsw_nb15", "cicids2018"}
    if config_dataset not in enabled_datasets:
        print(
            "Centralized training execution is not enabled for dataset "
            f"{config_dataset!r}."
        )
        return 1

    dataset_label = "CICIDS2018" if config_dataset == "cicids2018" else "UNSW-NB15"

    # Import the torch training entry point only now (after the dataset gate), so
    # config errors and refusals never require PyTorch.
    try:
        from secureids.training.centralized import (
            ExecutePreconditionError,
            run_centralized_training,
        )
    except ModuleNotFoundError as error:
        print(f"Full training requires PyTorch but an import failed: {error}")
        print("Install PyTorch in the active environment, then re-run.")
        return 1

    print(
        f"Starting full centralized training for {dataset_label} (this is a real "
        "run)."
    )
    if config_dataset == "cicids2018":
        print(
            "CICIDS2018 is large (~6.7M training rows); expect a longer run than "
            "UNSW. Monitor the GPU with 'nvidia-smi -l 5' and keep this terminal "
            "open until it finishes."
        )
    try:
        outcome = run_centralized_training(
            args.config,
            execute=True,
            project_root=PROJECT_ROOT,
            overwrite=args.overwrite,
        )
    except ExecutePreconditionError as error:
        print(str(error))
        print("Training did not start. Fix the issues above and re-run.")
        return 1
    except (TrainingConfigError, FileNotFoundError) as error:
        print(f"Centralized training failed: {error}")
        return 1

    test = outcome["test_metrics"]
    print(f"{dataset_label} full centralized training completed.")
    print(f"- checkpoint: {outcome['checkpoint']}")
    print(f"- test accuracy: {test['accuracy']:.4f}")
    print(f"- test macro_f1: {test['macro_f1']:.4f}")
    print(f"- test metrics json: {outcome['metrics_json']}")
    print(f"- confusion matrix csv: {outcome['confusion_matrix_csv']}")
    print(f"- training manifest: {outcome['manifest_json']}")
    print(f"- report: {outcome['report_md']}")
    return 0


def handle_train_centralized(args: argparse.Namespace) -> int:
    if args.dry_run and args.execute:
        print("Choose either --dry-run or --execute, not both.")
        return 1
    if not args.dry_run and not args.execute:
        print(
            "Centralized training requires an explicit mode. Use --dry-run for "
            "validation or --execute after approval."
        )
        return 1
    if args.execute:
        return _run_train_centralized_execute(args)

    # Lazy, torch-free import: the dry-run planner must work even without torch.
    from secureids.training.config import TrainingConfigError
    from secureids.training.planning import run_centralized_dry_run

    try:
        plan = run_centralized_dry_run(args.config, project_root=PROJECT_ROOT)
    except (TrainingConfigError, FileNotFoundError) as error:
        print(f"Centralized training dry-run failed: {error}")
        return 1

    requested = normalized_dataset_name(args.dataset)
    if requested is not None and requested != plan["dataset"]:
        print(
            f"--dataset {args.dataset!r} does not match config dataset "
            f"{plan['dataset']!r}."
        )
        return 1

    print("SecureIDS V2 centralized training dry-run completed safely.")
    print("No training, checkpoints, or model metrics were created.")
    print(f"- dataset: {plan['dataset']}")
    print(f"- config input_dim: {plan['config_input_dim']}")
    print(f"- detected input_dim: {plan['detected_input_dim']}")
    print(f"- input_dim matches: {plan['input_dim_matches']}")
    print(f"- feature_count: {plan['feature_count']}")
    print(f"- feature_names match input_dim: {plan['feature_names_match']}")
    print(f"- processed_dir exists: {plan['processed_dir_exists']}")
    print(f"- all processed splits available: {plan['all_inputs_available']}")
    print(f"- batch_size: {plan['training']['batch_size']}")
    print(f"- max_epochs: {plan['training']['max_epochs']}")
    print(f"- would create checkpoint: {plan['would_create']['checkpoint']}")
    print(
        "Execution remains disabled. Re-run with --execute only after approval "
        "in Task 8B."
    )
    return 0


def handle_smoke_train_centralized(args: argparse.Namespace) -> int:
    if not args.execute:
        print(
            "Smoke training requires --execute because it runs a tiny non-final "
            "training check."
        )
        return 1

    print(
        "This is a NON-FINAL smoke-training check. Do not report these metrics "
        "as final model results."
    )

    # Import smoke.py (which requires torch) ONLY here, after --execute is set.
    try:
        from secureids.training.config import SmokeConfigError, TrainingConfigError
        from secureids.training.smoke import run_smoke
    except ModuleNotFoundError as error:
        print(f"Smoke training requires PyTorch but an import failed: {error}")
        print(
            "Install PyTorch manually, then re-run. See "
            "docs/CENTRALIZED_TRAINING_SMOKE_DESIGN.md for setup guidance."
        )
        return 1

    expected_dataset = normalized_dataset_name(args.dataset)
    try:
        outcome = run_smoke(
            args.config,
            project_root=PROJECT_ROOT,
            expected_dataset=expected_dataset,
        )
    except (SmokeConfigError, TrainingConfigError, FileNotFoundError) as error:
        print(f"Smoke training failed: {error}")
        return 1

    result = outcome["dataset_result"]
    print(f"- dataset: {result['dataset']}")
    print(f"- smoke status: {result['status']}")
    print(f"- input_dim: {result['input_dim']}")
    print(f"- train samples used: {result['train_samples_used']}")
    print(f"- val samples used: {result['val_samples_used']}")
    print(f"- epochs run: {result['epochs_run']}, batches run: {result['batches_run']}")
    print(f"- forward/backward/loss ok: "
          f"{result['forward_pass_ok']}/{result['backward_pass_ok']}/{result['loss_computed']}")
    print(f"- logits shape [batch, 1] ok: {result['logits_shape_ok']}")
    print(f"- metrics computed: {result['metrics_computed']}")
    print(f"- final checkpoint created: False (smoke checkpoint: {result['checkpoint_created']})")
    print(f"- non-final JSON: {outcome['json_path']}")
    print(f"- non-final report: {outcome['report_path']}")
    print(
        "Reminder: these are NON-FINAL smoke results. Full train-centralized "
        "--execute remains disabled pending approval."
    )
    return 0 if result["status"] == "PASS" else 1


def handle_smoke_train_hierarchical(args: argparse.Namespace) -> int:
    print(
        "This is a NON-FINAL hierarchical smoke-training check. Do not report "
        "these diagnostics as final model results."
    )

    try:
        from secureids.training.hierarchical_config import (
            HierarchicalTrainingConfigError,
        )
        from secureids.training.hierarchical_smoke import (
            HierarchicalSmokeTrainingError,
            run_hierarchical_smoke,
        )
    except ModuleNotFoundError as error:
        print(f"Hierarchical smoke training requires PyTorch but an import failed: {error}")
        return 1

    expected_dataset = normalized_dataset_name(args.dataset)
    try:
        outcome = run_hierarchical_smoke(
            args.config,
            project_root=PROJECT_ROOT,
            expected_dataset=expected_dataset,
        )
    except (
        HierarchicalSmokeTrainingError,
        HierarchicalTrainingConfigError,
        FileNotFoundError,
        ValueError,
    ) as error:
        print(f"Hierarchical smoke training failed: {error}")
        print("No final checkpoints, final metrics, or full training outputs were created.")
        return 1

    result = outcome["dataset_result"]
    train = result["training"]
    diagnostics = result["smoke_diagnostics_non_final"]
    print(f"- dataset: {result['dataset']}")
    print(f"- smoke status: {result['status']}")
    print(f"- input_dim: {result['config']['input_dim']}")
    print(f"- attack_head_dim: {result['config']['attack_head_dim']}")
    print(f"- train batches run: {train['batches_run']}")
    print(
        "- forward/backward/loss ok: "
        f"{train['forward_pass_ok']}/{train['backward_pass_ok']}/{train['loss_finite']}"
    )
    print(
        "- optimizer step updated parameters: "
        f"{train['optimizer_step_updated_parameters']}"
    )
    print(
        "- val smoke binary F1 (non-final): "
        f"{diagnostics['val']['binary']['smoke_binary_f1']}"
    )
    print(
        "- val attack rows evaluated (non-final): "
        f"{diagnostics['val']['attack_family']['attack_rows_evaluated']}"
    )
    print("- final checkpoint created: False")
    print("- final metrics created: False")
    print(f"- non-final JSON: {outcome['json_path']}")
    print(f"- non-final report: {outcome['report_path']}")
    print("Reminder: these are NON-FINAL smoke diagnostics only.")
    return 0 if result["status"] == "PASS" else 1


def handle_check_hierarchical_training_readiness(args: argparse.Namespace) -> int:
    print("Running A8 hierarchical full-training readiness checks only.")
    print("No full training, optimizer loop, checkpoint save, or final metrics will run.")

    try:
        from secureids.training.hierarchical_config import (
            HierarchicalTrainingConfigError,
        )
        from secureids.training.hierarchical_readiness import (
            HierarchicalTrainingReadinessError,
            run_hierarchical_training_readiness,
        )
    except ModuleNotFoundError as error:
        print(f"Hierarchical readiness requires PyTorch/NumPy but an import failed: {error}")
        return 1

    try:
        outcome = run_hierarchical_training_readiness(
            dataset=args.dataset,
            project_root=PROJECT_ROOT,
        )
    except (
        HierarchicalTrainingReadinessError,
        HierarchicalTrainingConfigError,
        FileNotFoundError,
        ValueError,
    ) as error:
        print(f"Hierarchical training readiness failed: {error}")
        print("No final checkpoints, final metrics, or full training outputs were created.")
        return 1

    print(f"A8 readiness overall status: {outcome['status']}")
    for result in outcome["results"]:
        print(
            f"- {result['dataset']}: status={result['status']}, "
            f"ready={result['ready_for_full_hierarchical_training']}, "
            f"blocking={len(result['blocking_issues'])}, "
            f"warnings={len(result['warnings'])}"
        )
    print("A8 outputs written:")
    for path in outcome["json_paths"]:
        print(f"- {path}")
    print(f"- {outcome['report_path']}")
    print("Confirmed: no full hierarchical training, final checkpoints, or final metrics were created.")
    return 0 if outcome["status"] == "PASS" else 1


def handle_lock_hierarchical_class_weights(args: argparse.Namespace) -> int:
    print("Running A8.5 hierarchical class-weight strategy lock only.")
    print("Only train labels will be used. No training, evaluation, checkpoint, or final metric will run.")

    try:
        from secureids.training.hierarchical_class_weights import (
            HierarchicalClassWeightStrategyError,
            run_hierarchical_class_weight_lock,
        )
        from secureids.training.hierarchical_config import (
            HierarchicalTrainingConfigError,
        )
    except ModuleNotFoundError as error:
        print(f"Hierarchical class-weight lock requires NumPy/PyYAML but an import failed: {error}")
        return 1

    try:
        outcome = run_hierarchical_class_weight_lock(
            dataset=args.dataset,
            project_root=PROJECT_ROOT,
        )
    except (
        HierarchicalClassWeightStrategyError,
        HierarchicalTrainingConfigError,
        FileNotFoundError,
        ValueError,
    ) as error:
        print(f"Hierarchical class-weight strategy lock failed: {error}")
        print("No final checkpoints, final metrics, or full training outputs were created.")
        return 1

    print(f"A8.5 class-weight strategy overall status: {outcome['status']}")
    for result in outcome["results"]:
        print(
            f"- {result['dataset']}: status={result['status']}, "
            f"strategy_locked={result['strategy_locked']}, "
            f"safe={result['safe_for_full_training']}, "
            f"max_final_attack_weight={result['max_final_attack_weight']}"
        )
    print("A8.5 outputs written:")
    for path in outcome["json_paths"]:
        print(f"- {path}")
    print(f"- {outcome['doc_path']}")
    print("Confirmed: no full hierarchical training, final checkpoints, or final metrics were created.")
    return 0 if outcome["status"] == "PASS" else 1


def handle_train_hierarchical(args: argparse.Namespace) -> int:
    if not args.execute:
        print(
            "Hierarchical training requires --execute. No training was started. "
            "This is a real full training run; pass --execute only after approval."
        )
        return 1

    # Resolve the config dataset torch-free first, so config errors and the
    # dataset/config gate are handled without importing torch.
    from secureids.training.hierarchical_config import (
        HierarchicalTrainingConfigError,
        load_hierarchical_training_config,
    )

    try:
        config = load_hierarchical_training_config(args.config, project_root=PROJECT_ROOT)
    except (HierarchicalTrainingConfigError, FileNotFoundError) as error:
        print(f"Hierarchical training failed to load config: {error}")
        return 1

    try:
        dataset_label = _validate_train_hierarchical_cli_gate(
            dataset_selection=args.dataset,
            config_path=args.config,
            config_dataset=config.dataset,
            config_input_dim=config.input_dim,
            config_attack_head_dim=config.attack_head_dim,
            config_task=config.task,
        )
    except ValueError as error:
        print(f"Hierarchical training request rejected: {error}")
        return 1

    print(
        f"Starting REAL centralized hierarchical training for {dataset_label}. "
        "Checkpoint selected by validation only; "
        "test evaluated once after selection."
    )
    if config.dataset == "cicids2018":
        print(
            "CICIDS2018 is large (~6.7M training rows); expect a longer run than "
            "UNSW. Monitor GPU and system memory, and keep this terminal open "
            "until it finishes."
        )

    try:
        from secureids.training.hierarchical_trainer import (
            HierarchicalExecutePreconditionError,
            run_hierarchical_training,
        )
    except ModuleNotFoundError as error:
        print(f"Hierarchical training requires PyTorch but an import failed: {error}")
        return 1

    try:
        outcome = run_hierarchical_training(
            args.config,
            execute=True,
            project_root=PROJECT_ROOT,
            overwrite=args.overwrite,
        )
    except HierarchicalExecutePreconditionError as error:
        print(str(error))
        print("Training did not start. Fix the issues above and re-run.")
        return 1
    except (HierarchicalTrainingConfigError, FileNotFoundError) as error:
        print(f"Hierarchical training failed: {error}")
        return 1

    test = outcome["test_bundle"]
    print(f"{dataset_label} hierarchical training completed in {outcome['duration_seconds']}s.")
    print(f"- device: {outcome['device']} (cuda_available={outcome['cuda_available']})")
    print(f"- best epoch: {outcome['best_epoch']} (epochs run: {outcome['epochs_run']})")
    print(f"- best val hierarchical score: {outcome['best_val_hierarchical_score']:.6f}")
    print(f"- test binary macro_f1: {test['binary']['macro_f1']:.6f}")
    print(
        f"- test attack-family macro_f1 (attack rows): "
        f"{test['attack_family']['macro_f1_on_attack_rows']:.6f}"
    )
    print(f"- test rare-class macro_f1: {test['rare_class']['rare_class_macro_f1']}")
    print(f"- checkpoint: {outcome['checkpoint']}")
    print(f"- test metrics json: {outcome['metrics_json']}")
    print(f"- training manifest: {outcome['manifest_json']}")
    print(f"- report: {outcome['report_md']}")
    return 0


def handle_train_attack_family_specialist(args: argparse.Namespace) -> int:
    """UNSW A9.9 attack-family specialist. Dry-run unless --execute is passed."""

    # Torch-free config validation first, so a bad config fails without torch.
    from secureids.training.attack_family_specialist_config import (
        AttackFamilySpecialistConfigError,
    )
    from secureids.training.attack_family_specialist_trainer import (
        AttackFamilySpecialistError,
        run_attack_family_specialist_training,
    )

    if not args.execute:
        try:
            outcome = run_attack_family_specialist_training(
                args.config, execute=False, project_root=PROJECT_ROOT
            )
        except (AttackFamilySpecialistConfigError, AttackFamilySpecialistError, FileNotFoundError) as error:
            print(f"A9.9 specialist dry-run rejected: {error}")
            return 1
        plan = outcome["plan"]
        print("A9.9 attack-family specialist DRY RUN (no --execute): no training, no writes.")
        print(f"- experiment: {plan['experiment']} (seed {plan['seed']})")
        print(f"- dataset: {plan['dataset']} input_dim={plan['input_dim']} families={plan['num_attack_families']}")
        print(f"- attack_rows_only: {plan['attack_rows_only']}; validation_only_selection: {plan['validation_only_selection']}")
        print(f"- frozen A9 router: {plan['frozen_a9_router_checkpoint']} (present={plan['frozen_a9_router_present']}, trainable=False)")
        print(f"- all processed input arrays present: {plan['all_inputs_present']}")
        print(f"- planned checkpoint: {plan['planned_outputs']['checkpoint']} (already exists={plan['checkpoint_already_exists']})")
        print(f"- planned results dir: {plan['planned_outputs']['result_dir']}")
        print(f"- planned report: {plan['planned_outputs']['report_md']}")
        print("Pass --execute only after main-control approval to run real training.")
        return 0

    print(
        "Starting REAL UNSW A9.9 attack-family specialist training "
        "(frozen A9 Head 1; validation-only selection; test not tuned). "
        "Pass --execute only after main-control approval."
    )
    try:
        from secureids.training.attack_family_specialist_trainer import (
            AttackFamilySpecialistExecutePreconditionError,
        )
        outcome = run_attack_family_specialist_training(
            args.config, execute=True, project_root=PROJECT_ROOT, overwrite=args.overwrite
        )
    except AttackFamilySpecialistExecutePreconditionError as error:
        print(f"A9.9 specialist training precondition failed: {error}")
        return 1
    except (AttackFamilySpecialistConfigError, AttackFamilySpecialistError, FileNotFoundError) as error:
        print(f"A9.9 specialist training failed: {error}")
        return 1
    except ModuleNotFoundError as error:
        print(f"A9.9 specialist training requires PyTorch but an import failed: {error}")
        return 1

    print(f"A9.9 specialist training completed. wrote_checkpoint={outcome.get('wrote_checkpoint')}")
    print(f"- checkpoint: {outcome.get('checkpoint')}")
    print(f"- best val attack-family macro_f1: {outcome.get('best_val_attack_family_macro_f1')}")
    return 0


def handle_train_frozen_embedding_specialist(args: argparse.Namespace) -> int:
    """UNSW A9.10 frozen-embedding specialist. Dry-run unless --execute is passed."""

    from secureids.training.frozen_embedding_specialist_config import (
        FrozenEmbeddingSpecialistConfigError,
    )
    from secureids.training.frozen_embedding_specialist_trainer import (
        FrozenEmbeddingSpecialistError,
        run_frozen_embedding_specialist_training,
    )

    if not args.execute:
        try:
            outcome = run_frozen_embedding_specialist_training(
                args.config, execute=False, project_root=PROJECT_ROOT
            )
        except (FrozenEmbeddingSpecialistConfigError, FrozenEmbeddingSpecialistError, FileNotFoundError) as error:
            print(f"A9.10 frozen-embedding specialist dry-run rejected: {error}")
            return 1
        plan = outcome["plan"]
        print("A9.10 frozen-A9-embedding specialist DRY RUN (no --execute): no training, no writes.")
        print(f"- experiment: {plan['experiment']} (seed {plan['seed']})")
        print(
            f"- dataset: {plan['dataset']} input_dim={plan['input_dim']} "
            f"embedding_dim={plan['embedding_dim']} families={plan['num_attack_families']}"
        )
        print(
            f"- head_type: {plan['head_type']} dropout={plan['dropout']} "
            f"weight_decay={plan['weight_decay']} label_smoothing={plan['label_smoothing']}"
        )
        print(
            f"- attack_rows_only: {plan['attack_rows_only']}; "
            f"validation_only_selection: {plan['validation_only_selection']}; no_test_tuning: {plan['no_test_tuning']}"
        )
        print(
            f"- frozen A9 checkpoint: {plan['frozen_a9_checkpoint']} "
            f"(present={plan['frozen_a9_checkpoint_present']}, trainable=False)"
        )
        print(f"- embedding source: {plan['embedding_source']}")
        print(f"- all processed input arrays present: {plan['all_inputs_present']}")
        print(
            f"- planned checkpoint: {plan['planned_outputs']['checkpoint']} "
            f"(already exists={plan['planned_outputs_exist']['checkpoint']})"
        )
        print(f"- planned results dir: {plan['planned_outputs']['result_dir']}")
        print(f"- planned report: {plan['planned_outputs']['report_md']}")
        print("Pass --execute only after main-control approval to run real training.")
        return 0

    print(
        "Starting REAL UNSW A9.10 frozen-embedding specialist training "
        "(A9 encoder/router frozen; validation-only selection; test not tuned). "
        "Pass --execute only after main-control approval."
    )
    try:
        from secureids.training.frozen_embedding_specialist_trainer import (
            FrozenEmbeddingSpecialistExecutePreconditionError,
        )

        outcome = run_frozen_embedding_specialist_training(
            args.config, execute=True, project_root=PROJECT_ROOT, overwrite=args.overwrite
        )
    except FrozenEmbeddingSpecialistExecutePreconditionError as error:
        print(f"A9.10 frozen-embedding specialist training precondition failed: {error}")
        return 1
    except (FrozenEmbeddingSpecialistConfigError, FrozenEmbeddingSpecialistError, FileNotFoundError) as error:
        print(f"A9.10 frozen-embedding specialist training failed: {error}")
        return 1
    except ModuleNotFoundError as error:
        print(f"A9.10 frozen-embedding specialist training requires PyTorch but an import failed: {error}")
        return 1

    print(f"A9.10 frozen-embedding specialist training completed. wrote_checkpoint={outcome.get('wrote_checkpoint')}")
    print(f"- checkpoint: {outcome.get('checkpoint')}")
    print(f"- best val generalization score: {outcome.get('best_val_generalization_score')}")
    print(f"- oracle attack-family macro_f1: {outcome.get('oracle_attack_family_macro_f1')}")
    print(f"- routed attack-family macro_f1: {outcome.get('routed_attack_family_macro_f1')}")
    return 0


def handle_validate_centralized_baselines(args: argparse.Namespace) -> int:
    from secureids.training.baseline_validation import (
        run_centralized_baseline_validation,
    )

    outcome = run_centralized_baseline_validation(project_root=PROJECT_ROOT)
    print(
        "SecureIDS V2 centralized baseline validation "
        f"{outcome['overall_status']}."
    )
    print("No training, retraining, model evaluation, checkpoint updates, or metric updates were run.")
    for dataset in outcome["datasets"]:
        print(f"- {dataset['dataset']}: {dataset['status']}")
    print(f"- training report check: {outcome['training_report_check']['status']}")
    print("Validation outputs written:")
    print(f"- {outcome['outputs']['json']}")
    print(f"- {outcome['outputs']['markdown']}")
    return 0 if outcome["overall_status"] == "PASS" else 1


def handle_federated_dry_run(args: argparse.Namespace) -> int:
    from secureids.federated.config import FederatedConfigError
    from secureids.federated.dry_run import run_fedavg_dry_run

    try:
        outcome = run_fedavg_dry_run(
            dataset=args.dataset,
            config_path=args.config,
            project_root=PROJECT_ROOT,
        )
    except (FederatedConfigError, FileNotFoundError) as error:
        print(f"FedAvg dry-run failed before validation output could be written: {error}")
        print("No training, test evaluation, checkpoints, or final metrics were created.")
        return 1

    print(f"SecureIDS V2 FedAvg dry-run {outcome['status']}.")
    print("No federated training, test evaluation, checkpoints, or final metrics were created.")
    print(f"- dataset: {outcome['dataset']}")
    print(f"- config: {outcome['config_path']}")
    print(f"- algorithm: {outcome['algorithm']}")
    print(f"- clients: {outcome['num_clients']}")
    print(f"- feature_count: {outcome['feature_count']}")
    print(f"- train labels planned: {outcome['train_label_count']}")
    print(f"- failed checks: {len(outcome['failed_checks'])}")
    print("Dry-run outputs written:")
    print(f"- {outcome['outputs_written']['json']}")
    print(f"- {outcome['outputs_written']['markdown']}")
    return 0 if outcome["status"] == "PASS" else 1


def handle_federated_plan(args: argparse.Namespace) -> int:
    from secureids.federated.hierarchical_plan import (
        HierarchicalFederatedPlanError,
        run_hierarchical_federated_plan_dry_run,
    )

    if args.execute:
        print("federated-plan is scaffold validation only. No training was started.")
        print("Use a future approved runner for real hierarchical FedAvg/security runs.")
        return 1

    try:
        outcome = run_hierarchical_federated_plan_dry_run(
            config_path=args.config,
            project_root=PROJECT_ROOT,
        )
    except (HierarchicalFederatedPlanError, FileNotFoundError) as error:
        print(f"Hierarchical federated plan validation failed: {error}")
        print("No training, evaluation, checkpoints, metrics, or final paths were touched.")
        return 1

    print(f"SecureIDS V2 hierarchical federated plan {outcome['status']}.")
    print("Dry-run only: no writes, training, evaluation, checkpoints, or metrics.")
    print(f"- dataset: {outcome['dataset']}")
    print(f"- config: {outcome['config_path']}")
    print(f"- protocol: {outcome['protocol_label']}")
    print(f"- aggregation: {outcome['aggregation_strategy']}")
    print(f"- attack: {outcome['attack_type']}")
    print(f"- clients: {outcome['num_clients']}")
    missing = [check for check in outcome["path_checks"] if not check["exists"]]
    print(f"- lightweight path checks: {len(outcome['path_checks'])}")
    print(f"- missing lightweight paths: {len(missing)}")
    print(f"- validation scope: {outcome['validation_scope']}")
    print(f"- execution ready: {outcome['execution_ready']}")
    for blocker in outcome['execution_blockers']:
        print(f'  - {blocker}')
    return 0


def handle_federated_train_hierarchical(args: argparse.Namespace) -> int:
    from secureids.federated.hierarchical_plan import HierarchicalFederatedPlanError
    from secureids.federated.hierarchical_training import (
        HierarchicalFedAvgTrainingError,
        run_hierarchical_fedavg_training,
    )

    try:
        outcome = run_hierarchical_fedavg_training(
            config_path=args.config,
            project_root=PROJECT_ROOT,
            execute=args.execute,
            overwrite=args.overwrite,
        )
    except (
        HierarchicalFederatedPlanError,
        HierarchicalFedAvgTrainingError,
        FileNotFoundError,
        ValueError,
    ) as error:
        print(f"Hierarchical FedAvg request rejected: {error}")
        print("No checkpoints, metrics, reports, result directories, or final paths were created.")
        return 1

    if not args.execute:
        print(f"SecureIDS V2 hierarchical FedAvg dry-run {outcome['status']}.")
        print("Dry-run only: no writes, training, evaluation, checkpoints, metrics, or reports.")
        print(f"- dataset: {outcome['dataset']}")
        print(f"- config: {outcome['config_path']}")
        print(f"- protocol: {outcome['protocol_label']}")
        print(f"- initialization: {outcome['initialization']}")
        print("- centralized checkpoint: reference-only")
        print("- expected outputs:")
        for name, path in outcome["expected_outputs"].items():
            print(f"  - {name}: {path}")
        existing = [
            check for check in outcome["planned_output_checks"] if check["exists"]
        ]
        print(f"- existing planned outputs: {len(existing)}")
        print(f"- validation scope: {outcome['validation_scope']}")
        print(f"- execution ready: {outcome['execution_ready']}")
        for blocker in outcome['execution_blockers']:
            print(f'  - {blocker}')
        return 0

    dataset_label = "CICIDS2018" if outcome.dataset == "cicids2018" else "UNSW-NB15"
    print(f"{dataset_label} hierarchical FedAvg training completed.")
    print(f"- checkpoint: {outcome.checkpoint_path}")
    print(f"- best round: {outcome.best_round}")
    print(f"- rounds run: {outcome.rounds_run}")
    print(f"- metrics: {outcome.metrics_path}")
    print(f"- manifest: {outcome.manifest_path}")
    print(f"- report: {outcome.report_path}")
    print("This FL checkpoint is experimental and not promoted.")
    return 0


def handle_federated_train(args: argparse.Namespace) -> int:
    from secureids.federated.training import (
        FederatedTrainingError,
        run_fedavg_training,
    )

    if not args.execute:
        print("FedAvg training requires --execute. No training was started.")
        return 1

    try:
        outcome = run_fedavg_training(
            dataset=args.dataset,
            config_path=args.config,
            project_root=PROJECT_ROOT,
            execute=args.execute,
            overwrite=args.overwrite,
        )
    except FederatedTrainingError as error:
        print(str(error))
        print("No federated training outputs were created by this failed request.")
        return 1
    except FileNotFoundError as error:
        print(f"Required file not found: {error}")
        print("No federated training outputs were created by this failed request.")
        return 1

    dataset_label = "CICIDS2018" if outcome.dataset == "cicids2018" else "UNSW-NB15"
    print(f"{dataset_label} FedAvg training completed.")
    print(f"- checkpoint: {outcome.checkpoint_path}")
    print(f"- best round: {outcome.best_round}")
    print(f"- rounds run: {outcome.rounds_run}")
    print(f"- device: {outcome.device} (cuda_available={outcome.cuda_available})")
    print(f"- test accuracy: {outcome.test_metrics['accuracy']:.4f}")
    print(f"- test macro_f1: {outcome.test_metrics['macro_f1']:.4f}")
    print(f"- metrics: {outcome.metrics_path}")
    print(f"- manifest: {outcome.manifest_path}")
    print(f"- report: {outcome.report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
