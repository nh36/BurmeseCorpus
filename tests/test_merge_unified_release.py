from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from merge_unified_release import load_release_policy, merge_release


class MergeUnifiedReleaseTests(unittest.TestCase):
    def make_structured_record(self, record_id: str, title: str) -> dict:
        return {
            "record_id": record_id,
            "source_deposit": "4321314",
            "title_original": title,
            "source_file": f"{record_id}.txt",
            "provenance": {"created_from": "fixture"},
        }

    def make_source_record(
        self,
        record_id: str,
        canonical_record_id: str,
        source_entry_key: str,
        title: str,
        *,
        page: str = "1",
    ) -> dict:
        return {
            "record_id": record_id,
            "canonical_record_id": canonical_record_id,
            "source_entry_key": source_entry_key,
            "source_inscription_number": source_entry_key,
            "source_deposit": "1302525",
            "title_original": title,
            "source_title_normalized": title.casefold(),
            "source_page": page,
            "source_page_span": [page],
            "source_file": "supplementary.txt",
            "provenance": {"created_from": "fixture"},
        }

    def make_line(self, record_id: str, line_suffix: str, number: int, text: str) -> dict:
        return {
            "record_id": record_id,
            "line_id": f"{record_id}-{line_suffix}",
            "line_number_arabic": number,
            "text_original": text,
        }

    def write_policy_file(self, content: str) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        path = Path(tempdir.name) / "release_policy.tsv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_release_policy_reads_tsv(self) -> None:
        path = self.write_policy_file(
            "source_entry_number\tsource_entry_key\teditorial_status\ttarget_record_id\trelease_action\tline_action\tconfidence\trationale\tevidence_source\tnotes\n"
            "12\t12\tembedded_in_previous_vol7_record\tobi-v07-n0011-tx-p0030\tannotate_target_only\tdo_not_emit_duplicate_source_lines\thigh\tEntry 12 is embedded.\tcasefile\tDo not split.\n"
        )

        policy = load_release_policy(path)

        self.assertEqual(list(policy), ["12"])
        self.assertEqual(policy["12"]["target_record_id"], "obi-v07-n0011-tx-p0030")
        self.assertEqual(policy["12"]["release_action"], "annotate_target_only")

    def test_merge_suppresses_source_only_record_when_policy_requests_annotation_only(self) -> None:
        structured_inscriptions = [self.make_structured_record("obi-v07-n0011-tx-p0030", "Structured 11")]
        structured_lines = [self.make_line("obi-v07-n0011-tx-p0030", "l001", 1, "structured line")]
        source_inscriptions = [
            self.make_source_record("rfi-z1302525-n0012", "obi-v07-n0012-tx-p0034", "12", "Source 12", page="34")
        ]
        source_lines = [self.make_line("rfi-z1302525-n0012", "l001", 1, "source-only line")]
        policy = {
            "12": {
                "source_entry_number": "12",
                "source_entry_key": "12",
                "editorial_status": "embedded_in_previous_vol7_record",
                "target_record_id": "obi-v07-n0011-tx-p0030",
                "release_action": "annotate_target_only",
                "line_action": "do_not_emit_duplicate_source_lines",
                "confidence": "high",
                "rationale": "Entry 12 is embedded in record 11.",
                "evidence_source": "casefile",
                "notes": "Do not split the target record.",
            }
        }

        merged_inscriptions, merged_lines, editorial_relations, summary = merge_release(
            structured_inscriptions,
            structured_lines,
            source_inscriptions,
            source_lines,
            release_policy=policy,
        )

        self.assertEqual([record["record_id"] for record in merged_inscriptions], ["obi-v07-n0011-tx-p0030"])
        self.assertEqual(summary["added_from_source_only"], 0)
        self.assertEqual(summary["suppressed_source_only_by_policy"], 1)
        self.assertEqual(summary["editorial_relation_count"], 1)
        self.assertEqual(summary["target_records_annotated"], 1)
        self.assertFalse(summary["warnings"])
        self.assertEqual(len(merged_lines), 1)
        self.assertEqual(editorial_relations[0]["relation_type"], "embedded_in_previous_vol7_record")
        self.assertEqual(editorial_relations[0]["target_record_id"], "obi-v07-n0011-tx-p0030")
        self.assertEqual(editorial_relations[0]["release_action"], "annotate_target_only")
        self.assertEqual(
            merged_inscriptions[0]["editorial_relation_ids"],
            [editorial_relations[0]["relation_id"]],
        )

    def test_merge_preserves_normal_source_only_behavior_without_policy(self) -> None:
        structured_inscriptions = [self.make_structured_record("obi-v07-n0011-tx-p0030", "Structured 11")]
        structured_lines = [self.make_line("obi-v07-n0011-tx-p0030", "l001", 1, "structured line")]
        source_inscriptions = [
            self.make_source_record("rfi-z1302525-n0050", "obi-v07-n0050-tx-p0200", "50", "Source 50", page="200")
        ]
        source_lines = [self.make_line("rfi-z1302525-n0050", "l001", 1, "source-only line")]

        merged_inscriptions, merged_lines, editorial_relations, summary = merge_release(
            structured_inscriptions,
            structured_lines,
            source_inscriptions,
            source_lines,
            release_policy={},
        )

        self.assertEqual(len(merged_inscriptions), 2)
        self.assertEqual(summary["added_from_source_only"], 1)
        self.assertEqual(summary["suppressed_source_only_by_policy"], 0)
        self.assertEqual(summary["editorial_relation_count"], 0)
        self.assertEqual(len(editorial_relations), 0)
        self.assertEqual(len(merged_lines), 2)
        self.assertIn("obi-v07-n0050-tx-p0200", {record["record_id"] for record in merged_inscriptions})

    def test_merge_preserves_title_variant_relation_for_matched_record(self) -> None:
        structured_inscriptions = [self.make_structured_record("obi-v07-n0021-tx-p0064", "Structured 21")]
        structured_lines = [self.make_line("obi-v07-n0021-tx-p0064", "l001", 1, "structured line")]
        source_inscriptions = [
            self.make_source_record("rfi-z1302525-n0021", "obi-v07-n0021-tx-p0064", "21", "Variant Title 21", page="64")
        ]
        source_lines = [self.make_line("rfi-z1302525-n0021", "l001", 1, "source line")]
        policy = {
            "21": {
                "source_entry_number": "21",
                "source_entry_key": "21",
                "editorial_status": "title_variant_same_record",
                "target_record_id": "obi-v07-n0021-tx-p0064",
                "release_action": "annotate_target",
                "line_action": "use_structured_lines",
                "confidence": "high",
                "rationale": "Entry 21 is a title variant of record 21.",
                "evidence_source": "casefile",
                "notes": "Preserve both title forms.",
            }
        }

        merged_inscriptions, _merged_lines, editorial_relations, summary = merge_release(
            structured_inscriptions,
            structured_lines,
            source_inscriptions,
            source_lines,
            release_policy=policy,
        )

        self.assertEqual(summary["matched_with_source"], 1)
        self.assertEqual(summary["title_variant_matches"], 1)
        self.assertEqual(summary["editorial_relation_count"], 1)
        self.assertEqual(summary["target_records_annotated"], 1)
        self.assertEqual(merged_inscriptions[0]["merge_status"], "title_variant_match")
        self.assertEqual(merged_inscriptions[0]["source_title_original"], "Variant Title 21")
        self.assertEqual(merged_inscriptions[0]["editorial_title_variants"], ["Variant Title 21"])
        self.assertEqual(
            merged_inscriptions[0]["editorial_relation_ids"],
            [editorial_relations[0]["relation_id"]],
        )
        self.assertEqual(editorial_relations[0]["relation_type"], "title_variant_same_record")

    def test_merge_warns_and_falls_back_when_policy_target_is_missing(self) -> None:
        source_inscriptions = [
            self.make_source_record("rfi-z1302525-n0012", "obi-v07-n0012-tx-p0034", "12", "Source 12", page="34")
        ]
        source_lines = [self.make_line("rfi-z1302525-n0012", "l001", 1, "source-only line")]
        policy = {
            "12": {
                "source_entry_number": "12",
                "source_entry_key": "12",
                "editorial_status": "embedded_in_previous_vol7_record",
                "target_record_id": "obi-v07-n0011-tx-p0030",
                "release_action": "annotate_target_only",
                "line_action": "do_not_emit_duplicate_source_lines",
                "confidence": "high",
                "rationale": "Entry 12 is embedded in record 11.",
                "evidence_source": "casefile",
                "notes": "Do not split the target record.",
            }
        }

        merged_inscriptions, merged_lines, editorial_relations, summary = merge_release(
            [],
            [],
            source_inscriptions,
            source_lines,
            release_policy=policy,
        )

        self.assertEqual(summary["added_from_source_only"], 1)
        self.assertEqual(summary["suppressed_source_only_by_policy"], 0)
        self.assertEqual(summary["editorial_relation_count"], 0)
        self.assertEqual(len(editorial_relations), 0)
        self.assertEqual(len(merged_inscriptions), 1)
        self.assertEqual(len(merged_lines), 1)
        self.assertTrue(summary["warnings"])


if __name__ == "__main__":
    unittest.main()
