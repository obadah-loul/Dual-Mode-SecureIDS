# CICIDS Hierarchical EXP03 1.25 — Safe Promotion Plan

Status: **Promotion executed and recorded.** The command blocks below are retained as historical planning
context and should not be rerun unless main control explicitly asks for a recovery or audit exercise.

Generated: `2026-06-25` · Companion:
`docs/experiments/CICIDS_HIERARCHICAL_EXP03_125_AGGREGATE_REVIEW.md`,
`results/audits/cicids_hierarchical_exp03_125_aggregate_review.json`.

---

## 0. Current Status After Promotion

**Promotion executed and recorded.** EXP03 1.25 seed999 is now the official CICIDS hierarchical final
model.

- Final checkpoint: `models/final/final_cicids_hierarchical.pt`
- Promoted source checkpoint:
  `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`
- Promotion record:
  `results/audits/cicids_hierarchical_exp03_125_final_promotion_record_20260625_160136.json`
- Backup directory:
  `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136`
- Rollback target:
  `results/audits/promotion_backups/cicids_exp03_125_seed999_20260625_160136/models_final/final_cicids_hierarchical.pt`
- Source SHA256:
  `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Final SHA256:
  `2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0`
- Hashes match: `True`

The future commands below are retained as historical promotion planning context. Do not rerun them
unless main control explicitly asks for a recovery or audit exercise.

## 1. What would be promoted

- **Source (selected, validation-based) checkpoint:**
  `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt`
- **Destination final checkpoint:** `models/final/final_cicids_hierarchical.pt`

### Source → destination mapping (all replacements are backup-gated)

| Source (EXP03 1.25 seed999) | Destination (final) |
| --- | --- |
| `models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt` | `models/final/final_cicids_hierarchical.pt` |
| `results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999/` (test_metrics.json, training_history.csv, binary_confusion_matrix.csv, attack_family_confusion_matrix.csv, per_class_attack_metrics.csv, rare_class_metrics.csv, hierarchical_routing_summary.json, training_config_snapshot.yaml, class_weight_snapshot.json, model_summary.json) | `results/final/hierarchical/cicids/` (same file set) |
| `results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed999.json` | `results/audits/hierarchical_training_manifest_cicids2018.json` |
| `docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED999_REPORT.md` | `docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md` (update, not blind copy — keep the documented-limitations section) |

## 2. Mandatory safety rules

1. **Backup before replace.** No destination file may be overwritten until a verified timestamped backup
   of the *current* baseline exists.
2. **Preserve the old baseline.** The current `final_cicids_hierarchical.pt` (1,961,387 bytes, last
   written 2026-06-25 00:22) and the current `results/final/hierarchical/cicids/`, baseline manifest, and
   baseline report are copied into the backup folder and kept.
3. **No `--overwrite` flag** is used anywhere (there is no training/CLI step in promotion; this is a file
   copy gated on a verified backup).
4. **If a destination file already exists** (it does — these are the live final artifacts): that is
   expected; replacement proceeds **only** after the backup of that exact file is verified present. If
   the backup step fails or the backup is missing/empty, **abort** and replace nothing.
5. **Verify after copy** (size + SHA-256 + JSON parse + metric spot-check) before declaring success.
6. **Keep the experiment artifacts** under `models/experiments/` and `results/experiments/` intact (do
   not delete/move them; they remain the provenance of the promoted model).

## 3. Future promotion commands — run ONLY AFTER MAIN-CONTROL APPROVAL

> Do not run now. Copy-paste only after approval. PowerShell, from the project root.

### Step 0 — only after main-control approval, set up and verify the source exists

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL
Set-Location C:\IDS\IDS_V2\Secure-Distributed-Intrusion-Detection_V2
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "results/audits/promotion_backups/cicids_pre_exp03_125_promotion_$ts"
$srcCkpt = "models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999.pt"
$srcResults = "results/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed999"
$srcManifest = "results/audits/hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed999.json"
if (-not (Test-Path $srcCkpt)) { throw "ABORT: source checkpoint missing" }
if (-not (Test-Path $srcResults)) { throw "ABORT: source results dir missing" }
if (-not (Test-Path $srcManifest)) { throw "ABORT: source manifest missing" }
```

