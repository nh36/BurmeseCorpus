from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bibtex_common import normalize_for_match, surname_token, title_keyword_tokens
from corpus_common import REPO_ROOT, ensure_parent, read_tsv, write_tsv


JBRS_DIRECTORY = REPO_ROOT / "data/working/bibliography/jbrs"
JBRS_REFERENCE_HUNT_PATH = JBRS_DIRECTORY / "jbrs_reference_hunt.tsv"
JBRS_LOCAL_FILE_MANIFEST_PATH = JBRS_DIRECTORY / "jbrs_local_file_manifest.tsv"
JBRS_REFERENCE_FILE_MATCH_PATH = JBRS_DIRECTORY / "jbrs_reference_file_match.tsv"
JBRS_OCR_BATCH_PLAN_PATH = JBRS_DIRECTORY / "jbrs_ocr_batch_plan.tsv"
JBRS_OCR_STATUS_LOG_PATH = JBRS_DIRECTORY / "jbrs_ocr_status_log.tsv"
JBRS_TRANSLATION_CANDIDATE_LOG_PATH = JBRS_DIRECTORY / "jbrs_translation_candidate_log.tsv"
JBRS_PILOT_SUMMARY_PATH = JBRS_DIRECTORY / "jbrs_pilot_summary.json"
JBRS_README_PATH = JBRS_DIRECTORY / "README.md"

SOURCE_LIBRARY_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/source_library_manifest.tsv"
LOCAL_FILE_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/local_file_manifest.tsv"
OCR_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv"
OCR_TEXT_INDEX_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv"

DEFAULT_LOCAL_OUTPUT_ROOT = REPO_ROOT / "data_local/ocr/jbrs"
DEFAULT_RUNTIME_PATH_CACHE = DEFAULT_LOCAL_OUTPUT_ROOT / "manifest/jbrs_runtime_path_map.json"

REFERENCE_HUNT_FIELDS = [
    "reference_id",
    "source_file",
    "source_work_key_if_known",
    "matched_reference_text_short",
    "normalized_journal_title",
    "volume",
    "issue",
    "year",
    "page_range",
    "author",
    "article_title",
    "inscription_or_topic_keywords",
    "reference_confidence",
    "needs_manual_bibliographic_cleanup",
    "notes",
]

LOCAL_FILE_MANIFEST_FIELDS = [
    "local_file_id",
    "path_stub_or_redacted_path",
    "file_name",
    "extension",
    "file_size_bytes",
    "modified_date",
    "probable_author_from_path",
    "probable_title_from_filename",
    "probable_year_from_filename",
    "probable_volume_issue_from_filename",
    "folder_context",
    "is_probable_jbrs",
    "manifest_confidence",
    "needs_manual_review",
    "notes",
]

REFERENCE_FILE_MATCH_FIELDS = [
    "reference_id",
    "local_file_id",
    "match_status",
    "match_confidence",
    "match_basis",
    "author_match",
    "title_match",
    "year_match",
    "volume_issue_match",
    "path_context_match",
    "candidate_file_name",
    "candidate_path_stub",
    "next_action",
    "notes",
]

OCR_BATCH_PLAN_FIELDS = [
    "batch_id",
    "local_file_id",
    "file_name",
    "path_stub",
    "volume",
    "issue",
    "year",
    "page_count_estimate",
    "ocr_priority",
    "ocr_scope",
    "ocr_engine",
    "output_basename",
    "expected_output_format",
    "metadata_sidecar_path",
    "status",
    "blocked_by",
    "notes",
]

OCR_STATUS_LOG_FIELDS = [
    "ocr_job_id",
    "batch_id",
    "local_file_id",
    "file_name",
    "ocr_engine",
    "ocr_scope",
    "status",
    "pages_submitted",
    "pages_completed",
    "output_path_stub",
    "metadata_sidecar_stub",
    "error_type",
    "error_message_short",
    "created_at",
    "updated_at",
    "notes",
]

TRANSLATION_CANDIDATE_FIELDS = [
    "candidate_id",
    "local_file_id",
    "reference_id_if_any",
    "journal",
    "volume",
    "issue",
    "year",
    "article_title",
    "author",
    "page_range_or_page",
    "candidate_type",
    "evidence_marker",
    "short_evidence_snippet",
    "contains_translation_candidate",
    "contains_edition_or_transliteration_candidate",
    "contains_commentary_only",
    "confidence",
    "next_action",
    "notes",
]

SHORT_SNIPPET_LIMIT = 220
ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")
JOURNAL_TITLE = "Journal of the Burma Research Society"
JOURNAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bjournal of the burma research society\b",
        r"\bjournal of burma research society\b",
        r"\bj\.?\s*b\.?\s*r\.?\s*s\.?\b",
        r"\bjournal of the burma research soc(?:iety)?\b",
        r"\bj\.?\s*burma\s+res\.?\s+soc\.?\b",
        r"\bburma res\.?\s+soc\.?\b",
        r"\bburma research society\b",
        r"\bjour\.?\s*burma research soc\.?\b",
    ]
]
VOLUME_PATTERN = re.compile(r"\b(?:vol(?:ume)?\.?|v\.)\s*([ivxlcdm0-9]+)\b", re.IGNORECASE)
ISSUE_PATTERN = re.compile(r"\b(?:part|pt\.?|issue|no\.?|number)\s*([ivxlcdm0-9]+)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(18|19|20)\d{2}\b")
PAGE_RANGE_PATTERN = re.compile(r"\bpp?\.?\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)", re.IGNORECASE)
QUOTED_TITLE_PATTERN = re.compile(r"[\"“](.+?)[\"”]")
PAGE_MARKER_PATTERN = re.compile(r"\[\[page\s+([0-9]+)\]\]", re.IGNORECASE)

