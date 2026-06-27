# ENGINEERING_ARCHITECTURE_REVIEW.md

## 1. Purpose

This document records a project-quality architecture review completed before
enabling real preprocessing. The review checks structure, naming, documentation
language, CLI output, audit artifacts, dependencies, and safety boundaries so the
V2 repository remains professional, reproducible, and ready for the next
implementation phase.

## 2. Current Project Status

- V2 project skeleton is present.
- Design lock is present.
- Dataset schema audit framework is present.
- CICIDS2018 raw CSV files are under `data/raw/cicids2018`.
- UNSW-NB15 raw CSV files are under `data/raw/unsw_nb15`.
- Preprocessing design and dry-run validation are present.
- No real preprocessing has been run.
- No training has been run.
- No model checkpoints or final metrics exist.
- V2 is still not a Git repository.

## 3. Files And Folders Scanned

Scanned directly:

- `README.md`
- `.gitignore`
- `pyproject.toml`
- `requirements.txt`
- `configs/`
- `secureids/`
- `dashboard/`
- `docs/`
- `results/audits/`
- `tests/`

Raw data handling:

- `data/raw/` was inspected by file inventory and size only.
- Large CSV contents were not fully opened or processed.

Generated inventory:

- `results/audits/project_file_inventory.csv`

## 4. Issues Found

- README used milestone-style status sections instead of a final-facing project
  overview.
- CLI help and refusal text used implementation-phase labels that sounded
  informal.
- The preprocessing dry-run report generator used implementation-phase labels in
  report text and next-step recommendations.
- Dashboard text still described the project as a skeleton rather than an
  implementation-readiness demo surface.
- `.gitignore` did not exclude `.joblib` preprocessor artifacts.
- Development test dependency was not separated from runtime requirements.
- Some generated reports needed regeneration after wording cleanup.

## 5. Changes Made

- Rewrote `README.md` into a professional project overview with current status,
  dataset status, architecture, safe commands, reproducibility rules, and GitHub
  policy.
- Updated CLI help text and preprocessing refusal text to use professional
  wording.
- Updated preprocessing dry-run report generation to remove informal
  implementation-phase labels.
- Updated dashboard wording to state that final artifacts are unavailable rather
  than presenting the UI as an unfinished demo.
- Added `.joblib` to `.gitignore`.
- Added `requirements-dev.txt` with `pytest` as a development dependency.
- Clarified wording in `docs/PREPROCESSING_DESIGN.md`.
- Generated a safe project file inventory at
  `results/audits/project_file_inventory.csv`.
- Added this architecture review document.

## 6. Things Intentionally Not Changed

- Raw datasets were not moved, deleted, edited, or re-copied.
- V1 was not read as a writable project and was not modified.
- `docs/DESIGN_LOCK.md` was left intact where it records historical V1 context.
- No source layout was reorganized because current package boundaries are clear:
  dataset logic, preprocessing utilities, reporting, CLI, and dashboard are
  already separated.
- No dependencies were installed during this review.
- No Git repository was initialized.

## 7. Current Architecture Summary

- `secureids/datasets/` contains dataset-specific adapters and schema-audit
  logic for CICIDS2018 and UNSW-NB15.
- `secureids/preprocessing/` contains reusable preprocessing utilities and
  dry-run validation logic.
- `secureids/reporting/` contains audit and documentation output helpers.
- `secureids/cli.py` is a thin command layer for safe audit and dry-run
  validation commands.
- `configs/` contains dataset and preprocessing configuration skeletons.
- `docs/` contains design, compatibility, audit, dry-run, and architecture
  review documentation.
- `results/audits/` contains audit outputs and dry-run validation reports.
- `dashboard/app.py` remains a minimal demo entry point until final artifacts
  exist.

## 8. Remaining Risks

- Real preprocessing is still pending and must be implemented with strict
  train-only fitting for imputers, encoders, and scalers.
- The current environment does not include `pytest`; automated tests require the
  development dependency to be installed later.
- Generated audit reports currently use absolute local paths because they record
  the execution environment. This is acceptable for local evidence, but final
  reproducibility documentation should also include relative paths.
- Model, federated learning, security, attack simulation, robust aggregation,
  explainability, and dashboard result-loading modules are still skeletons.

## 9. Next Recommended Step

Review and approve the preprocessing dry-run validation outputs, then begin the
preprocessing implementation phase. The next phase should create processed
arrays and preprocessor artifacts only after explicit approval.

## 10. Safety Confirmation

- No preprocessing was run.
- No training was run.
- No checkpoints were created.
- No model metrics were created.
- V1 was not modified.
- No Git commit was created.
- No GitHub push occurred.
