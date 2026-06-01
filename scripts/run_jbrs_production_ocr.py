#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from corpus_common import ensure_parent, read_tsv, write_tsv
import ocr_jbrs_google_vision as ocr
from jbrs_workflow_common import (
    JBRS_ARTICLE_REFERENCE_TARGETS_PATH,
    JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH,
    DEFAULT_LOCAL_OUTPUT_ROOT,
    DEFAULT_PREFLIGHT_REPORT_PATH,
    DEFAULT_RUNTIME_PATH_CACHE,
    JBRS_BURMESE_RELEVANCE_GUESS_VALUES,
    JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
    JBRS_DIRECTORY,
    JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH,
    JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
    JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
    JBRS_FILE_ALIAS_MAP_FIELDS,
    JBRS_FILE_ALIAS_MAP_PATH,
    JBRS_FILE_RENAMING_PLAN_FIELDS,
    JBRS_FILE_RENAMING_PLAN_PATH,
    JBRS_FOLLOWUP_SOURCE_LEADS_PATH,
    JBRS_INSCRIPTIONAL_RELEVANCE_CLASS_VALUES,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_LANGUAGE_SCOPE_VALUES,
    JBRS_OCR_QUALITY_REVIEW_PATH,
    JBRS_OCR_PRODUCTION_SUMMARY_PATH,
    JBRS_OCR_PRODUCTION_RUN_LOG_FIELDS,
    JBRS_OCR_PRODUCTION_RUN_LOG_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_FIELDS,
    JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH,
    JBRS_OCR_TEXT_INDEX_FIELDS,
    JBRS_OCR_TEXT_INDEX_PATH,
    JBRS_OCR_TOP_EXTRACTION_CANDIDATES_FIELDS,
    JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH,
    JBRS_OCR_TRANSLATION_HIT_INDEX_FIELDS,
    JBRS_OCR_TRANSLATION_HIT_INDEX_PATH,
    JBRS_PILOT_SUMMARY_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_REFERENCE_HUNT_RAW_PATH,
    JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
    JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH,
    JBRS_WORKING_OCR_METADATA_ROOT,
    JBRS_WORKING_OCR_TEXT_ROOT,
    KNOWN_AUTHORS,
    apply_article_target_reviews,
    batch_is_selectable_for_ocr,
    build_jbrs_ocr_production_summary,
    build_pilot_summary,
    clean_article_title_fragment,
    detect_author,
    detect_title,
    looks_like_person_name,
    normalize_for_match,
    probable_title_from_descriptor,
    safe_path_stub,
    slugify,
    write_summary,
)

SELECTION_TERMS = [
    "inscription",
    "inscriptions",
    "pagan",
    "pinya",
    "ava",
    "burmese",
    "old burmese",
    "ananda",
    "shwegugyi",
    "pyu",
    "mon",
    "talaing",
    "pali",
    "translation",
    "text",
    "text and translation",
    "burmese inscription",
    "pagan inscription",
    "ppa",
    "list",
]
SELECTION_TERM_WEIGHTS = {
    "translation": 6,
    "inscription": 6,
    "inscriptions": 6,
    "burmese inscription": 7,
    "pagan inscription": 7,
    "text and translation": 7,
    "old burmese": 6,
    "burmese": 5,
    "ananda": 5,
    "shwegugyi": 5,
    "pyu": 5,
    "mon": 4,
    "talaing": 4,
    "pali": 4,
    "pagan": 3,
    "pinya": 3,
    "ava": 3,
    "text": 2,
    "ppa": 4,
    "list": 2,
}
TRANSLATION_MARKERS = [
    "translation",
    "translated",
    "text and translation",
    "literal translation",
    "partly translated",
]
TEXT_MARKERS = [
    "pali text",
    "burmese text",
    "text and translation",
    "text.",
]
INSCRIPTION_MARKERS = [
    "inscription",
    "inscriptions",
    "inscription reads",
    "the inscription says",
    "pagan inscription",
    "burmese inscription",
    "talaing inscription",
    "mon inscription",
    "pyu inscription",
    "selections from the inscriptions of pagan",
]
BURMESE_MARKERS = ["old burmese", "burmese text", "burmese inscription", "burmese version"]
PALI_MARKERS = ["pali", "pali text"]
MON_MARKERS = [" mon ", " talaing", "mon inscription", "talaing inscription"]
PYU_MARKERS = [" pyu ", "pyu inscription", "ancient pyu"]
CONTEXT_MARKERS = ["burma research society", "j.b.r.s.", "jbrs", "burma", "pagan", "pinya", "ava"]
BURMESE_CONTEXT_MARKERS = [
    "burmese",
    "old burmese",
    "burmese songs",
    "burmese text",
    "burmese inscription",
]
PALI_CONTEXT_MARKERS = ["pali", "pali literature", "pali text"]
MON_CONTEXT_MARKERS = [
    "mon",
    "talaing",
    "mon inscription",
    "talaing inscription",
    "talaing epigraphy",
]
PYU_CONTEXT_MARKERS = ["pyu", "pyu inscription", "ancient pyu"]
BURMESE_STRUCTURAL_MARKERS = [
    "burmese text",
    "burmese inscription",
    "old burmese",
    "burmese songs",
    "translation of burmese songs",
    "burmese version",
    "burmese versions",
]
PALI_STRUCTURAL_MARKERS = ["pali text", "pali version", "pali versions", "pali verse"]
MON_STRUCTURAL_MARKERS = ["talaing inscription", "mon inscription", "old talaing", "talaing epigraphy"]
PYU_STRUCTURAL_MARKERS = ["pyu inscription", "pyu text", "ancient pyu"]
INSCRIPTION_TITLE_MARKERS = [
    "inscription",
    "inscriptions",
    "burmese inscription",
    "pagan inscription",
    "old burmese",
    "text and translation",
    "epigraphy",
    "list",
    "ppa",
]
EPIGRAPHY_TITLE_MARKERS = [
    "epigraphy",
    "old burmese",
    "language",
    "comparative study",
    "nissaya",
]
GENERAL_BURMESE_TEXT_MARKERS = [
    "burmese songs",
    "burmese history",
    "burmese embassy",
    "burmese calendar",
    "burmese literature",
]
PAGE_MARKER_PATTERN = re.compile(r"^\[\[page (?P<page>\d+)\]\]$", re.MULTILINE)
CANDIDATE_REPORT_LIMIT = 50
INSCRIPTION_CANDIDATE_REPORT_LIMIT = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the first production JBRS OCR tranche and export searchable OCR text."
    )
    parser.add_argument("--batch-plan", type=Path, default=JBRS_OCR_BATCH_PLAN_PATH)
    parser.add_argument("--status-log", type=Path, default=JBRS_OCR_STATUS_LOG_PATH)
    parser.add_argument("--manifest", type=Path, default=JBRS_LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--reference-match", type=Path, default=JBRS_REFERENCE_FILE_MATCH_PATH)
    parser.add_argument("--citation-priority-queue", type=Path, default=JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH)
    parser.add_argument("--runtime-path-cache", type=Path, default=DEFAULT_RUNTIME_PATH_CACHE)
    parser.add_argument("--local-output-root", type=Path, default=DEFAULT_LOCAL_OUTPUT_ROOT)
    parser.add_argument("--repo-text-root", type=Path, default=JBRS_WORKING_OCR_TEXT_ROOT)
    parser.add_argument("--repo-metadata-root", type=Path, default=JBRS_WORKING_OCR_METADATA_ROOT)
    parser.add_argument("--production-run-log", type=Path, default=JBRS_OCR_PRODUCTION_RUN_LOG_PATH)
    parser.add_argument("--ocr-text-index", type=Path, default=JBRS_OCR_TEXT_INDEX_PATH)
    parser.add_argument("--translation-hit-index", type=Path, default=JBRS_OCR_TRANSLATION_HIT_INDEX_PATH)
    parser.add_argument(
        "--top-candidates-path",
        type=Path,
        default=JBRS_OCR_TOP_EXTRACTION_CANDIDATES_PATH,
    )
    parser.add_argument(
        "--top-inscription-candidates-path",
        type=Path,
        default=JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_PATH,
    )
    parser.add_argument(
        "--production-summary-path",
        type=Path,
        default=JBRS_OCR_PRODUCTION_SUMMARY_PATH,
    )
    parser.add_argument("--file-renaming-plan", type=Path, default=JBRS_FILE_RENAMING_PLAN_PATH)
    parser.add_argument("--file-alias-map", type=Path, default=JBRS_FILE_ALIAS_MAP_PATH)
    parser.add_argument("--preflight-report", type=Path, default=DEFAULT_PREFLIGHT_REPORT_PATH)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--selection-rule", default="citation-match then keyword/article priority")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebuild-indexes-only", action="store_true")
    return parser.parse_args()


