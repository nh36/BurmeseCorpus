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
    annotate_iob_text_search_rows,
    build_direct_query_search_rows,
    build_epigraphia_fascicle_coverage_rows,
    build_epigraphia_promoted_verification_rows,
    build_epigraphia_birmanica_review_rows,
    build_rescue_candidate_review_rows,
    build_search_hunt_rows,
    build_sip_witness_inspection_rows,
    build_source_witness_content_profile_rows,
    build_source_work_gap_rows,
    build_verification_report,
    ensure_epigraphia_candidate_and_classification_rows,
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
                    "gap_type": "has_verified_edition_but_translation_unknown",
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

    def test_gap_row_marks_verified_sip_as_verified_edition_translation_unknown(self) -> None:
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
            [],
        )

        self.assertEqual(gap_rows[0]["gap_type"], "has_verified_edition_but_translation_unknown")
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
        sample_entry = next(row for row in rows if row["inspection_area"] == "sample_entry")
        self.assertEqual(sample_entry["inspection_status"], "attempted_no_recoverable_text")
        self.assertEqual(sample_entry["contains_translation"], "unknown")
        self.assertEqual(sample_entry["contains_edition_or_transliteration"], "unknown")
        self.assertTrue(any(row["contains_edition_or_transliteration"] == "confirmed" for row in rows))

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

    def test_epigraphia_fascicle_can_be_promoted_to_verified_direct_witness(self) -> None:
        review_rows = [
            {
                "witness_id": "epigraphiaBirmanica--vol1",
                "file_label": "Duroiselle - Epigraphica Birmanica1.pdf",
                "source_work_key": "epigraphiaBirmanica",
                "probable_volume_or_fascicle": "Vol. 1",
                "title_page_snippet": "Epigraphica Birmanica Vol. I",
                "contents_snippet": "Preface and plates",
                "contains_translation": "false",
                "contains_edition_or_transliteration": "true",
                "contains_plate_or_image": "false",
                "classification": "actual_eb_fascicle",
                "confidence": "high",
                "next_action": "Promote after title-page confirmation.",
                "notes": "Local file label identifies an Epigraphica Birmanica fascicle directly.",
            }
        ]
        candidates, classifications = ensure_epigraphia_candidate_and_classification_rows(
            [],
            [],
            source_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", short_title="EB"),
            review_rows,
            {
                "eb-vol1": file_record(
                    candidate_file_id="eb-vol1",
                    candidate_file_label="Duroiselle - Epigraphica Birmanica1.pdf",
                    all_original_paths="OBI_LIBRARY_ROOT:Epigraphica Birmanica1.pdf",
                )
            },
        )
        promoted_rows, _ = build_epigraphia_promoted_verification_rows(
            review_rows,
            source_row(source_work_key="epigraphiaBirmanica", canonical_title="Epigraphia Birmanica", short_title="EB"),
            candidates,
        )
        coverage_rows = build_epigraphia_fascicle_coverage_rows(
            review_rows,
            [
                {
                    "source_work_key": "epigraphiaBirmanica",
                    "witness_id": "epigraphiaBirmanica--vol1",
                    "file_label": "Duroiselle - Epigraphica Birmanica1.pdf",
                    "verified_witness_type": "source_edition",
                    "content_profile_status": "confirmed",
                    "title_page_status": "confirmed",
                    "contents_status": "unknown",
                    "sample_entry_status": "unknown",
                    "translation_status": "unknown",
                    "edition_status": "confirmed",
                    "notes_commentary_status": "unknown",
                    "plate_image_status": "unknown",
                    "catalogue_metadata_status": "unknown",
                    "coverage_scope": "whole_work",
                    "confidence": "high",
                    "next_action": "Inspect contents.",
                    "notes": "",
                }
            ],
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(classifications[0]["witness_type"], "source_edition")
        self.assertEqual(promoted_rows[0]["verification_status"], "verified_direct_witness")
        self.assertEqual(promoted_rows[0]["contains_edition_verified"], "confirmed")
        self.assertEqual(coverage_rows[0]["contains_translation"], "unknown")

    def test_iob_plate_search_rows_are_false_positives_for_text(self) -> None:
        rows = annotate_iob_text_search_rows(
            [
                {
                    "query": "Inscriptions of Burma text",
                    "matched_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                    "matched_file_id": "iob-plates",
                    "match_type": "filename",
                    "match_confidence": "medium",
                    "short_evidence": "plate volume",
                    "searched_sources": "local_file_manifest",
                    "search_scope": "filename search",
                    "search_date_or_run_id": "test",
                    "search_result_status": "candidate_found",
                    "recommended_action": "Keep searching for text volume.",
                    "notes": "",
                },
                {
                    "query": "Inscriptions of Burma 1963 text",
                    "matched_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates6-20)_1963.pdf",
                    "matched_file_id": "iob-plates-2",
                    "match_type": "filename",
                    "match_confidence": "medium",
                    "short_evidence": "plate volume",
                    "searched_sources": "local_file_manifest",
                    "search_scope": "filename search",
                    "search_date_or_run_id": "test",
                    "search_result_status": "candidate_found",
                    "recommended_action": "Keep searching for text volume.",
                    "notes": "",
                },
            ]
        )

        for row in rows:
            self.assertEqual(row["is_plate_witness_candidate"], "true")
            self.assertEqual(row["is_text_witness_candidate"], "false")
            self.assertEqual(row["false_positive_for_text"], "true")
            self.assertEqual(
                row["recommended_action"],
                "Retain as a plate witness; continue searching for the companion text volume.",
            )

    def test_iob_plate_content_profile_uses_not_applicable_sample_entry(self) -> None:
        rows = build_source_witness_content_profile_rows(
            [
                {
                    "witness_id": "iob-plates",
                    "source_work_key": "lucePeMaungTinInscriptionsOfBurma",
                    "candidate_file_label": "Luce&PeMaungTin_InscriptionsOfBurma(Plates3,4,5)_1960.pdf",
                    "verification_status": "verified_plate_witness",
                    "verified_witness_type": "plate_volume",
                    "title_page_evidence": "Inscriptions of Burma Plates 3, 4, 5",
                    "confidence": "high",
                }
            ],
            [],
            [],
            {},
        )

        self.assertEqual(rows[0]["sample_entry_status"], "not_applicable")
        self.assertEqual(rows[0]["translation_status"], "not_applicable")
        self.assertEqual(
            rows[0]["next_action"],
            "Retain as a plate/facsimile witness and continue hunting the companion text volume.",
        )

    def test_missing_core_hunt_preserves_no_hit_rows_with_coverage(self) -> None:
        rows = build_search_hunt_rows(
            "uemSelectionsPagan",
            [("U E Maung", "author_name")],
            {
                "unrelated-pdf": file_record(
                    candidate_file_id="unrelated-pdf",
                    candidate_file_label="Unrelated witness.pdf",
                    all_original_paths="OBI_LIBRARY_ROOT:Unrelated witness.pdf",
                )
            },
            [],
            [],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_type"], "not_found")
        self.assertEqual(rows[0]["match_confidence"], "low")
        self.assertEqual(rows[0]["search_result_status"], "not_found")
        self.assertTrue(rows[0]["searched_sources"])
        self.assertTrue(rows[0]["search_scope"])
        self.assertTrue(rows[0]["search_date_or_run_id"])

    def test_missing_core_hunt_marks_sip_row_as_known_uem_false_positive(self) -> None:
        rows = build_search_hunt_rows(
            "uemSelectionsPagan",
            [("Selections from the Inscriptions of Pagan U E Maung", "title_variant")],
            {
                "sip-pdf": file_record(
                    candidate_file_id="sip-pdf",
                    candidate_file_label="Luce 1928 inscriptions of Pagan.pdf",
                    all_original_paths="OBI_LIBRARY_ROOT:Luce 1928 inscriptions of Pagan.pdf",
                )
            },
            [],
            [
                {
                    "source_work_key": "uemSelectionsPagan",
                    "candidate_file_label": "Luce 1928 inscriptions of Pagan.pdf",
                    "verification_status": "weak_false_positive",
                }
            ],
        )

        self.assertEqual(rows[0]["is_known_false_positive"], "true")
        self.assertIn("do not promote", rows[0]["recommended_action"].casefold())

    def test_direct_search_rows_include_search_status_metadata(self) -> None:
        rows = build_direct_query_search_rows(
            ["U E Maung"],
            {
                "uem-clue": file_record(
                    candidate_file_id="uem-clue",
                    candidate_file_label="Frasch bibliography note.pdf",
                    ocr_snippets=[{"matched_heading": "bibliography", "snippet_text": "U E Maung, Selections from the Inscriptions of Pagan, Rangoon 1958"}],
                )
            },
            clue_source_work_key="uemSelectionsPagan",
            raw_reference_rows=[
                {
                    "source_work_key": "uemSelectionsPagan",
                    "raw_reference_string": "UEM, p. 4",
                    "source_family_id": "sf-uem",
                }
            ],
        )

        self.assertEqual(rows[0]["search_result_status"], "bibliographic_clue_found")
        self.assertTrue(rows[0]["searched_sources"])
        self.assertTrue(rows[0]["search_scope"])
        self.assertTrue(rows[0]["search_date_or_run_id"])

    def test_report_counts_match_verification_rows(self) -> None:
        verification_rows = [
            {
                "witness_id": SIP_WITNESS_ID,
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
        sip_inspection_rows = [
            {
                "witness_id": SIP_WITNESS_ID,
                "inspection_area": "title_page",
                "inspection_status": "confirmed",
                "contains_translation": "unknown",
                "contains_edition_or_transliteration": "confirmed",
                "contains_notes_or_commentary": "unknown",
                "evidence_snippet": "Selections from the Inscriptions of Pagan",
            },
            {
                "witness_id": SIP_WITNESS_ID,
                "inspection_area": "sample_entry",
                "inspection_status": "attempted_no_recoverable_text",
                "contains_translation": "unknown",
                "contains_edition_or_transliteration": "unknown",
                "contains_notes_or_commentary": "unknown",
                "evidence_snippet": "",
            },
        ]
        content_profile_rows = [
            {
                "source_work_key": "sipSelectionsPagan",
                "witness_id": SIP_WITNESS_ID,
                "file_label": "Selections from the Inscriptions of Pagan.pdf",
                "verified_witness_type": "source_edition",
                "content_profile_status": "confirmed",
                "title_page_status": "confirmed",
                "contents_status": "unknown",
                "sample_entry_status": "attempted_no_recoverable_text",
                "translation_status": "unknown",
                "edition_status": "confirmed",
                "notes_commentary_status": "unknown",
                "plate_image_status": "not_applicable",
                "catalogue_metadata_status": "unknown",
                "coverage_scope": "whole_work",
                "confidence": "high",
                "next_action": "Retry targeted sample-entry OCR.",
                "notes": "",
            },
            {
                "source_work_key": "epigraphiaBirmanica",
                "witness_id": "eb1",
                "file_label": "Duroiselle - Epigraphica Birmanica1.pdf",
                "verified_witness_type": "source_edition",
                "content_profile_status": "confirmed",
                "title_page_status": "confirmed",
                "contents_status": "unknown",
                "sample_entry_status": "unknown",
                "translation_status": "unknown",
                "edition_status": "confirmed",
                "notes_commentary_status": "unknown",
                "plate_image_status": "unknown",
                "catalogue_metadata_status": "unknown",
                "coverage_scope": "whole_work",
                "confidence": "high",
                "next_action": "Inspect contents.",
                "notes": "",
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
            sip_inspection_rows,
            content_profile_rows,
            [{"witness_id": "eb1", "inspection_area": "title_page"}],
            [{"matched_file_label": "ue-maung-clue.pdf"}],
            [{"matched_file_label": "tn-clue.pdf"}],
            [{"matched_file_label": "iob-text.pdf", "search_result_status": "candidate_found", "is_text_witness_candidate": "false", "false_positive_for_text": "true"}],
            [{"matched_file_label": "", "search_result_status": "not_found"}],
            [{"source_work_key": "uemSelectionsPagan", "query": "U E Maung", "search_result_status": "not_found"}],
            [{"candidate_file_label": "111029.pdf"}],
            [{"file_label": "011041.pdf"}],
            [{"witness_id": "eb1"}],
        )

        self.assertEqual(report["verified_witness_count"], 2)
        self.assertEqual(report["verified_direct_witness_count"], 1)
        self.assertEqual(report["verified_plate_witness_count"], 1)
        self.assertEqual(report["source_works_needing_direct_witness_count"], 1)
        self.assertEqual(report["source_work_witness_gap_count"], 1)
        self.assertEqual(report["eb_fascicle_coverage_count"], 1)
        self.assertFalse(report["sip_sample_entry_inspected"])


if __name__ == "__main__":
    unittest.main()
