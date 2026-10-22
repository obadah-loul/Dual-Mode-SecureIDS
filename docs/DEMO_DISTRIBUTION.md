# Minimal demonstration distribution

The owner-authorized [v0.1.0 release](https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/tag/v0.1.0)
provides the [CICIDS demo archive](https://github.com/obadah-loul/Dual-Mode-SecureIDS/releases/download/v0.1.0/secureids-demo-cicids-v1.zip).
`configs/demo_artifacts.json` records its exact hash and download URL. The UNSW
seven-scenario bundle remains private with no public download URL. At approximately
1.81/3.72 MB, these need neither Git LFS nor an external cloud account. The source
contains the builder/installer, expected hashes, and rights notices.

## Contents and boundaries

For each included dataset the bundle contains one selected clean federated
checkpoint, four numeric arrays (features, binary labels, family labels, mask),
three feature/label JSON files, and `demo_samples.json`. The latter maps compact
storage to the exact original test indices and records original float32 row
hashes and source test-set size. A bundle manifest hashes every payload file.

The seven-row bundle contains only CICIDS Bot, DDoS-HOIC, DoS-GoldenEye,
SSH-Bruteforce and UNSW Exploits, Generic, Reconnaissance records already used in
the verified dashboard. There are no synthetic/padded rows and no cached model
predictions. The model computes inference and gradients at runtime. Checkpoints
are byte-for-byte copies of the selected recovered artifacts, not new exports.

Fitted joblib preprocessors are unnecessary because inputs are already normalized
and encoded. Their mixed historical scikit-learn versions do not affect this
replay. This is not an alternative raw-traffic preprocessing service or a
reproducible full experiment package. Full benchmark evidence remains historical.

## Rebuild from legitimately held matching artifacts

Use a Python3.12 environment with the project requirements. Put the authorized
processed sources under a root with `data/processed/<dataset>/hierarchical/`,
including X_test and its three original label/mask arrays and three JSON metadata
files. Put the two selected weights at the paths in `configs/selected_models.json`.

```console
python tools/demo_package.py build --artifact-root authorized-artifacts --models-root . --datasets cicids2018 --output output/secureids-demo-cicids-v1.zip
python tools/demo_package.py build --artifact-root authorized-artifacts --models-root . --datasets all --output output/secureids-demo-seven-v1.zip
```

The builder never overwrites an archive, trains, fits a transform, or deserializes
weights. ZIP timestamps/order are fixed for repeatability. Identical input bytes
produce identical output with the same Python/zlib toolchain. Its output hash
must match the catalog before it can be substituted for the reviewed bundle.
No official full dataset download or preprocessing rerun is performed by the tool.

For UNSW, a fresh provider CSV download alone is insufficient to reconstruct
these exact normalized samples. Obtain authorized matching historical processed
artifacts and the selected checkpoint, or obtain suitable permission for the
prepared compact bundle. Do not guess transforms, synthesize data, retrain, or
claim another row selection reproduces these seven demonstrations.

## Publication boundaries and future releases

1. Review the additional/cumulative patch, compact-package tests, rights notices,
   and public-candidate file manifest from the private review ZIP.
2. Confirm the owner's authority to distribute the project's code and weights;
   select a code/model license if open-source reuse is intended. Dataset grants
   are separate and the project does not override them.
3. Source and the CICIDS archive are published with owner authorization at v0.1.0.
   Retain attribution in future owner-approved releases. Keep the full seven-scenario ZIP
   private until UNSW republication/derived-artifact rights are clarified.
4. Set the relevant `download_url` field and README link to the actual uploaded
   asset, and verify its bytes against `SHA256SUMS-demo.txt`. Do not advertise a
   nonexistent release/tag or change pinned hashes without review.
5. Treat the independent review ZIP as private: it deliberately contains original
   local-path evidence and the held seven-scenario bundle. It is not a public
   GitHub asset.

The separate public-source candidate ZIP is assembled from an explicit source
file list, not by zipping the working directory. It excludes `.git`, local
configuration, models/datasets, environments, caches, local evidence and ZIPs.
The artifact candidate contains only its allowlisted compact files. The private
review ZIP includes exact original evidence, its hashes, both patches, and
packaging validation; original evidence is never silently redacted or altered.

One existing audit file, `results/audits/unsw_a9_vs_a9_6_comparison.json`, contained
a local instruction-attachment command path. Only `commands_run[0]` is replaced
by an explanatory privacy note in the publication working copy; all scientific
values and other fields are unchanged. The exact original bytes and before/after
hashes are retained in the private review ZIP. The original downloaded package
is untouched. Review patches also belong in that private ZIP, since removed
context can contain the old path. Do not publish the review ZIP as a release asset.
