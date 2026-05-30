from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_translation_witnesses import (
    SIP_WITNESS_ID,
    build_epigraphia_birmanica_review_rows,
    build_rescue_candidate_review_rows,
    build_sip_witness_inspection_rows,
    build_source_work_gap_rows,
    build_verification_report,
    update_plan_rows,
    verify_candidate_witness,
)


def source_row(**overrides: str) -> dict:
    row = {
        "source_work_key": "sipSelectionsPagan",
        "canonical_title": "Selections from the Inscriptions of Pagan",
        "short_title": "SIP",
        "authority_level": "book",
        "work_type": "book",
        "authors_editors": "Pe Maung Tin and G. H. Luce",
        "related_source_family_ids": "sf-sip",
        "related_acronyms": "SIP",
        "priority": "high",
    }
    row.update(overrides)
    return row


def candidate_row(**overrides: str) -> dict:
    row = {
        "witness_id": "w1",
        "source_work_key": "sipSelectionsPagan",
        "canonical_title": "Selections from the Inscriptions of Pagan",
        "candidate_file_label": "Selections from the Inscriptions of Pagan.pdf",
        "candidate_file_id": "sip-pdf",
        "match_type": "exact_title_filename",
        "match_confidence": "high",
    }
    row.update(overrides)
    return row


def classification_row(**overrides: str) -> dict:
    row = {
        "witness_type": "source_edition",
    }
    row.update(overrides)
    return row


def file_record(**overrides: str) -> dict:
    row = {
        "candidate_file_id": "sip-pdf",
        "candidate_file_label": "Selections from the Inscriptions of Pagan.pdf",
        "candidate_path_or_redacted_path": "data/local/bibliography_sources/sip/Selections from the Inscriptions of Pagan.pdf",
        "file_type": "pdf",
        "sha256_if_available": "abc",
        "local_cache_status": "copied",
        "source_folder_hints": "Burmese",
        "all_original_paths": "OBI_LIBRARY_ROOT:Thematic/Burmese/Selections from the Inscriptions of Pagan.pdf",
        "ocr_manifest_row": None,
        "ocr_snippets": [],
    }
    row.update(overrides)
    return row


