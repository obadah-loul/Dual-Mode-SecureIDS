# Local recovery and scientific corrections

22 October 2026, Asia/Dubai. This note supersedes conflicting current-status and
scientific claims in the historical documents. It does not rewrite historical
metrics, training snapshots, round histories, manifests, or model bytes.

## Recovered resources and identity

The reference package is `SecureIDS_Demo_Package`; repairs are isolated in sibling
`SecureIDS_Local_Repair`, detached at audited baseline
`afab2b0fe56c205201b930a99d5c999fe0489fd4`. All baseline source and evidence text
matched the downloaded package after line-ending normalization. No older source
replacement was needed. The previous read-only audit was reused.

The package has 935 files totaling 7,126,583,728 bytes, including 76 checkpoints
(34 under `models`, 42 under historical `results/experiments`), four joblib artifacts,
and binary/hierarchical processed arrays for CICIDS, UNSW A9, and UNSW A11.
The 34 small model files and four joblib files under `models` were copied into
the repair directory; historical experiment checkpoints remain externally stored.
JSON preprocessing metadata was copied. Large arrays were not duplicated.

All nine hierarchical splits were checked for dimensions, finite feature values,
binary label agreement, family mask consistency, and valid family IDs. Each
hierarchical X array is byte-identical to its corresponding binary X array.
This establishes consistency of the recovered processed artifacts, not identity
with absent raw CSV rows or freedom from duplicate/session leakage.

The selected centralized checkpoint SHA-256 values exactly match historical
frozen references:

| Model | SHA-256 |
|---|---|
| CICIDS centralized hierarchical | `2c154253162cf18cd25d78f2ab77127ce51c26488d1f9bcabc93baf591cd74c0` |
| UNSW centralized hierarchical | `5fe688bf43c68a7de63e106e0ad46f608bbae3d78dced6e90abbe2c6f956cbea` |

The CICIDS checkpoint metadata confirms EXP03 loss weight 1.25 and seed999,
matching its promoted result snapshot. The base training YAML remains an earlier
recipe and is marked accordingly. See `configs/selected_models.json` for all four
selected model identities. Federated checkpoint digests are local recovery
fingerprints; no independent historical digest was found. Their dataset IDs,
strict state shapes, and selected rounds (CICIDS19, UNSW16) are compatible with
the selected evidence. Seven replay scenarios execute real inference and XAI.

No raw dataset CSVs were present. Static joblib inspection found scikit-learn
1.7.2 in current UNSW/A11 and 1.9.0 in CICIDS/legacy UNSW. No joblib file was
unpickled. The tested environment supports processed-array inference; raw
transformation with these mixed historical artifacts remains unverified.

## Scientific interpretation

* **Malicious rate:** nominal Phase A 0.25 is floor-rounded to 1/5 = 0.20.
  Nominal 0.50 archival evidence used 2/5 = 0.40. Filenames and original values
  remain unchanged. Future round records report requested and realized fractions,
  counts, and participation separately. No exactly-25% experiment is claimed.
* **Attack semantics:** SignFlip multiplies absolute floating client model states,
  including floating buffers, by the attack scale. It does not flip the local
  parameter delta relative to the global state. Changing to delta poisoning would
  define a new protocol and require separately authorized experiments.
* **Evaluation:** validation selected checkpoints within runs, but documented
  test feedback informed later experiments and model choices. Historical results
  are exploratory; test independence cannot be restored retrospectively.
* **Family metrics:** main historical family macro-F1 scores use true attack rows,
  including binary misses. They are not routed deployment macro-F1. Routing
  counts and missed-as-benign rates must accompany them. The specialist routed
  implementation previously discarded `-1` predictions from confusion counts;
  future calculations now use an explicit missed-as-benign column, preserving
  false negatives and support. Historical specialist scores were not regenerated.
  Routed attribution accuracy is bounded by binary recall; macro-F1 does not
  have a universal ordering relative to oracle macro-F1.
* **Rare families:** [supplement](recovery/rare_class_supplement.csv) computes six
  means from saved per-class F1 values and the frozen rare-family definitions.
  These are derived summaries, not new predictions/evaluations. Four historical
  attack/defense bundles continue to contain null rare summaries. Corresponding
  future configs and fallback taxonomy resolution now supply canonical names.
* **Robustness:** Phase A is single-seed and uses a fixed malicious identity and
  nearly equal IID clients. It lacks a clean Trimmed Mean control. On UNSW the
  defended macro-F1 improves while the missed-attack rate worsens. This evidence
  does not support universal defense efficacy or deployment privacy guarantees.

## Security and execution contracts

