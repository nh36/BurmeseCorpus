#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from corpus_common import ensure_parent, read_tsv, write_tsv
from jbrs_workflow_common import (
    CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH,
    JBRS_OCR_TEXT_INDEX_FIELDS,
    LOCAL_FILE_MANIFEST_PATH,
    LOCAL_SOURCE_OCR_TEXT_INDEX_PATH,
    LOCAL_SOURCE_WORKING_OCR_METADATA_ROOT,
    LOCAL_SOURCE_WORKING_OCR_TEXT_ROOT,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGET_CITATION_TARGET_ID = "corpus-citation-target-0363"
TARGET_LOCAL_FILE_ID = "inscriptions_of_burma-b7c07d9f6d02"
TARGET_SOURCE_KEY = "lucePeMaungTinInscriptionsOfBurma"
LOCAL_OCR_TEXT_PATH = REPO_ROOT / "data_local/ocr/iob_vertical_slice/article_text/inscriptions_of_burma-b7c07d9f6d02.txt"
LOCAL_OCR_METADATA_PATH = REPO_ROOT / "data_local/ocr/iob_vertical_slice/manifest/inscriptions_of_burma-b7c07d9f6d02.json"
REPO_OCR_TEXT_PATH = LOCAL_SOURCE_WORKING_OCR_TEXT_ROOT / f"{TARGET_LOCAL_FILE_ID}.txt"
REPO_OCR_METADATA_PATH = LOCAL_SOURCE_WORKING_OCR_METADATA_ROOT / f"{TARGET_LOCAL_FILE_ID}.json"
EXTRACTION_NOTES_PATH = REPO_ROOT / "data/working/bibliography/inscriptions_of_burma_extraction_notes.md"
EXTRACTED_UNITS_PATH = REPO_ROOT / "data/working/bibliography/inscriptions_of_burma_extracted_units.tsv"
SAMPLE_REVIEW_PATH = REPO_ROOT / "data/working/bibliography/inscriptions_of_burma_linked_sample_review.tsv"

EXTRACTED_UNIT_FIELDS = [
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

SAMPLE_REVIEW_FIELDS = EXTRACTED_UNIT_FIELDS + ["review_category"]


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


def roman(number: int) -> str:
    values = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    result: list[str] = []
    remainder = number
    for value, glyph in values:
        while remainder >= value:
            result.append(glyph)
            remainder -= value
    return "".join(result)


def normalize_plate_key(label: str) -> str:
    cleaned = label.replace("Plate", "").replace(".", "").replace(",", " ").replace("&", " ")
    cleaned = cleaned.replace("(", " ").replace(")", " ")
    cleaned = cleaned.replace("l", "I")
    tokens = [token for token in re.split(r"\s+", cleaned.strip()) if token]
    if not tokens:
        return ""
    head_token = tokens[0]
    if head_token.isdigit():
        roman_token = roman(int(head_token))
    else:
        roman_token = re.sub(r"[^IVXLCDM]", "", head_token.upper())
    suffix = ""
    if len(tokens) > 1 and tokens[1].casefold() in {"a", "b"}:
        suffix = tokens[1].casefold()
    return roman_token + suffix


def text_from_lines(lines: list[str]) -> str:
    filtered = [
        compact(line)
        for line in lines
        if compact(line)
        and compact(line) not in {"INDEX OF PLATES", "[**]", "[1]", "[10]", "[13]"}
        and not re.fullmatch(r"\[\d+\]", compact(line))
    ]
    return "\n".join(filtered)


def parse_english_index_entries(pages: dict[int, list[str]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current_page = 0
    current_lines: list[str] = []
    for page_number in range(6, 11):
        for line in pages.get(page_number, []):
            normalized = compact(line)
            if not normalized or normalized in {"INDEX OF PLATES", "[**]", "[1]", "[10]", "[13]"}:
                continue
            if normalized.startswith("Plate "):
                if current_lines:
                    entries.append(
                        {
                            "page_number": str(current_page),
                            "entry_text": text_from_lines(current_lines),
                        }
                    )
                current_page = page_number
                current_lines = [line]
            elif current_lines:
                current_lines.append(line)
    if current_lines:
        entries.append(
            {
                "page_number": str(current_page),
                "entry_text": text_from_lines(current_lines),
            }
        )
    for entry in entries:
        match = re.match(r"^Plate\s+([A-Za-z0-9IVXLCDM]+(?:\s*[ab])?)", entry["entry_text"])
        if match:
            raw_label = match.group(1)
            plate_key = normalize_plate_key(raw_label)
            if plate_key.endswith(("a", "b")):
                source_entry_number = f"Plate {plate_key[:-1]} {plate_key[-1]}"
            else:
                source_entry_number = f"Plate {plate_key}"
        else:
            plate_key = ""
            source_entry_number = ""
        entry["source_entry_number"] = source_entry_number
        entry["plate_key"] = plate_key
        list_match = re.search(r"\bList\s+([^.,;]+)", entry["entry_text"])
        refs = []
        for label in ("SIP", "PPA", "TN", "UBI", "UB I", "UB II", "A", "B II", "JBRS"):
            ref_match = re.search(rf"\b{re.escape(label)}\s+([^.,;]+)", entry["entry_text"])
            if ref_match:
                refs.append(f"{label} {compact(ref_match.group(1))}")
        parts = []
        if list_match:
            parts.append(f"List {compact(list_match.group(1))}")
        parts.extend(refs)
        entry["detected_inscription_identifier"] = "; ".join(parts)
    return entries


def parse_abbreviation_entries(page_lines: list[str]) -> list[dict[str, str]]:
    start_tokens = ("A-", "B II-", "JBRS", "List ", "PPA ", "SIP-", "TN-", "UB 1-", "UB II-")
    entries: list[list[str]] = []
    current: list[str] = []
    for line in page_lines:
        normalized = compact(line)
        if not normalized or normalized == "ABBREVIATIONS":
            continue
        if normalized.startswith("သင်္ကေတ"):
            break
        if normalized.startswith(start_tokens):
            if current:
                entries.append(current)
            current = [normalized]
        elif current:
            current.append(normalized)
    if current:
        entries.append(current)
    rows: list[dict[str, str]] = []
    for index, lines in enumerate(entries, start=1):
        text = " ".join(lines)
        label = text.split(" ", 1)[0].rstrip(".")
        rows.append(
            {
                "extracted_unit_id": f"iob-abbrev-{index:02d}",
                "citation_target_id": TARGET_CITATION_TARGET_ID,
                "normalized_source_key": TARGET_SOURCE_KEY,
                "matched_local_file_id": TARGET_LOCAL_FILE_ID,
                "source_page_or_locator": "page 5",
                "source_entry_number": f"Abbreviation {label}",
                "detected_inscription_identifier": label,
                "detected_language": "English",
                "unit_type": "commentary",
                "ocr_text": text,
                "confidence": "high",
                "linked_corpus_record_id": "",
                "linked_inscription_id": "",
                "link_basis": "",
                "needs_manual_review": "false",
                "notes": "Abbreviation-definition witness from the OCRed front matter.",
            }
        )
    return rows


def build_preface_unit(pages: dict[int, list[str]]) -> dict[str, str]:
    page_two = [compact(line) for line in pages.get(2, []) if compact(line)]
    page_three = [compact(line) for line in pages.get(3, []) if compact(line)]
    snippet = " ".join(
        page_two[1:9]
        + [
            line
            for line in page_three
            if "published books containing the text of the inscription" in line
            or "brief identification of the inscription in Burmese" in line
        ]
    )
    return {
        "extracted_unit_id": "iob-preface-overview",
        "citation_target_id": TARGET_CITATION_TARGET_ID,
        "normalized_source_key": TARGET_SOURCE_KEY,
        "matched_local_file_id": TARGET_LOCAL_FILE_ID,
        "source_page_or_locator": "pages 2-3",
        "source_entry_number": "Preface",
        "detected_inscription_identifier": "facsimile preface statement",
        "detected_language": "English",
        "unit_type": "commentary",
        "ocr_text": snippet,
        "confidence": "high",
        "linked_corpus_record_id": "",
        "linked_inscription_id": "",
        "link_basis": "",
        "needs_manual_review": "false",
        "notes": "Front matter states that the volume publishes facsimiles and points readers to books containing text or English translation.",
    }


def build_unclear_plate_units(pages: dict[int, list[str]]) -> list[dict[str, str]]:
    sample_pages = [19, 24, 63, 106, 124]
    rows: list[dict[str, str]] = []
    for index, page_number in enumerate(sample_pages, start=1):
        lines = [compact(line) for line in pages.get(page_number, []) if compact(line)]
        excerpt = " ".join(lines[:8])[:700]
        rows.append(
            {
                "extracted_unit_id": f"iob-plate-page-{page_number:03d}",
                "citation_target_id": TARGET_CITATION_TARGET_ID,
                "normalized_source_key": TARGET_SOURCE_KEY,
                "matched_local_file_id": TARGET_LOCAL_FILE_ID,
                "source_page_or_locator": f"page {page_number}",
                "source_entry_number": lines[0] if lines else f"page {page_number}",
                "detected_inscription_identifier": "",
                "detected_language": "Mixed/OCR-noisy",
                "unit_type": "plate_or_rubbing_caption",
                "ocr_text": excerpt,
                "confidence": "low",
                "linked_corpus_record_id": "",
                "linked_inscription_id": "",
                "link_basis": "",
                "needs_manual_review": "true",
                "notes": "Actual plate page OCR is too noisy for safe inscription-level extraction; keep as a representative low-confidence facsimile witness.",
            }
        )
    return rows


def load_unique_simple_plate_links() -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in read_tsv(CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH)
        if row.get("citation_target_id") == TARGET_CITATION_TARGET_ID
    ]
    simple_by_key: dict[str, dict[str, object]] = defaultdict(lambda: {"records": set(), "citations": []})
    pattern = re.compile(r"^Pl\.\s*I\s+([0-9]+)([ab])?$", re.IGNORECASE)
    for row in rows:
        match = pattern.match(row.get("citation_raw", ""))
        if not match:
            continue
        plate_key = roman(int(match.group(1))) + (match.group(2) or "").lower()
        payload = simple_by_key[plate_key]
        payload["records"].add((row["corpus_record_id"], row["inscription_id"]))
        payload["citations"].append(row["citation_raw"])
    resolved: dict[str, dict[str, str]] = {}
    for plate_key, payload in simple_by_key.items():
        records = payload["records"]
        if len(records) != 1:
            continue
        corpus_record_id, inscription_id = next(iter(records))
        resolved[plate_key] = {
            "linked_corpus_record_id": corpus_record_id,
            "linked_inscription_id": inscription_id,
            "citation_raws": ", ".join(sorted(set(payload["citations"]))),
        }
    return resolved


def build_index_units(entries: list[dict[str, str]], link_rows: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, entry in enumerate(entries, start=1):
        link = link_rows.get(entry["plate_key"], {})
        is_linked = bool(link)
        note = "English index-of-plates entry extracted from the OCRed volume."
        if entry["plate_key"] == "LXXVa":
            note = "Simple plate locator is ambiguous across two corpus records; keep this entry unlinked for review."
        elif entry["plate_key"] == "LXXXIV":
            note = "Simple plate locator is ambiguous across multiple corpus records; keep this entry unlinked for review."
        elif is_linked:
            note = f"Linked through exact corpus plate citation(s): {link['citation_raws']}."
        rows.append(
            {
                "extracted_unit_id": f"iob-index-{index:03d}",
                "citation_target_id": TARGET_CITATION_TARGET_ID,
                "normalized_source_key": TARGET_SOURCE_KEY,
                "matched_local_file_id": TARGET_LOCAL_FILE_ID,
                "source_page_or_locator": f"page {entry['page_number']}",
                "source_entry_number": entry["source_entry_number"],
                "detected_inscription_identifier": entry["detected_inscription_identifier"],
                "detected_language": "English",
                "unit_type": "catalogue_entry",
                "ocr_text": entry["entry_text"],
                "confidence": "high" if is_linked else "medium",
                "linked_corpus_record_id": link.get("linked_corpus_record_id", ""),
                "linked_inscription_id": link.get("linked_inscription_id", ""),
                "link_basis": (
                    f"Exact structured corpus plate citation resolved to OCRed {entry['source_entry_number']}."
                    if is_linked
                    else ""
                ),
                "needs_manual_review": "false" if is_linked else "true",
                "notes": note,
            }
        )
    return rows


def build_sample_review(units: list[dict[str, str]]) -> list[dict[str, str]]:
    linked = [row for row in units if row["linked_corpus_record_id"]][:10]
    ambiguous = [
        row
        for row in units
        if row["source_entry_number"] in {"Plate LXXV a", "Plate LXXXIV"}
        or "ambiguous" in row["notes"]
    ][:5]
    low_confidence = [row for row in units if row["confidence"] == "low"][:5]
    commentary = [
        row
        for row in units
        if row["extracted_unit_id"] == "iob-preface-overview" or row["extracted_unit_id"].startswith("iob-abbrev-")
    ][:5]
    selected: list[dict[str, str]] = []
    for category, rows in (
        ("linked_catalogue_entry", linked),
        ("ambiguous_index_entry", ambiguous),
        ("ocr_failure_or_plate_noise", low_confidence),
        ("front_matter_context", commentary),
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
        "language_scope_guess": "Mixed Burmese/Pali",
        "canonical_ocr_text_path": str(REPO_OCR_TEXT_PATH.relative_to(REPO_ROOT)),
        "canonical_metadata_path": str(REPO_OCR_METADATA_PATH.relative_to(REPO_ROOT)),
        "canonical_file_name": manifest_row.get("file_name", ""),
        "probable_article_title": "Inscriptions of Burma",
        "probable_author": "G. H. Luce; Pe Maung Tin",
        "year": "",
        "source_category": "book_or_portfolio_pdf",
        "contains_translation_marker": "true" if re.search(r"\btranslation\b", text, re.IGNORECASE) else "false",
        "contains_text_marker": "true" if re.search(r"\btext\b", text, re.IGNORECASE) else "false",
        "contains_inscription_marker": "true" if re.search(r"\binscriptions?\b", text, re.IGNORECASE) else "false",
        "contains_burmese_marker": "true" if re.search(r"\bBurmese\b|[က-႟]", text) else "false",
        "contains_pali_marker": "true" if re.search(r"\bPali\b", text, re.IGNORECASE) else "false",
        "contains_mon_marker": "true" if re.search(r"\bMon\b", text, re.IGNORECASE) else "false",
        "contains_pyu_marker": "true" if re.search(r"\bPyu\b", text, re.IGNORECASE) else "false",
        "checksum_or_file_fingerprint": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "notes": "Repo-safe OCR export for the reviewed Inscriptions of Burma source. The OCR shows facsimile plates plus bilingual front matter and English/Burmese plate indexes; no inscription-level English translations were identified in this volume.",
    }


def build_repo_safe_index_row(metadata: dict[str, object], manifest_row: dict[str, str]) -> dict[str, str]:
    return {
        "local_file_id": TARGET_LOCAL_FILE_ID,
        "batch_id": "iob-ocr-0001",
        "file_name": manifest_row.get("file_name", ""),
        "old_file_name": manifest_row.get("file_name", ""),
        "canonical_file_name": manifest_row.get("file_name", ""),
        "probable_article_title": str(metadata["probable_article_title"]),
        "probable_author": str(metadata["probable_author"]),
        "year": "",
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


def write_notes() -> None:
    note = """# Inscriptions of Burma extraction notes

- **OCRed witness**: `inscriptions_of_burma-b7c07d9f6d02`
- **Observed structure**: bilingual front matter (English preface, Burmese preface, abbreviation lists), a clean English `INDEX OF PLATES` section on OCR pages 6-10, a Burmese plate index on pages 11-14, dimensions tables, and then mostly facsimile plate/rubbing pages whose OCR is noisy.
- **Contains recognizable inscription numbers**: yes, chiefly through plate numbers plus `List`, `SIP`, `PPA`, `TN`, `UB`, and `JBRS` cross-references in the English/Burmese index pages.
- **Contains Burmese inscription text**: the facsimile plate pages do contain Burmese script, but the OCR quality on the plate images is generally too poor for safe inscription-level extraction from this run.
- **Contains English translations**: no inscription-level English translations were found in the OCRed source text. The only `translation` hits are in the preface, where the editors explain that this facsimile series points readers to other published books containing the inscription text or English translation.
- **Contains plates/rubbings or transcribed text**: overwhelmingly plates/rubbings plus index/catalogue matter; this is not an edited text-and-translation volume.
- **Locator systems present**: Roman-numbered plates in the source itself, plus `List`, `SIP`, `PPA`, `TN`, `UB`, and occasional `JBRS` references in the index entries. The structured corpus cites this witness mostly as `Pl. I ...`, which corresponds to volume-I plate numbers that can be converted to the OCRed Roman plate entries.
- **Segmentation strategy**:
  1. Treat the preface and abbreviation page as commentary/context units.
  2. Treat the English `INDEX OF PLATES` entries as the main extractable units for this source.
  3. Link only exact, single-plate `Pl. I N[a|b]` corpus citations back to the matching Roman-numbered index entries.
  4. Keep range citations, multi-plate citations, and noisy facsimile plate pages as manual-review material.
"""
    EXTRACTION_NOTES_PATH.write_text(note, encoding="utf-8")


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
    write_tsv(LOCAL_SOURCE_OCR_TEXT_INDEX_PATH, [build_repo_safe_index_row(repo_metadata, manifest_row)], JBRS_OCR_TEXT_INDEX_FIELDS)

    pages = page_map_from_text(text)
    simple_links = load_unique_simple_plate_links()
    index_units = build_index_units(parse_english_index_entries(pages), simple_links)
    units = [build_preface_unit(pages)]
    units.extend(parse_abbreviation_entries(pages.get(5, [])))
    units.extend(index_units)
    units.extend(build_unclear_plate_units(pages))
    write_tsv(EXTRACTED_UNITS_PATH, units, EXTRACTED_UNIT_FIELDS)
    write_tsv(SAMPLE_REVIEW_PATH, build_sample_review(units), SAMPLE_REVIEW_FIELDS)
    write_notes()


if __name__ == "__main__":
    main()
