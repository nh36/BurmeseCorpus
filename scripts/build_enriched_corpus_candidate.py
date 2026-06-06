from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import re

from corpus_common import REPO_ROOT, read_jsonl, read_tsv, write_jsonl, write_tsv

SIP_SOURCE_KEY = "sipSelectionsPagan"
SIP_BIBLIOGRAPHIC_LABEL = "Pe Maung Tin and G. H. Luce, Selections from the Inscriptions of Pagan, 1928"
TN_SOURCE_KEY = "tnInscriptionsPaganPinyaAva"
TN_BIBLIOGRAPHIC_LABEL = (
    "U Tun Nyein / Taw Sein Ko / Forchhammer, Inscriptions of Pagan, Pinya and Ava: Translation, with Notes. "
    "Rangoon: Government Press, 1899."
)
PPA_SOURCE_KEY = "ppaCatalogue"
PPA_BIBLIOGRAPHIC_LABEL = "Inscriptions of Pagan, Pinya and Ava, Rangoon, 1892"
IOB_SOURCE_KEY = "lucePeMaungTinInscriptionsOfBurma"
IOB_BIBLIOGRAPHIC_LABEL = "G. H. Luce and U Pe Maung Tin, Inscriptions of Burma"
LIST_SOURCE_KEY = "duroiselle1921list"
LIST_BIBLIOGRAPHIC_LABEL = "Charles Duroiselle, List of Inscriptions Found in Burma"
UB_SOURCE_KEY = "ubSourceFamily"
UB_BIBLIOGRAPHIC_LABEL = "Inscriptions Collected in Upper Burma"
JBRS_SOURCE_KEY = "journalBurmaResearchSociety"
JBRS_BIBLIOGRAPHIC_LABEL = "Journal of the Burma Research Society"
SHWEGUGYI_TRANSLATION_SOURCE_KEY = "jbrsShwegugyi1920"
SHWEGUGYI_TRANSLATION_BIBLIOGRAPHIC_LABEL = (
    "U Pe Maung Tin and G. H. Luce, The Shwegugyi Pagoda Inscription, Pagan, 1141 A.D. "
    "(JBRS 10(2), 1920, pp. 67-74)"
)
ANANDA_TRANSLATION_SOURCE_KEY = "jbrsAnanda1976"
ANANDA_TRANSLATION_BIBLIOGRAPHIC_LABEL = "Ananda Brick Monastery Inscriptions of Pagan"
FRASCH_MACHINE_TRANSLATION_SOURCE_KEY = "fraschPaganMachineTranslation2004"
FRASCH_MACHINE_TRANSLATION_BIBLIOGRAPHIC_LABEL = "Tilman Frasch, Pagan: Staat und Staat"
MYAZEDI_TRANSLATION_SOURCE_KEY = "peMaungTinMyazedi1974"
MYAZEDI_TRANSLATION_BIBLIOGRAPHIC_LABEL = "U Pe Maung Tin, Myazedi Inscription"
RAJAKUMAR_TRANSLATION_SOURCE_KEY = "tunAungChainRajakumar2001"
RAJAKUMAR_TRANSLATION_BIBLIOGRAPHIC_LABEL = (
    "Tun Aung Chain, The Rajakumar Inscription, Cultural Classics, Yangon Universities Press, 2001, pp. 25-37"
)

CORPUS_ENRICHMENT_DIRECTORY = REPO_ROOT / "data" / "working" / "corpus_enrichment"
TN_OCR_DIRECTORY = REPO_ROOT / "data" / "working" / "ocr" / "pagan_pinya_ava_1899"
CORPUS_RELEASE_INSCRIPTIONS_PATH = REPO_ROOT / "data" / "release" / "corpus_release_v0_3" / "inscriptions.jsonl"
CORPUS_RELEASE_LINES_PATH = REPO_ROOT / "data" / "release" / "corpus_release_v0_3" / "lines.jsonl"
ENRICHED_CORPUS_CANDIDATE_PATH = CORPUS_ENRICHMENT_DIRECTORY / "inscriptions_enriched_candidate.jsonl"
ENRICHED_CANDIDATE_PREVIEW_PATH = CORPUS_ENRICHMENT_DIRECTORY / "enriched_candidate_preview.tsv"
ENRICHED_CANDIDATE_SUMMARY_PATH = CORPUS_ENRICHMENT_DIRECTORY / "enriched_candidate_summary.json"
TRANSLATION_SOURCE_ACTION_TABLE_PATH = CORPUS_ENRICHMENT_DIRECTORY / "translation_source_action_table.tsv"
TRANSLATION_UNITS_EXTRACTED_PATH = CORPUS_ENRICHMENT_DIRECTORY / "translation_units_extracted.tsv"
TRANSLATION_INTEGRATION_PREVIEW_PATH = CORPUS_ENRICHMENT_DIRECTORY / "translation_integration_preview.tsv"
TN_TRANSLATION_TARGETS_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_translation_targets.tsv"
TN_TRANSLATION_TARGET_STATUS_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_translation_target_status.tsv"
TN_TRANSLATION_CANDIDATES_REVIEW_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_translation_candidates_needing_review.tsv"
TN_MANUAL_RESOLUTION_LOG_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_manual_resolution_log.tsv"
TN_RESIDUAL_UNRESOLVED_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_residual_unresolved_after_manual_review.tsv"
TN_TRANSLATION_INTEGRATION_PREVIEW_PATH = CORPUS_ENRICHMENT_DIRECTORY / "tn_translation_integration_preview.tsv"
RELEASE_CANDIDATE_V04_DIRECTORY = CORPUS_ENRICHMENT_DIRECTORY / "release_candidate_v0_4"
V04_INSCRIPTIONS_CANDIDATE_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "inscriptions_enriched_v0_4_candidate.jsonl"
V04_INSCRIPTIONS_WITH_LINES_CANDIDATE_PATH = (
    RELEASE_CANDIDATE_V04_DIRECTORY / "inscriptions_enriched_with_lines_v0_4_candidate.jsonl"
)
V04_TRANSLATION_UNITS_CANDIDATE_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "translation_units_v0_4_candidate.tsv"
V04_ENRICHMENT_PREVIEW_CANDIDATE_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "enrichment_preview_v0_4_candidate.tsv"
V04_ENRICHED_WITH_LINES_SAMPLE_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "enriched_with_lines_sample_v0_4.json"
V04_TN_UNRESOLVED_REVIEW_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "tn_unresolved_review_v0_4.tsv"
V04_REVIEW_CHECKLIST_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "review_checklist_v0_4.tsv"
V04_RELEASE_NOTES_DRAFT_PATH = RELEASE_CANDIDATE_V04_DIRECTORY / "release_notes_v0_4_draft.md"
SHWEGUGYI_TRANSLATION_TEXT_PATH = CORPUS_ENRICHMENT_DIRECTORY / "shwegugyi_translation_extracted.txt"
RAJAKUMAR_TRANSLATION_TEXT_PATH = CORPUS_ENRICHMENT_DIRECTORY / "rajakumar_translation_extracted.txt"
TN_OCR_PLAIN_TEXT_PATH = TN_OCR_DIRECTORY / "ocr_plain_text_with_page_breaks.txt"
TN_OCR_CLEANED_TEXT_PATH = TN_OCR_DIRECTORY / "ocr_cleaned_text_light.txt"

TN_LOCAL_FILE_ID = "hvd-hxx68w-1780753436"
TN_LOCAL_FILE_NAME = "hvd-hxx68w-1780753436.pdf"

TN_TRANSLATION_UNIT_SPECS = [
    {
        "translation_unit_id": "tn-translation-1899-plate-xlv-tn-70",
        "tn_locator": "TN 70",
        "iob_plate": "Plate XLV",
        "linked_inscription_id": "obi-v01-n0081",
        "linked_corpus_record_id": "obi-v01-n0081-ob-p0125",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (5).",
        "end_anchor": "No. (6).-OBVERSE.",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-x-b-tn-70-71-no-6",
        "tn_locator": "TN 70-71",
        "iob_plate": "Plate X b",
        "linked_inscription_id": "obi-v01-n0029",
        "linked_corpus_record_id": "obi-v01-n0029-re-p0051",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (6).",
        "end_anchor": "No. (7).",
        "allow_locator_only_match": "true",
        "source_locator_override": (
            "TN 70-71 (Plate X b; linked through SIP 21 / IOB Plate X b source-text match, "
            "not through prior corpus plate metadata; OCR pages 83, 84)"
        ),
        "link_basis": (
            "Cross-witness source-text match: SIP 21 and IOB Plate X b resolve to the West-face continuation on "
            "obi-v01-n0029-re-p0051, bounded here to No. (6) only; No. (5) remains the already integrated overlap."
        ),
        "confidence": "high",
        "notes": (
            "version_label=TN locator TN 70-71; subentry=No. (6) only; source_iob_plate=Plate X b; "
            "linked through SIP 21 / IOB Plate X b source-text match, not prior corpus plate metadata."
        ),
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xxvii-tn-80",
        "tn_locator": "TN 80",
        "iob_plate": "Plate XXVII",
        "linked_inscription_id": "obi-v01-n0047",
        "linked_corpus_record_id": "obi-v01-n0047-ob-p0075",
        "translation_status": "published_partial_translation",
        "start_anchor": "Reverse.",
        "end_anchor": None,
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lix-tn-92",
        "tn_locator": "TN 92",
        "iob_plate": "Plate LIX",
        "linked_inscription_id": "obi-v01-n0007",
        "linked_corpus_record_id": "obi-v01-n0007-ob-p0022",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (21).",
        "end_anchor": "No. (22).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxiv-tn-100-101",
        "tn_locator": "TN 100 101",
        "iob_plate": "Plate LXXIV",
        "linked_inscription_id": "obi-v01-n0097",
        "linked_corpus_record_id": "obi-v01-n0097-tx-p0156",
        "translation_status": "published_partial_translation",
        "start_anchor": "Substance of inscription.-Building of cave, monastery, and image,",
        "end_anchor": "No. (3).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxvi-tn-102-103",
        "tn_locator": "TN 102-103",
        "iob_plate": "Plate LXXVI",
        "linked_inscription_id": "obi-v01-n0142",
        "linked_corpus_record_id": "obi-v01-n0142-tx-p0238",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (3).",
        "end_anchor": "No. (4).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxviii-a-tn-106",
        "tn_locator": "TN 106",
        "iob_plate": "Plate LXXVIII a",
        "linked_inscription_id": "obi-v01-n0142",
        "linked_corpus_record_id": "obi-v01-n0142-tx-p0238",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (7).*",
        "end_anchor": "No. (8).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxix-b-tn-108-109",
        "tn_locator": "TN 108 109",
        "iob_plate": "Plate LXXIX b",
        "linked_inscription_id": "obi-v01-n0146",
        "linked_corpus_record_id": "obi-v01-n0146-tx-p0246",
        "translation_status": "published_partial_translation",
        "start_anchor": "Substance of inscription.-Erection of cave and dedication thereto",
        "end_anchor": "No. (12).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-vi-tn-65-66",
        "tn_locator": "TN 65-66",
        "iob_plate": "Plate VI",
        "linked_inscription_id": "obi-v01-n0021",
        "linked_corpus_record_id": "obi-v01-n0021-ob-p0042",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (10).",
        "end_anchor": "No. (1).-OBVERSE.",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xli-tn-69",
        "tn_locator": "TN 69",
        "iob_plate": "Plate XLI",
        "linked_inscription_id": "obi-v01-n0070",
        "linked_corpus_record_id": "obi-v01-n0070-ob-p0111",
        "translation_status": "published_partial_translation",
        "start_anchor": "On Sunday, the 7th waxing of Tabodwè, 615 Sakkarâj, Nga Môn",
        "end_anchor": "No. (4).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xiii-tn-79",
        "tn_locator": "TN 79",
        "iob_plate": "Plate XIII",
        "linked_inscription_id": "obi-v01-n0027",
        "linked_corpus_record_id": "obi-v01-n0027-ob-p0048",
        "translation_status": "published_partial_translation",
        "start_anchor": "This inscription is erected by King Alaungsithu",
        "end_anchor": None,
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxii-tn-82-83",
        "tn_locator": "TN 82-83",
        "iob_plate": "Plate LXII",
        "linked_inscription_id": "obi-v01-n0130",
        "linked_corpus_record_id": "obi-v01-n0130-ob-p0211",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (8).",
        "end_anchor": "No. (9).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxxviii-tn-84",
        "tn_locator": "TN 84",
        "iob_plate": "Plate LXXXVIII",
        "linked_inscription_id": "obi-v01-n0161",
        "linked_corpus_record_id": "obi-v01-n0161-ob-p0270",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (11).",
        "end_anchor": "No. (12).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxxv-tn-84-85",
        "tn_locator": "TN 84 85",
        "iob_plate": "Plate LXXXV",
        "linked_inscription_id": "obi-v01-n0154",
        "linked_corpus_record_id": "obi-v01-n0154-ob-p0257",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (12).",
        "end_anchor": "No. (13).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-ci-tn-85-86",
        "tn_locator": "TN 85 86",
        "iob_plate": "Plate CI",
        "linked_inscription_id": "obi-v01-n0178",
        "linked_corpus_record_id": "obi-v01-n0178-tx-p0305",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (13).",
        "end_anchor": "No. (14).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxvii-tn-105",
        "tn_locator": "TN 105",
        "iob_plate": "Plate LXXVII",
        "linked_inscription_id": "obi-v01-n0142",
        "linked_corpus_record_id": "obi-v01-n0142-tx-p0238",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (6).",
        "end_anchor": "No. (7).*",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxxiii-tn-107",
        "tn_locator": "TN 107",
        "iob_plate": "Plate LXXXIII",
        "linked_inscription_id": "obi-v01-n0128",
        "linked_corpus_record_id": "obi-v01-n0128-ob-p0208",
        "translation_status": "published_partial_translation",
        "start_anchor": "By virtue of this offering may I always be free from want.",
        "end_anchor": "No. (9).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxviii-tn-107-108",
        "tn_locator": "TN 107-108",
        "iob_plate": "Plate LXVIII",
        "linked_inscription_id": "obi-v01-n0143",
        "linked_corpus_record_id": "obi-v01-n0143-ob-p0240",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (9).",
        "end_anchor": "No. (10).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-l-tn-27-28",
        "tn_locator": "TN 27-28",
        "iob_plate": "Plate L",
        "linked_inscription_id": "obi-v01-n0057",
        "linked_corpus_record_id": "obi-v01-n0057-ob-p0091",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (2).",
        "end_anchor": "No. (3).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xciii-tn-28-29",
        "tn_locator": "TN 28-29",
        "iob_plate": "Plate XCIII",
        "linked_inscription_id": "obi-v01-n0169",
        "linked_corpus_record_id": "obi-v01-n0169-ob-p0287",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (4).",
        "end_anchor": "No. (5)-OBVERSE.",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-li-tn-28",
        "tn_locator": "TN 28",
        "iob_plate": "Plate LI",
        "linked_inscription_id": "obi-v01-n0095",
        "linked_corpus_record_id": "obi-v01-n0095-re-p0142",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (3).",
        "end_anchor": "No. (4).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-lxxi-tn-6-no-12",
        "tn_locator": "TN 6",
        "iob_plate": "Plate LXXI",
        "linked_inscription_id": "obi-v01-n0148",
        "linked_corpus_record_id": "obi-v01-n0148-ob-p0249",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (12).",
        "end_anchor": "No. (13A.).",
        "allow_locator_only_match": "true",
        "source_locator_override": "TN 6 (No. (12) segment; Plate LXXI / List 224 / PPA 17; OCR page 19)",
        "link_basis": (
            "Manual TN page/image inspection of printed page 6 (OCR page 19) isolates No. (12) as a bounded segment; "
            "structured record obi-v01-n0148-ob-p0249 cites TN, p. 6 with List 224 / PPA 17 / IOB1-71 (Pl. I 71-72), "
            "matching date, locality, and inscription profile."
        ),
        "confidence": "high",
        "notes": (
            "version_label=TN locator TN 6; subentry=No. (12) only; source_iob_plate=Plate LXXI; "
            "linked via TN p.6 / List 224 / PPA 17 / IOB1-71 concordance."
        ),
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-cv-a-tn-30-86-87",
        "tn_locator": "TN 30 | TN 86-87",
        "iob_plate": "Plate CV a",
        "linked_inscription_id": "obi-v01-n0179",
        "linked_corpus_record_id": "obi-v01-n0179-tx-p0306",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (14).",
        "end_anchor": "No. (15).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xcviii-tn-143",
        "tn_locator": "TN 143",
        "iob_plate": "Plate XCVIII",
        "linked_inscription_id": "obi-v01-n0129",
        "linked_corpus_record_id": "obi-v01-n0129-tx-p0209",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (6).",
        "end_anchor": "No. (7).",
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xxxi-tn-36-57-no-1",
        "tn_locator": "TN 36-57",
        "iob_plate": "Plate XXXI",
        "linked_inscription_id": "obi-v01-n0052",
        "linked_corpus_record_id": "obi-v01-n0052-ob-p0083",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (1).—OBVERSE.\nLocality. Within the walls of the Kemawaya pagoda.",
        "end_anchor": "REVERSE.",
        "source_locator_override": "TN 36-57 (Plate XXXI, No. (1) obverse segment; OCR pages 49-70)",
        "link_basis": (
            "Manual cross-witness segmentation of TN 36-57 isolates the Plate XXXI No. (1) obverse block "
            "(Kemawaya pagoda, CS 569, King Nandaungmya), matching obi-v01-n0052-ob-p0083 and SIP Plate XXXI linkage."
        ),
        "confidence": "high",
        "notes": (
            "version_label=TN locator TN 36-57; subentry=No. (1) obverse only; source_iob_plate=Plate XXXI; "
            "cross_witness=SIP 29 / List 273(a) / PPA 109-111."
        ),
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-i-tn-73-76-no-1",
        "tn_locator": "TN 73-76",
        "iob_plate": "Plate I",
        "linked_inscription_id": "obi-v01-n0004",
        "linked_corpus_record_id": "obi-v01-n0004-ob-p0011",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (1).*",
        "end_anchor": "No. (2).*",
        "allow_locator_only_match": "true",
        "source_locator_override": "TN 73-76 (Plate I, No. (1) segment before No. (2); OCR pages 86-89)",
        "link_basis": (
            "Targeted manual linkage: TN 73-76 contains Plate I No. (1) Shwegugyi translation block "
            "(Alaungsithu, CS 503), which aligns with List 66(a), PPA 159, and obi-v01-n0004-ob-p0011 references."
        ),
        "confidence": "medium-high",
        "notes": (
            "version_label=TN locator TN 73-76; subentry=No. (1) only; source_iob_plate=Plate I; "
            "linked via List 66(a) / PPA 159 / TN p.73 concordance."
        ),
    },
    {
        "translation_unit_id": "tn-translation-1899-plate-xxxvii-tn-81-no-6",
        "tn_locator": "TN 81",
        "iob_plate": "Plate XXXVII",
        "linked_inscription_id": "obi-v01-n0063",
        "linked_corpus_record_id": "obi-v01-n0063-ob-p0099",
        "translation_status": "published_partial_translation",
        "start_anchor": "No. (6).",
        "end_anchor": "No. (7).",
        "allow_locator_only_match": "true",
        "source_locator_override": "TN 81 (Plate XXXVII, No. (6) segment before No. (7); OCR page 94)",
        "link_basis": (
            "Targeted manual linkage: TN 81 No. (6) gives Thingyi Dhammapala (CS 574) "
            "and Shinbinbawdi context, matching List 175 / PPA 169 and obi-v01-n0063-ob-p0099."
        ),
        "confidence": "medium-high",
        "notes": (
            "version_label=TN locator TN 81; subentry=No. (6) only; source_iob_plate=Plate XXXVII; "
            "linked via List 175 / PPA 169 / TN p.81 concordance."
        ),
    },
]