class TranslationWitnessVerificationTests(unittest.TestCase):
    def test_weak_filename_match_becomes_weak_false_positive(self) -> None:
        uem_source = source_row(
            source_work_key="uemSelectionsPagan",
            authors_editors="U E Maung (ed.)",
            related_source_family_ids="sf-uem",
            related_acronyms="UEM",
        )
        candidate = candidate_row(
            source_work_key="uemSelectionsPagan",
            canonical_title="Selections from the Inscriptions of Pagan",
            candidate_file_label="Selections from the Inscriptions of Pagan - Luce and Pe Maung Tin.pdf",
        )

        with patch(
            "verify_translation_witnesses.load_ocr_text",
            return_value="SELECTIONS FROM THE INSCRIPTIONS OF PAGAN\nBY PE MAUNG TIN AND G.H. LUCE",
        ):
            verification, _ = verify_candidate_witness(
                uem_source,
                candidate,
                classification_row(),
                file_record(candidate_file_label=candidate["candidate_file_label"]),
            )

        self.assertEqual(verification["verification_status"], "weak_false_positive")
        self.assertEqual(verification["directness"], "weak_related_match")

    def test_plate_volume_is_confirmed_plate_witness(self) -> None:
        iob_source = source_row(
            source_work_key="lucePeMaungTinInscriptionsOfBurma",
            canonical_title="Inscriptions of Burma",
            short_title="IOB",
            authors_editors="G. H. Luce and U Pe Maung Tin",
        )
        candidate = candidate_row(
            source_work_key="lucePeMaungTinInscriptionsOfBurma",
            canonical_title="Inscriptions of Burma",
            candidate_file_label="Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
        )

        verification, _ = verify_candidate_witness(iob_source, candidate, classification_row(witness_type="plate_volume"), file_record(candidate_file_label=candidate["candidate_file_label"]))

        self.assertEqual(verification["verification_status"], "verified_plate_witness")
        self.assertEqual(verification["contains_plate_or_image_verified"], "confirmed")

    def test_title_page_snippet_supports_direct_witness_classification(self) -> None:
        source = source_row()
        candidate = candidate_row()
        mock_text = "Selections from the Inscriptions of Pagan\nBy Pe Maung Tin and G. H. Luce\nRangoon\n"

        with patch("verify_translation_witnesses.load_ocr_text", return_value=mock_text):
            verification, snippets = verify_candidate_witness(source, candidate, classification_row(), file_record())

        self.assertEqual(verification["verification_status"], "verified_direct_witness")
        self.assertEqual(verification["contains_edition_verified"], "confirmed")
        self.assertTrue(any(row["snippet_type"] == "title_page" for row in snippets))

    def test_periodical_container_cannot_become_direct_witness(self) -> None:
        source = source_row(
            source_work_key="journalBurmaResearchSociety",
            canonical_title="Journal of the Burma Research Society",
            short_title="JBRS",
            authority_level="periodical",
            work_type="periodical",
            authors_editors="",
            related_source_family_ids="sf-jbrs",
            related_acronyms="JBRS",
        )
        candidate = candidate_row(
            source_work_key="journalBurmaResearchSociety",
            canonical_title="Journal of the Burma Research Society",
            candidate_file_label="011041.pdf",
        )

        verification, _ = verify_candidate_witness(source, candidate, classification_row(witness_type="periodical_container"), file_record(candidate_file_label="011041.pdf"))

        self.assertEqual(verification["verification_status"], "needs_title_page_review")
        self.assertNotEqual(verification["directness"], "direct_source")

    def test_plan_status_moves_to_verified_direct_witness_found(self) -> None:
        plan_rows = [
            {
                "source_work_key": "sipSelectionsPagan",
                "canonical_title": "Selections from the Inscriptions of Pagan",
                "source_family_ids": "sf-sip",
                "work_type": "book",
                "translation_likelihood": "high",
                "edition_likelihood": "high",
                "plate_or_image_likelihood": "medium",
                "priority": "high",
                "evidence": "",
                "next_action": "",
                "notes": "",
                "discovery_status": "candidate_witnesses_found",
                "candidate_witness_count": "1",
                "classified_witness_count": "1",
                "confirmed_translation_witness_count": "0",
                "confirmed_edition_witness_count": "0",
                "confirmed_plate_witness_count": "0",
                "verified_direct_witness_count": "0",
                "verified_translation_witness_count": "0",
                "verified_edition_witness_count": "0",
                "verified_plate_witness_count": "0",
                "weak_false_positive_count": "0",
                "next_review_action": "",
            }
        ]
        updated = update_plan_rows(
            plan_rows,
            [source_row()],
            [candidate_row()],
            [
                {
                    "witness_id": "w1",
                    "source_work_key": "sipSelectionsPagan",
                    "verification_status": "verified_direct_witness",
                    "contains_translation_verified": "unknown",
                    "contains_edition_verified": "confirmed",
                }
            ],
            [],
            [
                {
                    "source_work_key": "sipSelectionsPagan",
                    "gap_type": "needs_translation_check",
                    "next_action": "Inspect sample entries.",
                }
            ],
        )

        self.assertEqual(updated[0]["discovery_status"], "verified_direct_witness_found")
        self.assertEqual(updated[0]["verified_direct_witness_count"], "1")

    def test_plan_status_moves_to_needs_direct_witness_search(self) -> None:
        plan_rows = [
            {
                "source_work_key": "uemSelectionsPagan",
                "canonical_title": "Selections from the Inscriptions of Pagan",
                "source_family_ids": "sf-uem",
                "work_type": "book",
                "translation_likelihood": "high",
                "edition_likelihood": "high",
                "plate_or_image_likelihood": "medium",
                "priority": "high",
                "evidence": "",
                "next_action": "",
                "notes": "",
                "discovery_status": "candidate_witnesses_found",
                "candidate_witness_count": "1",
                "classified_witness_count": "1",
                "confirmed_translation_witness_count": "0",
                "confirmed_edition_witness_count": "0",
                "confirmed_plate_witness_count": "0",
                "verified_direct_witness_count": "0",
                "verified_translation_witness_count": "0",
                "verified_edition_witness_count": "0",
                "verified_plate_witness_count": "0",
                "weak_false_positive_count": "0",
                "next_review_action": "",
            }
        ]
        updated = update_plan_rows(
            plan_rows,
            [source_row(source_work_key="uemSelectionsPagan", authors_editors="U E Maung (ed.)", related_source_family_ids="sf-uem", related_acronyms="UEM")],
            [candidate_row(source_work_key="uemSelectionsPagan")],
            [
                {
                    "witness_id": "w1",
                    "source_work_key": "uemSelectionsPagan",
                    "verification_status": "weak_false_positive",
                    "contains_translation_verified": "no",
                    "contains_edition_verified": "no",
                }
            ],
            [
                {
                    "source_work_key": "uemSelectionsPagan",
                    "matched_file_label": "Selections from the Inscriptions of Pagan - Luce and Pe Maung Tin.pdf",
                }
            ],
            [
                {
                    "source_work_key": "uemSelectionsPagan",
                    "gap_type": "needs_direct_witness",
                    "next_action": "Keep SIP excluded and continue targeted U E Maung search.",
                }
            ],
        )

        self.assertEqual(updated[0]["discovery_status"], "needs_direct_witness_search")

    def test_gap_row_marks_verified_sip_as_needs_translation_check(self) -> None:
        gap_rows = build_source_work_gap_rows(
            [source_row()],
            [candidate_row(witness_id=SIP_WITNESS_ID)],
            [
                {
                    "witness_id": SIP_WITNESS_ID,
                    "source_work_key": "sipSelectionsPagan",
                    "verification_status": "verified_direct_witness",
                    "contains_translation_verified": "unknown",
                    "contains_edition_verified": "confirmed",
                }
            ],
            [],
            [],
            [],
        )

        self.assertEqual(gap_rows[0]["gap_type"], "needs_translation_check")
        self.assertEqual(gap_rows[0]["current_status"], "verified_direct_witness_found")

    def test_sip_inspection_does_not_confirm_translation_without_explicit_evidence(self) -> None:
        verification_rows = [
            {
                "witness_id": SIP_WITNESS_ID,
                "source_work_key": "sipSelectionsPagan",
                "candidate_file_label": "Selections from the Inscriptions of Pagan.pdf",
                "title_page_evidence": "Selections from the Inscriptions of Pagan by Pe Maung Tin and G. H. Luce",
                "ocr_or_text_snippet": "Selections from the Inscriptions of Pagan",
            }
        ]
        rows = build_sip_witness_inspection_rows(
            [source_row()],
            verification_rows,
            {
                "sip-pdf": file_record(
                    candidate_file_label="Selections from the Inscriptions of Pagan.pdf",
                    ocr_snippets=[{"matched_heading": "title", "snippet_text": "Selections from the Inscriptions of Pagan by Pe Maung Tin and G. H. Luce"}],
                )
            },
        )

        self.assertTrue(rows)
        self.assertTrue(all(row["contains_translation"] == "false" for row in rows))
        self.assertTrue(any(row["contains_edition_or_transliteration"] == "true" for row in rows))

    def test_rescue_candidate_review_marks_chronicle_file_secondary(self) -> None:
        rows = build_rescue_candidate_review_rows(
            {
                "111029.pdf": file_record(
                    candidate_file_id="111029.pdf",
                    candidate_file_label="111029.pdf",
                    all_original_paths="OBI_LIBRARY_ROOT:ChroniclleTagaung_PeMaungTinLuce1921.pdf",
                )
            },
            [{"matched_file_id": "111029.pdf", "search_term": "Luce Pe Maung Tin Selections"}],
        )

        self.assertEqual(rows[0]["classification"], "secondary_article")

    def test_epigraphia_numbered_pdf_stays_review_only(self) -> None:
        rows = build_epigraphia_birmanica_review_rows(
            [],
            {
                "011041.pdf": file_record(
                    candidate_file_id="011041.pdf",
                    candidate_file_label="011041.pdf",
                    all_original_paths="OBI_LIBRARY_ROOT:ElementaryLahooAkaWa_Antisdel-1911.pdf",
                )
            },
        )

        row = next(row for row in rows if row["file_label"] == "011041.pdf")
        self.assertEqual(row["classification"], "unrelated_numbered_pdf")
        self.assertIn("title page", row["next_action"].lower())

    def test_report_counts_match_verification_rows(self) -> None:
        verification_rows = [
            {
                "witness_id": "w1",
                "source_work_key": "sipSelectionsPagan",
                "verification_status": "verified_direct_witness",
                "contains_translation_verified": "unknown",
                "contains_edition_verified": "confirmed",
            },
            {
                "witness_id": "w2",
                "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                "verification_status": "verified_plate_witness",
                "contains_translation_verified": "no",
                "contains_edition_verified": "no",
            },
        ]
        report = build_verification_report(
            verification_rows,
            [{"witness_id": "w1"}, {"witness_id": "w2"}],
            [{"source_work_key": "uemSelectionsPagan", "matched_file_label": "candidate.pdf"}],
            [
                {"source_work_key": "sipSelectionsPagan", "discovery_status": "verified_direct_witness_found"},
                {"source_work_key": "uemSelectionsPagan", "discovery_status": "needs_direct_witness_search"},
            ],
            [{"source_work_key": "uemSelectionsPagan", "gap_type": "needs_direct_witness"}],
            [{"witness_id": SIP_WITNESS_ID}],
            [{"matched_file_label": "ue-maung-clue.pdf"}],
            [{"matched_file_label": "tn-clue.pdf"}],
            [{"candidate_file_label": "111029.pdf"}],
            [{"file_label": "011041.pdf"}],
        )

        self.assertEqual(report["verified_witness_count"], 2)
        self.assertEqual(report["verified_direct_witness_count"], 1)
        self.assertEqual(report["verified_plate_witness_count"], 1)
        self.assertEqual(report["source_works_needing_direct_witness_count"], 1)
        self.assertEqual(report["source_work_witness_gap_count"], 1)


if __name__ == "__main__":
    unittest.main()
