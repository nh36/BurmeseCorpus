#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from corpus_common import ensure_parent, read_tsv, write_tsv
import ocr_jbrs_google_vision as ocr
from jbrs_workflow_common import (
    DEFAULT_LOCAL_OUTPUT_ROOT,
    DEFAULT_PREFLIGHT_REPORT_PATH,
    DEFAULT_RUNTIME_PATH_CACHE,
    JBRS_BURMESE_RELEVANCE_GUESS_VALUES,
    JBRS_CORPUS_CITATION_PRIORITY_QUEUE_PATH,
    JBRS_DIRECTORY,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_LANGUAGE_SCOPE_VALUES,
    JBRS_OCR_PRODUCTION_RUN_LOG_FIELDS,
    JBRS_OCR_PRODUCTION_RUN_LOG_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    JBRS_OCR_TEXT_INDEX_FIELDS,
    JBRS_OCR_TEXT_INDEX_PATH,
    JBRS_OCR_TRANSLATION_HIT_INDEX_FIELDS,
    JBRS_OCR_TRANSLATION_HIT_INDEX_PATH,
    JBRS_REFERENCE_FILE_MATCH_PATH,
    JBRS_WORKING_OCR_METADATA_ROOT,
    JBRS_WORKING_OCR_TEXT_ROOT,
    batch_is_selectable_for_ocr,
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
]
SELECTION_TERM_WEIGHTS = {
    "translation": 6,
    "inscription": 6,
    "inscriptions": 6,
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
PAGE_MARKER_PATTERN = re.compile(r"^\[\[page (?P<page>\d+)\]\]$", re.MULTILINE)


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
    parser.add_argument("--preflight-report", type=Path, default=DEFAULT_PREFLIGHT_REPORT_PATH)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--selection-rule", default="citation-match then keyword/article priority")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
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


def marker_present(haystack: str, marker: str) -> bool:
    return marker.casefold() in haystack


def text_has_any_marker(haystack: str, markers: list[str]) -> bool:
    return any(marker_present(haystack, marker) for marker in markers)


def collect_keyword_hits(*values: str) -> list[str]:
    haystack = normalize_text(" ".join(value for value in values if value))
    return [term for term in SELECTION_TERMS if marker_present(haystack, term)]


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
        keyword_hits = collect_keyword_hits(
            batch_row.get("file_name", ""),
            manifest_row.get("file_name", ""),
            manifest_row.get("probable_title_from_filename", ""),
        )
        has_translation_keyword = any(term in {"translation", "text", "pali", "burmese", "old burmese"} for term in keyword_hits)
        has_inscription_keyword = any(
            term in {"inscription", "inscriptions", "ananda", "shwegugyi", "pyu", "mon", "talaing"}
            for term in keyword_hits
        )
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
            1 if has_translation_keyword else 0,
            1 if has_inscription_keyword else 0,
            keyword_score,
            len(keyword_hits),
            0 if multiple_candidate_match else 1,
            batch_priority_rank(batch_row.get("ocr_priority", "")),
            1 if is_article else 0,
            0 if is_whole_volume else 1,
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
    haystack = normalize_text(
        " ".join(
            [
                manifest_row.get("file_name", ""),
                manifest_row.get("probable_title_from_filename", ""),
                manifest_row.get("folder_context", ""),
                batch_row.get("file_name", ""),
                text,
            ]
        )
    )
    has_burmese = text_has_any_marker(haystack, BURMESE_MARKERS)
    has_pali = text_has_any_marker(haystack, PALI_MARKERS)
    has_mon = text_has_any_marker(haystack, MON_MARKERS)
    has_pyu = text_has_any_marker(haystack, PYU_MARKERS)
    if has_burmese and has_pali:
        return "Mixed Burmese/Pali"
    if has_burmese:
        return "Burmese"
    if has_pali:
        return "Pali"
    if has_mon:
        return "Mon"
    if has_pyu:
        return "Pyu"
    if text_has_any_marker(haystack, TRANSLATION_MARKERS + TEXT_MARKERS + INSCRIPTION_MARKERS):
        return "mixed_or_uncertain"
    if text_has_any_marker(haystack, CONTEXT_MARKERS):
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
                "year": str(metadata["year"]),
                "path_stub": metadata["path_stub"],
                "ocr_text_path": relative_stub(repo_text_path),
                "metadata_path": relative_stub(repo_metadata_path),
                "pages_completed": str(metadata["pages_completed"]),
                "ocr_status": "completed",
                "language_scope_guess": language_scope,
                "notes": metadata["notes"],
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


def run_production_batch(args: argparse.Namespace) -> int:
    batch_rows = read_tsv(args.batch_plan)
    status_rows = read_tsv(args.status_log)
    manifest_rows = read_tsv(args.manifest)
    match_rows = read_tsv(args.reference_match)
    citation_rows = read_tsv(args.citation_priority_queue)
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
    exit_code = 0
    if selected_batch_ids:
        exit_code = ocr.run_selected_batches(ocr_args)

    refreshed_status_rows = read_tsv(args.status_log)
    exported_records = load_repo_export_records(
        status_rows=refreshed_status_rows,
        batch_rows=batch_rows,
        manifest_rows=manifest_rows,
        local_output_root=args.local_output_root,
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