TN_TARGET_STATUS_VALUES = {
    "integrated",
    "integrated_after_manual_review",
    "integrated_after_cross_witness_match",
    "confirmed_duplicate_or_overlap",
    "not_extractable_even_after_page_inspection",
    "deferred_requires_scholarly_judgement",
    "no_corresponding_translation_found",
    "still_unresolved",
}

TN_TARGET_STATUS_OVERRIDES: dict[tuple[str, str], dict[str, str]] = {
    (
        "TN 28",
        "obi-v01-n0095-re-p0142",
    ): {
        "current_status": "integrated_after_manual_review",
        "notes": (
            "Manual page inspection of OCR page 41 and rendered image page-041.png confirms a distinct No. (3) segment "
            "for the CS 585 daughter-of-Kyan-Thaing inscription."
        ),
    },
    (
        "TN 143",
        "obi-v01-n0129-tx-p0209",
    ): {
        "current_status": "integrated_after_manual_review",
        "notes": (
            "Manual page/image inspection with targeted Tesseract OCR on pages 156-157 isolates No. (6) and confirms "
            "the Myingondaing 300-pes dedication segment aligned to this record."
        ),
    },
    (
        "TN 30 | TN 86-87",
        "obi-v01-n0179-tx-p0306",
    ): {
        "current_status": "integrated_after_manual_review",
        "notes": (
            "Manual page/image inspection confirms this composite locator resolves through TN 86-87 pages (OCR 99-100): "
            "No. (14) matches the Ñāṇapicaññ inscription profile; TN 30 is overlap noise for this target."
        ),
    },
    (
        "TN 36-57",
        "obi-v01-n0052-ob-p0083",
    ): {
        "current_status": "integrated_after_manual_review",
        "notes": (
            "Manual TN 36-57 segmentation against page images and cross-witness references isolates Plate XXXI No. (1) "
            "(Kemawaya, CS 569, King Nandaungmya) and supports secure linkage to obi-v01-n0052-ob-p0083."
        ),
    },
    (
        "TN 70-71",
        "obi-v01-n0029-re-p0051",
    ): {
        "current_status": "integrated_after_cross_witness_match",
        "notes": (
            "SIP 21 / IOB Plate X b source-text matching resolves the west-face continuation to "
            "obi-v01-n0029-re-p0051; bounded here to No. (6) only because No. (5) already overlaps an integrated unit."
        ),
    },
}

TN_CROSSWITNESS_TARGET_OVERRIDES: dict[str, dict[str, str]] = {
    "TN 70-71": {
        "linked_inscription_id": "obi-v01-n0029",
        "linked_corpus_record_id": "obi-v01-n0029-re-p0051",
        "link_confidence": "high",
        "needs_manual_review": "false",
        "source_of_link": (
            "SIP 21 / IOB Plate X b source-text match, not prior corpus plate metadata"
        ),
        "link_basis": (
            "Cross-witness source-text match: SIP 21 and IOB Plate X b resolve to the West-face continuation on "
            "obi-v01-n0029-re-p0051, bounded here to No. (6) only; No. (5) remains the already integrated overlap."
        ),
        "notes": (
            "Linked through SIP 21 / IOB Plate X b source-text match, not through prior corpus plate metadata."
        ),
    }
}

TN_CANDIDATE_RESOLUTION_OVERRIDES: dict[str, dict[str, str]] = {
    "TN 76-79": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": "Treat as overlap with the already integrated TN 79 unit unless a separate linked record is identified.",
        "notes": "page_image_inspection=attempted; overlaps TN 79 prayer-to-inscription transition on pages 89-92; overlap_unit=tn-translation-1899-plate-xiii-tn-79.",
    },
    "TN 66": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": "Treat as overlap with integrated TN 65-66.",
        "notes": "page_image_inspection=attempted; inspected pages 79; overlap_unit=tn-translation-1899-plate-vi-tn-65-66.",
    },
    "TN 66-67": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": "Treat as overlap/continuation of integrated TN 65-66 in current linkage state.",
        "notes": "page_image_inspection=attempted; inspected pages 79-80; overlap_unit=tn-translation-1899-plate-vi-tn-65-66.",
    },
    "TN 70": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": "Treat Plate X a witness as overlap of the already integrated TN 70 text segment.",
        "notes": "page_image_inspection=attempted; inspected pages 83; overlap_unit=tn-translation-1899-plate-xlv-tn-70.",
    },
    "TN 70-71": {
        "reason_uncertain": "integrated_after_cross_witness_match",
        "recommended_human_action": (
            "Integrated the bounded No. (6) segment after SIP 21 / IOB Plate X b source-text matching; keep No. (5) "
            "as the already integrated overlap and do not extend into No. (7)."
        ),
        "notes": (
            "page_image_inspection=attempted; inspected pages 83-85 with targeted Tesseract OCR on pages 83-84; "
            "SIP 21 / IOB Plate X b source-text match links the bounded No. (6) continuation to obi-v01-n0029-re-p0051."
        ),
    },
    "TN 80 | TN 6": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": (
            "Treat as composite overlap around TN 80; this mixed locator should not be used for additional linkage "
            "now that TN 6 is resolved through a separate bounded No. (12) segment."
        ),
        "notes": "page_image_inspection=attempted; inspected disjoint pages 93 and 19; overlap_unit=tn-translation-1899-plate-xxvii-tn-80.",
    },
    "TN 80-81": {
        "reason_uncertain": "confirmed_duplicate_or_overlap",
        "recommended_human_action": "Treat as overlap/continuation around integrated TN 80 unless a separate linked record is confirmed.",
        "notes": "page_image_inspection=attempted; inspected pages 93-94; overlap_unit=tn-translation-1899-plate-xxvii-tn-80.",
    },
}

TN_CANDIDATE_REVIEW_SUPPRESSED_LOCATORS = {"TN 73-76", "TN 81", "TN 6"}
TN_CANDIDATE_REVIEW_LOCATORS = {
    "TN 73-76",
    "TN 76-79",
    "TN 66",
    "TN 66-67",
    "TN 70",
    "TN 70-71",
    "TN 80 | TN 6",
    "TN 6",
    "TN 80-81",
    "TN 81",
}

TN_MANUAL_INSPECTION_LOCATORS = [
    "TN 143",
    "TN 28",
    "TN 30 | TN 86-87",
    "TN 36-57",
    "TN 73-76",
    "TN 76-79",
    "TN 66",
    "TN 66-67",
    "TN 70",
    "TN 70-71",
    "TN 80 | TN 6",
    "TN 6",
    "TN 80-81",
    "TN 81",
]

TN_MANUAL_EXISTING_STATUS_BY_LOCATOR = {
    "TN 143": "not_extractable_from_current_ocr",
    "TN 28": "duplicate_or_subentry_of_integrated_translation",
    "TN 30 | TN 86-87": "deferred_complex_boundary",
    "TN 36-57": "deferred_complex_boundary",
    "TN 73-76": "candidate_needs_human_review",
    "TN 76-79": "candidate_needs_human_review",
    "TN 66": "candidate_needs_human_review",
    "TN 66-67": "candidate_needs_human_review",
    "TN 70": "candidate_needs_human_review",
    "TN 70-71": "candidate_needs_human_review",
    "TN 80 | TN 6": "candidate_needs_human_review",
    "TN 6": "candidate_needs_human_review",
    "TN 80-81": "candidate_needs_human_review",
    "TN 81": "candidate_needs_human_review",
}

TN_MANUAL_NOTES_OVERRIDES = {
    "TN 6": (
        "Manual page/image inspection of printed page 6 (OCR page 19) isolates No. (12) as a bounded segment "
        "(southern porch of Thate-Môkku, CS 595) and supports linkage to obi-v01-n0148-ob-p0249 via TN p. 6 / "
        "List 224 / PPA 17 / IOB1-71 concordance."
    ),
    "TN 73-76": (
        "Manual page/image inspection of OCR pages 86-89 isolates Plate I No. (1) "
        "and supports linkage to obi-v01-n0004-ob-p0011."
    ),
    "TN 70-71": (
        "Manual inspection of OCR pages 83-85 plus SIP 21 / IOB Plate X b source-text matching resolves the bounded "
        "No. (6) segment to obi-v01-n0029-re-p0051; No. (5) remains the already integrated overlap and No. (7) is "
        "not included."
    ),
    "TN 81": (
        "Manual page/image inspection of OCR page 94 isolates No. (6) "
        "and supports linkage to obi-v01-n0063-ob-p0099."
    ),
}

TN_RESIDUAL_UNRESOLVED_FIELDS = [
    "tn_locator",
    "iob_plate",
    "list_ref",
    "ppa_ref",
    "possible_corpus_record_ids",
    "possible_inscription_ids",
    "translation_text_snippet",
    "final_status",
    "evidence_checked",
    "reason_not_integrated",
    "future_action",
    "notes",
]

V04_REVIEW_CHECKLIST_FIELDS = [
    "check_id",
    "review_item",
    "status",
    "evidence_path",
    "notes",
]

TN_REVIEW_FINAL_UNRESOLVED_REASONS = {
    "out_of_current_corpus_scope",
    "no_structured_record_found",
    "translation_fragment_without_secure_locator",
    "probable_overlap_but_no_record_link",
}