def boolish(value: str) -> bool:
    return value.strip().casefold() == "true"


def intish(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value: str) -> str:
    return f" {value.casefold()} "


def normalize_searchable_text(*values: str) -> str:
    normalized_parts: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
        normalized = re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", normalized)
        normalized = re.sub(r"[_./-]+", " ", normalized)
        normalized_parts.append(normalized)
    combined = " ".join(normalized_parts).casefold()
    combined = re.sub(r"[^0-9a-z\s]+", " ", combined)
    combined = re.sub(r"\s+", " ", combined).strip()
    return f" {combined} " if combined else " "


def marker_present(haystack: str, marker: str) -> bool:
    return marker.casefold() in haystack


def phrase_present(haystack: str, marker: str) -> bool:
    normalized_marker = normalize_searchable_text(marker).strip()
    return bool(normalized_marker) and f" {normalized_marker} " in haystack


def text_has_any_marker(haystack: str, markers: list[str]) -> bool:
    return any(marker_present(haystack, marker) for marker in markers)


def text_has_any_phrase(haystack: str, markers: list[str]) -> bool:
    return any(phrase_present(haystack, marker) for marker in markers)


def collect_keyword_hits(*values: str) -> list[str]:
    haystack = normalize_searchable_text(*values)
    return [term for term in SELECTION_TERMS if phrase_present(haystack, term)]


def metadata_haystack_for_record(
    record: dict[str, str],
    manifest_row: dict[str, str],
) -> str:
    return normalize_searchable_text(
        record.get("file_name", ""),
        record.get("path_stub", ""),
        manifest_row.get("file_name", ""),
        manifest_row.get("probable_title_from_filename", ""),
        manifest_row.get("folder_context", ""),
        manifest_row.get("path_stub_or_redacted_path", ""),
    )


def keyword_weight(keyword_hits: list[str]) -> int:
    return sum(SELECTION_TERM_WEIGHTS.get(term, 1) for term in keyword_hits)


def batch_priority_rank(value: str) -> int:
    return {"high": 2, "medium": 1, "low": 0}.get(value, 0)


def is_generic_numeric_file_name(file_name: str) -> bool:
    return bool(re.fullmatch(r"\d+[A-Za-z]?\.pdf", file_name or ""))


