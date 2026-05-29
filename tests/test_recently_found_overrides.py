from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_inventory import audit_recently_found_vs_vol7, load_editorial_overrides
from corpus_common import normalize_match_text


class RecentlyFoundOverrideTests(unittest.TestCase):
    def make_source_entry(self, number: int, title: str, page: int = 1) -> dict:
        return {
            "source_entry_number": number,
            "source_entry_key": str(number),
            "source_title": title,
            "source_title_normalized": normalize_match_text(title),
            "source_page": page,
        }

    def make_vol7_record(
        self,
        record_id: str,
        inscription_number: str,
        title: str,
        *,
        face: str = "text",
        page: str = "1",
    ) -> dict:
        return {
            "record_id": record_id,
            "source_inscription_number": inscription_number,
            "title_original": title,
            "face": face,
            "source_page": page,
        }

    def write_override_file(self, content: str) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        path = Path(tempdir.name) / "overrides.tsv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_editorial_overrides_reads_tsv(self) -> None:
        path = self.write_override_file(
            "source_entry_number\tsource_entry_key\toverride_type\ttarget_record_id\teditorial_status\tmatch_status\tmatch_confidence\trationale\tevidence_source\trelease_action\tnotes\n"
            "12\t12\tembedded_in_previous_record\tobi-v07-n0011-tx-p0030\tembedded_in_previous_vol7_record\teditorial_override\thigh\tExample rationale\tcasefile\taudit_only\tExample notes\n"
        )

        overrides = load_editorial_overrides(path)

        self.assertEqual(list(overrides), ["12"])
        self.assertEqual(overrides["12"]["target_record_id"], "obi-v07-n0011-tx-p0030")
        self.assertEqual(overrides["12"]["editorial_status"], "embedded_in_previous_vol7_record")

    def test_audit_applies_override_for_otherwise_missing_entry(self) -> None:
        source_entries = [self.make_source_entry(12, "ကန်သင်ဘုရားမြေကျောက်စာ", page=34)]
        vol7_entries = [self.make_vol7_record("obi-v07-n0011-tx-p0030", "11", "နက္ကာပြံကြီးမယားကျောက်စာ", page="30")]
        path = self.write_override_file(
            "source_entry_number\tsource_entry_key\toverride_type\ttarget_record_id\teditorial_status\tmatch_status\tmatch_confidence\trationale\tevidence_source\trelease_action\tnotes\n"
            "12\t12\tembedded_in_previous_record\tobi-v07-n0011-tx-p0030\tembedded_in_previous_vol7_record\teditorial_override\thigh\tEntry 12 is embedded in record 11.\tcasefile\taudit_only\tDo not treat as missing.\n"
        )
        overrides = load_editorial_overrides(path)

        rows, summary = audit_recently_found_vs_vol7(
            source_entries,
            vol7_entries,
            editorial_overrides=overrides,
            override_file=path,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_status"], "editorial_override")
        self.assertEqual(rows[0]["match_confidence"], "high")
        self.assertEqual(rows[0]["review_decision"], "embedded_in_previous_vol7_record")
        self.assertEqual(rows[0]["vol7_record_id"], "obi-v07-n0011-tx-p0030")
        self.assertEqual(rows[0]["vol7_inscription_number"], "11")
        self.assertEqual(rows[0]["vol7_title"], "နက္ကာပြံကြီးမယားကျောက်စာ")
        self.assertNotIn("missing_from_vol7", summary["status_counts"])
        self.assertEqual(summary["editorial_overrides"]["override_count"], 1)
        self.assertEqual(summary["editorial_overrides"]["applied_override_count"], 1)
        self.assertEqual(summary["editorial_overrides"]["missing_target_count"], 0)

    def test_audit_preserves_normal_behavior_without_override_file(self) -> None:
        rows, summary = audit_recently_found_vs_vol7(
            [self.make_source_entry(12, "ကန်သင်ဘုရားမြေကျောက်စာ", page=34)],
            [],
            editorial_overrides=load_editorial_overrides(Path("/tmp/does-not-exist-overrides.tsv")),
            override_file=Path("/tmp/does-not-exist-overrides.tsv"),
        )

        self.assertEqual(rows[0]["match_status"], "missing_from_vol7")
        self.assertEqual(rows[0]["review_decision"], "omission_in_volume7")
        self.assertEqual(summary["editorial_overrides"]["override_count"], 0)
        self.assertEqual(summary["editorial_overrides"]["applied_override_count"], 0)

    def test_audit_reports_missing_override_target(self) -> None:
        source_entries = [self.make_source_entry(37, "စူလာပိကြံသမီးကျောက်စာ", page=123)]
        path = self.write_override_file(
            "source_entry_number\tsource_entry_key\toverride_type\ttarget_record_id\teditorial_status\tmatch_status\tmatch_confidence\trationale\tevidence_source\trelease_action\tnotes\n"
            "37\t37\tembedded_in_previous_record\tobi-v07-n0036-tx-p0121\tembedded_in_previous_vol7_record\teditorial_override\thigh\tEntry 37 is embedded in record 36.\tcasefile\taudit_only\tDo not treat as missing.\n"
        )
        overrides = load_editorial_overrides(path)

        rows, summary = audit_recently_found_vs_vol7(
            source_entries,
            [],
            editorial_overrides=overrides,
            override_file=path,
        )

        self.assertEqual(rows[0]["match_status"], "target_missing")
        self.assertEqual(rows[0]["match_confidence"], "low")
        self.assertEqual(rows[0]["review_decision"], "embedded_in_previous_vol7_record")
        self.assertEqual(rows[0]["vol7_record_id"], "obi-v07-n0036-tx-p0121")
        self.assertEqual(summary["editorial_overrides"]["missing_target_count"], 1)
        self.assertTrue(summary["editorial_overrides"]["warnings"])


if __name__ == "__main__":
    unittest.main()