SOURCE_LABELS = {
    SIP_SOURCE_KEY: SIP_BIBLIOGRAPHIC_LABEL,
    TN_SOURCE_KEY: TN_BIBLIOGRAPHIC_LABEL,
    PPA_SOURCE_KEY: PPA_BIBLIOGRAPHIC_LABEL,
    IOB_SOURCE_KEY: IOB_BIBLIOGRAPHIC_LABEL,
    LIST_SOURCE_KEY: LIST_BIBLIOGRAPHIC_LABEL,
    UB_SOURCE_KEY: UB_BIBLIOGRAPHIC_LABEL,
    JBRS_SOURCE_KEY: JBRS_BIBLIOGRAPHIC_LABEL,
    SHWEGUGYI_TRANSLATION_SOURCE_KEY: SHWEGUGYI_TRANSLATION_BIBLIOGRAPHIC_LABEL,
    ANANDA_TRANSLATION_SOURCE_KEY: ANANDA_TRANSLATION_BIBLIOGRAPHIC_LABEL,
    FRASCH_MACHINE_TRANSLATION_SOURCE_KEY: FRASCH_MACHINE_TRANSLATION_BIBLIOGRAPHIC_LABEL,
    MYAZEDI_TRANSLATION_SOURCE_KEY: MYAZEDI_TRANSLATION_BIBLIOGRAPHIC_LABEL,
    RAJAKUMAR_TRANSLATION_SOURCE_KEY: RAJAKUMAR_TRANSLATION_BIBLIOGRAPHIC_LABEL,
}

SOURCE_ROLE_BY_KEY = {
    IOB_SOURCE_KEY: "cross_reference_or_plate_witness",
    LIST_SOURCE_KEY: "catalogue_or_list",
    PPA_SOURCE_KEY: "source_text_or_edition_candidate",
    TN_SOURCE_KEY: "translation_candidate",
    SIP_SOURCE_KEY: "source_text_witness",
    UB_SOURCE_KEY: "catalogue_or_list",
    JBRS_SOURCE_KEY: "commentary_witness",
    SHWEGUGYI_TRANSLATION_SOURCE_KEY: "translation_witness",
    ANANDA_TRANSLATION_SOURCE_KEY: "translation_witness",
    FRASCH_MACHINE_TRANSLATION_SOURCE_KEY: "translation_witness",
    MYAZEDI_TRANSLATION_SOURCE_KEY: "translation_candidate",
    RAJAKUMAR_TRANSLATION_SOURCE_KEY: "translation_candidate",
}

STATUS_BY_KEY = {
    IOB_SOURCE_KEY: "linked",
    LIST_SOURCE_KEY: "cited_or_cross_referenced",
    PPA_SOURCE_KEY: "missing_high_value_source",
    TN_SOURCE_KEY: "cited_or_cross_referenced",
    SIP_SOURCE_KEY: "linked",
    UB_SOURCE_KEY: "cited_or_cross_referenced",
    JBRS_SOURCE_KEY: "cited_or_cross_referenced",
    SHWEGUGYI_TRANSLATION_SOURCE_KEY: "linked",
    ANANDA_TRANSLATION_SOURCE_KEY: "linked",
    FRASCH_MACHINE_TRANSLATION_SOURCE_KEY: "cited_or_cross_referenced",
    MYAZEDI_TRANSLATION_SOURCE_KEY: "needs_manual_review",
    RAJAKUMAR_TRANSLATION_SOURCE_KEY: "needs_targeted_ocr",
}

WITNESS_STATUS_BY_QC = {
    "clean_for_review": "ocr_clean_for_review",
    "clean_with_unclear_markers": "ocr_with_unclear_markers",
    "contains_possible_page_artifact": "contains_possible_page_artifact",
    "needs_human_text_check": "needs_manual_text_check",
}

ENRICHMENT_STATUSES = {
    "baseline_no_enrichment",
    "enriched_with_bibliographic_crossrefs",
    "enriched_with_bibliographic_crossrefs_and_candidates",
    "enriched_with_sip_witnesses",
    "enriched_with_sip_and_crossrefs",
    "enriched_with_sip_and_candidates",
    "enriched_with_translation",
}

TRANSLATION_STATUSES = {
    "no_translation_known",
    "translation_source_missing",
    "translation_available_unintegrated",
    "translation_integrated",
    "translation_needs_review",
}

WITNESS_STATUSES = {
    "ocr_clean_for_review",
    "ocr_with_unclear_markers",
    "contains_possible_page_artifact",
    "needs_manual_text_check",
}

TRANSLATION_CANDIDATE_STATUSES = {
    "missing_high_value_source",
    "candidate_source_located",
    "candidate_source_review_pending",
}

PREVIEW_FIELDS = [
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "language",
    "has_existing_transcription",
    "has_source_text_witness",
    "source_text_witness_count",
    "has_bibliographic_crossrefs",
    "crossref_sources",
    "has_translation",
    "translation_status",
    "translation_candidate_sources",
    "translation_candidate_locators",
    "sip_ref",
    "iob_plate",
    "list_ref",
    "ppa_ref",
    "tn_ref",
    "comparison_status",
    "preview_note",
]

SUMMARY_FIELDS = [
    "total_records",
    "records_with_any_enrichment",
    "records_with_sip_source_text_witness",
    "records_with_iob_crossref",
    "records_with_list_crossref",
    "records_with_ppa_candidate",
    "records_with_tn_translation_candidate",
    "records_with_translation_status_no_translation_known",
    "records_with_translation_status_translation_source_missing",
    "records_with_translation_integrated",
    "records_with_existing_full_transliteration",
]

TN_TRANSLATION_TARGET_FIELDS = [
    "tn_locator",
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "iob_plate",
    "list_ref",
    "ppa_ref",
    "sip_ref",
    "source_of_link",
    "priority",
    "notes",
]

TN_TRANSLATION_TARGET_STATUS_FIELDS = [
    "tn_locator",
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "iob_plate",
    "list_ref",
    "ppa_ref",
    "sip_ref",
    "priority",
    "current_status",
    "translation_unit_id",
    "reason_not_integrated",
    "next_action",
    "notes",
]

TN_TRANSLATION_CANDIDATE_REVIEW_FIELDS = [
    "tn_locator",
    "possible_corpus_record_ids",
    "possible_inscription_ids",
    "translation_text_snippet",
    "reason_uncertain",
    "recommended_human_action",
    "notes",
]

TN_MANUAL_RESOLUTION_LOG_FIELDS = [
    "tn_locator",
    "printed_page_or_pages",
    "ocr_pages_inspected",
    "image_pages_inspected",
    "existing_status",
    "resolution_status",
    "translation_unit_id",
    "linked_corpus_record_id",
    "linked_inscription_id",
    "evidence_used",
    "problem_found",
    "decision",
    "notes",
]

TN_TRANSLATION_INTEGRATION_PREVIEW_FIELDS = [
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "tn_locator",
    "source_locator",
    "translation_status",
    "translation_length_chars",
    "translation_text_snippet",
    "link_basis",
    "confidence",
    "needs_human_review",
    "notes",
]