KNOWN_AUTHORS = [
    ("Charles Duroiselle", ["duroiselle", "charles duroiselle"]),
    ("Taw Sein Ko", ["taw sein ko", "tawseinko"]),
    ("Emil Forchhammer", ["forchhammer", "emil forchhammer"]),
    ("U Pe Maung Tin", ["pe maung tin", "pemaungtin", "u pe maung tin"]),
    ("G. H. Luce", ["g. h. luce", "g h luce", "luce"]),
    ("U Tun Nyein", ["tun nyein", "u tun nyein", "tunnyein"]),
    ("U E Maung", ["u e maung", "ue maung", "uemaung"]),
    ("C. O. Blagden", ["blagden", "c. o. blagden", "co blagden"]),
    ("Ba Shin", ["ba shin", "bashin"]),
    ("Than Tun", ["than tun", "thantun"]),
    ("Hla Pe", ["hla pe", "hlape"]),
    ("Htin Aung", ["htin aung", "htinaung"]),
    ("D. G. E. Hall", ["d. g. e. hall", "d g e hall", "hall"]),
    ("J. A. Stewart", ["j. a. stewart", "j a stewart", "stewart"]),
]
KEYWORD_MARKERS = [
    "inscription",
    "pagan",
    "pinya",
    "ava",
    "myazedi",
    "pyu",
    "mon",
    "talaing",
    "old burmese",
    "pali",
    "transliteration",
    "translation",
    "plate",
    "pegu",
]
TRANSLATION_MARKERS = [
    "translation",
    "translated by",
    "text and translation",
    "translation of",
    "the inscription reads",
    "the inscription says",
]
EDITION_MARKERS = [
    "inscription no.",
    "plate",
    "text",
    "transliteration",
    "edited by",
    "pagan inscription",
    "mon inscription",
    "talaing inscription",
    "old burmese",
    "pali",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def bool_string(value: bool) -> str:
    return "true" if value else "false"


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def truncate_short(value: str | None, *, limit: int = SHORT_SNIPPET_LIMIT) -> str:
    text = normalize_space(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_for_match(value)).strip("-")
    return slug or "jbrs"


def safe_path_stub(path_value: str | None, *, keep_parts: int = 4) -> str:
    raw = normalize_space(path_value)
    if not raw:
        return ""
    raw = raw.split(":", 1)[-1] if ":" in raw and not raw.startswith("/") else raw
    raw = raw.replace("\\", "/")
    parts = [part for part in raw.split("/") if part]
    if len(parts) <= keep_parts:
        return "/".join(parts)
    return "/".join(parts[-keep_parts:])


def last_page_number(page_scope: str | None) -> str:
    value = normalize_space(page_scope)
    if not value:
        return ""
    total = 0
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = [piece.strip() for piece in token.split("-", 1)]
            if start_text.isdigit() and end_text.isdigit():
                total += int(end_text) - int(start_text) + 1
                continue
        if token.isdigit():
            total += 1
    return str(total or "")


def contains_jbrs_marker(value: str | None) -> bool:
    text = value or ""
    return any(pattern.search(text) for pattern in JOURNAL_PATTERNS)


def choose_best_descriptor(values: list[str]) -> str:
    best = ""
    best_score = -1
    for value in values:
        text = normalize_space(value)
        if not text:
            continue
        score = len(re.findall(r"[A-Za-z]", text))
        if contains_jbrs_marker(text):
            score += 15
        if YEAR_PATTERN.search(text):
            score += 3
        if re.search(r"[A-Za-z]{4,}.*[A-Za-z]{4,}", text):
            score += 5
        if score > best_score:
            best = text
            best_score = score
    return best


def detect_author(value: str | None) -> str:
    text = normalize_for_match(value)
    for canonical, variants in KNOWN_AUTHORS:
        for variant in variants:
            if normalize_for_match(variant) in text:
                return canonical
    return ""


def detect_title(value: str | None) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    quoted = QUOTED_TITLE_PATTERN.search(text)
    if quoted:
        return truncate_short(quoted.group(1), limit=120)
    journal_match = re.search(r"\((?:JBRS|J\.?B\.?R\.?S\.?)\)\s*(.+)$", text, re.IGNORECASE)
    if journal_match:
        return truncate_short(journal_match.group(1), limit=120)
    author = detect_author(text)
    if author and JOURNAL_PATTERNS[0].search(text):
        author_pattern = re.escape(author.split()[-1])
        match = re.search(author_pattern + r"[\s,:-]+(.+?)\b(?:JBRS|J\.?B\.?R\.?S\.?)\b", text, re.IGNORECASE)
        if match:
            return truncate_short(match.group(1).strip(" ,.;:-"), limit=120)
    return ""


def extract_keywords(value: str | None) -> str:
    text = normalize_for_match(value)
    found: list[str] = []
    for marker in KEYWORD_MARKERS:
        normalized_marker = normalize_for_match(marker)
        if normalized_marker in text and marker not in found:
            found.append(marker)
    return "; ".join(found[:5])


def parse_reference_bits(value: str | None) -> tuple[str, str, str, str]:
    text = normalize_space(value)
    volume = ""
    issue = ""
    year = ""
    page_range = ""
    volume_match = VOLUME_PATTERN.search(text)
    if volume_match:
        volume = volume_match.group(1)
    issue_match = ISSUE_PATTERN.search(text)
    if issue_match:
        issue = issue_match.group(1)
    year_match = YEAR_PATTERN.search(text)
    if year_match:
        year = year_match.group(0)
    page_match = PAGE_RANGE_PATTERN.search(text)
    if page_match:
        page_range = page_match.group(1).replace(" ", "")
    return volume, issue, year, page_range


def reference_confidence(author: str, article_title: str, year: str, volume: str, page_range: str) -> str:
    score = 0
    if author:
        score += 2
    if article_title:
        score += 2
    if year:
        score += 1
    if volume:
        score += 1
    if page_range:
        score += 1
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def iter_reference_source_files() -> list[Path]:
    candidates: list[Path] = []
    explicit_files = [
        REPO_ROOT / "data/working/bibliography/bibtex_authority/source_work_authority.tsv",
        REPO_ROOT / "data/working/bibliography/bibtex_authority/bibliography_authority.bib",
        REPO_ROOT / "data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv",
        REPO_ROOT / "data/working/bibliography/translation_source_discovery_plan.tsv",
        OCR_TEXT_INDEX_PATH,
        REPO_ROOT / "docs/phase2_bibtex_authority.md",
    ]
    for path in explicit_files:
        if path.exists():
            candidates.append(path)
    discovery_dir = REPO_ROOT / "data/working/bibliography/translation_source_discovery"
    if discovery_dir.exists():
        for path in sorted(discovery_dir.rglob("*")):
            if path.is_file() and path.suffix.casefold() in {".tsv", ".md", ".json"}:
                candidates.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path not in seen and JBRS_DIRECTORY not in path.parents:
            unique.append(path)
            seen.add(path)
    return unique


def build_reference_hunt_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    reference_index = 0
    for path in iter_reference_source_files():
        relative = str(path.relative_to(REPO_ROOT))
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not contains_jbrs_marker(raw_line):
                continue
            text = truncate_short(raw_line)
            volume, issue, year, page_range = parse_reference_bits(raw_line)
            author = detect_author(raw_line)
            article_title = detect_title(raw_line)
            reference_index += 1
            rows.append(
                {
                    "reference_id": f"jbrs-ref-{reference_index:04d}",
                    "source_file": f"{relative}:{line_number}",
                    "source_work_key_if_known": "",
                    "matched_reference_text_short": text,
                    "normalized_journal_title": JOURNAL_TITLE,
                    "volume": volume,
                    "issue": issue,
                    "year": year,
                    "page_range": page_range,
                    "author": author,
                    "article_title": article_title,
                    "inscription_or_topic_keywords": extract_keywords(raw_line),
                    "reference_confidence": reference_confidence(author, article_title, year, volume, page_range),
                    "needs_manual_bibliographic_cleanup": bool_string(not (author and (article_title or year or volume))),
                    "notes": "Reference hunt derived from existing repository bibliography/workspace text.",
                }
            )
    return rows


def split_manifest_paths(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def probable_title_from_descriptor(value: str | None) -> str:
    text = Path((value or "").split("/")[-1]).stem.replace("_", " ")
    text = re.sub(r"[-]+", " ", text)
    text = re.sub(r"\b(?:JBRS|JBRS|Journal of the Burma Research Society)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(18|19|20)\d{2}\b", "", text)
    text = normalize_space(text)
    if re.fullmatch(r"[0-9A-Za-z]+", text or "") and text.upper() == (text or "").upper() and len(text) <= 8:
        return ""
    return truncate_short(text, limit=120)


def probable_volume_issue_from_text(value: str | None) -> str:
    volume, issue, _year, _pages = parse_reference_bits(value)
    parts = [part for part in [f"vol. {volume}" if volume else "", f"issue/part {issue}" if issue else ""] if part]
    return " | ".join(parts)


def find_best_jbrs_source_rows() -> list[dict]:
    rows: list[dict] = []
    if SOURCE_LIBRARY_MANIFEST_PATH.exists():
        rows.extend(read_tsv(SOURCE_LIBRARY_MANIFEST_PATH))
    return rows


def _manifest_confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get((value or "").casefold(), -1)


def merge_manifest_rows(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    merged = existing.copy()
    for key, value in incoming.items():
        if not value:
            continue
        current = merged.get(key, "")
        if not current:
            merged[key] = value
            continue
        if key == "manifest_confidence":
            if _manifest_confidence_rank(value) > _manifest_confidence_rank(current):
                merged[key] = value
        elif key == "needs_manual_review":
            if current == "true" and value == "false":
                merged[key] = value
        elif key == "file_name":
            current_is_generic = bool(re.fullmatch(r"[0-9A-Za-z_-]+\.[A-Za-z0-9]+", current))
            value_is_generic = bool(re.fullmatch(r"[0-9A-Za-z_-]+\.[A-Za-z0-9]+", value))
            if current_is_generic and not value_is_generic:
                merged[key] = value
        elif key in {"probable_title_from_filename", "probable_author_from_path", "folder_context", "notes"}:
            if len(value) > len(current):
                merged[key] = value
        elif key == "path_stub_or_redacted_path":
            if len(value.split("/")) > len(current.split("/")):
                merged[key] = value
    return merged


def upsert_manifest_row(manifest_by_id: dict[str, dict[str, str]], row: dict[str, str]) -> None:
    local_file_id = row.get("local_file_id", "")
    if not local_file_id:
        return
    existing = manifest_by_id.get(local_file_id)
    manifest_by_id[local_file_id] = merge_manifest_rows(existing, row) if existing else row


def build_local_manifest_rows(
    *,
    roots: list[Path] | None = None,
    existing_source_library_path: Path = SOURCE_LIBRARY_MANIFEST_PATH,
    existing_local_manifest_path: Path = LOCAL_FILE_MANIFEST_PATH,
    existing_ocr_manifest_path: Path = OCR_MANIFEST_PATH,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    manifest_by_id: dict[str, dict[str, str]] = {}
    runtime_path_cache: dict[str, str] = {}

    if existing_source_library_path.exists():
        for row in read_tsv(existing_source_library_path):
            descriptor_candidates = split_manifest_paths(row.get("all_original_paths", "")) + [row.get("primary_original_path", ""), row.get("file_name", "")]
            descriptor = choose_best_descriptor(descriptor_candidates)
            path_text = " ".join(descriptor_candidates + [row.get("source_folder_hints", "")])
            if not contains_jbrs_marker(path_text):
                continue
            local_file_id = row.get("canonical_local_file_id", "")
            path_stub = safe_path_stub(descriptor or row.get("primary_original_path", ""))
            probable_author = detect_author(descriptor)
            probable_title = probable_title_from_descriptor(descriptor) or probable_title_from_descriptor(row.get("file_name", ""))
            probable_year = YEAR_PATTERN.search(descriptor or row.get("file_name", "") or "")
            upsert_manifest_row(
                manifest_by_id,
                {
                "local_file_id": local_file_id,
                "path_stub_or_redacted_path": path_stub,
                "file_name": row.get("file_name", ""),
                "extension": Path(row.get("file_name", "")).suffix.casefold().lstrip("."),
                "file_size_bytes": row.get("file_size", ""),
                "modified_date": "",
                "probable_author_from_path": probable_author,
                "probable_title_from_filename": probable_title,
                "probable_year_from_filename": probable_year.group(0) if probable_year else "",
                "probable_volume_issue_from_filename": probable_volume_issue_from_text(descriptor),
                "folder_context": truncate_short(row.get("source_folder_hints", ""), limit=120),
                "is_probable_jbrs": "true",
                "manifest_confidence": "high",
                "needs_manual_review": bool_string(not probable_title),
                "notes": "Derived from existing redacted source_library_manifest.tsv entry.",
                },
            )
    if existing_local_manifest_path.exists():
        for row in read_tsv(existing_local_manifest_path):
            source_text = " ".join([row.get("file_name", ""), row.get("primary_original_path", ""), row.get("all_original_paths", ""), row.get("copied_path", ""), row.get("source_folder_hints", "")])
            if not contains_jbrs_marker(source_text):
                continue
            label = row.get("copied_path", "") or row.get("primary_original_path", "") or row.get("all_original_paths", "") or row.get("file_name", "")
            probable_year_match = YEAR_PATTERN.search(label or "")
            upsert_manifest_row(
                manifest_by_id,
                {
                    "local_file_id": row.get("canonical_local_file_id", "") or slugify(label),
                    "path_stub_or_redacted_path": safe_path_stub(row.get("primary_original_path", "") or row.get("copied_path", "")),
                    "file_name": row.get("file_name", "") or Path(label).name,
                    "extension": Path(row.get("file_name", "")).suffix.casefold().lstrip("."),
                    "file_size_bytes": row.get("file_size", ""),
                    "modified_date": "",
                    "probable_author_from_path": detect_author(label),
                    "probable_title_from_filename": probable_title_from_descriptor(label),
                    "probable_year_from_filename": probable_year_match.group(0) if probable_year_match else "",
                    "probable_volume_issue_from_filename": probable_volume_issue_from_text(label),
                    "folder_context": truncate_short(row.get("source_folder_hints", "") or "local_file_manifest supplement", limit=120),
                    "is_probable_jbrs": "true",
                    "manifest_confidence": "medium",
                    "needs_manual_review": "true",
                    "notes": "Supplemented from existing redacted local_file_manifest.tsv entry.",
                },
            )
    if existing_ocr_manifest_path.exists():
        for row in read_tsv(existing_ocr_manifest_path):
            source_text = " ".join([row.get("source_file_label", ""), row.get("source_path", "")])
            if not contains_jbrs_marker(source_text):
                continue
            local_file_id = row.get("source_file_id", "")
            upsert_manifest_row(
                manifest_by_id,
                {
                    "local_file_id": local_file_id,
                    "path_stub_or_redacted_path": safe_path_stub(row.get("source_path", "")),
                    "file_name": row.get("source_file_label", ""),
                    "extension": Path(row.get("source_file_label", "")).suffix.casefold().lstrip("."),
                    "file_size_bytes": "",
                    "modified_date": "",
                    "probable_author_from_path": detect_author(row.get("source_file_label", "")),
                    "probable_title_from_filename": probable_title_from_descriptor(row.get("source_file_label", "")),
                    "probable_year_from_filename": YEAR_PATTERN.search(row.get("source_file_label", "") or "").group(0) if YEAR_PATTERN.search(row.get("source_file_label", "") or "") else "",
                    "probable_volume_issue_from_filename": probable_volume_issue_from_text(row.get("source_file_label", "")),
                    "folder_context": "existing OCR manifest",
                    "is_probable_jbrs": "true",
                    "manifest_confidence": "medium",
                    "needs_manual_review": "true",
                    "notes": "Supplemented from existing OCR manifest metadata.",
                },
            )

    scan_roots = roots or []
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in {".pdf", ".djvu", ".tif", ".tiff", ".jpg", ".jpeg", ".png"}:
                continue
            joined = " ".join(path.parts[-6:])
            if "jbrs" not in normalize_for_match(joined) and "burma research society" not in normalize_for_match(joined):
                continue
            stat = path.stat()
            local_file_id = slugify(str(path.relative_to(root)))
            runtime_path_cache[local_file_id] = str(path)
            upsert_manifest_row(
                manifest_by_id,
                {
                "local_file_id": local_file_id,
                "path_stub_or_redacted_path": safe_path_stub(str(path.relative_to(root))),
                "file_name": path.name,
                "extension": path.suffix.casefold().lstrip("."),
                "file_size_bytes": str(stat.st_size),
                "modified_date": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "probable_author_from_path": detect_author(joined),
                "probable_title_from_filename": probable_title_from_descriptor(path.name),
                "probable_year_from_filename": YEAR_PATTERN.search(path.name or "").group(0) if YEAR_PATTERN.search(path.name or "") else "",
                "probable_volume_issue_from_filename": probable_volume_issue_from_text(path.name),
                "folder_context": truncate_short("/".join(path.parts[-4:-1]), limit=120),
                "is_probable_jbrs": "true",
                "manifest_confidence": "high",
                "needs_manual_review": bool_string(not probable_title_from_descriptor(path.name)),
                "notes": "Scanned from an explicit JBRS root and written without storing the absolute path.",
                },
            )

    rows = sorted(manifest_by_id.values(), key=lambda row: (row.get("probable_year_from_filename", ""), row.get("file_name", ""), row.get("local_file_id", "")))
    return rows, runtime_path_cache


def title_overlap(reference_title: str, candidate_title: str) -> bool:
    left = set(title_keyword_tokens(reference_title))
    right = set(title_keyword_tokens(candidate_title))
    if not left or not right:
        return False
    return len(left & right) >= max(1, min(len(left), len(right), 2))


def build_reference_file_match_rows(reference_rows: list[dict[str, str]], manifest_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for reference in reference_rows:
        best_score = -1
        best_rows: list[tuple[int, dict[str, str], list[str], str, str, str, str, str]] = []
        for manifest in manifest_rows:
            score = 0
            reasons: list[str] = []
            author_state = "none"
            title_state = "none"
            year_state = "none"
            volume_state = "none"
            path_state = "none"

            reference_author = surname_token(reference.get("author", ""))
            manifest_author = surname_token(manifest.get("probable_author_from_path", ""))
            if reference_author and manifest_author and reference_author == manifest_author:
                score += 3
                author_state = "exact"
                reasons.append("author")
            elif reference_author and reference_author in normalize_for_match(manifest.get("path_stub_or_redacted_path", "")):
                score += 2
                author_state = "path"
                reasons.append("author-path")

            if title_overlap(reference.get("article_title", ""), manifest.get("probable_title_from_filename", "")):
                score += 3
                title_state = "exact"
                reasons.append("title")
            elif reference.get("article_title") and normalize_for_match(reference.get("article_title", "")) in normalize_for_match(manifest.get("path_stub_or_redacted_path", "")):
                score += 2
                title_state = "path"
                reasons.append("title-path")

            if reference.get("year") and reference.get("year") == manifest.get("probable_year_from_filename"):
                score += 2
                year_state = "exact"
                reasons.append("year")
            if reference.get("volume") and reference.get("volume").casefold() in normalize_for_match(manifest.get("probable_volume_issue_from_filename", "")):
                score += 1
                volume_state = "exact"
                reasons.append("volume")
            if contains_jbrs_marker(manifest.get("folder_context", "")) or contains_jbrs_marker(manifest.get("path_stub_or_redacted_path", "")):
                score += 1
                path_state = "jbrs"
                reasons.append("path-context")

            if score > best_score:
                best_score = score
                best_rows = [(score, manifest, reasons, author_state, title_state, year_state, volume_state, path_state)]
            elif score == best_score and score >= 3:
                best_rows.append((score, manifest, reasons, author_state, title_state, year_state, volume_state, path_state))

        if best_score < 3 or not best_rows:
            rows.append(
                {
                    "reference_id": reference.get("reference_id", ""),
                    "local_file_id": "",
                    "match_status": "no_local_candidate_found",
                    "match_confidence": "low",
                    "match_basis": "",
                    "author_match": "none",
                    "title_match": "none",
                    "year_match": "none",
                    "volume_issue_match": "none",
                    "path_context_match": "none",
                    "candidate_file_name": "",
                    "candidate_path_stub": "",
                    "next_action": "Search author-surname folders and Burma/JBRS folders on the external drive using the parsed reference details.",
                    "notes": "No local JBRS candidate cleared the minimum author/title/year/context score.",
                }
            )
            continue

        score, manifest, reasons, author_state, title_state, year_state, volume_state, path_state = best_rows[0]
        if len(best_rows) > 1:
            status = "multiple_candidates"
            confidence = "medium"
            next_action = "Review the tied local candidates manually before queuing OCR."
            notes = f"{len(best_rows)} local files tied for the best score."
        elif score >= 6:
            status = "exact_or_near_exact_match"
            confidence = "high"
            next_action = "Queue this local file for high-priority OCR or existing-text review."
            notes = "Author/title/year/path signals agree strongly."
        else:
            status = "plausible_match"
            confidence = "medium"
            next_action = "Confirm the article identity manually, then queue OCR."
            notes = "This remains a plausible local match pending human confirmation."

        rows.append(
            {
                "reference_id": reference.get("reference_id", ""),
                "local_file_id": manifest.get("local_file_id", ""),
                "match_status": status,
                "match_confidence": confidence,
                "match_basis": ", ".join(reasons),
                "author_match": author_state,
                "title_match": title_state,
                "year_match": year_state,
                "volume_issue_match": volume_state,
                "path_context_match": path_state,
                "candidate_file_name": manifest.get("file_name", ""),
                "candidate_path_stub": manifest.get("path_stub_or_redacted_path", ""),
                "next_action": next_action,
                "notes": notes,
            }
        )
    return rows


def read_existing_ocr_map() -> dict[str, dict[str, str]]:
    rows = read_tsv(OCR_MANIFEST_PATH) if OCR_MANIFEST_PATH.exists() else []
    mapping: dict[str, dict[str, str]] = {}
    for row in rows:
        mapping[row.get("source_file_label", "").casefold()] = row
    return mapping


def build_ocr_batch_plan_rows(
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    runtime_path_cache: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    runtime_path_cache = runtime_path_cache or {}
    match_by_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in match_rows:
        if row.get("local_file_id"):
            match_by_file[row["local_file_id"]].append(row)
    existing_ocr_map = read_existing_ocr_map()
    rows: list[dict[str, str]] = []
    for manifest in manifest_rows:
        local_file_id = manifest.get("local_file_id", "")
        file_name = manifest.get("file_name", "")
        existing_ocr = existing_ocr_map.get(file_name.casefold(), {})
        matched_rows = [
            row
            for row in match_by_file.get(local_file_id, [])
            if row.get("match_status") in {"exact_or_near_exact_match", "plausible_match", "multiple_candidates"}
        ]
        priority = "high" if matched_rows else "medium"
        if manifest.get("manifest_confidence") == "low" or manifest.get("needs_manual_review") == "true":
            priority = "low" if not matched_rows else priority
        probable_title = manifest.get("probable_title_from_filename", "")
        if re.search(r"\b(vol(?:ume)?|journal|part)\b", probable_title, re.IGNORECASE):
            ocr_scope = "whole_volume"
        elif manifest.get("is_probable_jbrs") == "true":
            ocr_scope = "article_pages_only"
        else:
            ocr_scope = "skip_not_jbrs"
        if existing_ocr:
            extraction_method = existing_ocr.get("extraction_method", "")
            if "google-vision" in extraction_method:
                ocr_engine = "google_vision"
            elif "tesseract" in extraction_method:
                ocr_engine = "tesseract_fallback"
            else:
                ocr_engine = "existing_pdf_text"
            status = "completed"
            blocked_by = ""
        elif ocr_scope == "skip_not_jbrs":
            ocr_engine = "manual_review"
            status = "skipped"
            blocked_by = "not_a_probable_jbrs_file"
        else:
            ocr_engine = "google_vision"
            status = "ready_for_ocr"
            blocked_by = "" if local_file_id in runtime_path_cache else "needs runtime path cache from build_jbrs_local_manifest.py --root"
        output_basename = slugify(local_file_id or file_name)
        rows.append(
            {
                "batch_id": f"jbrs-ocr-{output_basename}",
                "local_file_id": local_file_id,
                "file_name": file_name,
                "path_stub": manifest.get("path_stub_or_redacted_path", ""),
                "volume": "",
                "issue": "",
                "year": manifest.get("probable_year_from_filename", ""),
                "page_count_estimate": last_page_number(existing_ocr.get("page_scope", "")),
                "ocr_priority": priority,
                "ocr_scope": ocr_scope,
                "ocr_engine": ocr_engine,
                "output_basename": output_basename,
                "expected_output_format": "metadata_sidecar+page_text+article_text+google_vision_json",
                "metadata_sidecar_path": f"data_local/ocr/jbrs/manifest/{output_basename}.json",
                "status": status,
                "blocked_by": blocked_by,
                "notes": "Matched corpus references elevate OCR priority; the committed plan stores path stubs only.",
            }
        )
    return rows


def build_ocr_status_log_rows(batch_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    existing_ocr_map = read_existing_ocr_map()
    created_at = now_iso()
    rows: list[dict[str, str]] = []
    for batch in batch_rows:
        existing_ocr = existing_ocr_map.get(batch.get("file_name", "").casefold(), {})
        output_stub = safe_path_stub(existing_ocr.get("local_text_path", "")) if existing_ocr else f"data_local/ocr/jbrs/page_text/{batch.get('output_basename', '')}.txt"
        pages_completed = batch.get("page_count_estimate", "") if batch.get("status") == "completed" else ""
        rows.append(
            {
                "ocr_job_id": f"{batch.get('batch_id', '')}-status",
                "batch_id": batch.get("batch_id", ""),
                "local_file_id": batch.get("local_file_id", ""),
                "file_name": batch.get("file_name", ""),
                "ocr_engine": batch.get("ocr_engine", ""),
                "ocr_scope": batch.get("ocr_scope", ""),
                "status": batch.get("status", ""),
                "pages_submitted": batch.get("page_count_estimate", "") if batch.get("status") == "completed" else "",
                "pages_completed": pages_completed,
                "output_path_stub": output_stub,
                "metadata_sidecar_stub": batch.get("metadata_sidecar_path", ""),
                "error_type": "",
                "error_message_short": "",
                "created_at": created_at,
                "updated_at": created_at,
                "notes": "Initialized from the OCR batch plan and any pre-existing local OCR metadata.",
            }
        )
    return rows


def page_marker_for_offset(text: str, offset: int) -> str:
    matches = list(PAGE_MARKER_PATTERN.finditer(text[:offset]))
    if not matches:
        return ""
    return matches[-1].group(1)


def best_text_source_for_file(local_file_id: str, file_name: str, output_path_stub: str | None = None) -> Path | None:
    if output_path_stub:
        candidate = REPO_ROOT / output_path_stub
        if candidate.exists():
            return candidate
    if OCR_MANIFEST_PATH.exists():
        for row in read_tsv(OCR_MANIFEST_PATH):
            if row.get("source_file_id") == local_file_id or row.get("source_file_label", "").casefold() == file_name.casefold():
                candidate = REPO_ROOT / row.get("local_text_path", "")
                if candidate.exists():
                    return candidate
    return None


def classify_text_candidate(text: str) -> tuple[str, str, str, str, str, str]:
    lowered = text.casefold()
    for marker in TRANSLATION_MARKERS:
        position = lowered.find(marker)
        if position >= 0:
            snippet = truncate_short(text[max(0, position - 80) : position + 140])
            candidate_type = "explicit_translation_heading" if "translation" in marker else "text_and_translation_structure"
            return candidate_type, marker, snippet, "true", "true", "false"
    for marker in EDITION_MARKERS:
        position = lowered.find(marker)
        if position >= 0:
            snippet = truncate_short(text[max(0, position - 80) : position + 140])
            if marker in {"inscription no.", "transliteration", "old burmese", "pali"}:
                return "edition_or_transliteration_only", marker, snippet, "false", "true", "false"
            return "commentary_or_citation_only", marker, snippet, "false", "false", "true"
    if "bibliography" in lowered:
        position = lowered.find("bibliography")
        snippet = truncate_short(text[max(0, position - 80) : position + 140])
        return "bibliography_only", "bibliography", snippet, "false", "false", "true"
    return "unclear_needs_manual_review", "", "", "false", "false", "false"


def build_translation_candidate_rows(
    reference_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    reference_by_id = {row.get("reference_id", ""): row for row in reference_rows}
    manifest_by_id = {row.get("local_file_id", ""): row for row in manifest_rows}
    status_by_file = {row.get("local_file_id", ""): row for row in status_rows}
    reference_ids_by_file: dict[str, list[str]] = defaultdict(list)
    for row in match_rows:
        if row.get("local_file_id"):
            reference_ids_by_file[row["local_file_id"]].append(row.get("reference_id", ""))

    rows: list[dict[str, str]] = []
    candidate_index = 0
    for local_file_id, manifest in manifest_by_id.items():
        status_row = status_by_file.get(local_file_id, {})
        text_path = best_text_source_for_file(local_file_id, manifest.get("file_name", ""), status_row.get("output_path_stub"))
        if not text_path:
            continue
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        candidate_type, marker, snippet, contains_translation, contains_edition, commentary_only = classify_text_candidate(text)
        if candidate_type == "unclear_needs_manual_review" and not reference_ids_by_file.get(local_file_id):
            continue
        page_marker = ""
        if marker:
            page_marker = page_marker_for_offset(text.casefold(), text.casefold().find(marker.casefold()))
        reference_id = reference_ids_by_file.get(local_file_id, [""])[0]
        reference_row = reference_by_id.get(reference_id, {})
        candidate_index += 1
        rows.append(
            {
                "candidate_id": f"jbrs-candidate-{candidate_index:04d}",
                "local_file_id": local_file_id,
                "reference_id_if_any": reference_id,
                "journal": JOURNAL_TITLE,
                "volume": reference_row.get("volume", ""),
                "issue": reference_row.get("issue", ""),
                "year": reference_row.get("year", "") or manifest.get("probable_year_from_filename", ""),
                "article_title": reference_row.get("article_title", "") or manifest.get("probable_title_from_filename", ""),
                "author": reference_row.get("author", "") or manifest.get("probable_author_from_path", ""),
                "page_range_or_page": page_marker or reference_row.get("page_range", ""),
                "candidate_type": candidate_type,
                "evidence_marker": marker,
                "short_evidence_snippet": snippet,
                "contains_translation_candidate": contains_translation,
                "contains_edition_or_transliteration_candidate": contains_edition,
                "contains_commentary_only": commentary_only,
                "confidence": "high" if candidate_type == "explicit_translation_heading" else ("medium" if marker else "low"),
                "next_action": "Inspect the local article manually before making any translation-coverage claim." if candidate_type != "bibliography_only" else "Treat as bibliography context only unless other article evidence appears.",
                "notes": f"Derived from local text at {safe_path_stub(str(text_path))}; committed output stores only a short snippet.",
            }
        )
    return rows


def build_pilot_summary(
    reference_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    batch_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> dict:
    matched_reference_ids = {
        row.get("reference_id", "")
        for row in match_rows
        if row.get("match_status") in {"exact_or_near_exact_match", "plausible_match", "multiple_candidates"} and row.get("local_file_id")
    }
    return {
        "reference_hunt_count": len(reference_rows),
        "local_file_manifest_count": len(manifest_rows),
        "reference_file_match_count": len(match_rows),
        "matched_reference_count": len(matched_reference_ids),
        "unmatched_reference_count": max(len(reference_rows) - len(matched_reference_ids), 0),
        "ocr_batch_plan_count": len(batch_rows),
        "ready_for_ocr_count": sum(row.get("status") == "ready_for_ocr" for row in batch_rows),
        "already_text_searchable_count": sum(row.get("status") == "already_text_searchable" for row in status_rows),
        "ocr_completed_count": sum(row.get("status") == "completed" for row in status_rows),
        "translation_candidate_count": len(candidate_rows),
        "explicit_translation_candidate_count": sum(row.get("candidate_type") == "explicit_translation_heading" for row in candidate_rows),
        "probable_translation_candidate_count": sum(row.get("candidate_type") in {"text_and_translation_structure", "probable_translation_parallel_text"} for row in candidate_rows),
        "edition_or_transliteration_only_count": sum(row.get("candidate_type") == "edition_or_transliteration_only" for row in candidate_rows),
        "manual_review_needed_count": sum(
            row.get("candidate_type") in {"unclear_needs_manual_review", "commentary_or_citation_only", "edition_or_transliteration_only"} or row.get("confidence") == "low"
            for row in candidate_rows
        ),
        "notes": [
            "This summary records repository reference-hunt, local-manifest, matching, and OCR-preparation state only.",
            "External-drive absolute paths and full OCR text stay outside committed metadata.",
            "Translation candidates are heuristic leads, not verified translation coverage.",
        ],
    }


def write_runtime_path_cache(path: Path, mapping: dict[str, str]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_summary(path: Path, summary: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_readme_text() -> str:
    return """# JBRS working metadata

This directory stores working metadata for the Journal of the Burma Research Society (JBRS) reference hunt, local-file matching, OCR planning, and translation-candidate triage. It does **not** store source PDFs, page images, or full OCR text.

## Typical workflow
1. Build the repository reference hunt:
   `python3 scripts/build_jbrs_reference_hunt.py`
2. Scan one or more external-drive roots without committing absolute paths:
   `python3 scripts/build_jbrs_local_manifest.py --root "/Volumes/ExternalDrive/JBRS" --root "/Volumes/ExternalDrive/Burmese"`
3. Match references to local files:
   `python3 scripts/match_jbrs_references_to_local_files.py`
4. Build the OCR batch/status plan:
   `python3 scripts/plan_jbrs_ocr_batches.py`
5. Dry-run the Google Vision workflow:
   `python3 scripts/ocr_jbrs_google_vision.py --dry-run --limit 5`
6. Detect translation candidates from existing text or OCR text:
   `python3 scripts/detect_jbrs_translation_candidates.py`

## Local OCR output location
- Preferred local output root: `data_local/ocr/jbrs/`
- Recommended subdirectories:
  - `manifest/`
  - `google_vision_json/`
  - `page_text/`
  - `article_text/`
  - `logs/`

## Safe to commit
- TSV manifests and match logs in this directory
- JSON summaries
- README and scripts
- short evidence snippets only

## Must not be committed
- source PDFs or page images
- full OCR text or long extracted passages
- Nathan's absolute external-drive paths
- Google credentials, API keys, or service-account secrets

## Guardrails
- The Berkeley IOB catalogue record is not a verified local witness.
- The IOB plate portfolios are not the missing companion text witness.
- SIP does not satisfy the separate UEM witness gap.
- JBRS translation-candidate rows are only review leads; do not treat OCR snippets or English prose as verified translation coverage.
"""


def validate_jbrs_workflow(
    *,
    reference_hunt_path: Path = JBRS_REFERENCE_HUNT_PATH,
    local_manifest_path: Path = JBRS_LOCAL_FILE_MANIFEST_PATH,
    reference_match_path: Path = JBRS_REFERENCE_FILE_MATCH_PATH,
    ocr_batch_plan_path: Path = JBRS_OCR_BATCH_PLAN_PATH,
    ocr_status_log_path: Path = JBRS_OCR_STATUS_LOG_PATH,
    translation_candidate_log_path: Path = JBRS_TRANSLATION_CANDIDATE_LOG_PATH,
    pilot_summary_path: Path = JBRS_PILOT_SUMMARY_PATH,
    readme_path: Path = JBRS_README_PATH,
) -> list[str]:
    errors: list[str] = []
    required_paths = [
        reference_hunt_path,
        local_manifest_path,
        reference_match_path,
        ocr_batch_plan_path,
        ocr_status_log_path,
        translation_candidate_log_path,
        pilot_summary_path,
        readme_path,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing required JBRS artifact: {path.name}")
    if errors:
        return errors

    reference_rows = read_tsv(reference_hunt_path)
    manifest_rows = read_tsv(local_manifest_path)
    match_rows = read_tsv(reference_match_path)
    batch_rows = read_tsv(ocr_batch_plan_path)
    status_rows = read_tsv(ocr_status_log_path)
    candidate_rows = read_tsv(translation_candidate_log_path)
    summary = json.loads(pilot_summary_path.read_text(encoding="utf-8"))
    readme_text = readme_path.read_text(encoding="utf-8")

    reference_ids = {row.get("reference_id", "") for row in reference_rows}
    local_file_ids = {row.get("local_file_id", "") for row in manifest_rows}
    batch_ids = {row.get("batch_id", "") for row in batch_rows}

    if not readme_text.strip():
        errors.append("README.md must not be empty")
    for phrase in [
        "Berkeley IOB catalogue record is not a verified local witness",
        "IOB plate portfolios are not the missing companion text witness",
        "SIP does not satisfy the separate UEM witness gap",
    ]:
        if phrase not in readme_text:
            errors.append(f"README.md is missing required guardrail language: {phrase}")

    for row in reference_rows:
        if len(row.get("matched_reference_text_short", "")) > SHORT_SNIPPET_LIMIT:
            errors.append(f"Reference hunt row {row.get('reference_id')} stores more than a short snippet")
    for row in manifest_rows:
        if ABSOLUTE_PATH_PATTERN.search(row.get("path_stub_or_redacted_path", "")):
            errors.append(f"Local manifest row {row.get('local_file_id')} stores an absolute path")
    for row in match_rows:
        if row.get("reference_id") and row.get("reference_id") not in reference_ids:
            errors.append(f"Reference-file match row references unknown reference_id {row.get('reference_id')}")
        if row.get("local_file_id") and row.get("local_file_id") not in local_file_ids:
            errors.append(f"Reference-file match row references unknown local_file_id {row.get('local_file_id')}")
    for row in batch_rows:
        if row.get("local_file_id") not in local_file_ids:
            errors.append(f"OCR batch row references unknown local_file_id {row.get('local_file_id')}")
    for row in status_rows:
        if row.get("batch_id") not in batch_ids:
            errors.append(f"OCR status row references unknown batch_id {row.get('batch_id')}")
        if row.get("output_path_stub", "").startswith("data/working/"):
            errors.append(f"OCR status row {row.get('ocr_job_id')} points into a committed working directory")
        if ABSOLUTE_PATH_PATTERN.search(row.get("output_path_stub", "")) or ABSOLUTE_PATH_PATTERN.search(row.get("metadata_sidecar_stub", "")):
            errors.append(f"OCR status row {row.get('ocr_job_id')} stores an absolute output path")
    for row in candidate_rows:
        if not row.get("local_file_id") and not row.get("reference_id_if_any"):
            errors.append(f"Translation candidate row {row.get('candidate_id')} must reference a local file or reference")
        if row.get("short_evidence_snippet") and len(row.get("short_evidence_snippet", "")) > SHORT_SNIPPET_LIMIT:
            errors.append(f"Translation candidate row {row.get('candidate_id')} stores more than a short evidence snippet")
        if row.get("candidate_type") == "explicit_translation_heading" and not row.get("evidence_marker"):
            errors.append(f"Explicit translation candidate {row.get('candidate_id')} is missing an evidence_marker")
    expected_summary = build_pilot_summary(reference_rows, manifest_rows, match_rows, batch_rows, status_rows, candidate_rows)
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"JBRS pilot summary count mismatch for {key}: expected {value!r}, found {summary.get(key)!r}")

    api_key_markers = [
        "AIza",
        "-----BEGIN PRIVATE KEY-----",
        "GOOGLE_API_KEY=",
        "GOOGLE_APPLICATION_CREDENTIALS=/Volumes/",
    ]
    for path in [
        reference_hunt_path,
        local_manifest_path,
        reference_match_path,
        ocr_batch_plan_path,
        ocr_status_log_path,
        translation_candidate_log_path,
        readme_path,
        REPO_ROOT / "scripts/ocr_jbrs_google_vision.py",
    ]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in api_key_markers:
            if marker in text:
                errors.append(f"{path.name} contains a forbidden credentials/path marker: {marker}")

    return errors
