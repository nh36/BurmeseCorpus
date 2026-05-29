from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_corpus_release import build_corpus_release
from validate_corpus import validate_dataset


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class CorpusReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.unified_dir = self.root / "unified_release_v0_2"
        self.sagaing_dir = self.root / "sagaing_v0_1"
        self.output_dir = self.root / "corpus_release_v0_3"
        self.overrides_file = self.root / "recently_found_editorial_overrides.tsv"
        self.release_policy_file = self.root / "recently_found_release_policy.tsv"
        self.exception_review_file = self.root / "recently_found_exception_review.json"

    def build_minimal_release(self) -> None:
        unified_inscriptions = [
            {
                "record_id": "obi-v07-n0011-tx-p0030",
                "source_deposit": "zenodo_4321314",
                "source_volume": "7",
                "source_part": None,
                "source_inscription_number": "11",
                "source_page": "30",
                "face": "tx",
                "number_of_faces": 1,
                "title_original": "Structured Eleven",
                "title_transliteration": None,
                "date_original": None,
                "date_normalized": None,
                "place_of_origin_original": None,
                "place_id": None,
                "current_location_original": None,
                "donor_original": None,
                "subject_original": None,
                "language_original": "Old Burmese",
                "references_original": "OBI 11",
                "notes_original": None,
                "full_transliteration": None,
                "source_file": "vol7/11.txt",
                "information_source": None,
                "provenance": {"source_release": "fixture"},
                "editorial_relation_ids": ["edrel-rfi-12-embedded-in-previous-record"],
                "merge_status": "editorial_relation_target",
            }
        ]
        unified_lines = [
            {
                "record_id": "obi-v07-n0011-tx-p0030",
                "line_id": "obi-v07-n0011-tx-p0030-l001",
                "line_number_arabic": 1,
                "text_original": "structured line",
            }
        ]
        editorial_relations = [
            {
                "relation_id": "edrel-rfi-12-embedded-in-previous-record",
                "relation_type": "embedded_in_previous_vol7_record",
                "source_entry_number": "12",
                "source_entry_key": "12",
                "source_record_id": "rfi-z1302525-n0012",
                "source_title_original": "Source Twelve",
                "source_page": "34",
                "source_page_span": ["34"],
                "target_record_id": "obi-v07-n0011-tx-p0030",
                "target_title_original": "Structured Eleven",
                "release_action": "annotate_target_only",
                "line_action": "do_not_emit_duplicate_source_lines",
                "confidence": "high",
                "rationale": "Embedded in previous record.",
                "evidence_source": "fixture",
                "notes": "No split.",
            }
        ]
        sagaing_inscriptions = [
            {
                "record_id": "sagaing-z1203709-n0001",
                "source_deposit": "zenodo_1203709",
                "source_volume": None,
                "source_part": None,
                "source_inscription_number": "1",
                "source_page": "5",
                "face": None,
                "number_of_faces": 1,
                "title_original": "Sagaing One",
                "title_transliteration": None,
                "date_original": None,
                "date_normalized": None,
                "place_of_origin_original": None,
                "place_id": None,
                "current_location_original": None,
                "donor_original": None,
                "subject_original": None,
                "language_original": "Old Burmese",
                "references_original": None,
                "notes_original": None,
                "full_transliteration": None,
                "source_file": "sagaing.txt",
                "information_source": None,
                "provenance": {"source_release": "fixture"},
            }
        ]
        sagaing_lines = [
            {
                "record_id": "sagaing-z1203709-n0001",
                "line_id": "sagaing-z1203709-n0001-l001",
                "line_number_arabic": 1,
                "text_original": "sagaing line",
            }
        ]

        write_jsonl(self.unified_dir / "inscriptions.jsonl", unified_inscriptions)
        write_jsonl(self.unified_dir / "lines.jsonl", unified_lines)
        write_jsonl(self.unified_dir / "editorial_relations.jsonl", editorial_relations)
        write_jsonl(self.sagaing_dir / "inscriptions.jsonl", sagaing_inscriptions)
        write_jsonl(self.sagaing_dir / "lines.jsonl", sagaing_lines)
        self.overrides_file.write_text("source_entry_number\n12\n", encoding="utf-8")
        self.release_policy_file.write_text("source_entry_number\n12\n", encoding="utf-8")
        self.exception_review_file.write_text(json.dumps({"cases": ["12"]}), encoding="utf-8")

        build_corpus_release(
            unified_dir=self.unified_dir,
            sagaing_dir=self.sagaing_dir,
            overrides_file=self.overrides_file,
            release_policy_file=self.release_policy_file,
            exception_review_file=self.exception_review_file,
            output_dir=self.output_dir,
        )

    def test_build_corpus_release_combines_inputs_and_preserves_relations(self) -> None:
        self.build_minimal_release()

        inscriptions = [json.loads(line) for line in (self.output_dir / "inscriptions.jsonl").read_text(encoding="utf-8").splitlines()]
        record_ids = {record["record_id"] for record in inscriptions}
        self.assertIn("obi-v07-n0011-tx-p0030", record_ids)
        self.assertIn("sagaing-z1203709-n0001", record_ids)
        self.assertIn("edrel-rfi-12-embedded-in-previous-record", inscriptions[0]["editorial_relation_ids"])
        self.assertEqual(
            {record["source_layer"] for record in inscriptions},
            {"structured_obi", "sagaing_supplementary"},
        )

        editorial_relations = [
            json.loads(line)
            for line in (self.output_dir / "editorial_relations.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(editorial_relations), 1)
        self.assertEqual(editorial_relations[0]["target_record_id"], "obi-v07-n0011-tx-p0030")

        manifest = json.loads((self.output_dir / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_inscription_count"], 2)
        self.assertEqual(manifest["total_line_count"], 2)
        self.assertEqual(manifest["editorial_relation_count"], 1)
        self.assertEqual(manifest["validation_status"], "valid")

        validation = validate_dataset(self.output_dir)
        self.assertFalse(validation["errors"])

        with sqlite3.connect(self.output_dir / "corpus_release.sqlite") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM inscriptions").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM editorial_relations").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0], 3)

    def test_validate_dataset_detects_missing_relation_target(self) -> None:
        self.build_minimal_release()
        relations = [
            json.loads(line)
            for line in (self.output_dir / "editorial_relations.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        relations[0]["target_record_id"] = "obi-v07-n9999-tx-p9999"
        write_jsonl(self.output_dir / "editorial_relations.jsonl", relations)

        validation = validate_dataset(self.output_dir)

        self.assertTrue(any("unknown target_record_id" in error for error in validation["errors"]))

    def test_validate_dataset_detects_orphan_line(self) -> None:
        self.build_minimal_release()
        lines = [json.loads(line) for line in (self.output_dir / "lines.jsonl").read_text(encoding="utf-8").splitlines()]
        lines[0]["record_id"] = "missing-record"
        write_jsonl(self.output_dir / "lines.jsonl", lines)

        validation = validate_dataset(self.output_dir)

        self.assertTrue(any("unknown record_id" in error for error in validation["errors"]))

    def test_validate_dataset_detects_absolute_path_in_manifest(self) -> None:
        self.build_minimal_release()
        manifest = json.loads((self.output_dir / "release_manifest.json").read_text(encoding="utf-8"))
        manifest["input_releases"] = ["/Users/example/private/path"]
        (self.output_dir / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        validation = validate_dataset(self.output_dir)

        self.assertTrue(any("absolute local path" in error for error in validation["errors"]))

    def test_validate_dataset_detects_manifest_count_mismatch(self) -> None:
        self.build_minimal_release()
        manifest = json.loads((self.output_dir / "release_manifest.json").read_text(encoding="utf-8"))
        manifest["total_inscription_count"] = 99
        (self.output_dir / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        validation = validate_dataset(self.output_dir)

        self.assertTrue(any("total_inscription_count" in error for error in validation["errors"]))

    def test_validate_dataset_detects_sqlite_count_mismatch(self) -> None:
        self.build_minimal_release()
        with sqlite3.connect(self.output_dir / "corpus_release.sqlite") as conn:
            conn.execute("DELETE FROM inscriptions WHERE record_id = ?", ("sagaing-z1203709-n0001",))
            conn.commit()

        validation = validate_dataset(self.output_dir)

        self.assertTrue(any("SQLite export table inscriptions count mismatch" in error for error in validation["errors"]))


if __name__ == "__main__":
    unittest.main()