def select_production_batch_rows(
    batch_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    citation_rows: list[dict[str, str]],
    limit: int,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    status_by_batch_id = {row["batch_id"]: row for row in status_rows}
    manifest_by_id = {row["local_file_id"]: row for row in manifest_rows}
    matches_by_local_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in match_rows:
        local_file_id = row.get("local_file_id", "")
        if local_file_id:
            matches_by_local_id[local_file_id].append(row)
    citation_local_ids = {
        row.get("candidate_local_file_id", "")
        for row in citation_rows
        if row.get("candidate_local_file_id", "")
    }
    scored_rows: list[dict[str, object]] = []
    skipped_batch_ids: list[str] = []
    for batch_row in batch_rows:
        status_row = status_by_batch_id.get(batch_row["batch_id"])
        if not batch_is_selectable_for_ocr(batch_row, status_row):
            skipped_batch_ids.append(batch_row["batch_id"])
            continue
        local_file_id = batch_row["local_file_id"]
        manifest_row = manifest_by_id.get(local_file_id, {})
        local_matches = matches_by_local_id.get(local_file_id, [])
        metadata_haystack = metadata_haystack_for_record(batch_row, manifest_row)
        keyword_hits = collect_keyword_hits(
            batch_row.get("file_name", ""),
            manifest_row.get("file_name", ""),
            manifest_row.get("probable_title_from_filename", ""),
            batch_row.get("path_stub", ""),
        )
        has_translation_keyword = any(
            term in {"translation", "text", "text and translation", "pali", "burmese", "old burmese"}
            for term in keyword_hits
        )
        has_inscription_keyword = any(
            term
            in {
                "inscription",
                "inscriptions",
                "burmese inscription",
                "pagan inscription",
                "old burmese",
                "ananda",
                "shwegugyi",
                "pyu",
                "mon",
                "talaing",
                "ppa",
                "list",
            }
            for term in keyword_hits
        )
        has_direct_inscription_phrase = text_has_any_phrase(metadata_haystack, INSCRIPTION_TITLE_MARKERS)
        has_general_burmese_text_phrase = text_has_any_phrase(metadata_haystack, GENERAL_BURMESE_TEXT_MARKERS)
        has_epigraphy_phrase = text_has_any_phrase(metadata_haystack, EPIGRAPHY_TITLE_MARKERS)
        exact_reference_match = any(
            row.get("match_status") == "exact_or_near_exact_match" for row in local_matches
        )
        direct_reference_match = any(
            row.get("match_status") in {"exact_or_near_exact_match", "plausible_match"}
            for row in local_matches
        )
        multiple_candidate_match = any(
            row.get("match_status") == "multiple_candidates" for row in local_matches
        )
        citation_priority = local_file_id in citation_local_ids
        is_article = boolish(manifest_row.get("is_article_split_pdf", ""))
        is_whole_volume = boolish(manifest_row.get("is_whole_issue_or_volume", ""))
        generic_numeric = is_generic_numeric_file_name(batch_row.get("file_name", ""))
        if generic_numeric and not (citation_priority or direct_reference_match or keyword_hits):
            skipped_batch_ids.append(batch_row["batch_id"])
            continue
        page_count = intish(batch_row.get("page_count_estimate", ""), default=9999)
        keyword_score = keyword_weight(keyword_hits)
        score = (
            1 if citation_priority else 0,
            1 if exact_reference_match else 0,
            1 if direct_reference_match else 0,
            1 if has_direct_inscription_phrase else 0,
            1 if has_inscription_keyword else 0,
            1 if has_translation_keyword else 0,
            1 if has_epigraphy_phrase else 0,
            keyword_score,
            len(keyword_hits),
            0 if multiple_candidate_match else 1,
            batch_priority_rank(batch_row.get("ocr_priority", "")),
            1 if is_article else 0,
            0 if is_whole_volume else 1,
            0 if has_general_burmese_text_phrase and not has_direct_inscription_phrase else 1,
            0 if generic_numeric else 1,
            -page_count,
            batch_row["batch_id"],
        )
        scored_rows.append(
            {
                "batch_row": batch_row,
                "score": score,
                "notes": "; ".join(
                    part
                    for part in [
                        "citation-priority" if citation_priority else "",
                        "exact-reference-match" if exact_reference_match else "",
                        "direct-reference-match" if direct_reference_match and not exact_reference_match else "",
                        "direct-inscription-signal" if has_direct_inscription_phrase else "",
                        f"keywords={','.join(keyword_hits[:6])}" if keyword_hits else "",
                        "article-pdf" if is_article else "",
                    ]
                    if part
                ),
            }
        )
    selected_scored_rows = sorted(scored_rows, key=lambda item: item["score"], reverse=True)[:limit]
    selected_rows = [item["batch_row"] for item in selected_scored_rows]
    selection_context = {
        "selectable_count": len(scored_rows),
        "skipped_batch_count": len(skipped_batch_ids),
        "deferred_count": max(len(scored_rows) - len(selected_rows), 0),
        "selected_notes": {item["batch_row"]["batch_id"]: item["notes"] for item in selected_scored_rows},
    }
    return selected_rows, selection_context


def relative_stub(path: Path) -> str:
    return path.relative_to(Path.cwd()).as_posix()


AUTHOR_SLUG_STOP_WORDS = {"u", "daw", "dr", "sir", "prof", "professor"}
TITLE_SLUG_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
REPO_RENAME_SCOPE_TOP_CANDIDATES = 50
REPO_RENAME_SCOPE_TOP_INSCRIPTION = 20


def detect_authors(value: str | None) -> list[str]:
    text = normalize_for_match(value)
    matches: list[str] = []
    for canonical, variants in KNOWN_AUTHORS:
        if any(normalize_for_match(variant) in text for variant in variants):
            if canonical not in matches:
                matches.append(canonical)
    return matches


def first_heading_lines(text: str, max_lines: int = 10) -> list[str]:
    first_page_text = split_pages(text)[0][1] if split_pages(text) else text
    lines: list[str] = []
    for raw_line in first_page_text.splitlines():
        stripped = " ".join(raw_line.split()).strip()
        if not stripped:
            if lines:
                break
            continue
        if PAGE_MARKER_PATTERN.fullmatch(stripped):
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return lines


def titleish_heading_lines(lines: list[str]) -> list[str]:
    selected: list[str] = []
    for line in lines:
        lowered = line.casefold()
        if lowered.startswith("by "):
            break
        if "journal of the burma research society" in lowered or lowered in {"j.b.r.s.", "jbrs"}:
            continue
        if re.search(r"\bvol(?:ume)?\.?\b|\bpart\b|\bpp?\.?\b", lowered):
            continue
        if looks_like_person_name(line):
            if selected:
                break
            continue
        selected.append(line)
        if len(selected) >= 4:
            break
    return selected


def infer_probable_author(record: dict[str, str], manifest_row: dict[str, str]) -> str:
    heading_lines = first_heading_lines(record["text"])
    candidate_sources = [
        " ".join(heading_lines[:6]),
        record.get("file_name", ""),
        record.get("path_stub", ""),
        manifest_row.get("probable_title_from_filename", ""),
        manifest_row.get("folder_context", ""),
    ]
    for line in heading_lines[:6]:
        by_match = re.match(r"(?i)^by\s+(.+)$", line)
        if by_match:
            by_value = by_match.group(1).strip(" ,.;:")
            canonical = detect_author(by_value)
            if canonical:
                return canonical
            if looks_like_person_name(by_value):
                return by_value
        authors = detect_authors(line)
        if authors:
            return authors[0]
        if looks_like_person_name(line):
            return line.strip(" ,.;:")
    for source in candidate_sources:
        canonical = detect_author(source)
        if canonical:
            return canonical
        authors = detect_authors(source)
        if authors:
            return authors[0]
    return ""


def infer_probable_title(record: dict[str, str], manifest_row: dict[str, str], author: str) -> str:
    heading_lines = first_heading_lines(record["text"])
    heading_text = " ".join(titleish_heading_lines(heading_lines))
    for candidate_source in (
        heading_text,
        " ".join(heading_lines[:6]),
        manifest_row.get("probable_title_from_filename", ""),
        record.get("file_name", ""),
        record.get("path_stub", ""),
    ):
        title = detect_title(candidate_source) or probable_title_from_descriptor(candidate_source)
        title = clean_article_title_fragment(author, title)
        if title:
            return title
    if heading_text:
        return clean_article_title_fragment(author, heading_text)
    return ""


def title_slug(title: str) -> str:
    parts = [part for part in normalize_for_match(title).split() if part not in TITLE_SLUG_STOP_WORDS]
    if not parts:
        parts = normalize_for_match(title).split()
    return "-".join(parts[:8]) or "untitled"


def author_slug(author: str) -> str:
    parts = [part for part in normalize_for_match(author).split() if part not in AUTHOR_SLUG_STOP_WORDS]
    if not parts:
        parts = normalize_for_match(author).split()
    return "-".join(parts[:5]) or "unknown-author"


def preferred_year(record: dict[str, str], manifest_row: dict[str, str]) -> str:
    for value in (record.get("year", ""), manifest_row.get("year", ""), record.get("file_name", "")):
        match = re.search(r"\b(18|19|20)\d{2}\b", value or "")
        if match:
            return match.group(0)
    return ""


def canonical_base_name(year: str, title: str, author: str) -> str:
    if not year or not title or not author:
        return ""
    return f"{year}-{title_slug(title)}-{author_slug(author)}"


def text_signature(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def rename_scope_local_file_ids(
    top_candidate_rows: list[dict[str, str]],
    top_inscription_rows: list[dict[str, str]],
) -> set[str]:
    scope = {
        row["local_file_id"] for row in top_candidate_rows[:REPO_RENAME_SCOPE_TOP_CANDIDATES]
    }
    scope.update(
        row["local_file_id"] for row in top_inscription_rows[:REPO_RENAME_SCOPE_TOP_INSCRIPTION]
    )
    for path in (
        JBRS_STRUCTURED_EXTRACTION_PLAN_PATH,
        JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
        JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
    ):
        for row in read_tsv(path):
            local_file_id = row.get("local_file_id", "") or row.get("source_local_file_id", "")
            if local_file_id:
                scope.add(local_file_id)
    return scope


def build_file_renaming_rows(
    exported_records: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    phase1_scope_local_ids: set[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    manifest_by_local_file_id = {row["local_file_id"]: row for row in manifest_rows}
    records_by_text_signature: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in exported_records:
        records_by_text_signature[text_signature(record["text"])].append(record)

    provisional_rows: list[dict[str, str]] = []
    alias_rows: list[dict[str, str]] = []
    for record in exported_records:
        manifest_row = manifest_by_local_file_id.get(record["local_file_id"], {})
        old_file_name = record.get("old_file_name", "") or record["file_name"]
        old_path_stub = record.get("old_path_stub", "") or record["path_stub"]
        current_ocr_text_path = record["ocr_text_path"]
        current_metadata_path = record["metadata_path"]
        duplicate_candidates = [
            candidate
            for candidate in records_by_text_signature[text_signature(record["text"])]
            if candidate["local_file_id"] != record["local_file_id"]
        ]
        named_duplicate = next(
            (
                candidate
                for candidate in duplicate_candidates
                if not is_generic_numeric_file_name(candidate.get("old_file_name", "") or candidate["file_name"])
            ),
            None,
        )
        probable_author = (
            (named_duplicate or {}).get("probable_author", "")
            or infer_probable_author(record, manifest_row)
        )
        probable_title = (
            (named_duplicate or {}).get("probable_article_title", "")
            or infer_probable_title(record, manifest_row, probable_author)
        )
        probable_year = (named_duplicate or {}).get("year", "") or preferred_year(record, manifest_row)
        proposed_base_name = canonical_base_name(probable_year, probable_title, probable_author)
        identity_confidence = "low"
        notes: list[str] = []
        if named_duplicate and proposed_base_name:
            identity_confidence = "high"
            notes.append(f"duplicate_of={named_duplicate['local_file_id']}")
        elif proposed_base_name and probable_title and probable_author:
            identity_confidence = "high" if not is_generic_numeric_file_name(old_file_name) else "medium"
        elif probable_title and probable_year:
            identity_confidence = "medium"
        stored_status = record.get("rename_status", "")
        preserved_status = stored_status if stored_status in {"renamed_in_repo", "already_canonical"} else ""
        rename_status = preserved_status or (
            "planned_repo_rename"
            if record["local_file_id"] in phase1_scope_local_ids
            and proposed_base_name
            and identity_confidence in {"high", "medium"}
            and (
                Path(current_ocr_text_path).name != f"{proposed_base_name}.txt"
                or Path(current_metadata_path).name != f"{proposed_base_name}.json"
            )
            else "already_canonical"
            if proposed_base_name
            and Path(current_ocr_text_path).name == f"{proposed_base_name}.txt"
            and Path(current_metadata_path).name == f"{proposed_base_name}.json"
            else "deferred_outside_phase1_scope"
            if proposed_base_name
            else "needs_manual_review"
        )
        provisional_rows.append(
            {
                "local_file_id": record["local_file_id"],
                "batch_id": record["batch_id"],
                "old_file_name": old_file_name,
                "old_path_stub": old_path_stub,
                "current_ocr_text_path": current_ocr_text_path,
                "current_metadata_path": current_metadata_path,
                "probable_article_title": probable_title,
                "probable_author": probable_author,
                "probable_year": probable_year,
                "canonical_base_name": proposed_base_name,
                "proposed_pdf_file_name": f"{proposed_base_name}.pdf" if proposed_base_name else "",
                "proposed_ocr_text_file_name": f"{proposed_base_name}.txt" if proposed_base_name else "",
                "proposed_metadata_file_name": f"{proposed_base_name}.json" if proposed_base_name else "",
                "identity_confidence": identity_confidence,
                "rename_status": rename_status,
                "notes": "; ".join(notes),
            }
        )

    grouped_by_base_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in provisional_rows:
        if row["canonical_base_name"]:
            grouped_by_base_name[row["canonical_base_name"]].append(row)
    for base_name, grouped_rows in grouped_by_base_name.items():
        if len(grouped_rows) <= 1:
            continue
        grouped_rows.sort(
            key=lambda row: (
                0 if row["rename_status"] == "already_canonical" else 1,
                0 if not is_generic_numeric_file_name(row["old_file_name"]) else 1,
                row["local_file_id"],
            )
        )
        for index, row in enumerate(grouped_rows, start=1):
            if index == 1:
                continue
            suffixed_base_name = f"{base_name}-scan-{index}"
            row["canonical_base_name"] = suffixed_base_name
            row["proposed_pdf_file_name"] = f"{suffixed_base_name}.pdf"
            row["proposed_ocr_text_file_name"] = f"{suffixed_base_name}.txt"
            row["proposed_metadata_file_name"] = f"{suffixed_base_name}.json"
            row["notes"] = "; ".join(
                part for part in [row["notes"], f"collision_with={base_name}"] if part
            )

    for row in provisional_rows:
        canonical_file_name = row["proposed_pdf_file_name"] or row["old_file_name"]
        canonical_ocr_text_path = (
            relative_stub(JBRS_WORKING_OCR_TEXT_ROOT / row["proposed_ocr_text_file_name"])
            if row["proposed_ocr_text_file_name"]
            else row["current_ocr_text_path"]
        )
        canonical_metadata_path = (
            relative_stub(JBRS_WORKING_OCR_METADATA_ROOT / row["proposed_metadata_file_name"])
            if row["proposed_metadata_file_name"]
            else row["current_metadata_path"]
        )
        alias_rows.append(
            {
                "local_file_id": row["local_file_id"],
                "old_file_name": row["old_file_name"],
                "old_path_stub": row["old_path_stub"],
                "canonical_file_name": canonical_file_name,
                "canonical_ocr_text_path": canonical_ocr_text_path,
                "canonical_metadata_path": canonical_metadata_path,
                "canonical_pdf_path_stub": (
                    f"data_local/sources/jbrs_canonical_pdfs/{canonical_file_name}"
                    if row["proposed_pdf_file_name"]
                    else ""
                ),
                "alias_status": row["rename_status"],
                "notes": row["notes"],
            }
        )
    provisional_rows.sort(key=lambda row: (row["old_file_name"], row["local_file_id"]))
    alias_rows.sort(key=lambda row: (row["old_file_name"], row["local_file_id"]))
    return provisional_rows, alias_rows


def apply_repo_ocr_renaming_plan(
    renaming_rows: list[dict[str, str]],
    alias_rows: list[dict[str, str]],
) -> None:
    alias_by_local_file_id = {row["local_file_id"]: row for row in alias_rows}
    for row in renaming_rows:
        alias_row = alias_by_local_file_id[row["local_file_id"]]
        current_text_path = Path.cwd() / row["current_ocr_text_path"]
        current_metadata_path = Path.cwd() / row["current_metadata_path"]
        target_text_path = Path.cwd() / alias_row["canonical_ocr_text_path"]
        target_metadata_path = Path.cwd() / alias_row["canonical_metadata_path"]
        ensure_parent(target_text_path)
        ensure_parent(target_metadata_path)
        if row["rename_status"] == "planned_repo_rename":
            if current_text_path != target_text_path:
                current_text_path.rename(target_text_path)
            if current_metadata_path != target_metadata_path:
                current_metadata_path.rename(target_metadata_path)
            row["rename_status"] = "renamed_in_repo"
            alias_row["alias_status"] = "renamed_in_repo"
        else:
            target_text_path = current_text_path
            target_metadata_path = current_metadata_path
            if row["rename_status"] == "already_canonical":
                alias_row["alias_status"] = "already_canonical"
        metadata = json.loads(target_metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "old_file_name": row["old_file_name"],
                "old_path_stub": row["old_path_stub"],
                "canonical_file_name": alias_row["canonical_file_name"],
                "canonical_base_name": row["canonical_base_name"],
                "canonical_ocr_text_path": relative_stub(target_text_path),
                "canonical_metadata_path": relative_stub(target_metadata_path),
                "canonical_pdf_path_stub": alias_row["canonical_pdf_path_stub"],
                "probable_article_title": row["probable_article_title"],
                "probable_author": row["probable_author"],
                "probable_year": row["probable_year"],
                "identity_confidence": row["identity_confidence"],
                "rename_status": row["rename_status"],
            }
        )
        target_metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

def source_category_from_manifest(manifest_row: dict[str, str]) -> str:
    if boolish(manifest_row.get("is_article_split_pdf", "")):
        return "article_pdf"
    if boolish(manifest_row.get("is_whole_issue_or_volume", "")):
        return "whole_volume_pdf"
    if (manifest_row.get("extension", "") or "").casefold() == ".pdf":
        return "pdf_other"
    return "other_source"


def split_pages(text: str) -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    current_marker = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        match = PAGE_MARKER_PATTERN.match(line.strip())
        if match:
            if current_marker or current_lines:
                pages.append((current_marker, "\n".join(current_lines).strip()))
            current_marker = f"page {int(match.group('page'))}"
            current_lines = []
        else:
            current_lines.append(line)
    if current_marker or current_lines:
        pages.append((current_marker, "\n".join(current_lines).strip()))
    return pages


def guess_language_scope(manifest_row: dict[str, str], batch_row: dict[str, str], text: str) -> str:
    metadata_haystack = normalize_searchable_text(
        manifest_row.get("file_name", ""),
        manifest_row.get("probable_title_from_filename", ""),
        manifest_row.get("folder_context", ""),
        manifest_row.get("path_stub_or_redacted_path", ""),
        batch_row.get("file_name", ""),
        batch_row.get("path_stub", ""),
    )
    text_haystack = normalize_searchable_text(text)
    broad_text_haystack = normalize_text(text)
    metadata_has_burmese = text_has_any_phrase(metadata_haystack, BURMESE_CONTEXT_MARKERS)
    metadata_has_pali = text_has_any_phrase(metadata_haystack, PALI_CONTEXT_MARKERS)
    metadata_has_mon = text_has_any_phrase(metadata_haystack, MON_CONTEXT_MARKERS)
    metadata_has_pyu = text_has_any_phrase(metadata_haystack, PYU_CONTEXT_MARKERS)
    text_has_burmese = text_has_any_phrase(text_haystack, BURMESE_STRUCTURAL_MARKERS)
    text_has_pali = text_has_any_phrase(text_haystack, PALI_STRUCTURAL_MARKERS)
    text_has_mon = text_has_any_phrase(text_haystack, MON_STRUCTURAL_MARKERS)
    text_has_pyu = text_has_any_phrase(text_haystack, PYU_STRUCTURAL_MARKERS)
    if metadata_has_burmese and (metadata_has_pali or text_has_pali):
        return "Mixed Burmese/Pali"
    if metadata_has_burmese:
        return "Burmese"
    if metadata_has_mon and not metadata_has_burmese:
        return "Mon"
    if metadata_has_pyu and not metadata_has_burmese:
        return "Pyu"
    if metadata_has_pali and not metadata_has_burmese:
        return "Pali"
    if text_has_burmese and text_has_pali:
        return "Mixed Burmese/Pali"
    if text_has_burmese:
        return "Burmese"
    if text_has_mon:
        return "Mon"
    if text_has_pyu:
        return "Pyu"
    if text_has_pali:
        return "Pali"
    if text_has_any_marker(broad_text_haystack, TRANSLATION_MARKERS + TEXT_MARKERS + INSCRIPTION_MARKERS):
        return "mixed_or_uncertain"
    if text_has_any_marker(broad_text_haystack, CONTEXT_MARKERS):
        return "non_burmese_relevant_context"
    return "mixed_or_uncertain"


def burmese_relevance_guess(language_scope: str) -> str:
    mapping = {
        "Burmese": "direct_burmese_relevance",
        "Mixed Burmese/Pali": "mixed_burmese_pali_relevance",
        "Pali": "pali_only_not_burmese_corpus_material",
        "Mon": "non_burmese_inscriptional_context",
        "Pyu": "non_burmese_inscriptional_context",
        "mixed_or_uncertain": "uncertain_needs_review",
        "non_burmese_relevant_context": "contextual_only",
    }
    return mapping[language_scope]


def inscriptional_relevance_class(
    record: dict[str, str],
    manifest_row: dict[str, str],
    hit_type_counts: Counter[str],
    marker_counts: Counter[str],
    citation_hits: list[dict[str, str]],
) -> str:
    metadata_haystack = metadata_haystack_for_record(record, manifest_row)
    language_scope = record["language_scope_guess"]
    translation_hit_count = hit_type_counts["translation_marker"]
    text_hit_count = hit_type_counts["text_marker"]
    inscription_hit_count = hit_type_counts["inscription_marker"]
    has_inscription_title = text_has_any_phrase(metadata_haystack, INSCRIPTION_TITLE_MARKERS)
    has_epigraphy_title = text_has_any_phrase(metadata_haystack, EPIGRAPHY_TITLE_MARKERS)
    has_general_burmese_text_title = text_has_any_phrase(metadata_haystack, GENERAL_BURMESE_TEXT_MARKERS)
    has_text_and_translation_marker = "text and translation" in marker_counts
    has_burmese_inscription_marker = any(
        marker in marker_counts
        for marker in {"burmese inscription", "pagan inscription", "inscription", "inscriptions"}
    )

    if language_scope in {"Mon", "Pyu"}:
        return "non_burmese_inscription_context"
    if language_scope == "Pali" and (inscription_hit_count or citation_hits):
        return "non_burmese_inscription_context"
    if (
        language_scope in {"Burmese", "Mixed Burmese/Pali"}
        and translation_hit_count
        and (inscription_hit_count or has_inscription_title or has_text_and_translation_marker)
    ):
        return "direct_inscription_translation"
    if (
        language_scope in {"Burmese", "Mixed Burmese/Pali"}
        and (inscription_hit_count or text_hit_count)
        and (has_inscription_title or has_burmese_inscription_marker)
    ):
        return "direct_inscription_text"
    if inscription_hit_count or citation_hits:
        return "inscription_commentary_or_citation"
    if has_epigraphy_title or "old burmese" in marker_counts:
        return "language_history_or_epigraphy"
    if language_scope in {"Burmese", "Mixed Burmese/Pali"} and translation_hit_count:
        return "general_burmese_text_translation"
    if has_general_burmese_text_title:
        return "general_burmese_text_translation"
    return "uncertain"


def marker_flags(text: str) -> dict[str, str]:
    haystack = normalize_text(text)
    return {
        "contains_translation_marker": "true" if text_has_any_marker(haystack, TRANSLATION_MARKERS) else "false",
        "contains_text_marker": "true" if text_has_any_marker(haystack, TEXT_MARKERS) else "false",
        "contains_inscription_marker": "true" if text_has_any_marker(haystack, INSCRIPTION_MARKERS) else "false",
        "contains_burmese_marker": "true" if text_has_any_marker(haystack, BURMESE_MARKERS) else "false",
        "contains_pali_marker": "true" if text_has_any_marker(haystack, PALI_MARKERS) else "false",
        "contains_mon_marker": "true" if text_has_any_marker(haystack, MON_MARKERS) else "false",
        "contains_pyu_marker": "true" if text_has_any_marker(haystack, PYU_MARKERS) else "false",
    }


def load_repo_export_records(
    status_rows: list[dict[str, str]],
    batch_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    local_output_root: Path,
    repo_text_root: Path,
    repo_metadata_root: Path,
) -> list[dict[str, str]]:
    ensure_parent(repo_text_root / ".keep")
    ensure_parent(repo_metadata_root / ".keep")
    batch_by_id = {row["batch_id"]: row for row in batch_rows}
    manifest_by_id = {row["local_file_id"]: row for row in manifest_rows}
    exported_records: list[dict[str, str]] = []
    for status_row in status_rows:
        if status_row.get("status") != "completed":
            continue
        local_file_id = status_row.get("local_file_id", "")
        batch_row = batch_by_id.get(status_row.get("batch_id", ""))
        manifest_row = manifest_by_id.get(local_file_id, {})
        if not batch_row or not local_file_id:
            continue
        output_stub = status_row.get("output_path_stub", "")
        if not output_stub:
            continue
        local_text_path = Path.cwd() / output_stub
        if not local_text_path.exists():
            continue
        text = local_text_path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        repo_text_path = repo_text_root / f"{local_file_id}.txt"
        repo_metadata_path = repo_metadata_root / f"{local_file_id}.json"
        ensure_parent(repo_text_path)
        repo_text_path.write_text(text, encoding="utf-8")
        repo_text_path_stub = relative_stub(repo_text_path)
        repo_metadata_path_stub = relative_stub(repo_metadata_path)
        pages_completed = status_row.get("completed_pages", "") or str(len(split_pages(text)))
        language_scope = guess_language_scope(manifest_row, batch_row, text)
        metadata = {
            "local_file_id": local_file_id,
            "batch_id": status_row.get("batch_id", ""),
            "file_name": batch_row.get("file_name", "") or manifest_row.get("file_name", ""),
            "path_stub": batch_row.get("path_stub", "") or manifest_row.get("path_stub_or_redacted_path", ""),
            "journal": "JBRS",
            "year": batch_row.get("year", "") or manifest_row.get("year", ""),
            "ocr_engine": "google_vision",
            "pages_completed": intish(pages_completed),
            "ocr_date": status_row.get("updated_at", "") or datetime.now(UTC).date().isoformat(),
            "source_category": source_category_from_manifest(manifest_row),
            "language_scope_guess": language_scope,
            "old_file_name": batch_row.get("file_name", "") or manifest_row.get("file_name", ""),
            "old_path_stub": batch_row.get("path_stub", "") or manifest_row.get("path_stub_or_redacted_path", ""),
            "canonical_file_name": batch_row.get("file_name", "") or manifest_row.get("file_name", ""),
            "canonical_base_name": "",
            "canonical_ocr_text_path": repo_text_path_stub,
            "canonical_metadata_path": repo_metadata_path_stub,
            "canonical_pdf_path_stub": "",
            "probable_article_title": "",
            "probable_author": "",
            "probable_year": batch_row.get("year", "") or manifest_row.get("year", ""),
            "identity_confidence": "low",
            "rename_status": "not_assessed",
            "notes": "Repo-safe OCR export copied from completed gitignored local OCR text; page images and Google Vision JSON remain under data_local/.",
        }
        ensure_parent(repo_metadata_path)
        repo_metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        flags = marker_flags(text)
        exported_records.append(
            {
                "local_file_id": local_file_id,
                "batch_id": status_row.get("batch_id", ""),
                "file_name": metadata["file_name"],
                "old_file_name": metadata["old_file_name"],
                "canonical_file_name": metadata["canonical_file_name"],
                "probable_article_title": metadata["probable_article_title"],
                "probable_author": metadata["probable_author"],
                "year": str(metadata["year"]),
                "path_stub": metadata["path_stub"],
                "old_path_stub": metadata["old_path_stub"],
                "new_path_stub_or_repo_path": repo_text_path_stub,
                "ocr_text_path": repo_text_path_stub,
                "metadata_path": repo_metadata_path_stub,
                "pages_completed": str(metadata["pages_completed"]),
                "ocr_status": "completed",
                "language_scope_guess": language_scope,
                "rename_status": metadata["rename_status"],
                "notes": metadata["notes"],
                "text": text,
                **flags,
            }
        )
    exported_records.sort(key=lambda row: (row["year"], row["file_name"], row["local_file_id"]))
    return exported_records


def load_committed_ocr_records(
    batch_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    repo_text_root: Path,
    repo_metadata_root: Path,
) -> list[dict[str, str]]:
    batch_by_local_file_id = {row["local_file_id"]: row for row in batch_rows}
    completed_local_file_ids = {
        row["local_file_id"]
        for row in status_rows
        if row.get("status") == "completed" and row.get("local_file_id", "")
    }
    manifest_by_local_file_id = {row["local_file_id"]: row for row in manifest_rows}
    exported_records: list[dict[str, str]] = []
    for metadata_path in sorted(repo_metadata_root.glob("*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        local_file_id = metadata.get("local_file_id", "") or metadata_path.stem
        if local_file_id not in completed_local_file_ids:
            continue
        text_path = Path.cwd() / (
            metadata.get("canonical_ocr_text_path", "") or relative_stub(repo_text_root / f"{local_file_id}.txt")
        )
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8")
        batch_row = batch_by_local_file_id.get(
            local_file_id,
            {
                "batch_id": metadata.get("batch_id", ""),
                "file_name": metadata.get("file_name", ""),
                "year": str(metadata.get("year", "")),
                "path_stub": metadata.get("path_stub", ""),
            },
        )
        manifest_row = manifest_by_local_file_id.get(
            local_file_id,
            {
                "file_name": metadata.get("file_name", ""),
                "probable_title_from_filename": metadata.get("file_name", ""),
                "folder_context": "",
                "path_stub_or_redacted_path": metadata.get("path_stub", ""),
            },
        )
        flags = marker_flags(text)
        exported_records.append(
            {
                "local_file_id": local_file_id,
                "batch_id": batch_row.get("batch_id", metadata.get("batch_id", "")),
                "file_name": batch_row.get("file_name", metadata.get("file_name", "")),
                "old_file_name": metadata.get("old_file_name", metadata.get("file_name", "")),
                "canonical_file_name": metadata.get("canonical_file_name", metadata.get("file_name", "")),
                "probable_article_title": metadata.get("probable_article_title", ""),
                "probable_author": metadata.get("probable_author", ""),
                "year": batch_row.get("year", str(metadata.get("year", ""))),
                "path_stub": batch_row.get("path_stub", metadata.get("path_stub", "")),
                "old_path_stub": metadata.get("old_path_stub", metadata.get("path_stub", "")),
                "new_path_stub_or_repo_path": metadata.get(
                    "canonical_ocr_text_path",
                    relative_stub(text_path),
                ),
                "ocr_text_path": relative_stub(text_path),
                "metadata_path": metadata.get("canonical_metadata_path", relative_stub(metadata_path)),
                "pages_completed": str(metadata.get("pages_completed", "")),
                "ocr_status": "completed",
                "language_scope_guess": guess_language_scope(manifest_row, batch_row, text),
                "rename_status": metadata.get("rename_status", "not_assessed"),
                "notes": metadata.get("notes", ""),
                "text": text,
                **flags,
            }
        )
    exported_records.sort(key=lambda row: (row["year"], row["file_name"], row["local_file_id"]))
    return exported_records


def build_hit_id(local_file_id: str, page_marker: str, hit_type: str, matched_marker: str) -> str:
    digest = hashlib.sha1(
        f"{local_file_id}|{page_marker}|{hit_type}|{matched_marker}".encode("utf-8")
    ).hexdigest()[:10]
    return f"jbrs-ocr-hit-{digest}"


def short_context(page_text: str, marker: str, limit: int = 180) -> str:
    normalized_page = re.sub(r"\s+", " ", page_text).strip()
    if not normalized_page:
        return ""
    marker_index = normalized_page.casefold().find(marker.casefold())
    if marker_index < 0:
        return normalized_page[:limit]
    start = max(marker_index - 50, 0)
    end = min(marker_index + len(marker) + 90, len(normalized_page))
    snippet = normalized_page[start:end]
    return snippet[:limit]


def priority_for_hit(hit_type: str, language_scope: str) -> str:
    if hit_type == "citation_reference_seed":
        return "high" if language_scope in {"Burmese", "Mixed Burmese/Pali"} else "medium"
    if hit_type == "translation_marker":
        return "high" if language_scope in {"Burmese", "Mixed Burmese/Pali", "mixed_or_uncertain"} else "medium"
    if hit_type in {"text_marker", "inscription_marker"}:
        return "medium" if language_scope != "non_burmese_relevant_context" else "low"
    return "low"


def next_action_for_hit(hit_type: str, language_scope: str) -> str:
    if hit_type == "citation_reference_seed":
        return "Prioritize OCR review around the cited section."
    if language_scope == "Pali":
        return "Keep indexed as Pali-only until Burmese relevance is demonstrated."
    if language_scope == "Mixed Burmese/Pali":
        return "Review OCR for Burmese and Pali unit boundaries before structured extraction."
    if hit_type == "translation_marker":
        return "Review OCR text for published translation boundaries."
    if hit_type in {"text_marker", "inscription_marker"}:
        return "Review OCR text for source-text boundaries and inscription linkage."
    return "Review language scope and corpus relevance."


def build_translation_hit_rows(
    exported_records: list[dict[str, str]],
    citation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    hit_rows: list[dict[str, str]] = []
    exported_by_local_id = {row["local_file_id"]: row for row in exported_records}
    marker_groups = [
        ("translation_marker", TRANSLATION_MARKERS),
        ("text_marker", TEXT_MARKERS),
        ("inscription_marker", INSCRIPTION_MARKERS),
    ]
    for record in exported_records:
        language_scope = record["language_scope_guess"]
        relevance_guess = burmese_relevance_guess(language_scope)
        for page_marker, page_text in split_pages(record["text"]):
            page_haystack = normalize_text(page_text)
            for hit_type, markers in marker_groups:
                for marker in markers:
                    if not marker_present(page_haystack, marker):
                        continue
                    hit_rows.append(
                        {
                            "hit_id": build_hit_id(record["local_file_id"], page_marker, hit_type, marker),
                            "local_file_id": record["local_file_id"],
                            "batch_id": record["batch_id"],
                            "file_name": record["file_name"],
                            "old_file_name": record.get("old_file_name", record["file_name"]),
                            "canonical_file_name": record.get("canonical_file_name", record["file_name"]),
                            "probable_article_title": record.get("probable_article_title", ""),
                            "probable_author": record.get("probable_author", ""),
                            "old_path_stub": record.get("old_path_stub", record["path_stub"]),
                            "new_path_stub_or_repo_path": record.get(
                                "new_path_stub_or_repo_path",
                                record["ocr_text_path"],
                            ),
                            "page_marker": page_marker,
                            "hit_type": hit_type,
                            "matched_marker": marker,
                            "short_context": short_context(page_text, marker),
                            "language_scope_guess": language_scope,
                            "burmese_relevance_guess": relevance_guess,
                            "priority": priority_for_hit(hit_type, language_scope),
                            "next_action": next_action_for_hit(hit_type, language_scope),
                            "notes": "",
                        }
                    )
        for citation_row in citation_rows:
            local_file_id = citation_row.get("candidate_local_file_id", "")
            if local_file_id != record["local_file_id"]:
                continue
            matched_marker = citation_row.get("corpus_citation_text_short", "") or citation_row.get(
                "normalized_source_reference", ""
            )
            hit_rows.append(
                {
                    "hit_id": build_hit_id(local_file_id, "", "citation_reference_seed", matched_marker),
                    "local_file_id": local_file_id,
                    "batch_id": record["batch_id"],
                    "file_name": record["file_name"],
                    "old_file_name": record.get("old_file_name", record["file_name"]),
                    "canonical_file_name": record.get("canonical_file_name", record["file_name"]),
                    "probable_article_title": record.get("probable_article_title", ""),
                    "probable_author": record.get("probable_author", ""),
                    "old_path_stub": record.get("old_path_stub", record["path_stub"]),
                    "new_path_stub_or_repo_path": record.get(
                        "new_path_stub_or_repo_path",
                        record["ocr_text_path"],
                    ),
                    "page_marker": "",
                    "hit_type": "citation_reference_seed",
                    "matched_marker": matched_marker,
                    "short_context": citation_row.get("normalized_source_reference", "")[:180],
                    "language_scope_guess": record["language_scope_guess"],
                    "burmese_relevance_guess": burmese_relevance_guess(record["language_scope_guess"]),
                    "priority": priority_for_hit("citation_reference_seed", record["language_scope_guess"]),
                    "next_action": next_action_for_hit("citation_reference_seed", record["language_scope_guess"]),
                    "notes": "Structured citation seed from jbrs_corpus_citation_priority_queue.tsv.",
                }
            )
    hit_rows.sort(key=lambda row: (row["local_file_id"], row["page_marker"], row["hit_type"], row["matched_marker"]))
    deduped: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for row in hit_rows:
        if row["hit_id"] in seen_ids:
            continue
        seen_ids.add(row["hit_id"])
        deduped.append(row)
    return deduped


def build_top_extraction_candidate_rows(
    exported_records: list[dict[str, str]],
    hit_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    citation_rows: list[dict[str, str]],
    limit: int = CANDIDATE_REPORT_LIMIT,
) -> list[dict[str, str]]:
    manifest_by_local_file_id = {row["local_file_id"]: row for row in manifest_rows}
    hits_by_local_file_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in hit_rows:
        hits_by_local_file_id[row["local_file_id"]].append(row)
    citation_rows_by_local_file_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in citation_rows:
        local_file_id = row.get("candidate_local_file_id", "")
        if local_file_id:
            citation_rows_by_local_file_id[local_file_id].append(row)

    scope_rank = {
        "Burmese": 6,
        "Mixed Burmese/Pali": 6,
        "mixed_or_uncertain": 4,
        "Mon": 3,
        "Pyu": 2,
        "Pali": 1,
        "non_burmese_relevant_context": 0,
    }
    inscription_class_rank = {
        "direct_inscription_translation": 6,
        "direct_inscription_text": 5,
        "inscription_commentary_or_citation": 4,
        "language_history_or_epigraphy": 3,
        "general_burmese_text_translation": 2,
        "non_burmese_inscription_context": 1,
        "uncertain": 0,
    }
    ranked_candidates: list[tuple[tuple[int, ...], dict[str, str]]] = []
    for record in exported_records:
        local_file_id = record["local_file_id"]
        local_hits = hits_by_local_file_id.get(local_file_id, [])
        if not local_hits:
            continue
        hit_type_counts = Counter(row["hit_type"] for row in local_hits)
        marker_counts = Counter(row["matched_marker"] for row in local_hits if row.get("matched_marker", ""))
        page_scores = Counter()
        for row in local_hits:
            page_marker = row.get("page_marker", "")
            if not page_marker:
                continue
            page_scores[page_marker] += {
                "citation_reference_seed": 5,
                "translation_marker": 4,
                "text_marker": 3,
                "inscription_marker": 2,
            }.get(row["hit_type"], 1)
        manifest_row = manifest_by_local_file_id.get(local_file_id, {})
        is_article_level = boolish(manifest_row.get("is_article_split_pdf", ""))
        is_whole_volume = boolish(manifest_row.get("is_whole_issue_or_volume", ""))
        translation_hit_count = hit_type_counts["translation_marker"]
        text_hit_count = hit_type_counts["text_marker"]
        inscription_hit_count = hit_type_counts["inscription_marker"]
        citation_hits = citation_rows_by_local_file_id.get(local_file_id, [])
        relevance_class = inscriptional_relevance_class(
            record=record,
            manifest_row=manifest_row,
            hit_type_counts=hit_type_counts,
            marker_counts=marker_counts,
            citation_hits=citation_hits,
        )
        score = (
            inscription_class_rank[relevance_class],
            scope_rank.get(record["language_scope_guess"], 0),
            1 if translation_hit_count and inscription_hit_count else 0,
            translation_hit_count,
            1 if translation_hit_count and text_hit_count else 0,
            inscription_hit_count,
            text_hit_count,
            1 if is_article_level else 0,
            1 if citation_hits else 0,
            0 if is_whole_volume else 1,
            -intish(record.get("year", ""), default=0),
        )
        reason_parts = [relevance_class, record["language_scope_guess"]]
        if translation_hit_count:
            reason_parts.append(f"{translation_hit_count} translation hits")
        if inscription_hit_count:
            reason_parts.append(f"{inscription_hit_count} inscription hits")
        if text_hit_count:
            reason_parts.append(f"{text_hit_count} text hits")
        if is_article_level:
            reason_parts.append("article-level PDF")
        if citation_hits:
            reason_parts.append("corpus-citation priority")
        recommended_next_action = (
            "queue_for_structured_extraction_review"
            if record["language_scope_guess"] in {"Burmese", "Mixed Burmese/Pali"} and translation_hit_count
            else "review_source_text_boundaries"
            if record["language_scope_guess"] in {"Burmese", "Mixed Burmese/Pali"} and (text_hit_count or inscription_hit_count)
            else "keep_searchable_outside_burmese_coverage"
            if record["language_scope_guess"] == "Pali"
            else "review_for_non_burmese_epigraphic_context"
            if record["language_scope_guess"] in {"Mon", "Pyu"}
            else "manual_scope_review_before_extraction"
        )
        notes: list[str] = []
        if citation_hits:
            notes.append(
                "citation_priority="
                + ",".join(sorted({row.get("priority", "") for row in citation_hits if row.get("priority", "")}))
            )
        if is_whole_volume:
            notes.append("whole_volume_or_issue")
        strongest_markers = ", ".join(
            f"{marker} x{count}" for marker, count in marker_counts.most_common(4)
        )
        sample_pages = ", ".join(page for page, _ in page_scores.most_common(3))
        ranked_candidates.append(
            (
                score,
                {
                    "candidate_rank": "",
                    "local_file_id": local_file_id,
                    "batch_id": record["batch_id"],
                    "file_name": record["file_name"],
                    "old_file_name": record.get("old_file_name", record["file_name"]),
                    "canonical_file_name": record.get("canonical_file_name", record["file_name"]),
                    "probable_article_title": record.get("probable_article_title", ""),
                    "probable_author": record.get("probable_author", ""),
                    "year": record["year"],
                    "old_path_stub": record.get("old_path_stub", record["path_stub"]),
                    "new_path_stub_or_repo_path": record.get(
                        "new_path_stub_or_repo_path",
                        record["ocr_text_path"],
                    ),
                    "ocr_text_path": record["ocr_text_path"],
                    "language_scope_guess": record["language_scope_guess"],
                    "burmese_relevance_guess": burmese_relevance_guess(record["language_scope_guess"]),
                    "inscriptional_relevance_class": relevance_class,
                    "translation_hit_count": str(translation_hit_count),
                    "text_hit_count": str(text_hit_count),
                    "inscription_hit_count": str(inscription_hit_count),
                    "strongest_markers": strongest_markers,
                    "sample_pages": sample_pages,
                    "reason_for_priority": "; ".join(reason_parts),
                    "recommended_next_action": recommended_next_action,
                    "notes": "; ".join(notes),
                },
            )
        )
    ranked_candidates.sort(
        key=lambda item: (
            -item[0][0],
            -item[0][1],
            -item[0][2],
            -item[0][3],
            -item[0][4],
            -item[0][5],
            -item[0][6],
            -item[0][7],
            -item[0][8],
            -item[0][9],
            -item[0][10],
            item[1]["file_name"],
            item[1]["local_file_id"],
        )
    )
    grouped_candidates: dict[str, list[tuple[tuple[int, ...], dict[str, str]]]] = defaultdict(list)
    for score, row in ranked_candidates:
        grouped_candidates[normalize_searchable_text(row["file_name"]).strip()].append((score, row))

    def local_id_preference(local_file_id: str) -> tuple[int, int]:
        return (
            1 if re.match(r"^\d{4}-", local_file_id) else 0,
            0 if re.search(r"[0-9a-f]{8,}$", local_file_id) else 1,
        )

    unique_ranked_candidates: list[tuple[tuple[int, ...], dict[str, str]]] = []
    for grouped_rows in grouped_candidates.values():
        best_score, best_row = max(
            grouped_rows,
            key=lambda item: (
                local_id_preference(item[1]["local_file_id"]),
                item[0],
            ),
        )
        unique_ranked_candidates.append((best_score, best_row))

    unique_ranked_candidates.sort(
        key=lambda item: (
            -item[0][0],
            -item[0][1],
            -item[0][2],
            -item[0][3],
            -item[0][4],
            -item[0][5],
            -item[0][6],
            -item[0][7],
            -item[0][8],
            -item[0][9],
            -item[0][10],
            item[1]["file_name"],
            item[1]["local_file_id"],
        )
    )
    candidate_rows = [row for _, row in unique_ranked_candidates[:limit]]
    for rank, row in enumerate(candidate_rows, start=1):
        row["candidate_rank"] = str(rank)
        if rank <= 20:
            row["notes"] = "; ".join(part for part in [row["notes"], "top_20_priority"] if part)
    return candidate_rows


def build_top_inscription_extraction_candidate_rows(
    top_candidate_rows: list[dict[str, str]],
    limit: int = INSCRIPTION_CANDIDATE_REPORT_LIMIT,
) -> list[dict[str, str]]:
    inscription_class_rank = {
        "direct_inscription_translation": 6,
        "direct_inscription_text": 5,
        "inscription_commentary_or_citation": 4,
        "language_history_or_epigraphy": 3,
        "non_burmese_inscription_context": 2,
        "uncertain": 1,
        "general_burmese_text_translation": 0,
    }
    scope_rank = {
        "Burmese": 3,
        "Mixed Burmese/Pali": 3,
        "mixed_or_uncertain": 2,
        "Mon": 1,
        "Pyu": 1,
        "Pali": 0,
        "non_burmese_relevant_context": 0,
    }
    ranked_rows = sorted(
        top_candidate_rows,
        key=lambda row: (
            -inscription_class_rank[row["inscriptional_relevance_class"]],
            -scope_rank[row["language_scope_guess"]],
            -intish(row["translation_hit_count"]),
            -intish(row["inscription_hit_count"]),
            -intish(row["text_hit_count"]),
            0 if "whole_volume_or_issue" in row["notes"] else 1,
            1 if "citation_priority=" in row["notes"] else 0,
            row["file_name"],
            row["local_file_id"],
        ),
    )
    inscription_rows = [dict(row) for row in ranked_rows[:limit]]
    for rank, row in enumerate(inscription_rows, start=1):
        row["candidate_rank"] = str(rank)
        row["notes"] = "; ".join(
            part for part in [row["notes"], "inscription_top_20_priority"] if part
        )
    return inscription_rows


def upsert_tsv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    key_field: str,
) -> None:
    existing = {
        row[key_field]: row for row in read_tsv(path)
    } if path.exists() else {}
    for row in rows:
        existing[row[key_field]] = row
    ordered_rows = [existing[key] for key in sorted(existing)]
    write_tsv(path, ordered_rows, fieldnames)


def refresh_pilot_summary(
    batch_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    citation_rows: list[dict[str, str]],
) -> None:
    raw_reference_rows = read_tsv(JBRS_REFERENCE_HUNT_RAW_PATH)
    target_rows = read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_PATH)
    target_review_rows = (
        read_tsv(JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH)
        if JBRS_ARTICLE_REFERENCE_TARGETS_REVIEW_PATH.exists()
        else []
    )
    reviewed_target_rows = apply_article_target_reviews(target_rows, target_review_rows)
    candidate_rows = read_tsv(JBRS_TRANSLATION_CANDIDATE_LOG_PATH) if JBRS_TRANSLATION_CANDIDATE_LOG_PATH.exists() else []
    candidate_review_rows = (
        read_tsv(JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH)
        if JBRS_TRANSLATION_CANDIDATE_REVIEW_PATH.exists()
        else []
    )
    excerpt_review_rows = (
        read_tsv(JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH)
        if JBRS_EMBEDDED_TRANSLATION_EXCERPT_REVIEW_PATH.exists()
        else []
    )
    followup_source_lead_rows = (
        read_tsv(JBRS_FOLLOWUP_SOURCE_LEADS_PATH)
        if JBRS_FOLLOWUP_SOURCE_LEADS_PATH.exists()
        else []
    )
    ocr_quality_review_rows = (
        read_tsv(JBRS_OCR_QUALITY_REVIEW_PATH)
        if JBRS_OCR_QUALITY_REVIEW_PATH.exists()
        else []
    )
    extraction_plan_rows = (
        read_tsv(JBRS_STRUCTURED_EXTRACTION_PLAN_PATH)
        if JBRS_STRUCTURED_EXTRACTION_PLAN_PATH.exists()
        else []
    )
    extracted_translation_unit_rows = (
        read_tsv(JBRS_EXTRACTED_TRANSLATION_UNITS_PATH)
        if JBRS_EXTRACTED_TRANSLATION_UNITS_PATH.exists()
        else []
    )
    extracted_source_text_unit_rows = (
        read_tsv(JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH)
        if JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH.exists()
        else []
    )
    write_summary(
        JBRS_PILOT_SUMMARY_PATH,
        build_pilot_summary(
            raw_reference_rows,
            reviewed_target_rows,
            manifest_rows,
            match_rows,
            batch_rows,
            status_rows,
            candidate_rows,
            candidate_review_rows,
            excerpt_review_rows,
            followup_source_lead_rows,
            ocr_quality_review_rows,
            citation_rows,
            extraction_plan_rows,
            extracted_translation_unit_rows,
            extracted_source_text_unit_rows,
        ),
    )


def run_production_batch(args: argparse.Namespace) -> int:
    batch_rows = read_tsv(args.batch_plan)
    status_rows = read_tsv(args.status_log)
    manifest_rows = read_tsv(args.manifest)
    match_rows = read_tsv(args.reference_match)
    citation_rows = read_tsv(args.citation_priority_queue)
    exit_code = 0
    selected_rows: list[dict[str, str]] = []
    selection_context = {"skipped_batch_count": 0, "deferred_count": 0}
    if not args.rebuild_indexes_only:
        selected_rows, selection_context = select_production_batch_rows(
            batch_rows=batch_rows,
            status_rows=status_rows,
            manifest_rows=manifest_rows,
            match_rows=match_rows,
            citation_rows=citation_rows,
            limit=args.limit,
        )
        selected_batch_ids = [row["batch_id"] for row in selected_rows]
        ocr_args = SimpleNamespace(
            batch_plan=args.batch_plan,
            status_log=args.status_log,
            runtime_path_cache=args.runtime_path_cache,
            local_output_root=args.local_output_root,
            preflight_report=args.preflight_report,
            batch_id=selected_batch_ids,
            limit=args.limit,
            execute=args.execute,
            dry_run=args.dry_run,
            rerun_failed=False,
            force_rerun_completed=False,
        )
        if selected_batch_ids:
            exit_code = ocr.run_selected_batches(ocr_args)
        refreshed_status_rows = read_tsv(args.status_log)
        load_repo_export_records(
            status_rows=refreshed_status_rows,
            batch_rows=batch_rows,
            manifest_rows=manifest_rows,
            local_output_root=args.local_output_root,
            repo_text_root=args.repo_text_root,
            repo_metadata_root=args.repo_metadata_root,
        )
    else:
        selected_batch_ids = []
        refreshed_status_rows = status_rows

    exported_records = load_committed_ocr_records(
        batch_rows=batch_rows,
        status_rows=refreshed_status_rows,
        manifest_rows=manifest_rows,
        repo_text_root=args.repo_text_root,
        repo_metadata_root=args.repo_metadata_root,
    )
    initial_hit_rows = build_translation_hit_rows(exported_records, citation_rows)
    initial_ranked_candidate_rows = build_top_extraction_candidate_rows(
        exported_records=exported_records,
        hit_rows=initial_hit_rows,
        manifest_rows=manifest_rows,
        citation_rows=citation_rows,
        limit=max(len(exported_records), CANDIDATE_REPORT_LIMIT),
    )
    initial_top_candidate_rows = initial_ranked_candidate_rows[:CANDIDATE_REPORT_LIMIT]
    initial_top_inscription_candidate_rows = build_top_inscription_extraction_candidate_rows(
        initial_ranked_candidate_rows,
        limit=min(INSCRIPTION_CANDIDATE_REPORT_LIMIT, len(initial_ranked_candidate_rows)),
    )
    phase1_scope_local_ids = rename_scope_local_file_ids(
        initial_top_candidate_rows,
        initial_top_inscription_candidate_rows,
    )
    renaming_plan_rows, alias_map_rows = build_file_renaming_rows(
        exported_records=exported_records,
        manifest_rows=manifest_rows,
        phase1_scope_local_ids=phase1_scope_local_ids,
    )
    apply_repo_ocr_renaming_plan(renaming_plan_rows, alias_map_rows)
    exported_records = load_committed_ocr_records(
        batch_rows=batch_rows,
        status_rows=refreshed_status_rows,
        manifest_rows=manifest_rows,
        repo_text_root=args.repo_text_root,
        repo_metadata_root=args.repo_metadata_root,
    )
    index_rows = [
        {field: record[field] for field in JBRS_OCR_TEXT_INDEX_FIELDS}
        for record in exported_records
    ]
    write_tsv(args.ocr_text_index, index_rows, JBRS_OCR_TEXT_INDEX_FIELDS)

    hit_rows = build_translation_hit_rows(exported_records, citation_rows)
    write_tsv(args.translation_hit_index, hit_rows, JBRS_OCR_TRANSLATION_HIT_INDEX_FIELDS)
    ranked_candidate_rows = build_top_extraction_candidate_rows(
        exported_records=exported_records,
        hit_rows=hit_rows,
        manifest_rows=manifest_rows,
        citation_rows=citation_rows,
        limit=max(len(exported_records), CANDIDATE_REPORT_LIMIT),
    )
    top_candidate_rows = ranked_candidate_rows[:CANDIDATE_REPORT_LIMIT]
    top_inscription_candidate_rows = build_top_inscription_extraction_candidate_rows(
        ranked_candidate_rows,
        limit=min(INSCRIPTION_CANDIDATE_REPORT_LIMIT, len(ranked_candidate_rows)),
    )
    write_tsv(args.top_candidates_path, top_candidate_rows, JBRS_OCR_TOP_EXTRACTION_CANDIDATES_FIELDS)
    write_tsv(
        args.top_inscription_candidates_path,
        top_inscription_candidate_rows,
        JBRS_OCR_TOP_INSCRIPTION_EXTRACTION_CANDIDATES_FIELDS,
    )
    renaming_plan_rows, alias_map_rows = build_file_renaming_rows(
        exported_records=exported_records,
        manifest_rows=manifest_rows,
        phase1_scope_local_ids=phase1_scope_local_ids,
    )
    write_tsv(args.file_renaming_plan, renaming_plan_rows, JBRS_FILE_RENAMING_PLAN_FIELDS)
    write_tsv(args.file_alias_map, alias_map_rows, JBRS_FILE_ALIAS_MAP_FIELDS)
    args.production_summary_path.write_text(
        json.dumps(
            build_jbrs_ocr_production_summary(
                text_index_rows=index_rows,
                translation_hit_rows=hit_rows,
                top_candidate_rows=top_candidate_rows,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    refresh_pilot_summary(
        batch_rows=batch_rows,
        status_rows=refreshed_status_rows,
        manifest_rows=manifest_rows,
        match_rows=match_rows,
        citation_rows=citation_rows,
    )

    if not args.rebuild_indexes_only:
        selected_batch_ids_set = set(selected_batch_ids)
        completed_count = sum(
            1
            for row in refreshed_status_rows
            if row.get("batch_id") in selected_batch_ids_set and row.get("status") == "completed"
        )
        failed_count = sum(
            1
            for row in refreshed_status_rows
            if row.get("batch_id") in selected_batch_ids_set and row.get("status") == "failed"
        )
        run_id = f"jbrs-prod-ocr-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        run_row = {
            "run_id": run_id,
            "run_date": datetime.now(UTC).date().isoformat(),
            "selection_rule": args.selection_rule,
            "selected_count": str(len(selected_rows)),
            "completed_count": str(completed_count),
            "failed_count": str(failed_count),
            "skipped_count": str(selection_context["skipped_batch_count"]),
            "output_text_root": relative_stub(args.repo_text_root),
            "metadata_root": relative_stub(args.repo_metadata_root),
            "notes": (
                ("dry_run; " if args.dry_run else "")
                + f"deferred_ready_rows={selection_context['deferred_count']}; "
                + f"selected_batch_ids={','.join(selected_batch_ids[:10])}"
                + ("..." if len(selected_batch_ids) > 10 else "")
            ),
        }
        upsert_tsv(
            args.production_run_log,
            [run_row],
            JBRS_OCR_PRODUCTION_RUN_LOG_FIELDS,
            key_field="run_id",
        )
    return exit_code


def main() -> int:
    args = parse_args()
    exit_code = run_production_batch(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
