#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
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
    SIP_CORPUS_LINK_REVIEW_FIELDS,
    SIP_CORPUS_LINK_REVIEW_PATH,
    SIP_CROSS_REFERENCE_TARGET_FIELDS,
    SIP_CROSS_REFERENCE_TARGETS_PATH,
    SIP_EXTRACTED_UNITS_PATH,
    SIP_EXTRACTION_NOTES_PATH,
    SIP_LINKED_SAMPLE_REVIEW_PATH,
    SIP_TEXT_COMPARISON_STATUSES,
    SIP_WITNESS_OCR_QUALITIES,
    SIP_WITNESS_REVIEW_STATUSES,
    SIP_WITNESS_TEXT_COMPARISON_FIELDS,
    SIP_WITNESS_TEXT_COMPARISON_PATH,
    SIP_WITNESS_UNIT_FIELDS,
    SIP_WITNESS_UNITS_PATH,
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
CORPUS_INSCRIPTIONS_PATH = REPO_ROOT / "data/release/corpus_release_v0_3/inscriptions.jsonl"
CORPUS_LINES_PATH = REPO_ROOT / "data/release/corpus_release_v0_3/lines.jsonl"

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


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def page_range_label(start_page: int, end_page: int) -> str:
    return f"{start_page}" if start_page == end_page else f"{start_page}-{end_page}"


