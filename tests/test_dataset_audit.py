from __future__ import annotations

import subprocess
import sys

from secureids.datasets.base import detect_label_column
from secureids.datasets.cicids2018 import CICIDS2018Adapter
from secureids.datasets.unsw_nb15 import UNSWNB15Adapter


def test_cicids_label_detection(tmp_path):
    csv_path = tmp_path / "cicids.csv"
    csv_path.write_text(
        "Flow Duration,Total Fwd Packets,Label\n1,2,BENIGN\n3,4,DoS\n",
        encoding="utf-8",
    )

    adapter = CICIDS2018Adapter(tmp_path)
    _, schema_audits = adapter.audit_schema()

    assert schema_audits[0].label_column == "Label"
    assert schema_audits[0].status == "ok"


def test_unsw_label_and_categorical_detection(tmp_path):
    csv_path = tmp_path / "unsw.csv"
    csv_path.write_text(
        "dur,proto,service,state,label\n0.1,tcp,http,FIN,0\n0.2,udp,dns,CON,1\n",
        encoding="utf-8",
    )

    adapter = UNSWNB15Adapter(tmp_path)
    _, schema_audits = adapter.audit_schema()
    audit = schema_audits[0]

    assert audit.label_column == "label"
    assert "dur" in audit.numeric_columns
    assert {"proto", "service", "state"}.issubset(set(audit.categorical_columns))


def test_detect_label_column_prefers_candidate_order():
    columns = ["attack_cat", "label"]

    assert detect_label_column(columns, ["label", "attack_cat"]) == "label"


def test_missing_raw_directory_handling(tmp_path):
    adapter = CICIDS2018Adapter(tmp_path / "missing")
    file_audits, schema_audits = adapter.audit_schema()

    assert file_audits[0].status == "missing_raw_dir"
    assert schema_audits == []


def test_cli_help_does_not_crash():
    result = subprocess.run(
        [sys.executable, "-m", "secureids.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "audit-data" in result.stdout