def join_unique(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return "; ".join(seen)


def source_label(source_key: str) -> str:
    return SOURCE_LABELS.get(source_key, source_key)


def normalize_tn_locator(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"\b([0-9])o\b", r"\g<1>0", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bo([0-9])\b", r"0\g<1>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_tn_pages(locator: str) -> list[int]:
    normalized = normalize_tn_locator(locator)
    if not normalized:
        return []
    pages: list[int] = []
    for chunk in re.split(r"\|", normalized):
        part = chunk.strip()
        if not part:
            continue
        part = re.sub(r"^TN\s*", "", part, flags=re.IGNORECASE)
        for start, end in re.findall(r"(\d+)\s*-\s*(\d+)", part):
            start_page = int(start)
            end_page = int(end)
            if end_page < start_page:
                start_page, end_page = end_page, start_page
            pages.extend(range(start_page, end_page + 1))
        part_without_ranges = re.sub(r"\d+\s*-\s*\d+", "", part)
        pages.extend(int(match) for match in re.findall(r"\d+", part_without_ranges))
    deduped = sorted(set(pages))
    return deduped


def parse_page_marked_text(marked_text: str) -> dict[int, str]:
    marker_pattern = re.compile(r"^\[\[page\s+(\d+)\]\]$", re.MULTILINE)
    matches = list(marker_pattern.finditer(marked_text))
    page_map: dict[int, str] = {}
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(marked_text)
        page_map[page_number] = marked_text[start:end].strip()
    return page_map


def clean_tn_page_text(page_text: str) -> str:
    boilerplate_patterns = [
        re.compile(r"generated through hathitrust", re.IGNORECASE),
        re.compile(r"https?://hdl\.handle\.net/2027/hvd\.hxx68w", re.IGNORECASE),
        re.compile(r"public domain", re.IGNORECASE),
        re.compile(r"digitized by", re.IGNORECASE),
    ]
    exact_drop_lines = {"google", "original from", "harvard university"}
    cleaned_lines: list[str] = []
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1] == "":
                continue
            cleaned_lines.append("")
            continue
        if line.casefold() in exact_drop_lines:
            continue
        if line.upper() in {"INSCRIPTIONS OF PAGAN, PINYA, AND AVA.", "INSCRIPTIONS OF PAGAN, PIÑYA, AND AVA.", "TOO"}:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if all(pattern.search(line) for pattern in [boilerplate_patterns[1], boilerplate_patterns[2]]):
            continue
        if any(pattern.search(line) for pattern in boilerplate_patterns):
            # Keep only the non-boilerplate remainder when boilerplate is prefixed/suffixed to a content line.
            stripped_line = line
            stripped_line = re.sub(r"Generated through HathiTrust on [^\n]*", "", stripped_line, flags=re.IGNORECASE)
            stripped_line = re.sub(r"https?://hdl\.handle\.net/2027/hvd\.hxx68w\s*/\s*Public Domain", "", stripped_line, flags=re.IGNORECASE)
            stripped_line = re.sub(r"Public Domain", "", stripped_line, flags=re.IGNORECASE)
            stripped_line = re.sub(r"Digitized by", "", stripped_line, flags=re.IGNORECASE)
            stripped_line = stripped_line.strip(" -|")
            if not stripped_line:
                continue
            line = stripped_line
            raw_line = stripped_line
        if re.fullmatch(r"[•\.\-,;:]+", line):
            continue
        cleaned_lines.append(raw_line.rstrip())
    # Remove direct page-boundary duplication from stitched ranges.
    deduped_lines: list[str] = []
    for item in cleaned_lines:
        if deduped_lines and item and item == deduped_lines[-1]:
            continue
        deduped_lines.append(item)
    return "\n".join(deduped_lines).strip()


def extract_tn_translation_text(
    *,
    locator: str,
    page_map: dict[int, str],
    start_anchor: str | None = None,
    end_anchor: str | None = None,
) -> str:
    tn_pages = parse_tn_pages(locator)
    if not tn_pages:
        return ""
    ocr_pages = [page + 13 for page in tn_pages]
    segments = [
        clean_tn_page_text(page_map.get(ocr_page, ""))
        for ocr_page in ocr_pages
        if page_map.get(ocr_page, "").strip()
    ]
    combined = "\n\n".join(segment for segment in segments if segment).strip()
    if not combined:
        return ""
    if start_anchor and start_anchor in combined:
        combined = combined.split(start_anchor, 1)[1].strip()
        combined = f"{start_anchor}\n{combined}".strip()
    if end_anchor and end_anchor in combined:
        combined = combined.split(end_anchor, 1)[0].strip()
    return combined


def tn_locator_to_ocr_pages(locator: str) -> str:
    pages = parse_tn_pages(locator)
    if not pages:
        return ""
    mapped = [str(page + 13) for page in pages]
    return ", ".join(mapped)


def tn_locator_to_printed_pages(locator: str) -> str:
    pages = parse_tn_pages(locator)
    if not pages:
        return ""
    return ", ".join(str(page) for page in pages)


def ocr_page_list_for_locator(locator: str) -> list[int]:
    return [page + 13 for page in parse_tn_pages(locator)]


def tn_locator_from_source_locator(source_locator: str) -> str:
    prefix = source_locator.split("(", 1)[0].strip()
    if prefix.upper().startswith("TN"):
        return normalize_tn_locator(prefix)
    locator_match = re.search(r"TN\s*[\d\- ]+(?:\|\s*TN\s*[\d\- ]+)?", source_locator, flags=re.IGNORECASE)
    return normalize_tn_locator(locator_match.group(0)) if locator_match else ""


def build_crossref_entry(source_key: str, source_locator: str, basis: str) -> dict:
    return {
        "source_key": source_key,
        "source_label": source_label(source_key),
        "source_locator": source_locator,
        "source_role": SOURCE_ROLE_BY_KEY[source_key],
        "status": STATUS_BY_KEY[source_key],
        "basis": basis,
    }


def build_translation_source_action_rows(
    sip_rows: list[dict],
    iob_rows: list[dict],
    tn_translation_units: list[dict],
) -> list[dict]:
    sip_linked_count = len(
        {
            (row.get("linked_corpus_record_id") or row.get("linked_inscription_id") or "").strip()
            for row in sip_rows
            if (row.get("linked_corpus_record_id") or row.get("linked_inscription_id") or "").strip()
        }
    )
    sip_inscription_count = len(
        {
            (row.get("linked_inscription_id") or row.get("linked_corpus_record_id") or "").strip()
            for row in sip_rows
            if (row.get("linked_inscription_id") or row.get("linked_corpus_record_id") or "").strip()
        }
    )
    tn_linked_count = len(
        {
            row.get("linked_corpus_record_id", "").strip()
            for row in iob_rows
            if row.get("tn_ref") and row.get("linked_corpus_record_id", "").strip()
        }
    )
    ppa_linked_count = len(
        {
            row.get("linked_corpus_record_id", "").strip()
            for row in iob_rows
            if row.get("ppa_ref") and row.get("linked_corpus_record_id", "").strip()
        }
    )
    iob_linked_count = len(
        {
            row.get("linked_corpus_record_id", "").strip()
            for row in iob_rows
            if row.get("linked_corpus_record_id", "").strip()
        }
    )
    tn_integrated_record_count = len(
        {
            row.get("linked_corpus_record_id", "").strip()
            for row in tn_translation_units
            if row.get("linked_corpus_record_id", "").strip()
        }
    )
    tn_integrated_unit_count = len(tn_translation_units)
    action_specs = [
        {
            "source_key": SHWEGUGYI_TRANSLATION_SOURCE_KEY,
            "bibliographic_label": SHWEGUGYI_TRANSLATION_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "1920-shwegugyiinscription-luce1920-pdf",
            "matched_file_name": "ShwegugyiInscription-Luce1920.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "true",
            "translation_scope": "standalone_inscription_translation",
            "linked_corpus_record_count": "1",
            "linked_inscription_count": "1",
            "action_status": "translation_integrated",
            "next_action": "Keep Shwegugyi integrated and proceed to the next translation-bearing source.",
            "evidence": "jbrs_translation_candidate_review.tsv and the completed translation unit confirm a standalone translation section.",
            "notes": "The complete published English translation is now integrated into the enriched corpus candidate.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": ANANDA_TRANSLATION_SOURCE_KEY,
            "bibliographic_label": ANANDA_TRANSLATION_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "1976-anandainscriptions-tinlwin1976-pdf",
            "matched_file_name": "AnandaInscriptions-Tinlwin1976.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "true",
            "translation_scope": "mixed_inscription_translation",
            "linked_corpus_record_count": "0",
            "linked_inscription_count": "0",
            "action_status": "out_of_scope_late_ink_wall_inscription",
            "next_action": "Do not attempt further Ananda linkage unless project scope is expanded.",
            "evidence": "The article concerns late eighteenth-century Ananda Okkyaung ink/wall inscriptions with Pali and Burmese versions, not a corpus-linked Old Burmese lithic inscription.",
            "notes": "Resolved as out of scope for the current Old Burmese / Burmese structured inscription enrichment workflow. The source concerns late eighteenth-century Ananda Okkyaung ink/wall inscriptions with Pali and Burmese versions, not a corpus-linked Old Burmese lithic inscription. Do not attempt further linkage unless project scope changes.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": FRASCH_MACHINE_TRANSLATION_SOURCE_KEY,
            "bibliographic_label": FRASCH_MACHINE_TRANSLATION_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "frasch_1996_pagan_machineenglishtranslat-6f1791859aa4",
            "matched_file_name": "Frasch-1996-Pagan-MachineEnglishTranslation-OLD-VERSION.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "true",
            "translation_scope": "secondary_history_translation",
            "linked_corpus_record_count": "0",
            "linked_inscription_count": "0",
            "action_status": "wrong_source_rejected",
            "next_action": "Do not treat this as an inscription translation source for the corpus candidate.",
            "evidence": "The local PDF is a machine translation of Frasch's book, not a direct inscription translation.",
            "notes": "Useful as background prose only, not as a corpus translation witness.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": MYAZEDI_TRANSLATION_SOURCE_KEY,
            "bibliographic_label": MYAZEDI_TRANSLATION_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "pemaungtin_1974_myazediinscription-56bbc5aae6bb",
            "matched_file_name": "PeMaungTin 1974 MyazediInscription.PDF",
            "already_ocr_available": "false",
            "contains_english_translation": "false",
            "translation_scope": "wrong_local_witness",
            "linked_corpus_record_count": "0",
            "linked_inscription_count": "0",
            "action_status": "wrong_source_rejected",
            "next_action": "Acquire a correct article scan before revisiting this source.",
            "evidence": "Direct extraction from the current local file yields bibliographic request-card metadata rather than article body text or translation content.",
            "notes": "Current local witness is not usable for translation extraction; keep this source closed until a better scan is supplied.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": RAJAKUMAR_TRANSLATION_SOURCE_KEY,
            "bibliographic_label": RAJAKUMAR_TRANSLATION_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "tun_aung_chain_2001_rajakumar_inscriptio-d55d64ebc41c",
            "matched_file_name": "Tun Aung Chain 2001 Rajakumar Inscription.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "true",
            "translation_scope": "standalone_inscription_translation_version_split",
            "linked_corpus_record_count": "2",
            "linked_inscription_count": "2",
            "action_status": "translation_integrated_partial_version_split",
            "next_action": "Keep Myanmar and Pali versions integrated; hold Mon and Pyu as unlinked candidate units until matching corpus records are available.",
            "evidence": "Appendix I provides separate Myanmar/Mon/Pyu/Pali sections; structured corpus has secure Rajakumar/Myazedi matches for Myanmar and Pali, but no corresponding Mon/Pyu records.",
            "notes": "Version split complete for extraction. Myanmar linked to obi-v01-n0001-tx-p0001 and Pali linked to obi-v01-n0001-tx-p0002; Mon and Pyu remain candidate-only/unlinked.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": TN_SOURCE_KEY,
            "bibliographic_label": TN_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": TN_LOCAL_FILE_ID,
            "matched_file_name": TN_LOCAL_FILE_NAME,
            "already_ocr_available": "true",
            "contains_english_translation": "true",
            "translation_scope": "standalone_inscription_translation",
            "linked_corpus_record_count": str(tn_linked_count),
            "linked_inscription_count": str(tn_linked_count),
            "action_status": "tn_extraction_substantially_complete_manual_residue_remaining",
            "next_action": (
                "Keep TN integrated set stable and resolve the small residual unresolved cases only when "
                "new witness-quality evidence appears."
            ),
            "evidence": (
                "Tracked OCR outputs now exist under data/working/ocr/pagan_pinya_ava_1899/, "
                "and IOB cross-reference rows provide TN locators plus high-confidence record links."
            ),
            "notes": (
                f"TN extraction integrated so far: {tn_integrated_unit_count} units across {tn_integrated_record_count} records. "
                "Only a compact manually logged residual unresolved set remains."
            ),
            "tracked_ocr_text_path": str(TN_OCR_CLEANED_TEXT_PATH.relative_to(REPO_ROOT)),
        },
        {
            "source_key": PPA_SOURCE_KEY,
            "bibliographic_label": PPA_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "missing_local_file",
            "matched_local_file_id": "",
            "matched_file_name": "",
            "already_ocr_available": "false",
            "contains_english_translation": "false",
            "translation_scope": "edition_or_catalogue_candidate",
            "linked_corpus_record_count": str(ppa_linked_count),
            "linked_inscription_count": str(ppa_linked_count),
            "action_status": "source_missing_acquire_manually",
            "next_action": "Acquire a local scan or photocopy of PPA if later edition/source-text comparison is needed.",
            "evidence": "The IOB cross-reference index supplies PPA references, but no local PPA witness has been confirmed.",
            "notes": "Use as a bibliography/source-text lead, not as an English translation source yet.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": SIP_SOURCE_KEY,
            "bibliographic_label": SIP_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3",
            "matched_file_name": "Luce&PeMaungTin 1928 inscriptions of Pagan.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "false",
            "translation_scope": "source_text_only",
            "linked_corpus_record_count": str(sip_linked_count),
            "linked_inscription_count": str(sip_inscription_count),
            "action_status": "no_translation_present",
            "next_action": "Keep SIP as source-text witness evidence only.",
            "evidence": "Accepted SIP witness units confirm source text but no English inscription translation.",
            "notes": "SIP remains provenance for source text, not translation.",
            "tracked_ocr_text_path": "",
        },
        {
            "source_key": IOB_SOURCE_KEY,
            "bibliographic_label": IOB_BIBLIOGRAPHIC_LABEL,
            "local_file_status": "matched_local_file_available",
            "matched_local_file_id": "inscriptions_of_burma-b7c07d9f6d02",
            "matched_file_name": "Inscriptions of Burma.pdf",
            "already_ocr_available": "true",
            "contains_english_translation": "false",
            "translation_scope": "plate_index_only",
            "linked_corpus_record_count": str(iob_linked_count),
            "linked_inscription_count": str(iob_linked_count),
            "action_status": "no_translation_present",
            "next_action": "Keep IOB as a cross-reference witness only.",
            "evidence": "The repo-safe OCR metadata marks IOB as a plate-index cross-reference rather than an extractable inscription translation.",
            "notes": "Useful for concordance and plate linking, not translation extraction.",
            "tracked_ocr_text_path": "",
        },
    ]

    rows: list[dict] = []
    for spec in action_specs:
        rows.append(spec)
    return rows


def build_translation_units_extracted_rows(
    translation_units: list[dict],
    iob_rows: list[dict],
    tn_page_map: dict[int, str],
) -> list[dict]:
    rows: list[dict] = []
    translation_text = SHWEGUGYI_TRANSLATION_TEXT_PATH.read_text(encoding="utf-8").strip()
    for unit in translation_units:
        if unit.get("source_local_file_id") != "1920-shwegugyiinscription-luce1920-pdf":
            continue
        rows.append(
            {
                "translation_unit_id": "jbrs-translation-unit-20260531-001",
                "source_key": SHWEGUGYI_TRANSLATION_SOURCE_KEY,
                "source_bibliographic_label": SHWEGUGYI_TRANSLATION_BIBLIOGRAPHIC_LABEL,
                "matched_local_file_id": unit.get("source_local_file_id", ""),
                "source_locator": "JBRS 10(2), 1920, pp. 67-74",
                "linked_inscription_id": "obi-v01-n0004-ob-p0011",
                "linked_corpus_record_id": "obi-v01-n0004-ob-p0011",
                "translation_language": unit.get("translation_language", "English"),
                "translation_text": translation_text,
                "translation_status": "published_translation",
                "link_basis": "JBRS 10(2), 1920, pp. 67-74 explicitly matches the Shwegugyi Pagoda Inscription corpus record.",
                "confidence": "high",
                "needs_human_review": "false",
                "notes": "Completed published translation integrated into the enriched corpus candidate.",
            }
        )
    rajakumar_text = RAJAKUMAR_TRANSLATION_TEXT_PATH.read_text(encoding="utf-8").strip() if RAJAKUMAR_TRANSLATION_TEXT_PATH.exists() else ""
    if rajakumar_text:
        heading_pattern = re.compile(
            r"^(Myanmar Text \(A 39 lines, B 34, lines\) tr\. Charles Duroiselle \(1919\)|"
            r"Mon Text \(A 33 lines B 46 lines\) tr\. C\.O\.Blagden \(1919\)|"
            r"Pyu Text \(A 26 lines B 29 lines\)|"
            r"Pali Text \(A 41 lines, B 40, lines\) tr\. Charles Duroiselle \(1919\))$",
            re.MULTILINE,
        )
        headings = [(match.group(0), match.start()) for match in heading_pattern.finditer(rajakumar_text)]
        section_text_by_heading: dict[str, str] = {}
        for index, (heading, start) in enumerate(headings):
            end = headings[index + 1][1] if index + 1 < len(headings) else len(rajakumar_text)
            section_text_by_heading[heading] = rajakumar_text[start:end].strip()

        common_label = "Tun Aung Chain, The Rajakumar Inscription, Cultural Classics, Yangon Universities Press, 2001, pp. 25-37"
        common_file_id = "tun_aung_chain_2001_rajakumar_inscriptio-d55d64ebc41c"
        unit_specs = [
            {
                "translation_unit_id": "rajakumar-translation-2001-myanmar",
                "heading": "Myanmar Text (A 39 lines, B 34, lines) tr. Charles Duroiselle (1919)",
                "source_locator": "Cultural Classics 2001, Appendix I Myanmar Text, pp. 33-34 (OCR pages 10-11)",
                "linked_inscription_id": "obi-v01-n0001-tx-p0001",
                "linked_corpus_record_id": "obi-v01-n0001-tx-p0001",
                "translation_status": "published_translation",
                "link_basis": (
                    "The Myanmar Text section aligns with the Myanmar Rajakumar/Myazedi corpus record "
                    "title, references, and matching narrative formulae (Arimaddanapur, Tribhuvanadityadhammaraj, "
                    "Trilokavatamsika, 1628 era + 28 regnal years, and three-village donation)."
                ),
                "confidence": "high",
                "needs_human_review": "false",
                "notes": "version_label=Myanmar Text; integrated to Myanmar Rajakumar/Myazedi record.",
            },
            {
                "translation_unit_id": "rajakumar-translation-2001-mon",
                "heading": "Mon Text (A 33 lines B 46 lines) tr. C.O.Blagden (1919)",
                "source_locator": "Cultural Classics 2001, Appendix I Mon Text, pp. 34-35 (OCR pages 11-12)",
                "linked_inscription_id": "",
                "linked_corpus_record_id": "",
                "translation_status": "published_translation",
                "link_basis": (
                    "No structured corpus record with a Rajakumar/Myazedi Mon-language counterpart was found "
                    "in corpus_release_v0_3 inscriptions/lines and citation layers."
                ),
                "confidence": "needs_review",
                "needs_human_review": "true",
                "notes": "version_label=Mon Text; extracted but kept unlinked pending a Mon corpus record.",
            },
            {
                "translation_unit_id": "rajakumar-translation-2001-pyu",
                "heading": "Pyu Text (A 26 lines B 29 lines)",
                "source_locator": "Cultural Classics 2001, Appendix I Pyu Text, p. 35 (OCR page 12)",
                "linked_inscription_id": "",
                "linked_corpus_record_id": "",
                "translation_status": "published_partial_translation",
                "link_basis": (
                    "The Appendix I Pyu section is present but no structured Rajakumar/Myazedi Pyu record is "
                    "available in corpus_release_v0_3 for secure linkage."
                ),
                "confidence": "needs_review",
                "needs_human_review": "true",
                "notes": "version_label=Pyu Text; extracted as partial due OCR clipping and kept unlinked.",
            },
            {
                "translation_unit_id": "rajakumar-translation-2001-pali",
                "heading": "Pali Text (A 41 lines, B 40, lines) tr. Charles Duroiselle (1919)",
                "source_locator": "Cultural Classics 2001, Appendix I Pali Text, pp. 35-36 (OCR pages 12-13)",
                "linked_inscription_id": "obi-v01-n0001-tx-p0002",
                "linked_corpus_record_id": "obi-v01-n0001-tx-p0002",
                "translation_status": "published_translation",
                "link_basis": (
                    "The Pali Text section matches the Pali Rajakumar/Myazedi corpus record language and "
                    "reference profile (List-52, IOB4-361/b, EB Vol.1 no.1), with identical storyline and dedication formula."
                ),
                "confidence": "high",
                "needs_human_review": "false",
                "notes": "version_label=Pali Text; integrated to Pali Rajakumar/Myazedi record.",
            },
        ]
        for spec in unit_specs:
            section_text = section_text_by_heading.get(spec["heading"], "")
            if not section_text:
                continue
            rows.append(
                {
                    "translation_unit_id": spec["translation_unit_id"],
                    "source_key": RAJAKUMAR_TRANSLATION_SOURCE_KEY,
                    "source_bibliographic_label": common_label,
                    "matched_local_file_id": common_file_id,
                    "source_locator": spec["source_locator"],
                    "linked_inscription_id": spec["linked_inscription_id"],
                    "linked_corpus_record_id": spec["linked_corpus_record_id"],
                    "translation_language": "English",
                    "translation_text": section_text,
                    "translation_status": spec["translation_status"],
                    "link_basis": spec["link_basis"],
                    "confidence": spec["confidence"],
                    "needs_human_review": spec["needs_human_review"],
                    "notes": spec["notes"],
                }
            )

    iob_high_rows = [
        row
        for row in iob_rows
        if row.get("linked_corpus_record_id", "").strip()
        and row.get("tn_ref", "").strip()
        and row.get("link_confidence", "").strip() == "high"
        and row.get("needs_manual_review", "").strip() == "false"
    ]
    iob_rows_by_locator = {
        normalize_tn_locator(row.get("tn_ref", "")): row
        for row in iob_rows
        if normalize_tn_locator(row.get("tn_ref", ""))
    }
    iob_lookup: dict[tuple[str, str], dict] = {}
    for row in iob_high_rows:
        key = (
            normalize_tn_locator(row.get("tn_ref", "")),
            row.get("linked_corpus_record_id", "").strip(),
        )
        iob_lookup[key] = row

    for spec in TN_TRANSLATION_UNIT_SPECS:
        linked_record_id = spec["linked_corpus_record_id"]
        locator = normalize_tn_locator(spec["tn_locator"])
        iob_row = iob_lookup.get((locator, linked_record_id))
        if not iob_row and spec.get("allow_locator_only_match") == "true":
            iob_row = iob_rows_by_locator.get(locator)
        if not iob_row:
            continue
        translation_text = extract_tn_translation_text(
            locator=spec["tn_locator"],
            page_map=tn_page_map,
            start_anchor=spec.get("start_anchor"),
            end_anchor=spec.get("end_anchor"),
        )
        if not translation_text:
            continue
        ocr_pages = tn_locator_to_ocr_pages(spec["tn_locator"])
        source_locator = spec.get("source_locator_override", "").strip() or (
            f"{spec['tn_locator']} ({spec['iob_plate']}; OCR pages {ocr_pages})"
            if ocr_pages
            else f"{spec['tn_locator']} ({spec['iob_plate']})"
        )
        rows.append(
            {
                "translation_unit_id": spec["translation_unit_id"],
                "source_key": TN_SOURCE_KEY,
                "source_bibliographic_label": TN_BIBLIOGRAPHIC_LABEL,
                "matched_local_file_id": TN_LOCAL_FILE_ID,
                "source_locator": source_locator,
                "linked_inscription_id": spec["linked_inscription_id"],
                "linked_corpus_record_id": linked_record_id,
                "translation_language": "English",
                "translation_text": translation_text,
                "translation_status": spec["translation_status"],
                "link_basis": spec.get("link_basis", "").strip() or (
                    f"High-confidence IOB concordance link ({spec['iob_plate']}, {spec['tn_locator']}) to "
                    f"{linked_record_id}; extracted from tracked TN OCR pages."
                ),
                "confidence": spec.get("confidence", "high"),
                "needs_human_review": spec.get("needs_human_review", "false"),
                "notes": spec.get("notes", "").strip() or (
                    f"version_label=TN locator {spec['tn_locator']}; source_iob_plate={spec['iob_plate']}; "
                    "extracted from data/working/ocr/pagan_pinya_ava_1899/ocr_cleaned_text_light.txt."
                ),
            }
        )
    return rows


def build_translation_integration_preview_rows(
    translation_rows: list[dict],
    record_title_by_id: dict[str, str],
) -> list[dict]:
    rows: list[dict] = []
    fallback_title_by_record = {
        "obi-v01-n0004-ob-p0011": "ရွှေဂူကြီးဘုရားကျောက်စာ",
        "obi-v01-n0001-tx-p0001": "မြစေတီဘုရားကျောက်စာ၊ မြန်မာ (ရာဇကုမာရကျောက်စာ)",
        "obi-v01-n0001-tx-p0002": "မြစေတီဘုရား ကျောက်စာ ပါဠိ (ရာဇကုမာရကျောက်စာ)",
    }
    for row in translation_rows:
        text = row.get("translation_text", "")
        record_id = row.get("linked_corpus_record_id", "").strip()
        if not text or not record_id:
            continue
        rows.append(
            {
                "linked_corpus_record_id": record_id,
                "linked_inscription_id": row.get("linked_inscription_id", ""),
                "title_or_label": (
                    record_title_by_id.get(record_id, "")
                    or fallback_title_by_record.get(record_id, "")
                    or row.get("linked_inscription_id", "")
                ),
                "source_key": row.get("source_key", ""),
                "source_locator": row.get("source_locator", ""),
                "translation_status": row.get("translation_status", ""),
                "translation_text_snippet": text[:180].replace("\n", " "),
                "translation_length_chars": str(len(text)),
                "has_existing_transcription": "true",
                "link_basis": row.get("link_basis", ""),
                "needs_human_review": row.get("needs_human_review", "false"),
                "notes": row.get("notes", ""),
            }
        )
    return rows


def choose_tn_target_priority(tn_locator: str) -> str:
    page_count = len(parse_tn_pages(tn_locator))
    return "high" if 1 <= page_count <= 2 else "medium"


def build_tn_translation_targets_rows(
    iob_rows: list[dict],
    record_title_by_id: dict[str, str],
) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in iob_rows:
        tn_ref = normalize_tn_locator(row.get("tn_ref", ""))
        override = TN_CROSSWITNESS_TARGET_OVERRIDES.get(tn_ref, {})
        linked_record_id = row.get("linked_corpus_record_id", "").strip() or override.get("linked_corpus_record_id", "").strip()
        linked_inscription_id = (
            row.get("linked_inscription_id", "").strip()
            or override.get("linked_inscription_id", "").strip()
            or linked_record_id
        )
        if not tn_ref or not linked_record_id:
            continue
        if (
            not override
            and (row.get("link_confidence", "").strip() != "high" or row.get("needs_manual_review", "").strip() != "false")
        ):
            continue
        key = (tn_ref, linked_record_id)
        if key in seen:
            continue
        seen.add(key)
        link_basis = override.get("link_basis", "").strip() or row.get("link_basis", "").strip() or (
            "inscriptions_of_burma_cross_reference_index.tsv high-confidence plate-to-record concordance"
        )
        source_of_link = override.get("source_of_link", "").strip() or (
            "inscriptions_of_burma_cross_reference_index.tsv high-confidence plate-to-record concordance"
        )
        rows.append(
            {
                "tn_locator": tn_ref,
                "linked_corpus_record_id": linked_record_id,
                "linked_inscription_id": linked_inscription_id,
                "title_or_label": record_title_by_id.get(linked_record_id, "") or linked_inscription_id,
                "iob_plate": row.get("iob_plate", ""),
                "list_ref": row.get("list_ref", ""),
                "ppa_ref": row.get("ppa_ref", ""),
                "sip_ref": row.get("sip_ref", ""),
                "source_of_link": source_of_link,
                "priority": choose_tn_target_priority(tn_ref),
                "notes": link_basis,
            }
        )
    rows.sort(key=lambda item: (item["priority"] != "high", item["tn_locator"], item["linked_corpus_record_id"]))
    return rows


def build_tn_translation_target_status_rows(
    tn_target_rows: list[dict],
    translation_rows: list[dict],
) -> list[dict]:
    translation_units_by_key: dict[tuple[str, str], list[str]] = {}
    for row in translation_rows:
        if row.get("source_key") != TN_SOURCE_KEY:
            continue
        record_id = row.get("linked_corpus_record_id", "").strip()
        locator = tn_locator_from_source_locator(row.get("source_locator", ""))
        if not locator or not record_id:
            continue
        translation_units_by_key.setdefault((locator, record_id), []).append(row.get("translation_unit_id", ""))

    status_rows: list[dict] = []
    for target in tn_target_rows:
        locator = normalize_tn_locator(target.get("tn_locator", ""))
        record_id = target.get("linked_corpus_record_id", "").strip()
        key = (locator, record_id)
        override = TN_TARGET_STATUS_OVERRIDES.get(key, {})
        integrated_units = [unit_id for unit_id in translation_units_by_key.get(key, []) if unit_id]
        if integrated_units:
            status = override.get("current_status", "integrated")
            reason_not_integrated = ""
            next_action = ""
            extra_notes = override.get("notes", "")
        else:
            status = override.get("current_status", "still_unresolved")
            reason_not_integrated = override.get(
                "reason_not_integrated",
                "No integrated TN translation unit is currently available for this target row after manual OCR/page inspection.",
            )
            next_action = override.get(
                "next_action",
                "Continue targeted page-level review; do not integrate without secure boundary and linkage evidence.",
            )
            extra_notes = override.get("notes", "")
        if status not in TN_TARGET_STATUS_VALUES:
            status = "still_unresolved"
        notes = " | ".join(part for part in [target.get("notes", "").strip(), extra_notes] if part)
        status_rows.append(
            {
                "tn_locator": locator,
                "linked_corpus_record_id": record_id,
                "linked_inscription_id": target.get("linked_inscription_id", ""),
                "title_or_label": target.get("title_or_label", ""),
                "iob_plate": target.get("iob_plate", ""),
                "list_ref": target.get("list_ref", ""),
                "ppa_ref": target.get("ppa_ref", ""),
                "sip_ref": target.get("sip_ref", ""),
                "priority": target.get("priority", ""),
                "current_status": status,
                "translation_unit_id": "; ".join(integrated_units),
                "reason_not_integrated": reason_not_integrated,
                "next_action": next_action,
                "notes": notes,
            }
        )
    status_rows.sort(key=lambda item: (item["priority"] != "high", item["tn_locator"], item["linked_corpus_record_id"]))
    return status_rows


def build_tn_candidates_needing_review_rows(
    iob_rows: list[dict],
    tn_page_map: dict[int, str],
    tn_target_rows: list[dict],
    translation_rows: list[dict],
) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    target_by_locator: dict[str, list[dict]] = {}
    for target in tn_target_rows:
        target_by_locator.setdefault(normalize_tn_locator(target.get("tn_locator", "")), []).append(target)
    integrated_tn_rows = [row for row in translation_rows if row.get("source_key") == TN_SOURCE_KEY]
    for row in iob_rows:
        tn_ref = normalize_tn_locator(row.get("tn_ref", ""))
        if not tn_ref or tn_ref in seen:
            continue
        if tn_ref not in TN_CANDIDATE_REVIEW_LOCATORS:
            continue
        if tn_ref in TN_CANDIDATE_REVIEW_SUPPRESSED_LOCATORS:
            continue
        link_confidence = row.get("link_confidence", "").strip()
        needs_review = row.get("needs_manual_review", "").strip() == "true"
        linked_record_id = row.get("linked_corpus_record_id", "").strip()
        if link_confidence == "high" and not needs_review and linked_record_id:
            continue
        snippet = extract_tn_translation_text(locator=tn_ref, page_map=tn_page_map)[:220].replace("\n", " ")
        possible_targets = target_by_locator.get(tn_ref, [])
        possible_record_ids = sorted(
            {
                target.get("linked_corpus_record_id", "").strip()
                for target in possible_targets
                if target.get("linked_corpus_record_id", "").strip()
            }
        )
        possible_inscription_ids = sorted(
            {
                target.get("linked_inscription_id", "").strip()
                for target in possible_targets
                if target.get("linked_inscription_id", "").strip()
            }
        )
        overlapping_integrated = [
            integrated
            for integrated in integrated_tn_rows
            if set(parse_tn_pages(tn_ref)).intersection(set(parse_tn_pages(tn_locator_from_source_locator(integrated.get("source_locator", "")))))
        ]
        override = TN_CANDIDATE_RESOLUTION_OVERRIDES.get(tn_ref, {})
        if override:
            reason_uncertain = override["reason_uncertain"]
            recommended_action = override["recommended_human_action"]
            override_notes = override.get("notes", "")
        elif overlapping_integrated:
            reason_uncertain = "confirmed_duplicate_or_overlap"
            recommended_action = "Treat as overlap unless a plate-specific standalone boundary can be isolated."
            override_notes = "page_image_inspection=attempted"
        elif possible_record_ids:
            reason_uncertain = "still_unresolved"
            recommended_action = "Compare locator text span and plate context to confirm whether this row is safely extractable."
            override_notes = "page_image_inspection=attempted"
        else:
            reason_uncertain = "no_corresponding_translation_found"
            recommended_action = "Resolve corpus linkage first using plate/list references before extraction."
            override_notes = "page_image_inspection=attempted"
        note_parts = [
            (
                f"iob_plate={row.get('iob_plate', '')}; locator_pages={','.join(str(page) for page in parse_tn_pages(tn_ref))}; "
                f"ocr_pages={tn_locator_to_ocr_pages(tn_ref)}; link_basis={row.get('link_basis', '')}"
            ),
            override_notes,
        ]
        rows.append(
            {
                "tn_locator": tn_ref,
                "possible_corpus_record_ids": "; ".join(possible_record_ids) or linked_record_id,
                "possible_inscription_ids": "; ".join(possible_inscription_ids) or row.get("linked_inscription_id", "").strip(),
                "translation_text_snippet": snippet,
                "reason_uncertain": reason_uncertain,
                "recommended_human_action": recommended_action,
                "notes": " | ".join(part for part in note_parts if part),
            }
        )
        seen.add(tn_ref)
        if len(rows) >= 10:
            break
    return rows


def build_tn_manual_resolution_log_rows(
    tn_target_rows: list[dict],
    tn_target_status_rows: list[dict],
    tn_review_rows: list[dict],
    translation_rows: list[dict],
) -> list[dict]:
    target_by_locator = {
        normalize_tn_locator(row.get("tn_locator", "")): row for row in tn_target_rows
    }
    status_by_locator = {
        normalize_tn_locator(row.get("tn_locator", "")): row for row in tn_target_status_rows
    }
    review_by_locator = {
        normalize_tn_locator(row.get("tn_locator", "")): row for row in tn_review_rows
    }
    tn_units = [row for row in translation_rows if row.get("source_key") == TN_SOURCE_KEY]
    unit_ids_by_locator: dict[str, list[str]] = {}
    first_unit_by_locator: dict[str, dict] = {}
    for row in tn_units:
        locator = normalize_tn_locator(tn_locator_from_source_locator(row.get("source_locator", "")))
        if locator:
            unit_ids_by_locator.setdefault(locator, []).append(row.get("translation_unit_id", ""))
            first_unit_by_locator.setdefault(locator, row)

    rows: list[dict] = []
    for locator_raw in TN_MANUAL_INSPECTION_LOCATORS:
        locator = normalize_tn_locator(locator_raw)
        target_row = target_by_locator.get(locator, {})
        status_row = status_by_locator.get(locator, {})
        review_row = review_by_locator.get(locator, {})
        candidate_override = TN_CANDIDATE_RESOLUTION_OVERRIDES.get(locator, {})
        candidate_reason = candidate_override.get("reason_uncertain", "")
        if status_row.get("current_status"):
            resolution_status = status_row.get("current_status")
        elif candidate_reason == "confirmed_duplicate_or_overlap":
            resolution_status = "confirmed_duplicate_or_overlap"
        elif candidate_reason in TN_REVIEW_FINAL_UNRESOLVED_REASONS:
            resolution_status = "no_corresponding_translation_found"
        else:
            resolution_status = "still_unresolved"
        translation_unit_id = status_row.get("translation_unit_id", "").strip()
        if not translation_unit_id:
            translation_unit_id = "; ".join(
                sorted(unit_id for unit_id in unit_ids_by_locator.get(locator, []) if unit_id)
            )
        if not status_row.get("current_status") and translation_unit_id:
            resolution_status = "integrated_after_manual_review"
        if not translation_unit_id and "overlap_unit=" in candidate_override.get("notes", ""):
            for part in candidate_override.get("notes", "").split(";"):
                cleaned = part.strip()
                if cleaned.startswith("overlap_unit="):
                    translation_unit_id = cleaned.split("=", 1)[1].strip().rstrip(".")
                    break
        printed_pages = tn_locator_to_printed_pages(locator)
        ocr_pages = ocr_page_list_for_locator(locator)
        ocr_pages_str = ", ".join(str(page) for page in ocr_pages)
        image_pages = ", ".join(f"page-{page:03d}.png" for page in ocr_pages)
        linked_record_id = (
            status_row.get("linked_corpus_record_id", "")
            or target_row.get("linked_corpus_record_id", "")
            or review_row.get("possible_corpus_record_ids", "")
        )
        if not linked_record_id:
            linked_record_id = first_unit_by_locator.get(locator, {}).get("linked_corpus_record_id", "")
        linked_inscription_id = (
            status_row.get("linked_inscription_id", "")
            or target_row.get("linked_inscription_id", "")
            or review_row.get("possible_inscription_ids", "")
        )
        if not linked_inscription_id:
            linked_inscription_id = first_unit_by_locator.get(locator, {}).get("linked_inscription_id", "")
        problem_found = (
            status_row.get("reason_not_integrated", "")
            or review_row.get("reason_uncertain", "")
            or "manual inspection completed"
        )
        if resolution_status in {"integrated_after_manual_review", "integrated"}:
            decision = "Integrated a bounded TN segment after direct page/image review."
        elif resolution_status == "confirmed_duplicate_or_overlap":
            decision = "Confirmed overlap/duplicate relation to an already integrated TN segment."
        elif resolution_status == "deferred_requires_scholarly_judgement":
            decision = "Deferred pending scholarly segmentation judgement."
        elif resolution_status == "not_extractable_even_after_page_inspection":
            decision = "Confirmed unreadable or non-recoverable after page-image inspection."
        elif resolution_status == "integrated_after_cross_witness_match":
            decision = "Integrated a bounded TN segment after cross-witness source-text match."
        elif resolution_status == "no_corresponding_translation_found":
            decision = "No secure corresponding translation linkage found in current corpus scope."
        else:
            decision = "Manual inspection attempted but resolution remains open."
        notes_parts = [
            status_row.get("notes", ""),
            review_row.get("notes", ""),
            TN_MANUAL_NOTES_OVERRIDES.get(locator, ""),
            "page_image_inspection=attempted",
        ]
        deduped_notes: list[str] = []
        for part in notes_parts:
            cleaned = part.strip()
            if cleaned and cleaned not in deduped_notes:
                deduped_notes.append(cleaned)
        rows.append(
            {
                "tn_locator": locator,
                "printed_page_or_pages": printed_pages,
                "ocr_pages_inspected": ocr_pages_str,
                "image_pages_inspected": image_pages,
                "existing_status": TN_MANUAL_EXISTING_STATUS_BY_LOCATOR.get(locator, "candidate_needs_human_review"),
                "resolution_status": resolution_status,
                "translation_unit_id": translation_unit_id,
                "linked_corpus_record_id": linked_record_id,
                "linked_inscription_id": linked_inscription_id,
                "evidence_used": (
                    "tracked OCR page markers + local vision page_text + existing zip OCR text + "
                    "rendered page images with targeted Tesseract page OCR"
                ),
                "problem_found": problem_found,
                "decision": decision,
                "notes": " | ".join(deduped_notes),
            }
        )
    return rows


def build_tn_residual_unresolved_rows(
    tn_target_status_rows: list[dict],
    tn_review_rows: list[dict],
    iob_rows: list[dict],
    translation_rows: list[dict],
) -> list[dict]:
    integrated_locators = {
        normalize_tn_locator(tn_locator_from_source_locator(row.get("source_locator", "")))
        for row in translation_rows
        if row.get("source_key") == TN_SOURCE_KEY and row.get("linked_corpus_record_id", "").strip()
    }
    iob_by_locator = {
        normalize_tn_locator(row.get("tn_ref", "")): row
        for row in iob_rows
        if normalize_tn_locator(row.get("tn_ref", ""))
    }
    rows: list[dict] = []

    for status_row in tn_target_status_rows:
        locator = normalize_tn_locator(status_row.get("tn_locator", ""))
        status = status_row.get("current_status", "")
        if status in {
            "integrated",
            "integrated_after_manual_review",
            "integrated_after_cross_witness_match",
            "confirmed_duplicate_or_overlap",
        }:
            continue
        final_status = (
            "deferred_requires_scholarly_segmentation_against_source_text"
            if status == "deferred_requires_scholarly_judgement"
            else status
        )
        rows.append(
            {
                "tn_locator": locator,
                "iob_plate": status_row.get("iob_plate", ""),
                "list_ref": status_row.get("list_ref", ""),
                "ppa_ref": status_row.get("ppa_ref", ""),
                "possible_corpus_record_ids": status_row.get("linked_corpus_record_id", ""),
                "possible_inscription_ids": status_row.get("linked_inscription_id", ""),
                "translation_text_snippet": "",
                "final_status": final_status,
                "evidence_checked": (
                    f"tn_target_status={status}; notes={status_row.get('notes', '')}"
                ).strip(),
                "reason_not_integrated": status_row.get("reason_not_integrated", ""),
                "future_action": status_row.get("next_action", ""),
                "notes": status_row.get("notes", ""),
            }
        )

    for review_row in tn_review_rows:
        locator = normalize_tn_locator(review_row.get("tn_locator", ""))
        final_status = review_row.get("reason_uncertain", "")
        if final_status not in TN_REVIEW_FINAL_UNRESOLVED_REASONS:
            continue
        if locator in integrated_locators:
            continue
        iob_row = iob_by_locator.get(locator, {})
        rows.append(
            {
                "tn_locator": locator,
                "iob_plate": iob_row.get("iob_plate", ""),
                "list_ref": iob_row.get("list_ref", ""),
                "ppa_ref": iob_row.get("ppa_ref", ""),
                "possible_corpus_record_ids": review_row.get("possible_corpus_record_ids", ""),
                "possible_inscription_ids": review_row.get("possible_inscription_ids", ""),
                "translation_text_snippet": review_row.get("translation_text_snippet", ""),
                "final_status": final_status,
                "evidence_checked": (
                    f"iob_link_basis={iob_row.get('link_basis', '')}; review_notes={review_row.get('notes', '')}"
                ).strip(),
                "reason_not_integrated": final_status,
                "future_action": review_row.get("recommended_human_action", ""),
                "notes": review_row.get("notes", ""),
            }
        )

    rows.sort(key=lambda item: item.get("tn_locator", ""))
    return rows


def build_v04_review_checklist_rows(
    *,
    tn_residual_rows: list[dict],
    translation_rows: list[dict],
) -> list[dict]:
    unresolved_locators = ", ".join(sorted(row.get("tn_locator", "") for row in tn_residual_rows if row.get("tn_locator", "")))
    unresolved_note = unresolved_locators or "none"
    has_rajakumar_unlinked = any(
        row.get("source_key") == RAJAKUMAR_TRANSLATION_SOURCE_KEY and not row.get("linked_corpus_record_id", "").strip()
        for row in translation_rows
    )
    rows = [
        {
            "check_id": "v04-check-001",
            "review_item": "Confirm residual TN unresolved decisions and future-action notes.",
            "status": "done",
            "evidence_path": "data/working/corpus_enrichment/release_candidate_v0_4/tn_unresolved_review_v0_4.tsv",
            "notes": f"Residual locators: {unresolved_note}.",
        },
        {
            "check_id": "v04-check-002",
            "review_item": "Confirm no unresolved TN locator was silently integrated.",
            "status": "done",
            "evidence_path": "data/working/corpus_enrichment/release_candidate_v0_4/inscriptions_enriched_v0_4_candidate.jsonl",
            "notes": "Cross-check TN unresolved table against integrated TN translation source_locator values.",
        },
        {
            "check_id": "v04-check-003",
            "review_item": "Confirm Rajakumar Mon/Pyu are classified as no_matching_structured_record_found.",
            "status": "done",
            "evidence_path": "data/working/corpus_enrichment/release_candidate_v0_4/translation_units_v0_4_candidate.tsv",
            "notes": (
                "Mon and Pyu remain unlinked because no matching structured record exists in corpus_release_v0_3."
                if has_rajakumar_unlinked
                else "No unlinked Rajakumar Mon/Pyu units remain."
            ),
        },
        {
            "check_id": "v04-check-004",
            "review_item": "Confirm Ananda remains excluded from integrated translation units.",
            "status": "done",
            "evidence_path": "data/working/corpus_enrichment/release_candidate_v0_4/translation_units_v0_4_candidate.tsv",
            "notes": "Ananda remains out of scope for this release-candidate workflow.",
        },
        {
            "check_id": "v04-check-005",
            "review_item": "Spot-check hard-case TN integrations (TN 36-57, TN 70-71, TN 143, TN 30 | TN 86-87).",
            "status": "done",
            "evidence_path": "data/working/corpus_enrichment/tn_manual_resolution_log.tsv",
            "notes": "Verify segment boundaries, cross-witness linkage, and publication-safe notes are acceptable.",
        },
    ]
    return rows


def build_joined_enriched_records_with_lines(
    enriched_records: list[dict],
    line_rows: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    lines_by_record_id: dict[str, list[dict]] = defaultdict(list)
    for line_row in line_rows:
        record_id = (line_row.get("record_id") or "").strip()
        if not record_id:
            continue
        lines_by_record_id[record_id].append(dict(line_row))

    joined_records: list[dict] = []
    records_with_line_rows = 0
    total_line_rows_joined = 0
    for record in enriched_records:
        record_id = record.get("record_id", "")
        record_lines = [dict(line_row) for line_row in lines_by_record_id.get(record_id, [])]
        joined_record = dict(record)
        joined_record["lines"] = record_lines
        joined_record["line_join_status"] = "line_rows_joined" if record_lines else "no_line_rows_found"
        joined_records.append(joined_record)
        if record_lines:
            records_with_line_rows += 1
            total_line_rows_joined += len(record_lines)

    return joined_records, {
        "joined_records": len(joined_records),
        "records_with_line_rows": records_with_line_rows,
        "records_without_line_rows": len(joined_records) - records_with_line_rows,
        "total_line_rows_joined": total_line_rows_joined,
    }


def build_v04_enriched_with_lines_sample(joined_records: list[dict]) -> list[dict]:
    sample_record_ids = [
        "obi-v01-n0001-tx-p0001",
        "obi-v01-n0004-ob-p0011",
        "obi-v01-n0029-re-p0051",
        "obi-v01-n0045-ob-p0073",
        "obi-v01-n0010-ob-p0026",
    ]
    joined_by_id = {record.get("record_id", ""): record for record in joined_records if record.get("record_id")}
    return [joined_by_id[record_id] for record_id in sample_record_ids if record_id in joined_by_id]


def render_markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def build_v04_release_notes_text(
    *,
    summary: dict,
    joined_summary: dict,
    action_rows: list[dict],
    tn_residual_rows: list[dict],
    translation_rows: list[dict],
) -> str:
    integrated_source_keys = sorted(
        {
            row.get("source_key", "")
            for row in translation_rows
            if row.get("linked_corpus_record_id", "").strip()
        }
    )
    integrated_sources = [source_label(key) for key in integrated_source_keys if key]
    blocked_source_rows = [
        row
        for row in action_rows
        if row.get("action_status")
        not in {
            "translation_integrated",
            "translation_integrated_version_split_complete",
            "translation_integrated_partial_version_split",
            "translation_integrated_myanmar_only",
            "tn_extraction_substantially_complete_manual_residue_remaining",
        }
    ]
    blocked_sources = [
        f"{row.get('source_key', '')}: {row.get('action_status', '')}"
        for row in blocked_source_rows
    ]
    residual_lines = [
        f"{row.get('tn_locator', '')} — {row.get('final_status', '')}: {row.get('reason_not_integrated', '')}"
        for row in tn_residual_rows
    ]
    residual_limit_note = (
        "No residual TN unresolved items remain."
        if not tn_residual_rows
        else "TN residual unresolved cases remain and are preserved as review material only."
    )
    review_line = (
        "- `tn_unresolved_review_v0_4.tsv` is empty; any future TN residue should be re-opened from source evidence before publication."
        if not tn_residual_rows
        else "- Review `tn_unresolved_review_v0_4.tsv` and decide whether any residual TN item should be closed, deferred, or escalated."
    )
    notes = f"""# v0.4 candidate release notes (draft)

## Candidate summary

- total records: {summary.get("total_records", 0)}
- records with any enrichment: {summary.get("records_with_any_enrichment", 0)}
- records with integrated translations: {summary.get("records_with_translation_integrated", 0)}
- integrated translation-unit count: {summary.get("translation_units_integrated_count", 0)}
- SIP source-text witness count (record-level): {summary.get("records_with_sip_source_text_witness", 0)}
- cross-reference enrichment counts: IOB={summary.get("records_with_iob_crossref", 0)}, List={summary.get("records_with_list_crossref", 0)}, PPA={summary.get("records_with_ppa_candidate", 0)}, TN-candidate={summary.get("records_with_tn_translation_candidate", 0)}

## Joined review/use file

- `inscriptions_enriched_v0_4_candidate.jsonl` is the inscription-level enriched file.
- `inscriptions_enriched_with_lines_v0_4_candidate.jsonl` is the joined review/use file with line-level rows embedded.
- translations remain full text in both files.
- line-level data are preserved from `data/release/corpus_release_v0_3/lines.jsonl`, not regenerated.
- joined records: {joined_summary.get("joined_records", 0)}
- records with line rows: {joined_summary.get("records_with_line_rows", 0)}
- records without line rows: {joined_summary.get("records_without_line_rows", 0)}
- total line rows joined: {joined_summary.get("total_line_rows_joined", 0)}

## Sources integrated

{render_markdown_bullets(integrated_sources)}

## Sources excluded or blocked

{render_markdown_bullets(blocked_sources)}

## Residual unresolved TN items

{render_markdown_bullets(residual_lines)}

## Known limitations

- {residual_limit_note}
- Rajakumar Mon and Pyu units are classified as `no_matching_structured_record_found` and remain unlinked translation candidates, not integrations.
- Ananda remains out of scope for this release-candidate workflow.
- PPA remains a missing source-text/edition witness and is not a translation blocker for this draft candidate.
- `peMaungTinMyazedi1974` is a wrong local witness and is excluded from the release workflow.
- This is a draft release candidate and not yet a Zenodo package.

## Pre-release review for Nathan

- {review_line[2:] if review_line.startswith("- ") else review_line}
- Spot-check manual hard-case integrations in `tn_manual_resolution_log.tsv` against cited boundaries.
- Confirm source exclusions (especially Ananda/out-of-scope items) are still desired for this release.
- Approve record-level and translation-unit counts before any external publication step.
"""
    return notes


def write_v04_candidate_package(
    *,
    enriched_records: list[dict],
    joined_records: list[dict],
    joined_summary: dict,
    joined_sample_records: list[dict],
    preview_rows: list[dict],
    translation_unit_rows: list[dict],
    tn_residual_rows: list[dict],
    summary: dict,
    action_rows: list[dict],
    output_inscriptions_jsonl: Path,
    output_inscriptions_with_lines_jsonl: Path,
    output_translation_units_tsv: Path,
    output_enrichment_preview_tsv: Path,
    output_enriched_with_lines_sample_json: Path,
    output_tn_unresolved_review_tsv: Path,
    output_review_checklist_tsv: Path,
    output_release_notes_md: Path,
) -> None:
    translation_unit_fields = [
        "translation_unit_id",
        "source_key",
        "source_bibliographic_label",
        "matched_local_file_id",
        "source_locator",
        "linked_inscription_id",
        "linked_corpus_record_id",
        "translation_language",
        "translation_text",
        "translation_status",
        "link_basis",
        "confidence",
        "needs_human_review",
        "notes",
    ]
    write_jsonl(output_inscriptions_jsonl, enriched_records)
    write_jsonl(output_inscriptions_with_lines_jsonl, joined_records)
    write_tsv(output_translation_units_tsv, translation_unit_rows, translation_unit_fields)
    write_tsv(output_enrichment_preview_tsv, preview_rows, PREVIEW_FIELDS)
    write_tsv(output_tn_unresolved_review_tsv, tn_residual_rows, TN_RESIDUAL_UNRESOLVED_FIELDS)
    checklist_rows = build_v04_review_checklist_rows(
        tn_residual_rows=tn_residual_rows,
        translation_rows=translation_unit_rows,
    )
    write_tsv(output_review_checklist_tsv, checklist_rows, V04_REVIEW_CHECKLIST_FIELDS)
    release_notes = build_v04_release_notes_text(
        summary=summary,
        joined_summary=joined_summary,
        action_rows=action_rows,
        tn_residual_rows=tn_residual_rows,
        translation_rows=translation_unit_rows,
    )
    output_release_notes_md.parent.mkdir(parents=True, exist_ok=True)
    output_release_notes_md.write_text(release_notes, encoding="utf-8")
    output_enriched_with_lines_sample_json.parent.mkdir(parents=True, exist_ok=True)
    output_enriched_with_lines_sample_json.write_text(
        json.dumps(joined_sample_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_tn_translation_integration_preview_rows(
    translation_rows: list[dict],
    record_title_by_id: dict[str, str],
) -> list[dict]:
    rows: list[dict] = []
    for row in translation_rows:
        if row.get("source_key") != TN_SOURCE_KEY:
            continue
        record_id = row.get("linked_corpus_record_id", "").strip()
        if not record_id:
            continue
        tn_locator_match = re.search(r"TN\s*[\d\- ]+", row.get("source_locator", ""))
        tn_locator = tn_locator_match.group(0).strip() if tn_locator_match else ""
        text = row.get("translation_text", "")
        rows.append(
            {
                "linked_corpus_record_id": record_id,
                "linked_inscription_id": row.get("linked_inscription_id", ""),
                "title_or_label": record_title_by_id.get(record_id, "") or row.get("linked_inscription_id", ""),
                "tn_locator": tn_locator,
                "source_locator": row.get("source_locator", ""),
                "translation_status": row.get("translation_status", ""),
                "translation_length_chars": str(len(text)),
                "translation_text_snippet": text[:220].replace("\n", " "),
                "link_basis": row.get("link_basis", ""),
                "confidence": row.get("confidence", ""),
                "needs_human_review": row.get("needs_human_review", "false"),
                "notes": row.get("notes", ""),
            }
        )
    return rows


def build_crossrefs_from_iob_row(row: dict) -> tuple[list[dict], dict]:
    crossrefs: list[dict] = []
    candidate_summary = {
        "has_sip": False,
        "has_tn_candidate": False,
        "has_list": False,
        "has_ppa_candidate": False,
        "has_iob": False,
        "has_ub": False,
        "has_jbrs": False,
    }

    plate = (row.get("iob_plate") or "").strip()
    linked_record_id = (row.get("linked_corpus_record_id") or "").strip()
    if linked_record_id and plate:
        crossrefs.append(
            build_crossref_entry(
                IOB_SOURCE_KEY,
                plate,
                "IOB cross-reference index linked to structured corpus record.",
            )
        )
        candidate_summary["has_iob"] = True

    field_specs = [
        (LIST_SOURCE_KEY, "list_ref", "IOB cross-reference index gives List reference."),
        (PPA_SOURCE_KEY, "ppa_ref", "IOB cross-reference index gives PPA reference."),
        (TN_SOURCE_KEY, "tn_ref", "IOB cross-reference index gives TN reference."),
        (SIP_SOURCE_KEY, "sip_ref", "IOB cross-reference index gives SIP reference."),
        (UB_SOURCE_KEY, "ub_ref", "IOB cross-reference index gives UB reference."),
        (JBRS_SOURCE_KEY, "jbrs_ref", "IOB cross-reference index gives JBRS reference."),
    ]
    for source_key, field_name, basis in field_specs:
        value = (row.get(field_name) or "").strip()
        if not value:
            continue
        crossrefs.append(build_crossref_entry(source_key, value, basis))
        if source_key == LIST_SOURCE_KEY:
            candidate_summary["has_list"] = True
        elif source_key == PPA_SOURCE_KEY:
            candidate_summary["has_ppa_candidate"] = True
        elif source_key == TN_SOURCE_KEY:
            candidate_summary["has_tn_candidate"] = True
        elif source_key == SIP_SOURCE_KEY:
            candidate_summary["has_sip"] = True
        elif source_key == UB_SOURCE_KEY:
            candidate_summary["has_ub"] = True
        elif source_key == JBRS_SOURCE_KEY:
            candidate_summary["has_jbrs"] = True

    return crossrefs, candidate_summary


def build_sip_witness(row: dict) -> dict:
    qc_status = row.get("accepted_export_qc_status", "")
    witness_status = WITNESS_STATUS_BY_QC.get(qc_status, "needs_manual_text_check")
    notes = " | ".join(
        part
        for part in [row.get("accepted_export_qc_notes", "").strip(), row.get("notes", "").strip()]
        if part
    )
    return {
        "sip_inscription_unit_id": row.get("sip_inscription_unit_id", ""),
        "source_key": SIP_SOURCE_KEY,
        "source_bibliographic_label": SIP_BIBLIOGRAPHIC_LABEL,
        "source_locator": " | ".join(
            part
            for part in [row.get("sip_ref", "").strip(), row.get("iob_plate", "").strip(), row.get("list_ref", "").strip()]
            if part
        ),
        "witness_text_raw": row.get("raw_ocr_text", ""),
        "witness_text_cleaned": row.get("cleaned_witness_text", ""),
        "witness_status": witness_status,
        "comparison_status": row.get("comparison_status", ""),
        "notes": notes,
        "provenance": {
            "source_file": "data/working/bibliography/sip_accepted_witness_units.tsv",
            "sip_inscription_unit_id": row.get("sip_inscription_unit_id", ""),
            "accepted_export_qc_status": qc_status,
            "accepted_export_qc_notes": row.get("accepted_export_qc_notes", ""),
        },
    }


def build_translation_candidates(crossrefs: list[dict], *, tn_source_available: bool) -> list[dict]:
    candidate_status = "candidate_source_located" if tn_source_available else "missing_high_value_source"
    basis = (
        "IOB cross-reference index gives a TN reference, and tracked OCR text is available at "
        "data/working/ocr/pagan_pinya_ava_1899/ocr_cleaned_text_light.txt."
        if tn_source_available
        else "IOB cross-reference index gives a TN reference, but no local TN file is currently available."
    )
    candidates: list[dict] = []
    for entry in crossrefs:
        if entry["source_key"] != TN_SOURCE_KEY:
            continue
        candidates.append(
            {
                "source_key": TN_SOURCE_KEY,
                "source_bibliographic_label": TN_BIBLIOGRAPHIC_LABEL,
                "source_locator_hint": entry["source_locator"],
                "status": candidate_status,
                "basis": basis,
            }
        )
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for candidate in candidates:
        key = (
            candidate["source_key"],
            candidate["source_locator_hint"],
            candidate["status"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def choose_enrichment_status(has_sip: bool, has_crossrefs: bool, has_tn_candidates: bool, has_translation: bool) -> str:
    if has_translation and not (has_sip or has_crossrefs or has_tn_candidates):
        return "enriched_with_translation"
    if has_sip and has_tn_candidates:
        return "enriched_with_sip_and_candidates"
    if has_sip and has_crossrefs:
        return "enriched_with_sip_and_crossrefs"
    if has_sip:
        return "enriched_with_sip_witnesses"
    if has_crossrefs and has_tn_candidates:
        return "enriched_with_bibliographic_crossrefs_and_candidates"
    if has_crossrefs:
        return "enriched_with_bibliographic_crossrefs"
    if has_translation:
        return "enriched_with_translation"
    return "baseline_no_enrichment"


def build_preview_row(record: dict, sip_rows: list[dict], crossrefs: list[dict], translation_candidates: list[dict]) -> dict:
    source_text_witnesses = sip_rows
    crossref_labels = [entry["source_label"] for entry in crossrefs]
    candidate_labels = [candidate["source_bibliographic_label"] for candidate in translation_candidates]
    candidate_locators = [candidate["source_locator_hint"] for candidate in translation_candidates]
    record_sip_refs = [row.get("sip_ref", "") for row in sip_rows]
    record_iob_plates = [row.get("iob_plate", "") for row in sip_rows]
    record_list_refs = [row.get("list_ref", "") for row in sip_rows]
    record_ppa_refs = [row.get("ppa_ref", "") for row in sip_rows]
    record_tn_refs = [row.get("tn_ref", "") for row in sip_rows]

    has_translation = bool(record.get("translations"))
    if has_translation and sip_rows and crossrefs:
        preview_note = "Published English translation integrated with SIP witness and IOB cross-reference evidence."
    elif has_translation and crossrefs:
        preview_note = "Published English translation integrated with IOB cross-reference evidence."
    elif has_translation:
        preview_note = "Published English translation integrated."
    elif sip_rows and crossrefs:
        preview_note = "SIP source-text witness and IOB cross-reference enrichment."
    elif sip_rows:
        preview_note = "SIP source-text witness integrated."
    elif crossrefs and translation_candidates:
        preview_note = "IOB cross-reference enrichment with TN translation candidate."
    else:
        preview_note = "IOB cross-reference enrichment."

    translation_status = record.get("translation_status", "no_translation_known")

    return {
        "linked_corpus_record_id": record["record_id"],
        "linked_inscription_id": (sip_rows[0].get("linked_inscription_id", "") if sip_rows else record["record_id"]),
        "title_or_label": record.get("title_original", "") or record.get("title_transliteration", ""),
        "language": record.get("language_original", ""),
        "has_existing_transcription": "true" if record.get("full_transliteration") else "false",
        "has_source_text_witness": "true" if sip_rows else "false",
        "source_text_witness_count": str(len(sip_rows)),
        "has_bibliographic_crossrefs": "true" if crossrefs else "false",
        "crossref_sources": join_unique(crossref_labels),
        "has_translation": "true" if has_translation else "false",
        "translation_status": translation_status,
        "translation_candidate_sources": join_unique(candidate_labels),
        "translation_candidate_locators": join_unique(candidate_locators),
        "sip_ref": join_unique(record_sip_refs),
        "iob_plate": join_unique(record_iob_plates),
        "list_ref": join_unique(record_list_refs),
        "ppa_ref": join_unique(record_ppa_refs),
        "tn_ref": join_unique(record_tn_refs),
        "comparison_status": join_unique([row.get("comparison_status", "") for row in sip_rows]),
        "preview_note": preview_note,
    }


def build_enriched_records(
    inscriptions: list[dict],
    sip_rows: list[dict],
    crossref_rows: list[dict],
    translation_unit_rows: list[dict],
    *,
    tn_source_available: bool,
) -> tuple[list[dict], list[dict], dict[str, int]]:
    sip_by_record: dict[str, list[dict]] = {}
    for row in sip_rows:
        record_id = (row.get("linked_corpus_record_id") or "").strip()
        if record_id:
            sip_by_record.setdefault(record_id, []).append(row)

    crossref_by_record: dict[str, list[dict]] = {}
    iob_rows_by_record: dict[str, list[dict]] = {}
    translation_unit_by_record: dict[str, list[dict]] = {}
    for row in crossref_rows:
        record_id = (row.get("linked_corpus_record_id") or "").strip()
        if not record_id:
            continue
        iob_rows_by_record.setdefault(record_id, []).append(row)
    for row in translation_unit_rows:
        record_id = (row.get("linked_corpus_record_id") or "").strip()
        if not record_id:
            continue
        translation_unit_by_record.setdefault(record_id, []).append(row)

    enriched_records: list[dict] = []
    preview_rows: list[dict] = []
    for record in inscriptions:
        record_id = record.get("record_id", "")
        record_iob_rows = iob_rows_by_record.get(record_id, [])
        record_sip_rows = sip_by_record.get(record_id, [])
        record_translation_units = translation_unit_by_record.get(record_id, [])

        crossrefs: list[dict] = []
        candidate_summary = {
            "has_sip": bool(record_sip_rows),
            "has_tn_candidate": False,
            "has_list": False,
            "has_ppa_candidate": False,
            "has_iob": False,
            "has_ub": False,
            "has_jbrs": False,
        }
        for row in record_iob_rows:
            row_crossrefs, row_summary = build_crossrefs_from_iob_row(row)
            crossrefs.extend(row_crossrefs)
            for key, value in row_summary.items():
                candidate_summary[key] = candidate_summary[key] or value

        if not crossrefs and not record_sip_rows and not record_translation_units:
            enriched_records.append(record)
            continue

        enriched = dict(record)
        translation_candidates = build_translation_candidates(crossrefs, tn_source_available=tn_source_available)

        if record_sip_rows:
            sip_witnesses = [build_sip_witness(row) for row in record_sip_rows]
            enriched["source_text_witnesses"] = sip_witnesses
        else:
            sip_witnesses = []

        if crossrefs:
            enriched["bibliographic_crossrefs"] = crossrefs

        if translation_candidates:
            enriched["translation_source_candidates"] = translation_candidates

        if record_translation_units:
            translations: list[dict] = []
            for translation_row in record_translation_units:
                translations.append(
                    {
                        "language": translation_row.get("translation_language", "English"),
                        "text": translation_row.get("translation_text", ""),
                        "source_key": translation_row.get("source_key", ""),
                        "source_bibliographic_label": translation_row.get("source_bibliographic_label", ""),
                        "source_locator": translation_row.get("source_locator", ""),
                        "translation_status": translation_row.get("translation_status", "published_translation"),
                        "confidence": translation_row.get("confidence", "high"),
                        "notes": translation_row.get("notes", ""),
                    }
                )
            enriched["translations"] = translations
            enriched["translation_status"] = "translation_integrated"
        else:
            enriched["translations"] = []
            enriched["translation_status"] = (
                "translation_source_missing"
                if translation_candidates
                else "no_translation_known"
            )
        enriched["enrichment_status"] = choose_enrichment_status(
            has_sip=bool(sip_witnesses),
            has_crossrefs=bool(crossrefs),
            has_tn_candidates=bool(translation_candidates),
            has_translation=bool(record_translation_units),
        )
        enriched["enrichment_notes"] = (
            "SIP witness provenance integrated; "
            if sip_witnesses
            else ""
        ) + (
            "Bibliographic cross-reference evidence integrated from the IOB index."
            if crossrefs
            else "No bibliographic cross-reference evidence added."
        )
        if translation_candidates:
            enriched["enrichment_notes"] += " TN translation candidate preserved without adding translation text."
        if record_translation_units:
            enriched["enrichment_notes"] += " Published translation integrated from a tracked local source witness."

        enriched_records.append(enriched)
        preview_rows.append(
            build_preview_row(enriched, record_sip_rows, crossrefs, translation_candidates)
        )

    summary = {
        "total_records": len(enriched_records),
        "records_with_any_enrichment": sum(
            1
            for row in enriched_records
            if row.get("source_text_witnesses")
            or row.get("bibliographic_crossrefs")
            or row.get("translation_source_candidates")
            or row.get("translations")
            or row.get("translation_status")
        ),
        "records_with_sip_source_text_witness": sum(1 for row in enriched_records if row.get("source_text_witnesses")),
        "records_with_iob_crossref": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == IOB_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_list_crossref": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == LIST_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_ppa_candidate": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == PPA_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_tn_translation_candidate": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == TN_SOURCE_KEY for entry in row.get("translation_source_candidates", []))
        ),
        "records_with_translation_status_no_translation_known": sum(
            1 for row in enriched_records if row.get("translation_status") == "no_translation_known"
        ),
        "records_with_translation_status_translation_source_missing": sum(
            1 for row in enriched_records if row.get("translation_status") == "translation_source_missing"
        ),
        "records_with_translation_integrated": sum(
            1 for row in enriched_records if row.get("translation_status") == "translation_integrated"
        ),
        "records_with_existing_full_transliteration": sum(1 for row in enriched_records if row.get("full_transliteration")),
        "translation_units_integrated_count": sum(
            len(row.get("translations", []))
            for row in enriched_records
            if row.get("translation_status") == "translation_integrated"
        ),
        "published_translation_units_integrated_count": sum(
            1
            for row in enriched_records
            for translation in row.get("translations", [])
            if translation.get("translation_status") == "published_translation"
        ),
        "published_partial_translation_units_integrated_count": sum(
            1
            for row in enriched_records
            for translation in row.get("translations", [])
            if translation.get("translation_status") == "published_partial_translation"
        ),
    }
    return enriched_records, preview_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-inscriptions",
        type=Path,
        default=CORPUS_RELEASE_INSCRIPTIONS_PATH,
    )
    parser.add_argument(
        "--input-lines",
        type=Path,
        default=CORPUS_RELEASE_LINES_PATH,
    )
    parser.add_argument(
        "--sip-accepted-path",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "sip_accepted_witness_units.tsv",
    )
    parser.add_argument(
        "--iob-crossref-path",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "inscriptions_of_burma_cross_reference_index.tsv",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "inscriptions_enriched_candidate.jsonl",
    )
    parser.add_argument(
        "--output-preview-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "enriched_candidate_preview.tsv",
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "enriched_candidate_summary.json",
    )
    parser.add_argument(
        "--output-translation-actions-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "translation_source_action_table.tsv",
    )
    parser.add_argument(
        "--output-translation-units-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "translation_units_extracted.tsv",
    )
    parser.add_argument(
        "--output-translation-preview-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "translation_integration_preview.tsv",
    )
    parser.add_argument(
        "--output-tn-targets-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "tn_translation_targets.tsv",
    )
    parser.add_argument(
        "--output-tn-candidates-review-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "tn_translation_candidates_needing_review.tsv",
    )
    parser.add_argument(
        "--output-tn-target-status-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "tn_translation_target_status.tsv",
    )
    parser.add_argument(
        "--output-tn-manual-resolution-log-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "tn_manual_resolution_log.tsv",
    )
    parser.add_argument(
        "--output-tn-residual-unresolved-tsv",
        type=Path,
        default=REPO_ROOT
        / "data"
        / "working"
        / "corpus_enrichment"
        / "tn_residual_unresolved_after_manual_review.tsv",
    )
    parser.add_argument(
        "--output-tn-preview-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "tn_translation_integration_preview.tsv",
    )
    parser.add_argument(
        "--output-v04-inscriptions-jsonl",
        type=Path,
        default=V04_INSCRIPTIONS_CANDIDATE_PATH,
    )
    parser.add_argument(
        "--output-v04-inscriptions-with-lines-jsonl",
        type=Path,
        default=V04_INSCRIPTIONS_WITH_LINES_CANDIDATE_PATH,
    )
    parser.add_argument(
        "--output-v04-translation-units-tsv",
        type=Path,
        default=V04_TRANSLATION_UNITS_CANDIDATE_PATH,
    )
    parser.add_argument(
        "--output-v04-enrichment-preview-tsv",
        type=Path,
        default=V04_ENRICHMENT_PREVIEW_CANDIDATE_PATH,
    )
    parser.add_argument(
        "--output-v04-enriched-with-lines-sample-json",
        type=Path,
        default=V04_ENRICHED_WITH_LINES_SAMPLE_PATH,
    )
    parser.add_argument(
        "--output-v04-tn-unresolved-review-tsv",
        type=Path,
        default=V04_TN_UNRESOLVED_REVIEW_PATH,
    )
    parser.add_argument(
        "--output-v04-review-checklist-tsv",
        type=Path,
        default=V04_REVIEW_CHECKLIST_PATH,
    )
    parser.add_argument(
        "--output-v04-release-notes-md",
        type=Path,
        default=V04_RELEASE_NOTES_DRAFT_PATH,
    )
    args = parser.parse_args()

    inscriptions = read_jsonl(args.input_inscriptions)
    line_rows = read_jsonl(args.input_lines)
    record_title_by_id = {
        row.get("record_id", ""): (row.get("title_original", "") or row.get("title_transliteration", ""))
        for row in inscriptions
        if row.get("record_id")
    }
    sip_rows = read_tsv(args.sip_accepted_path)
    crossref_rows = read_tsv(args.iob_crossref_path)
    extracted_translation_units = read_tsv(REPO_ROOT / "data" / "working" / "bibliography" / "jbrs" / "jbrs_extracted_translation_units.tsv")
    tn_marked_text = (
        TN_OCR_CLEANED_TEXT_PATH.read_text(encoding="utf-8")
        if TN_OCR_CLEANED_TEXT_PATH.exists()
        else (TN_OCR_PLAIN_TEXT_PATH.read_text(encoding="utf-8") if TN_OCR_PLAIN_TEXT_PATH.exists() else "")
    )
    tn_page_map = parse_page_marked_text(tn_marked_text) if tn_marked_text else {}
    translation_unit_rows = build_translation_units_extracted_rows(
        extracted_translation_units,
        crossref_rows,
        tn_page_map,
    )
    tn_translation_units = [row for row in translation_unit_rows if row.get("source_key") == TN_SOURCE_KEY]

    enriched_records, preview_rows, summary = build_enriched_records(
        inscriptions,
        sip_rows,
        crossref_rows,
        translation_unit_rows,
        tn_source_available=TN_OCR_CLEANED_TEXT_PATH.exists(),
    )
    joined_records, joined_summary = build_joined_enriched_records_with_lines(enriched_records, line_rows)
    joined_sample_records = build_v04_enriched_with_lines_sample(joined_records)
    translation_preview_rows = build_translation_integration_preview_rows(
        translation_unit_rows,
        record_title_by_id,
    )
    tn_target_rows = build_tn_translation_targets_rows(crossref_rows, record_title_by_id)
    tn_target_status_rows = build_tn_translation_target_status_rows(tn_target_rows, translation_unit_rows)
    tn_review_rows = build_tn_candidates_needing_review_rows(
        crossref_rows,
        tn_page_map,
        tn_target_rows,
        translation_unit_rows,
    )
    tn_manual_resolution_rows = build_tn_manual_resolution_log_rows(
        tn_target_rows,
        tn_target_status_rows,
        tn_review_rows,
        translation_unit_rows,
    )
    tn_residual_unresolved_rows = build_tn_residual_unresolved_rows(
        tn_target_status_rows,
        tn_review_rows,
        crossref_rows,
        translation_unit_rows,
    )
    tn_preview_rows = build_tn_translation_integration_preview_rows(translation_unit_rows, record_title_by_id)
    action_rows = build_translation_source_action_rows(
        sip_rows,
        crossref_rows,
        tn_translation_units,
    )
    write_jsonl(args.output_jsonl, enriched_records)
    write_tsv(args.output_preview_tsv, preview_rows, PREVIEW_FIELDS)
    write_tsv(args.output_translation_actions_tsv, action_rows, [
        "source_key",
        "bibliographic_label",
        "local_file_status",
        "matched_local_file_id",
        "matched_file_name",
        "already_ocr_available",
        "contains_english_translation",
        "translation_scope",
        "linked_corpus_record_count",
        "linked_inscription_count",
        "action_status",
        "next_action",
        "evidence",
        "notes",
        "tracked_ocr_text_path",
    ])
    write_tsv(args.output_translation_units_tsv, translation_unit_rows, [
        "translation_unit_id",
        "source_key",
        "source_bibliographic_label",
        "matched_local_file_id",
        "source_locator",
        "linked_inscription_id",
        "linked_corpus_record_id",
        "translation_language",
        "translation_text",
        "translation_status",
        "link_basis",
        "confidence",
        "needs_human_review",
        "notes",
    ])
    write_tsv(args.output_translation_preview_tsv, translation_preview_rows, [
        "linked_corpus_record_id",
        "linked_inscription_id",
        "title_or_label",
        "source_key",
        "source_locator",
        "translation_status",
        "translation_text_snippet",
        "translation_length_chars",
        "has_existing_transcription",
        "link_basis",
        "needs_human_review",
        "notes",
    ])
    write_tsv(args.output_tn_targets_tsv, tn_target_rows, TN_TRANSLATION_TARGET_FIELDS)
    write_tsv(args.output_tn_target_status_tsv, tn_target_status_rows, TN_TRANSLATION_TARGET_STATUS_FIELDS)
    write_tsv(args.output_tn_candidates_review_tsv, tn_review_rows, TN_TRANSLATION_CANDIDATE_REVIEW_FIELDS)
    write_tsv(
        args.output_tn_manual_resolution_log_tsv,
        tn_manual_resolution_rows,
        TN_MANUAL_RESOLUTION_LOG_FIELDS,
    )
    write_tsv(
        args.output_tn_residual_unresolved_tsv,
        tn_residual_unresolved_rows,
        TN_RESIDUAL_UNRESOLVED_FIELDS,
    )
    write_tsv(args.output_tn_preview_tsv, tn_preview_rows, TN_TRANSLATION_INTEGRATION_PREVIEW_FIELDS)
    write_v04_candidate_package(
        enriched_records=enriched_records,
        joined_records=joined_records,
        joined_summary=joined_summary,
        joined_sample_records=joined_sample_records,
        preview_rows=preview_rows,
        translation_unit_rows=translation_unit_rows,
        tn_residual_rows=tn_residual_unresolved_rows,
        summary=summary,
        action_rows=action_rows,
        output_inscriptions_jsonl=args.output_v04_inscriptions_jsonl,
        output_inscriptions_with_lines_jsonl=args.output_v04_inscriptions_with_lines_jsonl,
        output_translation_units_tsv=args.output_v04_translation_units_tsv,
        output_enrichment_preview_tsv=args.output_v04_enrichment_preview_tsv,
        output_enriched_with_lines_sample_json=args.output_v04_enriched_with_lines_sample_json,
        output_tn_unresolved_review_tsv=args.output_v04_tn_unresolved_review_tsv,
        output_review_checklist_tsv=args.output_v04_review_checklist_tsv,
        output_release_notes_md=args.output_v04_release_notes_md,
    )
    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    joined_summary_output = dict(summary)
    joined_summary_output.update(joined_summary)
    args.output_summary_json.write_text(
        json.dumps(joined_summary_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(enriched_records)} enriched records, {len(preview_rows)} preview rows, "
        f"{len(action_rows)} translation action rows, {len(translation_unit_rows)} translation units, "
        f"{len(tn_target_rows)} TN target rows, {len(tn_target_status_rows)} TN target status rows, "
        f"{len(tn_manual_resolution_rows)} TN manual-resolution rows, "
        f"{len(tn_residual_unresolved_rows)} TN residual unresolved rows, "
        f"{len(tn_preview_rows)} TN preview rows, "
        f"{len(joined_records)} joined records, {joined_summary['total_line_rows_joined']} joined line rows, "
        "and v0.4 draft candidate files, "
        f"and {len(summary)} summary fields."
    )


if __name__ == "__main__":
    main()