### Step 1 — only after main-control approval, BACK UP the current baseline first

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL — backup must succeed before any replace
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item "models/final/final_cicids_hierarchical.pt"            "$backup/final_cicids_hierarchical.pt"
Copy-Item "results/final/hierarchical/cicids"                    "$backup/cicids_results" -Recurse
Copy-Item "results/audits/hierarchical_training_manifest_cicids2018.json" "$backup/hierarchical_training_manifest_cicids2018.json"
Copy-Item "docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md"          "$backup/CICIDS_HIERARCHICAL_TRAINING_REPORT.md"
# Verify the backup is present and non-empty BEFORE proceeding:
if (-not (Test-Path "$backup/final_cicids_hierarchical.pt")) { throw "ABORT: backup checkpoint missing" }
(Get-FileHash "models/final/final_cicids_hierarchical.pt" -Algorithm SHA256).Hash |
  Out-File -Encoding utf8 "$backup/baseline_checkpoint.sha256"
"Backed up baseline at $ts" | Out-File -Encoding utf8 "$backup/BACKUP_OK.txt"
```

### Step 2 — only after main-control approval AND a verified backup, replace the final artifacts

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL — requires $backup/BACKUP_OK.txt to exist
if (-not (Test-Path "$backup/BACKUP_OK.txt")) { throw "ABORT: backup not verified; do not replace" }
Copy-Item $srcCkpt    "models/final/final_cicids_hierarchical.pt"          # replaces (backup exists)
Copy-Item "$srcResults/*" "results/final/hierarchical/cicids/"             # replaces result files
Copy-Item $srcManifest "results/audits/hierarchical_training_manifest_cicids2018.json"
# Final report: update from the seed999 report but KEEP a documented-limitations section.
# (Do this as a reviewed edit, not a blind overwrite, so the SlowHTTPTest/FTP + tiny-class limits remain.)
```

### Step 3 — only after main-control approval, VALIDATE the promoted artifacts

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL
.\.venv\Scripts\python.exe -c "import json; d=json.load(open('results/final/hierarchical/cicids/test_metrics.json',encoding='utf-8')); a=d['test_metrics']['attack_family']['macro_f1_on_attack_rows']; print('promoted attack-family macro-F1:', round(a,6)); assert abs(a-0.875094)<1e-4, 'metric mismatch vs seed999'"
(Get-FileHash "models/final/final_cicids_hierarchical.pt" -Algorithm SHA256).Hash
(Get-FileHash $srcCkpt -Algorithm SHA256).Hash   # must equal the line above
```

### Step 4 — only after main-control approval, RECORD the promotion

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL — write an immutable promotion record
$record = @{
  promotion = "cicids_hierarchical_exp03_125_seed999_to_final"
  approved_by = "<main-control name/initials>"
  promoted_utc = (Get-Date).ToUniversalTime().ToString("o")
  source_checkpoint = $srcCkpt
  destination_checkpoint = "models/final/final_cicids_hierarchical.pt"
  backup_dir = $backup
  selection_basis = "highest validation hierarchical score (seed999 = 0.913383)"
  documented_limitations = "SlowHTTPTest/FTP feature-limited; Web-XSS/SQL-Injection tiny-support"
} | ConvertTo-Json
$record | Out-File -Encoding utf8 "results/audits/cicids_hierarchical_promotion_record.json"
```

## 4. Rollback (if anything looks wrong after promotion)

```powershell
# ONLY AFTER MAIN-CONTROL APPROVAL — restore the backed-up baseline
Copy-Item "$backup/final_cicids_hierarchical.pt" "models/final/final_cicids_hierarchical.pt"
Copy-Item "$backup/cicids_results/*" "results/final/hierarchical/cicids/"
Copy-Item "$backup/hierarchical_training_manifest_cicids2018.json" "results/audits/hierarchical_training_manifest_cicids2018.json"
Copy-Item "$backup/CICIDS_HIERARCHICAL_TRAINING_REPORT.md" "docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md"
```

## 5. What to send back after promotion (if approved later)

1. Confirmation that the backup folder exists and is verified (`$backup/BACKUP_OK.txt`,
   `baseline_checkpoint.sha256`).
2. The promoted final checkpoint SHA-256 = the seed999 source SHA-256 (proves an exact copy).
3. The promoted `results/final/hierarchical/cicids/test_metrics.json` headline metrics (attack-family
   macro-F1 0.875094, rare 0.780177, correct-attribution 0.913331, missed-as-benign 0.051221) matching
   seed999.
4. `results/audits/cicids_hierarchical_promotion_record.json` contents (who approved, when, source,
   backup path).
5. Confirmation the documented-limitations section is present in the updated final report.
6. Confirmation the EXP01/EXP02/EXP03 experiment artifacts were left intact.

## 6. Boundaries (this task)

No promotion, copy, overwrite, backup, training, preprocessing, XAI, Streamlit, Git, or final-artifact
modification was performed. The selected checkpoint exists; the final checkpoint is untouched. Next
decision: **main control approves or declines the safe final promotion above.**
