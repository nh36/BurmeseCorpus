#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from corpus_common import ensure_parent, read_tsv, write_tsv
from jbrs_workflow_common import (
    INSCRIPTIONS_OF_BURMA_CROSS_REFERENCE_INDEX_PATH,
    JBRS_OCR_TEXT_INDEX_FIELDS,
    LOCAL_FILE_MANIFEST_PATH,
    LOCAL_SOURCE_OCR_TEXT_INDEX_PATH,
    LOCAL_SOURCE_WORKING_OCR_METADATA_ROOT,
    LOCAL_SOURCE_WORKING_OCR_TEXT_ROOT,
    MISSING_HIGH_VALUE_SOURCES_PATH,
    SIP_CROSS_REFERENCE_TARGET_FIELDS,
    SIP_CROSS_REFERENCE_TARGETS_PATH,
    SIP_EXTRACTED_UNITS_PATH,
    SIP_EXTRACTION_NOTES_PATH,
    SIP_LINKED_SAMPLE_REVIEW_PATH,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_CITATION_TARGET_ID = "corpus-citation-target-0371"
TARGET_SOURCE_KEY = "sipSelectionsPagan"
TARGET_LOCAL_FILE_ID = "luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3"
TARGET_FILE_NAME = "Luce 1928 inscriptions of Pagan.pdf"
LOCAL_OCR_TEXT_PATH = (
    REPO_ROOT / "data_local/ocr/sip_vertical_slice/article_text/luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3.txt"
)
LOCAL_OCR_METADATA_PATH = (
    REPO_ROOT / "data_local/ocr/sip_vertical_slice/manifest/luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3.json"
)
REPO_OCR_TEXT_PATH = LOCAL_SOURCE_WORKING_OCR_TEXT_ROOT / f"{TARGET_LOCAL_FILE_ID}.txt"
REPO_OCR_METADATA_PATH = LOCAL_SOURCE_WORKING_OCR_METADATA_ROOT / f"{TARGET_LOCAL_FILE_ID}.json"

SIP_EXTRACTED_UNIT_FIELDS = [
    "extracted_unit_id",
    "citation_target_id",
    "normalized_source_key",
    "matched_local_file_id",
    "source_page_or_locator",
    "source_entry_number",
    "detected_inscription_identifier",
    "detected_language",
    "unit_type",
    "ocr_text",
    "confidence",
    "linked_corpus_record_id",
    "linked_inscription_id",
    "link_basis",
    "needs_manual_review",
    "notes",
]
SIP_SAMPLE_REVIEW_FIELDS = SIP_EXTRACTED_UNIT_FIELDS + ["review_category"]


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def page_map_from_text(text: str) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    current_page = 0
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.fullmatch(r"\[\[page (\d+)\]\]", line.strip())
        if match:
            if current_page:
                pages[current_page] = current_lines
            current_page = int(match.group(1))
            current_lines = []
        else:
            current_lines.append(line.rstrip())
    if current_page:
        pages[current_page] = current_lines
    return pages


def merge_note_bits(*values: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in [item.strip() for item in value.split("|") if item.strip()]:
            if part not in seen:
                seen.add(part)
                parts.append(part)
    return " | ".join(parts)


def normalize_sip_ref(value: str) -> str:
    digits = re.findall(r"\d+", value)
    if not digits:
        return compact(value)
    if len(digits) == 1:
        return f"SIP {digits[0]}"
    return f"SIP {digits[0]}-{digits[1]}"


def sip_page_range(value: str) -> tuple[int, int] | None:
    digits = [int(token) for token in re.findall(r"\d+", value)]
    if not digits:
        return None
    if len(digits) == 1:
        return digits[0], digits[0]
    return digits[0], digits[1]


def ocr_pages_for_sip_pages(start_page: int, end_page: int) -> list[int]:
    # OCR page markers include 10 pages of front matter before SIP printed page 1.
    return list(range(start_page + 10, end_page + 11))


def build_cross_reference_targets() -> list[dict[str, str]]:
    rows = [
        row
        for row in read_tsv(INSCRIPTIONS_OF_BURMA_CROSS_REFERENCE_INDEX_PATH)
        if row.get("sip_ref", "").strip()
    ]
    targets: list[dict[str, str]] = []
    for row in rows:
        targets.append(
            {
                "sip_ref": normalize_sip_ref(row["sip_ref"]),
                "iob_plate": row["iob_plate"],
                "iob_plate_normalized": row["iob_plate_normalized"],
                "list_ref": row["list_ref"],
                "ppa_ref": row["ppa_ref"],
                "tn_ref": row["tn_ref"],
                "place_or_object_description": row["place_or_object_description"],
                "linked_inscription_id": row["linked_inscription_id"],
                "linked_corpus_record_id": row["linked_corpus_record_id"],
                "link_confidence": row["link_confidence"],
                "needs_manual_review": row["needs_manual_review"],
                "notes": row["notes"],
            }
        )
    return targets


def block_text_for_pages(page_map: dict[int, list[str]], start_page: int, end_page: int) -> str:
    lines: list[str] = []
    for printed_page, ocr_page in zip(range(start_page, end_page + 1), ocr_pages_for_sip_pages(start_page, end_page)):
        page_lines = [compact(line) for line in page_map.get(ocr_page, []) if compact(line)]
        if not page_lines:
            continue
        lines.append(f"[[SIP page {printed_page} / OCR page {ocr_page}]]")
        lines.extend(page_lines)
    return "\n".join(lines).strip()


def block_text_for_ocr_pages(page_map: dict[int, list[str]], start_page: int, end_page: int) -> str:
    lines: list[str] = []
    for ocr_page in range(start_page, end_page + 1):
        page_lines = [compact(line) for line in page_map.get(ocr_page, []) if compact(line)]
        if not page_lines:
            continue
        lines.append(f"[[OCR page {ocr_page}]]")
        lines.extend(page_lines)
    return "\n".join(lines).strip()


def build_preface_unit(page_map: dict[int, list[str]]) -> dict[str, str]:
    text = block_text_for_ocr_pages(page_map, 1, 10)
    return {
        "extracted_unit_id": "sip-preface-overview",
        "citation_target_id": TARGET_CITATION_TARGET_ID,
        "normalized_source_key": TARGET_SOURCE_KEY,
        "matched_local_file_id": TARGET_LOCAL_FILE_ID,
        "source_page_or_locator": "OCR pages 1-10",
        "source_entry_number": "Preface",
        "detected_inscription_identifier": "edition preface",
        "detected_language": "Burmese/English front matter",
        "unit_type": "commentary",
        "ocr_text": text,
        "confidence": "high",
        "linked_corpus_record_id": "",
        "linked_inscription_id": "",
        "link_basis": "",
        "needs_manual_review": "false",
        "notes": "Front matter explains editorial principles and the relationship to earlier inscription books.",
    }


def build_contents_unit(page_map: dict[int, list[str]]) -> dict[str, str]:
    text = block_text_for_ocr_pages(page_map, 8, 10)
    return {
        "extracted_unit_id": "sip-contents-overview",
        "citation_target_id": TARGET_CITATION_TARGET_ID,
        "normalized_source_key": TARGET_SOURCE_KEY,
        "matched_local_file_id": TARGET_LOCAL_FILE_ID,
        "source_page_or_locator": "OCR pages 8-10",
        "source_entry_number": "Contents",
        "detected_inscription_identifier": "table of contents / catalogue",
        "detected_language": "Burmese",
        "unit_type": "catalogue_entry",
        "ocr_text": text,
        "confidence": "medium",
        "linked_corpus_record_id": "",
        "linked_inscription_id": "",
        "link_basis": "",
        "needs_manual_review": "true",
        "notes": "Contents-style crosswalk page listing inscription titles and locations.",
    }


def build_sip_units(page_map: dict[int, list[str]], sip_targets: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, target in enumerate(sip_targets, start=1):
        page_range = sip_page_range(target["sip_ref"])
        if not page_range:
            text = ""
            confidence = "low"
            unit_type = "unclear"
            needs_manual_review = "true"
            note = "Could not parse a SIP page range from the IOB cross-reference target."
        else:
            start_page, end_page = page_range
            text = block_text_for_pages(page_map, start_page, end_page)
            confidence = "high" if target["linked_corpus_record_id"] and target["needs_manual_review"] == "false" else "medium"
            unit_type = "source_text"
            needs_manual_review = target["needs_manual_review"] if text else "true"
            note = (
                f"Extracted from SIP printed pages {start_page}-{end_page} using the OCR page offset observed from the scanned volume."
                if text
                else "No OCR text was recovered for the expected SIP pages."
            )
        identifier_bits = [
            target["list_ref"],
            target["iob_plate"],
            target["place_or_object_description"],
        ]
        rows.append(
            {
                "extracted_unit_id": f"sip-unit-{index:03d}",
                "citation_target_id": TARGET_CITATION_TARGET_ID,
                "normalized_source_key": TARGET_SOURCE_KEY,
                "matched_local_file_id": TARGET_LOCAL_FILE_ID,
                "source_page_or_locator": target["sip_ref"],
                "source_entry_number": target["sip_ref"],
                "detected_inscription_identifier": " | ".join(bit for bit in identifier_bits if bit),
                "detected_language": "Old Burmese/Burmese",
                "unit_type": unit_type,
                "ocr_text": text,
                "confidence": confidence,
                "linked_corpus_record_id": target["linked_corpus_record_id"],
                "linked_inscription_id": target["linked_inscription_id"],
                "link_basis": (
                    f"IOB cross-reference: {target['iob_plate']} -> {target['sip_ref']}."
                    if target["linked_corpus_record_id"]
                    else ""
                ),
                "needs_manual_review": needs_manual_review,
                "notes": merge_note_bits(target["notes"], note),
            }
        )
    return rows


def build_ocr_noise_unit(page_map: dict[int, list[str]]) -> dict[str, str]:
    lines = [compact(line) for line in page_map.get(195, []) if compact(line)]
    return {
        "extracted_unit_id": "sip-tail-noise",
        "citation_target_id": TARGET_CITATION_TARGET_ID,
        "normalized_source_key": TARGET_SOURCE_KEY,
        "matched_local_file_id": TARGET_LOCAL_FILE_ID,
        "source_page_or_locator": "OCR page 195",
        "source_entry_number": "Tail page sample",
        "detected_inscription_identifier": "",
        "detected_language": "Mixed/OCR-noisy",
        "unit_type": "unclear",
        "ocr_text": " ".join(lines[:12]),
        "confidence": "low",
        "linked_corpus_record_id": "",
        "linked_inscription_id": "",
        "link_basis": "",
        "needs_manual_review": "true",
        "notes": "Representative end-of-volume OCR noise / blank-page artifact kept for sample review.",
    }


def build_repo_safe_metadata(local_metadata: dict[str, object], text: str, manifest_row: dict[str, str]) -> dict[str, object]:
    return {
        "local_file_id": TARGET_LOCAL_FILE_ID,
        "citation_target_id": TARGET_CITATION_TARGET_ID,
        "normalized_source_key": TARGET_SOURCE_KEY,
        "file_name": manifest_row.get("file_name", ""),
        "path_stub": manifest_row.get("copied_path", ""),
        "ocr_engine": local_metadata.get("ocr_engine", "google_vision"),
        "ocr_date": local_metadata.get("ocr_date", ""),
        "pages_completed": local_metadata.get("page_count", 0),
        "language_scope_guess": "Burmese",
        "canonical_ocr_text_path": str(REPO_OCR_TEXT_PATH.relative_to(REPO_ROOT)),
        "canonical_metadata_path": str(REPO_OCR_METADATA_PATH.relative_to(REPO_ROOT)),
        "canonical_file_name": manifest_row.get("file_name", ""),
        "probable_article_title": "Selections from the Inscriptions of Pagan",
        "probable_author": "Pe Maung Tin; G. H. Luce",
        "year": "1928",
        "source_category": "book_or_portfolio_pdf",
        "source_role": "edition_witness",
        "contains_translation_marker": "false",
        "contains_inscription_level_translation": "false",
        "contains_source_text_marker": "true",
        "contains_extractable_source_text": "true",
        "contains_plate_index": "false",
        "contains_facsimile_plates": "false",
        "contains_text_marker": "true",
        "contains_inscription_marker": "true",
        "contains_burmese_marker": "true",
        "contains_pali_marker": "true" if re.search(r"\bပါဠိ\b|\bPali\b", text, re.IGNORECASE) else "false",
        "contains_mon_marker": "false",
        "contains_pyu_marker": "false",
        "checksum_or_file_fingerprint": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "notes": "Repo-safe OCR export for the confirmed SIP witness. The OCR shows Burmese front matter, contents/crosswalk pages, and edited inscription text pages, with no inscription-level English translation detected in this volume.",
    }


def build_repo_safe_index_row(metadata: dict[str, object], manifest_row: dict[str, str]) -> dict[str, str]:
    return {
        "local_file_id": TARGET_LOCAL_FILE_ID,
        "batch_id": "sip-ocr-0001",
        "file_name": manifest_row.get("file_name", ""),
        "old_file_name": manifest_row.get("file_name", ""),
        "canonical_file_name": manifest_row.get("file_name", ""),
        "probable_article_title": str(metadata["probable_article_title"]),
        "probable_author": str(metadata["probable_author"]),
        "year": str(metadata["year"]),
        "path_stub": manifest_row.get("copied_path", ""),
        "old_path_stub": manifest_row.get("copied_path", ""),
        "new_path_stub_or_repo_path": str(REPO_OCR_TEXT_PATH.relative_to(REPO_ROOT)),
        "ocr_text_path": str(REPO_OCR_TEXT_PATH.relative_to(REPO_ROOT)),
        "metadata_path": str(REPO_OCR_METADATA_PATH.relative_to(REPO_ROOT)),
        "pages_completed": str(metadata["pages_completed"]),
        "ocr_status": "completed",
        "language_scope_guess": str(metadata["language_scope_guess"]),
        "contains_translation_marker": str(metadata["contains_translation_marker"]),
        "contains_text_marker": str(metadata["contains_text_marker"]),
        "contains_inscription_marker": str(metadata["contains_inscription_marker"]),
        "contains_burmese_marker": str(metadata["contains_burmese_marker"]),
        "contains_pali_marker": str(metadata["contains_pali_marker"]),
        "contains_mon_marker": str(metadata["contains_mon_marker"]),
        "contains_pyu_marker": str(metadata["contains_pyu_marker"]),
        "notes": str(metadata["notes"]),
    }


def write_local_source_index(row: dict[str, str]) -> None:
    rows = read_tsv(LOCAL_SOURCE_OCR_TEXT_INDEX_PATH) if LOCAL_SOURCE_OCR_TEXT_INDEX_PATH.exists() else []
    rows_by_id = {item["local_file_id"]: item for item in rows if item.get("local_file_id")}
    rows_by_id[row["local_file_id"]] = row
    merged_rows = sorted(rows_by_id.values(), key=lambda item: item["local_file_id"])
    write_tsv(LOCAL_SOURCE_OCR_TEXT_INDEX_PATH, merged_rows, JBRS_OCR_TEXT_INDEX_FIELDS)


def write_notes() -> None:
    note = """# SIP extraction notes

- **Confirmed witness**: `luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3`
- **Bibliographic identity**: the OCRed title page confirms *Selections from the Inscriptions of Pagan*, by Pe Maung Tin and G. H. Luce, University of Rangoon Department of Oriental Studies Publication No. 1, 1928.
- **Contains edited Burmese / Old Burmese source text**: yes. The body pages contain edited Burmese inscription text arranged by numbered inscription entries.
- **Contains English translation**: no inscription-level English translation was identified in the OCRed volume.
- **Contains transliteration/transcription**: the book appears to present edited Burmese inscription text rather than a separate Roman transliteration layer.
- **Contains commentary**: yes. There is Burmese front matter/preface and brief editorial/contextual matter around the text and contents.
- **Locator system**: SIP page numbers are the useful extraction locator, and the IOB concordance links those SIP page references back to IOB plates plus List/PPA/TN references. The OCRed PDF includes about 10 prefatory pages before SIP printed page 1, so SIP printed page `N` maps approximately to OCR page `N + 10`.
- **Segmentation strategy**:
  1. Keep the title page, preface, and contents as commentary/catalogue context.
  2. Use the IOB-derived `sip_cross_reference_targets.tsv` rows as the extraction spine.
  3. Extract one SIP unit per cited SIP page range, linking only the rows that already have high-confidence corpus links through the IOB concordance.
  4. Leave uncertain SIP references and noisy/end-matter artifacts marked for manual review.
"""
    SIP_EXTRACTION_NOTES_PATH.write_text(note, encoding="utf-8")


def write_missing_high_value_sources_note() -> None:
    note = """# Missing high-value sources

- **TN / Tun Nyein, *Inscriptions of Pagan, Pinya, and Ava. Translation, with Notes* (1899)** remains a high-value translation witness but was not found locally. The targeted local hunt only surfaced false-friend near-title files.
- **PPA / *Inscriptions of Pagan, Pinya, and Ava* (1892)** remains a high-value source-text witness but was not found locally after rejecting the earlier annual-report stand-in and checking the near-title local files.
- These two witnesses should be acquired manually if possible before any new OCR work is planned around them.
"""
    MISSING_HIGH_VALUE_SOURCES_PATH.write_text(note, encoding="utf-8")


def build_sample_review(units: list[dict[str, str]]) -> list[dict[str, str]]:
    linked = [row for row in units if row["linked_corpus_record_id"]][:10]
    uncertain = [row for row in units if row["needs_manual_review"] == "true" and row["unit_type"] == "source_text"][:5]
    commentary = [row for row in units if row["unit_type"] in {"commentary", "catalogue_entry"}][:3]
    noisy = [row for row in units if row["unit_type"] == "unclear"][:2]
    selected: list[dict[str, str]] = []
    for category, rows in (
        ("linked_source_text", linked),
        ("uncertain_link", uncertain),
        ("front_matter_context", commentary),
        ("ocr_failure_or_noise", noisy),
    ):
        for row in rows:
            selected.append({**row, "review_category": category})
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in selected:
        if row["extracted_unit_id"] in seen:
            continue
        seen.add(row["extracted_unit_id"])
        deduped.append(row)
        if len(deduped) == 20:
            break
    return deduped


def main() -> None:
    text = LOCAL_OCR_TEXT_PATH.read_text(encoding="utf-8")
    local_metadata = json.loads(LOCAL_OCR_METADATA_PATH.read_text(encoding="utf-8"))
    manifest_row = next(
        row
        for row in read_tsv(LOCAL_FILE_MANIFEST_PATH)
        if row.get("canonical_local_file_id") == TARGET_LOCAL_FILE_ID
    )

    ensure_parent(REPO_OCR_TEXT_PATH)
    REPO_OCR_TEXT_PATH.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

    repo_metadata = build_repo_safe_metadata(local_metadata, text, manifest_row)
    ensure_parent(REPO_OCR_METADATA_PATH)
    REPO_OCR_METADATA_PATH.write_text(json.dumps(repo_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_local_source_index(build_repo_safe_index_row(repo_metadata, manifest_row))

    sip_targets = build_cross_reference_targets()
    write_tsv(SIP_CROSS_REFERENCE_TARGETS_PATH, sip_targets, SIP_CROSS_REFERENCE_TARGET_FIELDS)

    page_map = page_map_from_text(text)
    units = [build_preface_unit(page_map), build_contents_unit(page_map)]
    units.extend(build_sip_units(page_map, sip_targets))
    units.append(build_ocr_noise_unit(page_map))
    write_tsv(SIP_EXTRACTED_UNITS_PATH, units, SIP_EXTRACTED_UNIT_FIELDS)
    write_tsv(SIP_LINKED_SAMPLE_REVIEW_PATH, build_sample_review(units), SIP_SAMPLE_REVIEW_FIELDS)
    write_notes()
    write_missing_high_value_sources_note()


if __name__ == "__main__":
    main()