def clean_witness_text(raw_text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in raw_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("[["):
            continue
        line = compact(raw_line)
        line = re.sub(r"\*{2,}|\.(?:\s*\.){2,}", "[unclear]", line)
        line = re.sub(r"\[\s*\]", "[unclear]", line)
        line = re.sub(r"\[unclear\](?:\s*\[unclear\])+", "[unclear]", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def normalize_for_compare(text: str) -> str:
    cleaned = re.sub(r"\[\[.*?\]\]", " ", text)
    cleaned = re.sub(r"(?m)^\(?[0-9၀-၉]+[\)\].။\-\s]*", "", cleaned)
    cleaned = cleaned.replace("[unclear]", "")
    cleaned = re.sub(r"[\s\.,;:()\\/\-\[\]{}*]+", "", cleaned)
    return cleaned


def ngrams(text: str, size: int = 5) -> set[str]:
    if len(text) < size:
        return set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def ocr_quality_for_text(raw_text: str) -> str:
    cleaned = clean_witness_text(raw_text)
    if len(cleaned) < 80:
        return "unusable"
    unclear_count = cleaned.count("[unclear]")
    latin_count = len(re.findall(r"[A-Za-z]", cleaned))
    burmese_count = len(re.findall(r"[က-႟]", cleaned))
    latin_ratio = latin_count / max(len(cleaned), 1)
    if unclear_count >= 6 or (burmese_count and latin_ratio > 0.10):
        return "noisy_but_salvageable"
    if unclear_count >= 1 or latin_ratio > 0.03:
        return "usable_with_minor_noise"
    return "good"


def comparison_status_for_texts(cleaned_witness_text: str, corpus_text: str, ocr_quality: str) -> str:
    if not corpus_text.strip():
        return "corpus_text_absent_sip_supplies_candidate"
    witness_norm = normalize_for_compare(cleaned_witness_text)
    corpus_norm = normalize_for_compare(corpus_text)
    if len(witness_norm) < 40 or len(corpus_norm) < 40:
        return "ocr_too_noisy" if ocr_quality == "noisy_but_salvageable" else "corpus_text_not_comparable"
    witness_grams = ngrams(witness_norm)
    corpus_grams = ngrams(corpus_norm)
    if not witness_grams or not corpus_grams:
        return "corpus_text_not_comparable"
    overlap = len(witness_grams & corpus_grams) / max(1, min(len(witness_grams), len(corpus_grams)))
    if overlap >= 0.08:
        return "corpus_text_present_sip_confirms"
    if ocr_quality == "noisy_but_salvageable":
        return "ocr_too_noisy"
    return "corpus_text_present_sip_differs"


def comparison_note(status: str) -> str:
    mapping = {
        "corpus_text_present_sip_confirms": "Corpus text is present and the SIP witness broadly confirms the same inscription text.",
        "corpus_text_present_sip_differs": "Corpus text is present, but the SIP witness diverges or preserves materially different readings/snippets.",
        "corpus_text_absent_sip_supplies_candidate": "No structured corpus text is currently linked, so SIP supplies a candidate witness text.",
        "corpus_text_not_comparable": "The linked corpus text could not be compared safely against the SIP witness snippet.",
        "ocr_too_noisy": "The SIP OCR remains too noisy for a stable comparison.",
    }
    return mapping[status]


def snippet(text: str, limit: int = 220) -> str:
    return compact(text.replace("\n", " "))[:limit]


def load_corpus_context() -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    inscription_by_record_id: dict[str, dict[str, object]] = {}
    for row in read_jsonl(CORPUS_INSCRIPTIONS_PATH):
        inscription_by_record_id[str(row["record_id"])] = row
    line_rows_by_record_id: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in read_jsonl(CORPUS_LINES_PATH):
        line_rows_by_record_id[str(row["record_id"])].append(
            (int(row.get("line_number_arabic") or 0), str(row.get("text_original", "")))
        )
    corpus_text_by_record_id: dict[str, str] = {}
    for record_id, line_rows in line_rows_by_record_id.items():
        ordered = [text for _, text in sorted(line_rows, key=lambda item: (item[0], item[1])) if text.strip()]
        corpus_text_by_record_id[record_id] = "\n".join(ordered).strip()
    return inscription_by_record_id, corpus_text_by_record_id


def build_witness_units(
    sip_units: list[dict[str, str]],
) -> tuple[list[dict[str, str]], int]:
    witness_rows: list[dict[str, str]] = []
    rejected_noise_count = 0
    for index, row in enumerate(sip_units, start=1):
        raw_text = row["ocr_text"].strip()
        cleaned_text = clean_witness_text(raw_text)
        ocr_quality = ocr_quality_for_text(raw_text)
        if ocr_quality == "unusable":
            rejected_noise_count += 1
            continue
        if row["linked_corpus_record_id"]:
            review_status = "accepted_witness_unit" if ocr_quality == "good" else "needs_text_cleanup"
            link_confidence = "high"
        else:
            review_status = "needs_link_review"
            link_confidence = "medium"
        page_range = sip_page_range(row["source_page_or_locator"])
        if page_range:
            start_page, end_page = page_range
            printed_page_range = page_range_label(start_page, end_page)
            ocr_page_range = page_range_label(start_page + 10, end_page + 10)
        else:
            printed_page_range = row["source_page_or_locator"]
            ocr_page_range = ""
        witness_rows.append(
            {
                "witness_unit_id": f"sip-witness-{index:03d}",
                "source_key": TARGET_SOURCE_KEY,
                "citation_target_id": TARGET_CITATION_TARGET_ID,
                "matched_local_file_id": TARGET_LOCAL_FILE_ID,
                "printed_page_range": printed_page_range,
                "ocr_page_range": ocr_page_range,
                "sip_ref": row["source_page_or_locator"],
                "iob_plate": next((part.strip() for part in row["detected_inscription_identifier"].split("|") if part.strip().startswith("Plate ")), ""),
                "list_ref": next((part.strip() for part in row["detected_inscription_identifier"].split("|") if part.strip().startswith("List ")), ""),
                "ppa_ref": "",
                "tn_ref": "",
                "linked_inscription_id": row["linked_inscription_id"],
                "linked_corpus_record_id": row["linked_corpus_record_id"],
                "unit_type": row["unit_type"],
                "language": row["detected_language"],
                "raw_ocr_text": raw_text,
                "cleaned_witness_text": cleaned_text,
                "witness_text": cleaned_text,
                "ocr_quality": ocr_quality,
                "link_confidence": link_confidence,
                "link_basis": row["link_basis"],
                "review_status": review_status,
                "notes": row["notes"],
            }
        )
    return witness_rows, rejected_noise_count


def enrich_witness_units_with_cross_refs(
    witness_rows: list[dict[str, str]],
    sip_targets: list[dict[str, str]],
) -> list[dict[str, str]]:
    target_by_ref = {row["sip_ref"]: row for row in sip_targets}
    enriched: list[dict[str, str]] = []
    for row in witness_rows:
        target = target_by_ref.get(row["sip_ref"], {})
        enriched.append(
            {
                **row,
                "iob_plate": target.get("iob_plate", row["iob_plate"]),
                "list_ref": target.get("list_ref", row["list_ref"]),
                "ppa_ref": target.get("ppa_ref", ""),
                "tn_ref": target.get("tn_ref", ""),
            }
        )
    return enriched


def build_link_review_rows(
    witness_rows: list[dict[str, str]],
    inscription_by_record_id: dict[str, dict[str, object]],
    corpus_text_by_record_id: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in witness_rows:
        record_id = row["linked_corpus_record_id"]
        corpus_record = inscription_by_record_id.get(record_id, {})
        corpus_text = corpus_text_by_record_id.get(record_id, "")
        comparison_status = comparison_status_for_texts(row["cleaned_witness_text"], corpus_text, row["ocr_quality"])
        if not record_id:
            review_decision = "needs_human_review"
        elif row["review_status"] == "accepted_witness_unit":
            review_decision = "accept_link"
        else:
            review_decision = "accept_link_but_text_needs_cleanup"
        rows.append(
            {
                "witness_unit_id": row["witness_unit_id"],
                "sip_ref": row["sip_ref"],
                "iob_plate": row["iob_plate"],
                "linked_inscription_id": row["linked_inscription_id"],
                "linked_corpus_record_id": record_id,
                "existing_corpus_has_text": "true" if corpus_text else "false",
                "existing_corpus_language": str(corpus_record.get("language_original") or ""),
                "witness_text_snippet": snippet(row["cleaned_witness_text"]),
                "corpus_text_snippet": snippet(corpus_text),
                "link_confidence": row["link_confidence"],
                "link_basis": row["link_basis"],
                "review_decision": review_decision,
                "notes": comparison_note(comparison_status),
            }
        )
    return rows


def build_text_comparison_rows(
    witness_rows: list[dict[str, str]],
    corpus_text_by_record_id: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in witness_rows:
        if row["link_confidence"] != "high" or not row["linked_corpus_record_id"]:
            continue
        corpus_text = corpus_text_by_record_id.get(row["linked_corpus_record_id"], "")
        status = comparison_status_for_texts(row["cleaned_witness_text"], corpus_text, row["ocr_quality"])
        rows.append(
            {
                "linked_corpus_record_id": row["linked_corpus_record_id"],
                "linked_inscription_id": row["linked_inscription_id"],
                "sip_ref": row["sip_ref"],
                "iob_plate": row["iob_plate"],
                "sip_witness_text_snippet": snippet(row["cleaned_witness_text"]),
                "corpus_text_snippet": snippet(corpus_text),
                "comparison_status": status,
                "observed_difference": comparison_note(status),
                "needs_manual_review": "true" if status in {"corpus_text_present_sip_differs", "ocr_too_noisy", "corpus_text_not_comparable"} else "false",
                "notes": row["link_basis"],
            }
        )
    return rows


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


def build_sample_review(
    units: list[dict[str, str]],
    witness_rows: list[dict[str, str]],
    rejected_noise_count: int,
) -> list[dict[str, str]]:
    def sample_row_from_witness(row: dict[str, str]) -> dict[str, str]:
        return {
            "extracted_unit_id": row["witness_unit_id"],
            "citation_target_id": row["citation_target_id"],
            "normalized_source_key": row["source_key"],
            "matched_local_file_id": row["matched_local_file_id"],
            "source_page_or_locator": row["sip_ref"],
            "source_entry_number": row["sip_ref"],
            "detected_inscription_identifier": " | ".join(
                bit for bit in [row.get("list_ref", ""), row.get("iob_plate", "")] if bit
            ),
            "detected_language": row["language"],
            "unit_type": row["unit_type"],
            "ocr_text": row["witness_text"],
            "confidence": row["link_confidence"],
            "linked_corpus_record_id": row["linked_corpus_record_id"],
            "linked_inscription_id": row["linked_inscription_id"],
            "link_basis": row["link_basis"],
            "needs_manual_review": "true" if row["review_status"] != "accepted_witness_unit" else "false",
            "notes": row["notes"],
        }

    linked = [sample_row_from_witness(row) for row in witness_rows if row["linked_corpus_record_id"]][:10]
    uncertain = [sample_row_from_witness(row) for row in witness_rows if row["review_status"] == "needs_link_review"][:5]
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
    inscription_by_record_id, corpus_text_by_record_id = load_corpus_context()
    witness_rows, rejected_noise_count = build_witness_units([row for row in units if row["unit_type"] == "source_text"])
    witness_rows = enrich_witness_units_with_cross_refs(witness_rows, sip_targets)
    link_review_rows = build_link_review_rows(witness_rows, inscription_by_record_id, corpus_text_by_record_id)
    comparison_rows = build_text_comparison_rows(witness_rows, corpus_text_by_record_id)
    write_tsv(SIP_WITNESS_UNITS_PATH, witness_rows, SIP_WITNESS_UNIT_FIELDS)
    write_tsv(SIP_CORPUS_LINK_REVIEW_PATH, link_review_rows, SIP_CORPUS_LINK_REVIEW_FIELDS)
    write_tsv(SIP_WITNESS_TEXT_COMPARISON_PATH, comparison_rows, SIP_WITNESS_TEXT_COMPARISON_FIELDS)
    write_tsv(
        SIP_LINKED_SAMPLE_REVIEW_PATH,
        build_sample_review(units, witness_rows, rejected_noise_count),
        SIP_SAMPLE_REVIEW_FIELDS + ["review_category"] if "review_category" not in SIP_SAMPLE_REVIEW_FIELDS else SIP_SAMPLE_REVIEW_FIELDS,
    )
    write_notes()
    write_missing_high_value_sources_note()


if __name__ == "__main__":
    main()