The dashboard reports current fingerprints, with no independent trusted-reference
comparison. Prediction records bind sample, checkpoint, feature schema, and
family mapping hashes. A benign binary decision suppresses the family result and
family attribution; a missed true attack remains an incorrect routed outcome.

The aggregation hook distinguishes a local fingerprint self-check from comparison
against supplied pre-existing records. Supplied records must match client and
round identities and unchanged payloads. Neither case authenticates a sender.
Existing historical self-verification records cannot be upgraded into independent
integrity evidence. Hashing is not the Byzantine defense; Trimmed Mean is the
evaluated aggregator. There is no new network or cryptographic protocol.

All active checkpoint loaders explicitly use restricted `weights_only=True`,
with no legacy unrestricted fallback. Numeric arrays disallow pickle and writable
mapping modes. Nonfinite scores/updates, invalid labels, mismatched hierarchical
masks, and nonfinite inference/attribution outputs are rejected.

The runner rejects partial participation and alternative splitting at execution
instead of silently ignoring them. Configuration PASS and execution readiness
are separate. Readiness checks supported strategies, input shapes, source
availability, centralized reference digests, and output collisions. It is a
preflight, not proof a future full run will succeed. Existing historical outputs
correctly block reruns.

Future federated checkpoints/manifests record architecture, config snapshot/hash,
source tree hash, Git revision, runtime versions, input array hashes, and checkpoint
hash. These additions cannot recover missing historic execution provenance.

Base preprocessing now refuses existing outputs and exclusively creates the
preprocessor file. Hierarchical overwrite checks happen only after source and
label validation. Future UNSW ingestion checks canonical partition counts,
binary distributions, unique IDs, and matching schemas. Hierarchical label
reconstruction requires the same raw source bytes/order, split policy, and
binary array digests. Old binary manifests without that identity chain fail
closed; historical preprocessing must not be overwritten to manufacture it.
Canonical sizes/distributions alone are not independent dataset authenticity.

## Finding disposition

| Finding | Local disposition | Remaining boundary |
|---|---|---|
| F01 | Models, preprocessors, processed arrays recovered; demo runs | Raw CSVs absent; portable artifact distribution still needed |
| F02 | Requested/realized rate reporting corrected | Historical experiment remains 20%, not exact25% |
| F03 | Unconditional UI verification removed | No independent reference for live records |
| F04 | Self-check vs supplied comparison distinguished | No authenticated origin or historical update payloads |
| F05 | Claims corrected and test reuse disclosed | Cannot undo historical test-informed selection |
| F06 | Future UNSW source-role guards added | Raw source authenticity cannot be verified here |
| F07 | Full-state SignFlip explicitly identified | Delta attack would be a different experiment |
| F08 | Unsupported participation/split rejected at execution | Partial/non-IID execution remains unsupported |
| F09 | Numerical/label/mask guards and regressions added | No full benchmark reevaluation performed |
| F10 | Consistent canonical rare definitions; derived supplement | Original null entries preserved |
| F11 | Future execution/config/model/data identities recorded | Historical source/runtime chain incomplete |
| F12 | Python3.12 environment and dependencies pinned/tested | Mixed joblib versions not certified for raw inference |
| F13 | Stale absence/aggregation expectations repaired | Tests do not establish full research reproducibility |
| F14 | Promoted recipe verified against checkpoint and indexed | Earlier base recipe intentionally retained |
| F15 | Live gating and specialist missed-family accounting fixed | Historical specialist metrics remain unchanged |
| F16 | Restricted checkpoint loading and numeric array reads | Unsupported serialized objects fail closed |
| F17 | Output collisions/exclusive preprocessing writes guarded | Explicit overwrite remains an intentional destructive operation |
| F18 | Recovered array alignment checked; future identity gates | No raw-row identity or duplicate/session proof retrospectively |
| F19 | Configuration scope, readiness, blockers exposed | Preflight is not actual execution |

## Publication handoff

The local `verification/COMPLETION_REPORT.md`, `repair.patch`, test XML/logs,
artifact inventories, and preservation evidence are the review package. The
patch excludes arrays, models, the virtual environment, and machine-specific
paths. It does not by itself distribute the required demo artifacts.

Before publication, the Project Control Center should review the diff and these
scientific qualifications, define a licensed/versioned artifact delivery method,
and decide whether raw CSV preprocessing is required for the release. If it is,
recover the original raw files and compatible preprocessing environments. An
untouched confirmatory evaluation or a different poisoning protocol would be
new research requiring separate authorization; neither is required to use the
verified saved-scenario demo. No commit, branch, PR, push, or publication was made.
