# Dataset and artifact distribution notices

Sources checked 22 October 2026. These notices do not relicense third-party data
or assert that ownership of the project code/checkpoints has been independently
established. No project-wide open-source license has been supplied by the owner.
Public visibility alone does not grant an open-source license. The owner must
select any desired code/model license before advertising open-source reuse.

## CSE-CIC-IDS2018

The Canadian Institute for Cybersecurity / University of New Brunswick explicitly
permits redistribution, republication and mirroring with dataset citation and
the required source/AWS link. Retain this attribution with processed row subsets.

- Dataset: CSE-CIC-IDS2018, Communications Security Establishment (CSE) and
  Canadian Institute for Cybersecurity (CIC), University of New Brunswick.
- Provider and license: https://www.unb.ca/cic/datasets/ids-2018.html
- AWS dataset page: https://registry.opendata.aws/cse-cic-ids2018/
- Paper: Iman Sharafaldin, Arash Habibi Lashkari, Ali A. Ghorbani,
  "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic
  Characterization", ICISSP, 2018.

The four CICIDS demo rows are preprocessed derivatives from the recovered
project's processed test split, not raw packet captures. Raw-source matching
remains unverified as described in the scientific notes. Provider permission
does not independently verify the provenance of the downloaded project files.

## UNSW-NB15

The official provider grants perpetual free academic research use, requires
citation of the five papers below, and requires agreement for commercial use.
It does not expressly give this project an unrestricted right to republish
processed samples or relicence trained artifacts.

- Provider / usage terms: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- Nour Moustafa and Jill Slay, "UNSW-NB15: a comprehensive data set for network
  intrusion detection systems (UNSW-NB15 network data set)", MilCIS, 2015.
- Nour Moustafa and Jill Slay, "The evaluation of Network Anomaly Detection
  Systems: Statistical analysis of the UNSW-NB15 data set and the comparison
  with the KDD99 data set", Information Security Journal, 2016.
- Nour Moustafa et al., "Novel geometric area analysis technique for anomaly
  detection using trapezoidal area estimation on large-scale networks", IEEE
  Transactions on Big Data, 2017.
- Nour Moustafa et al., "Big data analytics for intrusion detection system:
  statistical decision-making using finite dirichlet mixture models", Data
  Analytics and Decision Support for Cybersecurity, 2017, pp.127–156.
- Mohanad Sarhan, Siamak Layeghy, Nour Moustafa, Marius Portmann, "NetFlow
  Datasets for Machine Learning-Based Network Intrusion Detection Systems",
  BDTA/WiCON 2020 proceedings, 2021.

The complete seven-scenario archive is **private review only pending clarification
of UNSW republication/derived-artifact rights**. Do not upload that archive as a
public release asset until the owner has suitable permission. No assertion is
made that redistribution is prohibited; the grant was not established here.

Alternative: an eligible academic user can obtain the dataset from the provider
under its terms and request authorized access to the owner's original matching
processed artifacts/checkpoint. `tools/demo_package.py build` then extracts the
same three genuine rows locally. A generic fresh dataset download alone will
not reproduce these exact standardized rows: the matching historical artifacts
are required, and no retraining or guessed preprocessing is substituted.

## Release split

- `secureids-demo-cicids-v1.zip`: small four-scenario public-release candidate,
  with CICIDS attribution. Owner code/model ownership and release approval remain
  the owner's responsibility.
- `secureids-demo-seven-v1.zip`: complete seven-scenario private review bundle,
  including UNSW-derived artifacts; held from public distribution.
- Neither archive contains raw datasets, fitted joblib preprocessors, full test
  splits, optimizer state, or unnecessary historical checkpoints. The selected
  checkpoint bytes are retained exactly; no reserialization or model training
  occurs. No license grant for those checkpoints is invented.
