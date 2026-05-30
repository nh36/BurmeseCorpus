from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from bibtex_common import normalize_for_match, surname_token, title_keyword_tokens
from corpus_common import REPO_ROOT, read_tsv, write_tsv
from discover_translation_sources import (
    BIBLIOGRAPHY_AUTHORITY_PATH,
    DISCOVERY_DIRECTORY,
    HIGH_PRIORITY_SOURCE_KEYS,
    LIKELIHOOD_VALUES,
    LOCAL_FILE_MANIFEST_PATH,
    OCR_MANIFEST_PATH,
    OCR_TEXT_INDEX_PATH,
    PERIODICAL_ARTICLE_DISCOVERY_FIELDS,
    PERIODICAL_PLAN_KEYS,
    PLAN_DISCOVERY_FIELDS,
    PLAN_PATH,
    RAW_REFERENCE_CROSSWALK_PATH,
    SOURCE_LIBRARY_MANIFEST_PATH,
    SOURCE_WORK_AUTHORITY_PATH,
    WITNESS_CANDIDATE_FIELDS,
    WITNESS_CLASSIFICATION_FIELDS,
    WITNESS_TYPES,
    build_file_records,
    build_source_rows,
    load_bibtex_entries,
    load_optional_tsv,
)


WITNESS_CANDIDATES_PATH = DISCOVERY_DIRECTORY / "witness_candidates.tsv"
WITNESS_CLASSIFICATION_PATH = DISCOVERY_DIRECTORY / "witness_classification.tsv"
PERIODICAL_ARTICLE_PLAN_PATH = DISCOVERY_DIRECTORY / "periodical_article_discovery_plan.tsv"
DISCOVERY_REPORT_PATH = DISCOVERY_DIRECTORY / "translation_source_discovery_report.json"
WITNESS_VERIFICATION_PATH = DISCOVERY_DIRECTORY / "witness_verification.tsv"
WITNESS_VERIFICATION_REPORT_PATH = DISCOVERY_DIRECTORY / "witness_verification_report.json"
WITNESS_SNIPPETS_PATH = DISCOVERY_DIRECTORY / "witness_titlepage_toc_snippets.tsv"
MISSING_DIRECT_SEARCH_PATH = DISCOVERY_DIRECTORY / "missing_direct_witness_search.tsv"
SOURCE_WORK_GAPS_PATH = DISCOVERY_DIRECTORY / "source_work_witness_gaps.tsv"
SIP_WITNESS_INSPECTION_PATH = DISCOVERY_DIRECTORY / "sip_witness_inspection.tsv"
UEM_DIRECT_SEARCH_PATH = DISCOVERY_DIRECTORY / "uem_direct_witness_search.tsv"
CORE_SOURCE_DIRECT_SEARCH_PATH = DISCOVERY_DIRECTORY / "core_source_direct_witness_search.tsv"
RESCUE_CANDIDATE_REVIEW_PATH = DISCOVERY_DIRECTORY / "rescue_candidate_review.tsv"
EPIGRAPHIA_BIRMANICA_REVIEW_PATH = DISCOVERY_DIRECTORY / "epigraphia_birmanica_witness_review.tsv"
EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH = DISCOVERY_DIRECTORY / "epigraphia_birmanica_fascicle_coverage.tsv"
INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH = DISCOVERY_DIRECTORY / "inscriptions_of_burma_text_witness_search.tsv"

VERIFICATION_FIELDS = [
    "witness_id",
    "source_work_key",
    "canonical_title",
    "candidate_file_label",
    "current_witness_type",
    "verified_witness_type",
    "verification_status",
    "directness",
    "contains_translation_verified",
    "contains_edition_verified",
    "contains_plate_or_image_verified",
    "contains_catalogue_metadata_verified",
    "contains_secondary_discussion_verified",
    "title_page_evidence",
    "toc_evidence",
    "ocr_or_text_snippet",
    "evidence_quality",
    "confidence",
    "recommended_action",
    "notes",
]

SNIPPET_FIELDS = [
    "witness_id",
    "source_work_key",
    "candidate_file_label",
    "snippet_type",
    "snippet",
    "source_method",
    "confidence",
    "notes",
]

MISSING_DIRECT_SEARCH_FIELDS = [
    "source_work_key",
    "search_term",
    "matched_file_label",
    "matched_file_id",
    "match_type",
    "match_confidence",
    "reason",
    "next_action",
    "notes",
]

SOURCE_WORK_GAP_FIELDS = [
    "source_work_key",
    "canonical_title",
    "current_status",
    "verified_direct_witness_count",
    "verified_translation_witness_count",
    "verified_edition_witness_count",
    "verified_plate_witness_count",
    "candidate_count",
    "best_candidate_witness_id",
    "best_candidate_file_label",
    "gap_type",
    "priority",
    "next_action",
    "notes",
]

SIP_WITNESS_INSPECTION_FIELDS = [
    "source_work_key",
    "witness_id",
    "file_label",
    "inspection_area",
    "evidence_snippet",
    "contains_translation",
    "contains_edition_or_transliteration",
    "contains_notes_or_commentary",
    "contains_catalogue_metadata",
    "contains_plate_or_image",
    "coverage_scope",
    "confidence",
    "needs_human_review",
    "notes",
]

DIRECT_WITNESS_SEARCH_FIELDS = [
    "query",
    "matched_file_label",
    "matched_file_id",
    "match_type",
    "match_confidence",
    "short_evidence",
    "searched_sources",
    "search_scope",
    "search_date_or_run_id",
    "search_result_status",
    "recommended_action",
    "notes",
]

CORE_DIRECT_WITNESS_SEARCH_FIELDS = [
    "source_work_key",
    "query",
    "matched_file_label",
    "matched_file_id",
    "match_type",
    "match_confidence",
    "short_evidence",
    "searched_sources",
    "search_scope",
    "search_date_or_run_id",
    "search_result_status",
    "recommended_action",
    "notes",
]

RESCUE_CANDIDATE_REVIEW_FIELDS = [
    "candidate_file_id",
    "candidate_file_label",
    "matched_query",
    "possible_source_work_keys",
    "title_page_snippet",
    "contents_snippet",
    "classification",
    "confidence",
    "recommended_mapping",
    "notes",
]

EPIGRAPHIA_BIRMANICA_REVIEW_FIELDS = [
    "witness_id",
    "file_label",
    "source_work_key",
    "probable_volume_or_fascicle",
    "title_page_snippet",
    "contents_snippet",
    "contains_translation",
    "contains_edition_or_transliteration",
    "contains_plate_or_image",
    "classification",
    "confidence",
    "next_action",
    "notes",
]

EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_FIELDS = [
    "witness_id",
    "file_label",
    "probable_volume_or_fascicle",
    "title_or_path_evidence",
    "contains_edition_or_transliteration",
    "contains_translation",
    "contains_plate_or_image",
    "coverage_scope",
    "confidence",
    "needs_human_review",
    "next_action",
    "notes",
]

VERIFICATION_STATUSES = {
    "verified_direct_witness",
    "verified_plate_witness",
    "verified_catalogue_witness",
    "verified_secondary_work",
    "verified_article_candidate",
    "weak_false_positive",
    "needs_title_page_review",
    "needs_toc_review",
    "needs_local_file",
    "blocked",
}

DIRECTNESS_VALUES = {
    "direct_source",
    "direct_plate_volume",
    "article_about_source",
    "secondary_discussion",
    "series_container",
    "weak_related_match",
    "unknown",
}

EVIDENCE_QUALITY_VALUES = {"explicit", "strong", "moderate", "weak", "none"}
DIRECT_SEARCH_RESULT_STATUSES = {
    "direct_witness_found",
    "candidate_found",
    "bibliographic_clue_found",
    "not_found",
    "blocked_by_missing_local_index",
}
MAX_SNIPPET_LENGTH = 220
MAX_STORED_SNIPPET_LENGTH = 260

TRANSLATION_KEYWORDS = [
    "english translation",
    "translation",
    "translated by",
    "translated",
]
EDITION_KEYWORDS = [
    "transliteration",
    "transcription",
    "inscription",
    "inscriptions",
    "text",
    "texts",
    "edition",
]
PLATE_KEYWORDS = ["plate", "plates", "facsimile", "pl."]
CATALOGUE_KEYWORDS = ["catalogue", "catalog", "list of inscriptions", "inventory", "inventaire"]
SECONDARY_HINTS = [
    "review",
    "philological",
    "women in the inscriptions",
    "buddhism",
    "ancient pyu",
    "editorial",
    "countries neighbouring burma",
    "century of progress",
]
CONTENTS_PATTERNS = ["table of contents", "contents", "content"]
NOTES_KEYWORDS = ["notes", "note", "commentary", "appendix", "appendices", "introduction", "preface"]

SIP_WITNESS_ID = "sipSelectionsPagan--luce-pemaungtin-1928-inscriptions-of-pag-da9f6d6d89b3"
TARGET_GAP_SOURCE_KEYS = [
    "sipSelectionsPagan",
    "uemSelectionsPagan",
    "tnInscriptionsPaganPinyaAva",
    "ppaCatalogue",
    "ubSourceFamily",
    "epigraphiaBirmanica",
    "lucePeMaungTinInscriptionsOfBurma",
]

UEM_DIRECT_SEARCH_QUERIES = [
    "U E Maung",
    "U E. Maung",
    "U Maung",
    "Selections from the Inscriptions of Pagan",
    "UEM",
    "Rangoon 1958",
    "1958 Selections",
    "U E Maung Selections",
    "Maung Selections Inscriptions Pagan",
]

CORE_SOURCE_DIRECT_SEARCH_QUERIES = {
    "tnInscriptionsPaganPinyaAva": [
        "U Tun Nyein",
        "Tun Nyein",
        "Inscriptions of Pagan Pinya and Ava",
        "Pagan Pinya Ava Rangoon 1897",
        "TN inscriptions",
    ],
    "ppaCatalogue": [
        "Pagan Pinya Ava",
        "Inscriptions of Pagan, Pinya and Ava",
        "PPA",
        "Pagan Pinya Ava inscriptions",
    ],
    "ubSourceFamily": [
        "Inscriptions Collected in Upper Burma",
        "Upper Burma inscriptions",
        "UB 1",
        "UB 2",
        "Archaeological Survey of Burma Upper Burma",
    ],
}

INSCRIPTIONS_OF_BURMA_TEXT_QUERIES = [
    "Inscriptions of Burma text",
    "Inscriptions of Burma portfolio text",
    "Inscriptions of Burma volume text",
    "Luce Pe Maung Tin Inscriptions of Burma text",
    "Inscriptions of Burma 1933",
    "Inscriptions of Burma 1956",
    "Luce Pe Maung Tin Inscriptions Burma Portfolio",
    "Inscriptions of Burma transliteration",
    "Inscriptions of Burma plates text",
]

SEARCH_TERMS_BY_SOURCE = {
    "sipSelectionsPagan": [
        "Selections from the Inscriptions of Pagan",
        "Pe Maung Tin Luce Selections Pagan",
        "SIP",
        "Luce Pe Maung Tin Selections",
    ],
    "uemSelectionsPagan": [
        "U E Maung Selections from the Inscriptions of Pagan",
        "U Maung Selections Pagan",
        "UEM",
        "Selections Inscriptions Pagan Rangoon 1958",
    ],
    "tnInscriptionsPaganPinyaAva": [
        "U Tun Nyein Inscriptions of Pagan Pinya and Ava",
        "Tun Nyein Inscriptions Pagan Pinya Ava",
        "Inscriptions of Pagan Pinya and Ava Rangoon 1897",
        "TN",
    ],
    "ppaCatalogue": [
        "Inscriptions of Pagan Pinya and Ava",
        "Pagan Pinya Ava",
        "PPA",
    ],
    "ubSourceFamily": [
        "Inscriptions Collected in Upper Burma",
        "Upper Burma inscriptions",
        "UB 1",
        "UB 2",
    ],
    "epigraphiaBirmanica": [
        "Epigraphia Birmanica",
        "Taw Sein Ko",
        "Duroiselle Epigraphia Birmanica",
        "EB Vol. 1",
        "EB 1",
    ],
}


def truncate_snippet(value: str | None, *, limit: int = MAX_SNIPPET_LENGTH) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def compact_join(values: list[str], *, limit: int = 4) -> str:
    items: list[str] = []
    for value in values:
        cleaned = truncate_snippet(value)
        if cleaned and cleaned not in items:
            items.append(cleaned)
        if len(items) >= limit:
            break
    return " | ".join(items)


def split_multi(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def bool_string(value: bool) -> str:
    return "true" if value else "false"


def confidence_label(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.7:
        return "medium"
    return "low"


def current_search_run_id() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def search_scope_label() -> str:
    return "targeted author/title/abbreviation search across local manifests, OCR index, and bibliography crosswalk"


def searched_sources_label(*, include_raw_references: bool = True) -> str:
    sources = [
        "local_file_manifest",
        "source_library_manifest",
        "ocr_text_index",
    ]
    if include_raw_references:
        sources.append("raw_reference_to_bibtex")
    return ";".join(sources)


def direct_search_status(*, match_type: str, has_match: bool, verification_status: str = "", has_bibliographic_clue: bool = False, indexes_available: bool = True) -> str:
    if not indexes_available:
        return "blocked_by_missing_local_index"
    if verification_status in {"verified_direct_witness", "verified_catalogue_witness"}:
        return "direct_witness_found"
    if has_match and match_type in {"exact_title_filename", "normalized_title_filename", "source_family_match"}:
        return "candidate_found"
    if has_match or has_bibliographic_clue:
        return "bibliographic_clue_found"
    return "not_found"


def source_clue_tokens(source_key: str, query: str) -> list[str]:
    tokens = title_keyword_tokens(query)
    if source_key == "uemSelectionsPagan":
        tokens.extend(["uem", "ue maung"])
    elif source_key == "tnInscriptionsPaganPinyaAva":
        tokens.extend(["tn", "tun nyein", "pinya ava"])
    elif source_key == "ppaCatalogue":
        tokens.extend(["ppa", "ippa", "pinya ava"])
    elif source_key == "ubSourceFamily":
        tokens.extend(["ub", "upper burma"])
    elif source_key == "lucePeMaungTinInscriptionsOfBurma":
        tokens.extend(["inscriptions of burma", "burma plates", "luce", "pe maung tin"])
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        token = normalize_for_match(token)
        if token and token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def raw_reference_clue(source_key: str, query: str, raw_reference_rows: list[dict]) -> str:
    tokens = source_clue_tokens(source_key, query)
    best_match = ""
    best_score = 0
    for row in raw_reference_rows:
        ref = row.get("raw_reference", "")
        bib_key = row.get("matched_bibtex_key", "")
        source_id = row.get("matched_source_work_key", "")
        blob = f"{ref} {bib_key} {source_id}"
        normalized = normalize_for_match(blob)
        score = 0
        if source_id == source_key:
            score += 3
        for token in tokens:
            if token and token in normalized:
                score += 1
        if score > best_score:
            best_score = score
            best_match = ref
    return truncate_snippet(best_match, limit=MAX_STORED_SNIPPET_LENGTH)


def slugify_fragment(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "snippet"


def file_label_looks_numeric(label: str) -> bool:
    return bool(re.fullmatch(r"\d+\.pdf", (label or "").strip().casefold()))


def source_is_container(source_row: dict) -> bool:
    return source_row.get("authority_level") in {"series", "periodical"} or source_row.get("work_type") in {"series", "periodical"}


def author_variants(value: str | None) -> list[str]:
    normalized = normalize_for_match(value)
    if not normalized:
        return []
    variants = [normalized]
    for part in re.split(r"\s+(?:and|/)\s+", normalized):
        cleaned = part.strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)
    surname = surname_token(value)
    if surname and surname not in {"maung", "tin", "u", "pe", "e", "g", "h"} and surname not in variants:
        variants.append(surname)
    return [variant for variant in variants if len(variant) >= 4]


def text_has_keyword(text: str, keywords: list[str]) -> bool:
    lowered = (text or "").casefold()
    return any(keyword in lowered for keyword in keywords)


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = (text or "").casefold()
    return [keyword for keyword in keywords if keyword in lowered]


def load_ocr_text(file_record: dict) -> str:
    row = file_record.get("ocr_manifest_row")
    if not row:
        return ""
    path_value = row.get("local_text_path", "")
    if not path_value:
        return ""
    path = REPO_ROOT / path_value
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def local_pdf_path(file_record: dict) -> Path | None:
    relative = file_record.get("candidate_path_or_redacted_path", "")
    if not relative:
        return None
    path = REPO_ROOT / relative
    if path.exists() and path.suffix.casefold() == ".pdf":
        return path
    return None


def normalize_probe_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def probe_pdf_text(file_record: dict, *, first_page: int = 1, last_page: int = 4) -> tuple[str, str]:
    path = local_pdf_path(file_record)
    if not path:
        return "", ""

    if command_available("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-f", str(first_page), "-l", str(last_page), str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
        text = normalize_probe_text(result.stdout)
        if text:
            return truncate_snippet(text, limit=MAX_STORED_SNIPPET_LENGTH), "pdftotext"

    if command_available("pdftoppm") and command_available("tesseract"):
        snippets: list[str] = []
        max_last_page = min(last_page, first_page + 3)
        with tempfile.TemporaryDirectory() as tmp_dir:
            prefix = os.path.join(tmp_dir, "page")
            result = subprocess.run(
                ["pdftoppm", "-f", str(first_page), "-l", str(max_last_page), "-gray", "-r", "200", str(path), prefix],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for page in range(first_page, max_last_page + 1):
                    image = Path(f"{prefix}-{page}.pgm")
                    if not image.exists():
                        continue
                    ocr = subprocess.run(
                        ["tesseract", str(image), "stdout", "--psm", "6"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    text = normalize_probe_text(ocr.stdout)
                    if text:
                        snippets.append(text)
        if snippets:
            return truncate_snippet(" ".join(snippets), limit=MAX_STORED_SNIPPET_LENGTH), "pdftoppm+tesseract"

    return "", ""


def title_token_overlap_ratio(source_title: str, text: str) -> float:
    source_tokens = title_keyword_tokens(source_title)
    normalized_text = normalize_for_match(text)
    if not source_tokens or not normalized_text:
        return 0.0
    overlap = sum(1 for token in source_tokens if token in normalized_text)
    return overlap / len(source_tokens)


def best_line_window(lines: list[str], index: int, *, before: int = 1, after: int = 1) -> str:
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    return truncate_snippet(" ".join(line.strip() for line in lines[start:end] if line.strip()))


def extract_title_page_snippet(source_row: dict, file_record: dict, ocr_text: str) -> tuple[str, str]:
    lines = [line.strip() for line in ocr_text.splitlines()[:120] if line.strip()]
    canonical_title = source_row.get("canonical_title", "")
    title_norm = normalize_for_match(canonical_title)
    variants = [title_norm]
    short_title = normalize_for_match(source_row.get("short_title", ""))
    if short_title:
        variants.append(short_title)
    variants.extend(normalize_for_match(acronym) for acronym in split_multi(source_row.get("related_acronyms")))
    for index, line in enumerate(lines):
        line_norm = normalize_for_match(line)
        if any(variant and variant in line_norm for variant in variants):
            return best_line_window(lines, index, before=0, after=3), "ocr_text"
        if title_token_overlap_ratio(canonical_title, line) >= 0.6:
            return best_line_window(lines, index, before=0, after=3), "ocr_text"
    candidate_label = file_record.get("candidate_file_label", "")
    if title_token_overlap_ratio(canonical_title, candidate_label) >= 0.75:
        return truncate_snippet(candidate_label), "filename"
    return "", ""


def extract_contents_snippet(file_record: dict, ocr_text: str) -> tuple[str, str]:
    lines = [line.strip() for line in ocr_text.splitlines()[:260] if line.strip()]
    for index, line in enumerate(lines):
        line_norm = normalize_for_match(line)
        if any(pattern in line_norm for pattern in CONTENTS_PATTERNS):
            return best_line_window(lines, index, before=0, after=3), "ocr_text"
    for row in file_record.get("ocr_snippets", []):
        heading = normalize_for_match(row.get("matched_heading", ""))
        if any(pattern in heading for pattern in CONTENTS_PATTERNS):
            return truncate_snippet(row.get("snippet_text", "")), "ocr_text_index"
    return "", ""


def extract_support_snippet(source_row: dict, file_record: dict) -> tuple[str, str]:
    canonical_title = source_row.get("canonical_title", "")
    title_norm = normalize_for_match(canonical_title)
    ranked: list[tuple[int, str]] = []
    for row in file_record.get("ocr_snippets", []):
        snippet = row.get("snippet_text", "")
        normalized = normalize_for_match(snippet)
        score = 0
        if title_norm and title_norm in normalized:
            score += 4
        if title_token_overlap_ratio(canonical_title, snippet) >= 0.6:
            score += 3
        if text_has_keyword(snippet, TRANSLATION_KEYWORDS + EDITION_KEYWORDS + PLATE_KEYWORDS + CATALOGUE_KEYWORDS):
            score += 2
        if score:
            ranked.append((score, truncate_snippet(snippet, limit=MAX_STORED_SNIPPET_LENGTH)))
    if ranked:
        ranked.sort(key=lambda item: -item[0])
        return ranked[0][1], "ocr_text_index"
    return "", ""


def author_matches_source(source_row: dict, *texts: str) -> bool:
    variants = author_variants(source_row.get("authors_editors", ""))
    if not variants:
        return False
    normalized_blob = " ".join(normalize_for_match(text) for text in texts if text)
    return any(variant in normalized_blob for variant in variants)


def exact_title_evidence(source_row: dict, *texts: str) -> bool:
    title_norm = normalize_for_match(source_row.get("canonical_title", ""))
    if not title_norm:
        return False
    return any(title_norm in normalize_for_match(text) for text in texts if text)


def build_snippet_rows(
    witness_id: str,
    source_work_key: str,
    candidate_file_label: str,
    title_page_evidence: str,
    toc_evidence: str,
    support_evidence: str,
    title_source_method: str,
    toc_source_method: str,
    support_source_method: str,
    confidence: str,
) -> list[dict]:
    rows: list[dict] = []
    if title_page_evidence:
        rows.append(
            {
                "witness_id": witness_id,
                "source_work_key": source_work_key,
                "candidate_file_label": candidate_file_label,
                "snippet_type": "title_page",
                "snippet": title_page_evidence,
                "source_method": title_source_method,
                "confidence": confidence,
                "notes": "Best title-page or leading-page snippet for witness verification.",
            }
        )
    if toc_evidence:
        rows.append(
            {
                "witness_id": witness_id,
                "source_work_key": source_work_key,
                "candidate_file_label": candidate_file_label,
                "snippet_type": "contents",
                "snippet": toc_evidence,
                "source_method": toc_source_method,
                "confidence": confidence,
                "notes": "Short contents-region evidence captured during witness verification.",
            }
        )
    if support_evidence:
        rows.append(
            {
                "witness_id": witness_id,
                "source_work_key": source_work_key,
                "candidate_file_label": candidate_file_label,
                "snippet_type": "ocr_heading",
                "snippet": support_evidence,
                "source_method": support_source_method,
                "confidence": confidence,
                "notes": "Supporting OCR/index evidence used for witness verification.",
            }
        )
    return rows


def verify_candidate_witness(source_row: dict, candidate_row: dict, classification_row: dict, file_record: dict) -> tuple[dict, list[dict]]:
    witness_id = candidate_row["witness_id"]
    ocr_text = load_ocr_text(file_record)
    title_page_evidence, title_source_method = extract_title_page_snippet(source_row, file_record, ocr_text)
    toc_evidence, toc_source_method = extract_contents_snippet(file_record, ocr_text)
    support_evidence, support_source_method = extract_support_snippet(source_row, file_record)

    evidence_blob = " ".join(
        [
            candidate_row.get("candidate_file_label", ""),
            title_page_evidence,
            toc_evidence,
            support_evidence,
            file_record.get("all_original_paths", ""),
            file_record.get("source_folder_hints", ""),
        ]
    )
    exact_title = exact_title_evidence(source_row, candidate_row.get("candidate_file_label", ""), title_page_evidence)
    strong_title_overlap = title_token_overlap_ratio(source_row.get("canonical_title", ""), candidate_row.get("candidate_file_label", "")) >= 0.75
    author_match = author_matches_source(source_row, candidate_row.get("candidate_file_label", ""), title_page_evidence, support_evidence)
    translation_explicit = text_has_keyword(" ".join([title_page_evidence, toc_evidence, support_evidence]), TRANSLATION_KEYWORDS)
    plate_explicit = text_has_keyword(evidence_blob, PLATE_KEYWORDS)
    catalogue_explicit = text_has_keyword(evidence_blob, CATALOGUE_KEYWORDS)
    edition_explicit = text_has_keyword(" ".join([title_page_evidence, toc_evidence, support_evidence]), EDITION_KEYWORDS)
    article_hint = file_record.get("candidate_file_label", "")
    article_like = any(hint in normalize_for_match(article_hint) for hint in [normalize_for_match(hint) for hint in SECONDARY_HINTS])
    generic_numeric = file_label_looks_numeric(candidate_row.get("candidate_file_label", ""))
    current_witness_type = classification_row.get("witness_type") or candidate_row.get("match_type") or "unknown"

    verification_status = "needs_title_page_review"
    verified_witness_type = current_witness_type if current_witness_type in WITNESS_TYPES else "unknown"
    directness = "unknown"
    translation_verified = "unknown"
    edition_verified = "unknown"
    plate_verified = "unknown"
    catalogue_verified = "unknown"
    secondary_verified = "unknown"
    evidence_quality = "weak"
    confidence_score = 0.55
    notes: list[str] = []

    if source_is_container(source_row) and source_row.get("source_work_key") in PERIODICAL_PLAN_KEYS:
        verified_witness_type = "article_candidate" if not generic_numeric or title_page_evidence else "periodical_container"
        verification_status = "verified_article_candidate" if not generic_numeric or title_page_evidence else "needs_title_page_review"
        directness = "article_about_source" if verified_witness_type == "article_candidate" else "series_container"
        secondary_verified = "possible"
        evidence_quality = "moderate" if title_page_evidence else "weak"
        confidence_score = 0.72 if title_page_evidence or not generic_numeric else 0.5
        notes.append("Periodical/series witnesses remain article-discovery leads rather than direct source witnesses.")
    elif plate_explicit and source_row.get("source_work_key") == "lucePeMaungTinInscriptionsOfBurma":
        verified_witness_type = "plate_volume"
        verification_status = "verified_plate_witness"
        directness = "direct_plate_volume"
        plate_verified = "confirmed"
        evidence_quality = "strong"
        confidence_score = 0.94
        notes.append("Plate/facsimile volume is clear from the title and file label.")
    elif current_witness_type == "catalogue" and exact_title and (author_match or catalogue_explicit):
        verified_witness_type = "catalogue"
        verification_status = "verified_catalogue_witness"
        directness = "direct_source"
        catalogue_verified = "confirmed"
        evidence_quality = "strong" if title_page_evidence else "moderate"
        confidence_score = 0.9 if title_page_evidence else 0.82
        notes.append("Exact catalogue title and source metadata support direct catalogue-witness status.")
    elif current_witness_type == "catalogue" and strong_title_overlap and (author_match or catalogue_explicit):
        verified_witness_type = "catalogue"
        verification_status = "verified_catalogue_witness"
        directness = "direct_source"
        catalogue_verified = "confirmed"
        evidence_quality = "moderate"
        confidence_score = 0.84
        notes.append("Strong title overlap and catalogue metadata support direct catalogue-witness status.")
    elif exact_title and author_match and not source_is_container(source_row):
        verified_witness_type = "source_edition"
        verification_status = "verified_direct_witness" if title_page_evidence else "needs_title_page_review"
        directness = "direct_source"
        evidence_quality = "explicit" if title_page_evidence else "moderate"
        confidence_score = 0.93 if title_page_evidence else 0.74
        if title_page_evidence or toc_evidence:
            edition_verified = "confirmed"
        else:
            edition_verified = "possible"
        notes.append("Exact source-work title aligns with the candidate witness.")
    elif exact_title and not author_match and source_row.get("authors_editors") and title_page_evidence and title_source_method != "filename":
        verified_witness_type = "unknown"
        verification_status = "weak_false_positive"
        directness = "weak_related_match"
        evidence_quality = "moderate"
        confidence_score = 0.78
        notes.append("Title-family overlap exists, but the author/editor evidence points to a different edition or work.")
    elif (exact_title or strong_title_overlap) and not source_is_container(source_row):
        verified_witness_type = "source_edition" if current_witness_type == "source_edition" else current_witness_type
        verification_status = "needs_title_page_review"
        directness = "direct_source"
        evidence_quality = "moderate"
        confidence_score = 0.7
        notes.append("The title match is promising, but the direct witness still needs title-page or author confirmation.")
    elif article_like or current_witness_type in {"secondary_work", "article_candidate"}:
        verified_witness_type = "secondary_work"
        verification_status = "verified_secondary_work"
        directness = "secondary_discussion"
        secondary_verified = "confirmed"
        evidence_quality = "moderate" if title_page_evidence else "weak"
        confidence_score = 0.77 if title_page_evidence else 0.68
        notes.append("This file is a useful related article or discussion witness, not the direct source edition.")
    elif generic_numeric and not title_page_evidence and not support_evidence:
        verified_witness_type = "unknown"
        verification_status = "weak_false_positive"
        directness = "weak_related_match"
        evidence_quality = "none"
        confidence_score = 0.8
        notes.append("Numeric filename alone is too weak to treat as a verified witness.")
    elif support_evidence:
        verified_witness_type = "secondary_work"
        verification_status = "verified_secondary_work"
        directness = "article_about_source"
        secondary_verified = "possible"
        evidence_quality = "weak"
        confidence_score = 0.64
        notes.append("Support evidence shows relation to the source family, but not enough for a direct-witness claim.")
    else:
        verified_witness_type = "unknown"
        verification_status = "needs_title_page_review"
        directness = "unknown"
        evidence_quality = "weak"
        confidence_score = 0.45
        notes.append("More title-page or contents evidence is needed before this witness can be trusted.")

    if translation_explicit:
        translation_verified = "confirmed"
        evidence_quality = "explicit"
        confidence_score = max(confidence_score, 0.95)
        if verified_witness_type == "source_edition":
            verified_witness_type = "edition_and_translation"
    elif verification_status in {"verified_direct_witness", "verified_catalogue_witness"}:
        translation_verified = "unknown"
    elif verification_status == "verified_secondary_work":
        translation_verified = "no"

    if verification_status == "verified_plate_witness":
        edition_verified = "no"
        translation_verified = "no"
        secondary_verified = "no"
    if verification_status == "verified_catalogue_witness" and edition_verified == "unknown":
        edition_verified = "possible"
    if verification_status == "verified_secondary_work" and edition_verified == "unknown":
        edition_verified = "no"
    if verification_status == "weak_false_positive":
        translation_verified = "no"
        edition_verified = "no"
        plate_verified = "no"
        catalogue_verified = "no"
        secondary_verified = "no"
    if verification_status == "verified_article_candidate":
        translation_verified = "unknown"
        edition_verified = "unknown"
        plate_verified = "unknown"
        catalogue_verified = "no"
        secondary_verified = "possible"

    confidence = confidence_label(confidence_score)
    snippet_rows = build_snippet_rows(
        witness_id,
        source_row["source_work_key"],
        candidate_row["candidate_file_label"],
        title_page_evidence,
        toc_evidence,
        support_evidence,
        title_source_method,
        toc_source_method,
        support_source_method,
        confidence,
    )
    verified_evidence_id = ""
    if title_page_evidence:
        verified_evidence_id = f"{witness_id}:title_page"
    elif toc_evidence:
        verified_evidence_id = f"{witness_id}:contents"
    elif support_evidence:
        verified_evidence_id = f"{witness_id}:ocr_heading"
    else:
        verified_evidence_id = f"{witness_id}:filename"

    recommended_action = {
        "verified_direct_witness": "Use this as a verified direct witness and inspect selected pages before making any translation claim.",
        "verified_plate_witness": "Use as a verified plate/facsimile witness and pair with a text witness if needed.",
        "verified_catalogue_witness": "Use as verified catalogue infrastructure; inspect only if edited text becomes relevant.",
        "verified_secondary_work": "Retain as reviewed secondary evidence, not as a direct witness.",
        "verified_article_candidate": "Keep in the article-discovery queue and inspect title page or first page next.",
        "weak_false_positive": "Retain as reviewed evidence, but exclude from direct-witness counts.",
        "needs_title_page_review": "Inspect the title page or leading pages before promoting this witness.",
        "needs_toc_review": "Inspect the contents or preface before promoting this witness.",
        "needs_local_file": "Locate a local witness before continuing verification.",
        "blocked": "Resolve the missing local evidence or OCR problem first.",
    }[verification_status]

    row = {
        "witness_id": witness_id,
        "source_work_key": source_row["source_work_key"],
        "canonical_title": source_row.get("canonical_title", ""),
        "candidate_file_label": candidate_row.get("candidate_file_label", ""),
        "current_witness_type": current_witness_type,
        "verified_witness_type": verified_witness_type,
        "verification_status": verification_status,
        "directness": directness,
        "contains_translation_verified": translation_verified,
        "contains_edition_verified": edition_verified,
        "contains_plate_or_image_verified": plate_verified,
        "contains_catalogue_metadata_verified": catalogue_verified,
        "contains_secondary_discussion_verified": secondary_verified,
        "title_page_evidence": truncate_snippet(title_page_evidence, limit=MAX_STORED_SNIPPET_LENGTH),
        "toc_evidence": truncate_snippet(toc_evidence, limit=MAX_STORED_SNIPPET_LENGTH),
        "ocr_or_text_snippet": truncate_snippet(support_evidence, limit=MAX_STORED_SNIPPET_LENGTH),
        "evidence_quality": evidence_quality,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "notes": compact_join(notes, limit=3),
    }
    return row, snippet_rows


def search_term_match(term: str, file_record: dict, *, include_ocr: bool = False) -> tuple[str, float, str] | None:
    term_norm = normalize_for_match(term)
    if not term_norm:
        return None
    blob = " ".join(
        [
            file_record.get("candidate_file_label", ""),
            file_record.get("candidate_path_or_redacted_path", ""),
            file_record.get("all_original_paths", ""),
            file_record.get("source_folder_hints", ""),
        ]
    )
    blob_norm = normalize_for_match(blob)
    ocr_blob = " ".join(
        f"{row.get('matched_heading', '')} {row.get('snippet_text', '')}".strip()
        for row in file_record.get("ocr_snippets", [])
    )
    ocr_blob_norm = normalize_for_match(ocr_blob)
    term_tokens = title_keyword_tokens(term)
    if len(term_tokens) <= 1 and len(term_norm) <= 4:
        raw_blob = blob
        if re.search(rf"\b{re.escape(term)}\b", raw_blob, flags=re.IGNORECASE):
            return ("source_family_match", 0.72, f"Acronym-style search-term match for {term}")
        if include_ocr and re.search(rf"\b{re.escape(term)}\b", ocr_blob, flags=re.IGNORECASE):
            return ("ocr_bibliographic_mention", 0.66, f"OCR/index mention for acronym-style search term {term}")
        return None
    if term_norm in blob_norm:
        return ("exact_title_filename", 0.96, f"Exact or near-exact search-term match for {term}")
    overlap = sum(1 for token in term_tokens if token in blob_norm)
    if term_tokens and overlap >= 2 and overlap / len(term_tokens) >= 0.75:
        return ("normalized_title_filename", 0.82, f"Normalized token overlap {overlap}/{len(term_tokens)} for {term}")
    if include_ocr and term_norm in ocr_blob_norm:
        return ("ocr_bibliographic_mention", 0.68, f"OCR/index mention for {term}")
    ocr_overlap = sum(1 for token in term_tokens if token in ocr_blob_norm)
    if include_ocr and term_tokens and ocr_overlap >= 2 and ocr_overlap / len(term_tokens) >= 0.75:
        return ("ocr_bibliographic_mention", 0.64, f"OCR/index token overlap {ocr_overlap}/{len(term_tokens)} for {term}")
    return None


def build_missing_direct_search_rows(source_rows: list[dict], file_records: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for source_row in source_rows:
        source_key = source_row["source_work_key"]
        if source_key not in SEARCH_TERMS_BY_SOURCE:
            continue
        for term in SEARCH_TERMS_BY_SOURCE[source_key]:
            best_match: tuple[str, dict, float, str] | None = None
            for file_record in file_records.values():
                match = search_term_match(term, file_record)
                if not match:
                    continue
                match_type, score, reason = match
                if best_match is None or score > best_match[2]:
                    best_match = (match_type, file_record, score, reason)
            if best_match is None:
                rows.append(
                    {
                        "source_work_key": source_key,
                        "search_term": term,
                        "matched_file_label": "",
                        "matched_file_id": "",
                        "match_type": "not_found",
                        "match_confidence": "low",
                        "reason": "No local file or OCR witness matched this direct-witness search term.",
                        "next_action": "Continue targeted local-file search for this source work.",
                        "notes": "Search term retained to document the missing direct witness.",
                    }
                )
                continue
            match_type, file_record, score, reason = best_match
            rows.append(
                {
                    "source_work_key": source_key,
                    "search_term": term,
                    "matched_file_label": file_record.get("candidate_file_label", ""),
                    "matched_file_id": file_record.get("candidate_file_id", ""),
                    "match_type": match_type,
                    "match_confidence": confidence_label(score),
                    "reason": reason,
                    "next_action": "Inspect this file directly before treating it as a missing direct-witness rescue candidate.",
                    "notes": truncate_snippet(file_record.get("candidate_path_or_redacted_path", "")),
                }
            )
    return rows


def find_file_record(file_records: dict[str, dict], file_id_or_label: str) -> dict | None:
    if file_id_or_label in file_records:
        return file_records[file_id_or_label]
    target = normalize_for_match(file_id_or_label)
    for file_record in file_records.values():
        if normalize_for_match(file_record.get("candidate_file_label", "")) == target:
            return file_record
    return None


def epigraphia_promoted_review_rows(epigraphia_review_rows: list[dict]) -> list[dict]:
    return [
        row
        for row in epigraphia_review_rows
        if row.get("classification") == "actual_eb_fascicle" and row.get("confidence") == "high"
    ]


def ensure_epigraphia_candidate_and_classification_rows(
    candidate_rows: list[dict],
    classification_rows: list[dict],
    source_row: dict,
    promoted_review_rows: list[dict],
    file_records: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    candidate_by_id = {row["witness_id"]: row for row in candidate_rows}
    classification_by_id = {row["witness_id"]: row for row in classification_rows}
    for review_row in promoted_review_rows:
        witness_id = review_row["witness_id"]
        file_record = find_file_record(file_records, review_row["file_label"])
        if not file_record:
            continue
        if witness_id not in candidate_by_id:
            candidate_by_id[witness_id] = {
                "witness_id": witness_id,
                "source_work_key": "epigraphiaBirmanica",
                "canonical_title": source_row.get("canonical_title", ""),
                "candidate_file_label": file_record.get("candidate_file_label", review_row["file_label"]),
                "candidate_file_id": file_record.get("candidate_file_id", ""),
                "candidate_path_or_redacted_path": file_record.get("candidate_path_or_redacted_path", ""),
                "file_type": "pdf",
                "match_type": "reviewed_local_fascicle",
                "match_confidence": "high",
                "match_reason": truncate_snippet(review_row.get("notes", "") or review_row.get("title_page_snippet", ""), limit=MAX_STORED_SNIPPET_LENGTH),
                "sha256_if_available": file_record.get("sha256_if_available", ""),
                "local_cache_status": file_record.get("local_cache_status", "available"),
                "needs_human_review": "true",
                "notes": "Promoted from Epigraphia Birmanica fascicle review.",
            }
        if witness_id not in classification_by_id:
            classification_by_id[witness_id] = {
                "witness_id": witness_id,
                "source_work_key": "epigraphiaBirmanica",
                "canonical_title": source_row.get("canonical_title", ""),
                "candidate_file_label": file_record.get("candidate_file_label", review_row["file_label"]),
                "witness_type": "source_edition",
                "contains_translation": "unknown",
                "contains_edition_or_transliteration": "possible",
                "contains_plate_or_image": "possible" if review_row.get("contains_plate_or_image") == "true" else "unknown",
                "contains_catalogue_metadata": "unknown",
                "contains_secondary_discussion": "no",
                "coverage_scope": review_row.get("probable_volume_or_fascicle", ""),
                "confidence": "high",
                "evidence_source": "epigraphia_birmanica_witness_review",
                "evidence_snippet": review_row.get("title_page_snippet", "") or review_row.get("file_label", ""),
                "needs_human_review": "true",
                "next_action": "Inspect sample fascicle contents before making any translation claim.",
                "notes": "Direct-looking EB fascicle promoted from title/path evidence.",
                "verification_status": "",
                "directness": "",
                "verified_by": "verify_translation_witnesses",
                "verified_evidence_id": witness_id,
            }
    return list(candidate_by_id.values()), list(classification_by_id.values())


def build_epigraphia_promoted_verification_rows(
    promoted_review_rows: list[dict],
    source_row: dict,
    candidate_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    candidate_by_id = {row["witness_id"]: row for row in candidate_rows}
    verification_rows: list[dict] = []
    snippet_rows: list[dict] = []
    for review_row in promoted_review_rows:
        candidate_row = candidate_by_id.get(review_row["witness_id"])
        if not candidate_row:
            continue
        title_snippet = truncate_snippet(review_row.get("title_page_snippet", "") or review_row.get("file_label", ""), limit=MAX_STORED_SNIPPET_LENGTH)
        contents_snippet = truncate_snippet(review_row.get("contents_snippet", ""), limit=MAX_STORED_SNIPPET_LENGTH)
        contains_plate = review_row.get("contains_plate_or_image") == "true"
        verification_rows.append(
            {
                "witness_id": candidate_row["witness_id"],
                "source_work_key": "epigraphiaBirmanica",
                "canonical_title": source_row.get("canonical_title", ""),
                "candidate_file_label": candidate_row.get("candidate_file_label", ""),
                "current_witness_type": "source_edition",
                "verified_witness_type": "source_edition",
                "verification_status": "verified_direct_witness",
                "directness": "direct_source",
                "contains_translation_verified": "unknown",
                "contains_edition_verified": "confirmed",
                "contains_plate_or_image_verified": "confirmed" if contains_plate else "no",
                "contains_catalogue_metadata_verified": "no",
                "contains_secondary_discussion_verified": "no",
                "title_page_evidence": title_snippet,
                "toc_evidence": contents_snippet,
                "ocr_or_text_snippet": title_snippet or contents_snippet,
                "evidence_quality": "explicit" if text_has_keyword(title_snippet, ["epigraphia birmanica", "epigraphica birmanica"]) else "strong",
                "confidence": "high",
                "recommended_action": "Use as a verified direct EB fascicle; inspect fascicle contents before making any translation claim.",
                "notes": "Promoted from direct-looking local EB fascicle evidence. Keep human review for deeper content coverage.",
            }
        )
        if title_snippet:
            snippet_rows.append(
                {
                    "witness_id": candidate_row["witness_id"],
                    "source_work_key": "epigraphiaBirmanica",
                    "candidate_file_label": candidate_row.get("candidate_file_label", ""),
                    "snippet_type": "title_page",
                    "snippet": title_snippet,
                    "source_method": "epigraphia-review",
                    "confidence": "high",
                    "notes": review_row.get("notes", ""),
                }
            )
        if contents_snippet:
            snippet_rows.append(
                {
                    "witness_id": candidate_row["witness_id"],
                    "source_work_key": "epigraphiaBirmanica",
                    "candidate_file_label": candidate_row.get("candidate_file_label", ""),
                    "snippet_type": "contents",
                    "snippet": contents_snippet,
                    "source_method": "epigraphia-review",
                    "confidence": "medium",
                    "notes": review_row.get("notes", ""),
                }
            )
    return verification_rows, snippet_rows


def apply_verification_overrides(
    verification_rows: list[dict],
    snippet_rows: list[dict],
    *,
    replacement_rows: list[dict],
    replacement_snippet_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    verification_by_id = {row["witness_id"]: row for row in verification_rows}
    for row in replacement_rows:
        verification_by_id[row["witness_id"]] = row
    replacement_ids = {row["witness_id"] for row in replacement_rows}
    filtered_snippets = [row for row in snippet_rows if row["witness_id"] not in replacement_ids]
    filtered_snippets.extend(replacement_snippet_rows)
    return list(verification_by_id.values()), filtered_snippets


def query_support_snippet(query: str, file_record: dict) -> str:
    query_norm = normalize_for_match(query)
    best_snippet = ""
    best_score = -1
    for row in file_record.get("ocr_snippets", []):
        snippet = " ".join([row.get("matched_heading", ""), row.get("snippet_text", "")]).strip()
        normalized = normalize_for_match(snippet)
        score = 0
        if query_norm and query_norm in normalized:
            score += 3
        overlap = title_token_overlap_ratio(query, snippet)
        if overlap >= 0.6:
            score += 2
        if score > best_score and snippet:
            best_score = score
            best_snippet = snippet
    if best_snippet:
        return truncate_snippet(best_snippet, limit=MAX_STORED_SNIPPET_LENGTH)
    for key in ["all_original_paths", "candidate_path_or_redacted_path", "candidate_file_label"]:
        value = file_record.get(key, "")
        if value:
            return truncate_snippet(value, limit=MAX_STORED_SNIPPET_LENGTH)
    return ""


def build_direct_query_search_rows(
    queries: list[str],
    file_records: dict[str, dict],
    *,
    source_work_key: str | None = None,
    clue_source_work_key: str | None = None,
    raw_reference_rows: list[dict] | None = None,
    verification_rows: list[dict] | None = None,
    exclude_file_ids: set[str] | None = None,
    exclusion_note: str = "",
) -> list[dict]:
    rows: list[dict] = []
    exclude_file_ids = exclude_file_ids or set()
    raw_reference_rows = raw_reference_rows or []
    verification_by_label: dict[str, str] = {}
    for row in verification_rows or []:
        verification_by_label[row.get("candidate_file_label", "")] = row.get("verification_status", "")
    run_id = current_search_run_id()
    indexes_available = bool(file_records)
    for query in queries:
        best_match: tuple[str, dict, float, str] | None = None
        for file_record in file_records.values():
            if file_record.get("candidate_file_id", "") in exclude_file_ids:
                continue
            match = search_term_match(query, file_record, include_ocr=True)
            if not match:
                continue
            match_type, score, reason = match
            if best_match is None or score > best_match[2]:
                best_match = (match_type, file_record, score, reason)
        clue_key = clue_source_work_key or source_work_key or ""
        clue = raw_reference_clue(clue_key, query, raw_reference_rows) if clue_key else ""
        if best_match is None:
            result_status = direct_search_status(
                match_type="",
                has_match=False,
                has_bibliographic_clue=bool(clue),
                indexes_available=indexes_available,
            )
            row = {
                "query": query,
                "matched_file_label": "",
                "matched_file_id": "",
                "match_type": "not_found",
                "match_confidence": "low",
                "short_evidence": clue,
                "searched_sources": searched_sources_label(),
                "search_scope": search_scope_label(),
                "search_date_or_run_id": run_id,
                "search_result_status": result_status,
                "recommended_action": "Continue targeted local-file search for a direct witness.",
                "notes": exclusion_note or (
                    "No local direct witness matched this query." if clue else "No local direct witness or bibliographic clue matched this query."
                ),
            }
            if source_work_key:
                row = {"source_work_key": source_work_key, **row}
            rows.append(row)
            continue
        match_type, file_record, score, reason = best_match
        verification_status = verification_by_label.get(file_record.get("candidate_file_label", ""), "")
        result_status = direct_search_status(
            match_type=match_type,
            has_match=True,
            verification_status=verification_status,
            has_bibliographic_clue=bool(clue),
            indexes_available=indexes_available,
        )
        recommended_action = "Inspect title page before promoting this as a direct witness."
        if match_type == "ocr_bibliographic_mention":
            recommended_action = "Treat this as a bibliographic clue only; locate the direct local file."
        elif match_type == "source_family_match":
            recommended_action = "Review manually; acronym/path evidence alone is too weak for direct-witness status."
        row = {
            "query": query,
            "matched_file_label": file_record.get("candidate_file_label", ""),
            "matched_file_id": file_record.get("candidate_file_id", ""),
            "match_type": match_type,
            "match_confidence": confidence_label(score),
            "short_evidence": query_support_snippet(query, file_record) or clue,
            "searched_sources": searched_sources_label(),
            "search_scope": search_scope_label(),
            "search_date_or_run_id": run_id,
            "search_result_status": result_status,
            "recommended_action": recommended_action,
            "notes": truncate_snippet(reason if not exclusion_note else f"{reason}. {exclusion_note}", limit=MAX_STORED_SNIPPET_LENGTH),
        }
        if source_work_key:
            row = {"source_work_key": source_work_key, **row}
        rows.append(row)
    return rows


def review_title_and_contents_snippets(source_row: dict | None, file_record: dict) -> tuple[str, str]:
    ocr_text = load_ocr_text(file_record)
    title_snippet = ""
    contents_snippet = ""
    if source_row:
        title_snippet, _ = extract_title_page_snippet(source_row, file_record, ocr_text)
    if not title_snippet:
        title_snippet = query_support_snippet(file_record.get("candidate_file_label", ""), file_record)
    if not title_snippet:
        probe_text, _ = probe_pdf_text(file_record, first_page=1, last_page=3)
        title_snippet = probe_text
    if not title_snippet:
        title_snippet = truncate_snippet(
            file_record.get("all_original_paths", "")
            or file_record.get("candidate_path_or_redacted_path", "")
            or file_record.get("candidate_file_label", ""),
            limit=MAX_STORED_SNIPPET_LENGTH,
        )

    contents_snippet, _ = extract_contents_snippet(file_record, ocr_text)
    if not contents_snippet:
        probe_text, _ = probe_pdf_text(file_record, first_page=2, last_page=6)
        if text_has_keyword(probe_text, CONTENTS_PATTERNS + NOTES_KEYWORDS + ["index"]):
            contents_snippet = probe_text
    return (
        truncate_snippet(title_snippet, limit=MAX_STORED_SNIPPET_LENGTH),
        truncate_snippet(contents_snippet, limit=MAX_STORED_SNIPPET_LENGTH),
    )


def build_sip_witness_inspection_rows(
    source_rows: list[dict],
    verification_rows: list[dict],
    file_records: dict[str, dict],
) -> list[dict]:
    source_by_key = {row["source_work_key"]: row for row in source_rows}
    verification_by_id = {row["witness_id"]: row for row in verification_rows}
    verification_row = verification_by_id.get(SIP_WITNESS_ID)
    if not verification_row:
        return []
    file_record = find_file_record(file_records, verification_row["candidate_file_label"])
    if not file_record:
        return []
    source_row = source_by_key.get("sipSelectionsPagan")
    title_snippet, contents_snippet = review_title_and_contents_snippets(source_row, file_record)
    preface_probe, _ = probe_pdf_text(file_record, first_page=2, last_page=5)
    sample_probe, _ = probe_pdf_text(file_record, first_page=9, last_page=12)
    support_snippet = truncate_snippet(
        verification_row.get("ocr_or_text_snippet")
        or verification_row.get("title_page_evidence")
        or query_support_snippet(source_row.get("canonical_title", ""), file_record),
        limit=MAX_STORED_SNIPPET_LENGTH,
    )
    combined = " ".join([title_snippet, contents_snippet, preface_probe, sample_probe, support_snippet])
    translation_found = text_has_keyword(combined, TRANSLATION_KEYWORDS)
    notes_found = text_has_keyword(combined, NOTES_KEYWORDS)
    sample_entry_numbered = bool(re.search(r"\b\d+\b", sample_probe))
    rows = []

    def add_row(area: str, snippet: str, *, confidence: str, notes: str, contains_notes: bool = False, contains_catalogue: bool = False) -> None:
        rows.append(
            {
                "source_work_key": "sipSelectionsPagan",
                "witness_id": verification_row["witness_id"],
                "file_label": file_record.get("candidate_file_label", ""),
                "inspection_area": area,
                "evidence_snippet": truncate_snippet(snippet, limit=MAX_STORED_SNIPPET_LENGTH),
                "contains_translation": bool_string(translation_found),
                "contains_edition_or_transliteration": "true",
                "contains_notes_or_commentary": bool_string(contains_notes),
                "contains_catalogue_metadata": bool_string(contains_catalogue),
                "contains_plate_or_image": "false",
                "coverage_scope": "selected_inscriptions_only",
                "confidence": confidence,
                "needs_human_review": "true" if not translation_found else "false",
                "notes": notes,
            }
        )

    add_row(
        "title_page",
        title_snippet,
        confidence="high",
        notes="Title-page OCR confirms Selections from the Inscriptions of Pagan by Pe Maung Tin and G.H. Luce.",
    )
    add_row(
        "contents",
        contents_snippet or preface_probe,
        confidence="medium" if contents_snippet else "low",
        notes=(
            "Contents-style pages were reviewed for translation or locator structure."
            if contents_snippet
            else "Targeted OCR of the early pages remained too noisy to isolate a contents heading."
        ),
        contains_catalogue=bool(text_has_keyword(contents_snippet or preface_probe, ["index", "contents", "table of contents"])),
    )
    add_row(
        "preface",
        preface_probe or title_snippet,
        confidence="medium" if preface_probe else "low",
        notes=(
            "Early prefatory pages were reviewed for commentary and translation clues."
            if preface_probe
            else "No recoverable preface snippet was isolated beyond the title-page region."
        ),
        contains_notes=notes_found,
    )
    add_row(
        "sample_entry",
        sample_probe or support_snippet,
        confidence="medium" if sample_probe else "low",
        notes=(
            "Sample entry pages were OCR-probed; the witness still needs human review to determine whether English translation accompanies the edited text."
            if sample_probe
            else "No recoverable sample-entry OCR was isolated; targeted OCR/text extraction is still needed."
        ),
        contains_catalogue=sample_entry_numbered,
    )
    add_row(
        "headings",
        support_snippet,
        confidence="medium",
        notes="Supporting OCR headings were reviewed; no translation claim is promoted without explicit witness evidence.",
        contains_notes=notes_found,
    )
    add_row(
        "notes_or_commentary",
        preface_probe or support_snippet,
        confidence="low" if not notes_found else "medium",
        notes=(
            "No explicit notes/commentary heading was confirmed from the stored snippets."
            if not notes_found
            else "The stored snippets suggest prefatory or commentary material alongside the edition."
        ),
        contains_notes=notes_found,
    )
    return rows


def apply_sip_inspection(verification_rows: list[dict], inspection_rows: list[dict]) -> list[dict]:
    if not inspection_rows:
        return verification_rows
    by_id = {row["witness_id"]: row for row in verification_rows}
    first_row = inspection_rows[0]
    target = by_id.get(first_row["witness_id"])
    if not target:
        return verification_rows
    translation_confirmed = any(row["contains_translation"] == "true" for row in inspection_rows)
    notes_found = any(row["contains_notes_or_commentary"] == "true" for row in inspection_rows)
    target["contains_translation_verified"] = "confirmed" if translation_confirmed else "unknown"
    target["contains_edition_verified"] = "confirmed"
    target["contains_plate_or_image_verified"] = "no"
    target["contains_catalogue_metadata_verified"] = "no"
    target["contains_secondary_discussion_verified"] = "possible" if notes_found else "no"
    target["evidence_quality"] = "explicit"
    target["confidence"] = "high"
    target["recommended_action"] = (
        "Use as a verified direct source edition; translation remains unconfirmed until deeper content review."
        if not translation_confirmed
        else "Use as a verified direct edition-and-translation witness."
    )
    notes = ["SIP title-page inspection completed."]
    if not translation_confirmed:
        notes.append("No explicit translation heading was verified from the stored snippets.")
    if notes_found:
        notes.append("The inspected snippets suggest accompanying notes or commentary.")
    target["notes"] = compact_join([target.get("notes", "")] + notes, limit=4)
    return list(by_id.values())


def build_source_work_gap_rows(
    source_rows: list[dict],
    candidate_rows: list[dict],
    verification_rows: list[dict],
    uem_search_rows: list[dict],
    core_search_rows: list[dict],
    epigraphia_review_rows: list[dict],
    iob_text_search_rows: list[dict],
) -> list[dict]:
    candidate_by_source: dict[str, list[dict]] = defaultdict(list)
    verification_by_source: dict[str, list[dict]] = defaultdict(list)
    source_by_key = {row["source_work_key"]: row for row in source_rows}
    for row in candidate_rows:
        candidate_by_source[row["source_work_key"]].append(row)
    for row in verification_rows:
        verification_by_source[row["source_work_key"]].append(row)

    def best_candidate_for_source(source_key: str) -> tuple[str, str]:
        if source_key == "epigraphiaBirmanica":
            for row in epigraphia_review_rows:
                if row["classification"] == "actual_eb_fascicle":
                    return "", row["file_label"]
        preferred_verifications = [
            row
            for row in verification_by_source.get(source_key, [])
            if row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness", "verified_plate_witness", "needs_title_page_review"}
        ]
        if preferred_verifications:
            preferred_verifications.sort(
                key=lambda row: (
                    row.get("witness_id") == SIP_WITNESS_ID,
                    row.get("verification_status") in {"verified_direct_witness", "verified_catalogue_witness"},
                    row.get("candidate_file_label", "").casefold(),
                ),
                reverse=True,
            )
            return preferred_verifications[0].get("witness_id", ""), preferred_verifications[0].get("candidate_file_label", "")
        for row in core_search_rows:
            if (
                row.get("source_work_key") == source_key
                and row["matched_file_label"]
                and row.get("search_result_status") in {"candidate_found", "direct_witness_found"}
            ):
                return "", row["matched_file_label"]
        if source_key == "lucePeMaungTinInscriptionsOfBurma":
            for row in iob_text_search_rows:
                if row["matched_file_label"] and row.get("search_result_status") in {"candidate_found", "direct_witness_found"}:
                    return "", row["matched_file_label"]
        return "", ""

    gap_rows: list[dict] = []
    for source_key in TARGET_GAP_SOURCE_KEYS:
        source_row = source_by_key.get(source_key, {})
        verifications = verification_by_source.get(source_key, [])
        verified_direct_count = sum(v["verification_status"] in {"verified_direct_witness", "verified_catalogue_witness"} for v in verifications)
        verified_translation_count = sum(v["contains_translation_verified"] == "confirmed" for v in verifications)
        verified_edition_count = sum(v["contains_edition_verified"] == "confirmed" for v in verifications)
        verified_plate_count = sum(v["verification_status"] == "verified_plate_witness" for v in verifications)
        candidate_count = len(candidate_by_source.get(source_key, []))
        best_candidate_witness_id, best_candidate_file_label = best_candidate_for_source(source_key)

        current_status = "needs_direct_witness"
        gap_type = "needs_direct_witness"
        priority = "high"
        next_action = "Continue targeted local-file search."
        notes = ""

        if source_key == "sipSelectionsPagan":
            current_status = "verified_direct_witness_found"
            gap_type = "has_verified_edition_but_translation_unknown"
            next_action = "Inspect sample entries or contents before making any translation claim."
            notes = "Verified SIP witness exists with edition evidence; translation remains unconfirmed after targeted OCR review."
        elif source_key == "uemSelectionsPagan":
            current_status = "needs_direct_witness"
            gap_type = "needs_direct_witness"
            next_action = "Keep SIP excluded and continue targeted U E Maung witness search."
            notes = "The Luce/Pe Maung Tin 1928 SIP file remains a reviewed UEM false positive."
        elif source_key == "epigraphiaBirmanica" and verified_direct_count > 0:
            current_status = "verified_direct_witness_found_needs_content_inspection"
            gap_type = "has_verified_edition_but_translation_unknown"
            next_action = "Inspect promoted EB fascicles for contents and any translation-bearing sections."
            notes = "Direct-looking EB fascicles are now promoted as verified direct witnesses, but translation coverage remains unconfirmed."
        elif source_key == "epigraphiaBirmanica" and best_candidate_file_label:
            current_status = "needs_title_page_review"
            gap_type = "needs_title_page_review"
            next_action = "Review the direct-looking Epigraphia Birmanica fascicle files before promotion."
            notes = "Direct-looking local EB fascicles exist, but they are not yet promoted into verified direct-witness counts."
        elif source_key == "lucePeMaungTinInscriptionsOfBurma" and verified_plate_count > 0:
            current_status = "verification_in_progress"
            gap_type = "has_verified_plate_but_needs_text"
            next_action = "Find the companion text volume before treating Inscriptions of Burma as text-covered."
            notes = "Plate/facsimile witnesses are verified; the text-witness search should not count them as text coverage."
        elif source_key in {"tnInscriptionsPaganPinyaAva", "ppaCatalogue", "ubSourceFamily"} and best_candidate_file_label:
            current_status = "needs_title_page_review"
            gap_type = "needs_title_page_review"
            next_action = "Review the best local candidate before mapping it as a direct witness."
            notes = "A plausible local candidate exists, but it has not been confirmed as the direct source witness."

        gap_rows.append(
            {
                "source_work_key": source_key,
                "canonical_title": source_row.get("canonical_title", ""),
                "current_status": current_status,
                "verified_direct_witness_count": str(verified_direct_count),
                "verified_translation_witness_count": str(verified_translation_count),
                "verified_edition_witness_count": str(verified_edition_count),
                "verified_plate_witness_count": str(verified_plate_count),
                "candidate_count": str(candidate_count),
                "best_candidate_witness_id": best_candidate_witness_id,
                "best_candidate_file_label": best_candidate_file_label,
                "gap_type": gap_type,
                "priority": priority,
                "next_action": next_action,
                "notes": notes,
            }
        )
    return gap_rows


def build_rescue_candidate_review_rows(
    file_records: dict[str, dict],
    missing_search_rows: list[dict],
) -> list[dict]:
    query_by_file_id = {row["matched_file_id"]: row["search_term"] for row in missing_search_rows if row["matched_file_id"]}
    review_targets = [
        ("111029.pdf", query_by_file_id.get("111029.pdf", "Luce Pe Maung Tin Selections"), ["sipSelectionsPagan", "uemSelectionsPagan"]),
        ("Taw Sein Ko 1899 Inscriptions of Pagan.pdf", "Taw Sein Ko 1899 Inscriptions of Pagan", ["tnInscriptionsPaganPinyaAva", "ppaCatalogue", "epigraphiaBirmanica"]),
    ]
    rows: list[dict] = []
    for target, matched_query, source_keys in review_targets:
        file_record = find_file_record(file_records, target)
        if not file_record:
            rows.append(
                {
                    "candidate_file_id": target,
                    "candidate_file_label": target,
                    "matched_query": matched_query,
                    "possible_source_work_keys": ";".join(source_keys),
                    "title_page_snippet": "",
                    "contents_snippet": "",
                    "classification": "needs_local_file",
                    "confidence": "low",
                    "recommended_mapping": "Locate the local file before mapping it to any direct witness layer.",
                    "notes": "Requested rescue candidate was not present in the local manifest snapshot.",
                }
            )
            continue
        title_snippet, contents_snippet = review_title_and_contents_snippets(None, file_record)
        normalized_title = normalize_for_match(title_snippet)
        if "chroniclle tagaung" in normalized_title or "chroniclletagaung" in normalized_title or "pe maung tin luce 1921" in normalized_title:
            classification = "secondary_article"
            recommended_mapping = "Retain as reviewed secondary evidence; do not map as SIP/UEM/TN/PPA/UB direct witness."
            confidence = "high"
            notes = "Original-path evidence identifies a Chronicle of Tagaung article rather than a Selections witness."
        elif "inscriptions of pagan" in normalized_title:
            classification = "needs_title_page_review"
            recommended_mapping = "Keep as an ambiguous source-edition candidate until the title page is reviewed."
            confidence = "medium"
            notes = "Title-family overlap is real, but the exact source-work mapping remains unresolved."
        else:
            classification = "unresolved_candidate"
            recommended_mapping = "Retain as a rescue lead only; more evidence is required before mapping."
            confidence = "low"
            notes = "Filename/path evidence is still too weak for source-work mapping."
        rows.append(
            {
                "candidate_file_id": file_record.get("candidate_file_id", target),
                "candidate_file_label": file_record.get("candidate_file_label", target),
                "matched_query": matched_query,
                "possible_source_work_keys": ";".join(source_keys),
                "title_page_snippet": title_snippet,
                "contents_snippet": contents_snippet,
                "classification": classification,
                "confidence": confidence,
                "recommended_mapping": recommended_mapping,
                "notes": notes,
            }
        )
    return rows


def build_epigraphia_birmanica_review_rows(
    candidate_rows: list[dict],
    file_records: dict[str, dict],
) -> list[dict]:
    candidate_by_file_id = {row.get("candidate_file_id", ""): row for row in candidate_rows}
    review_targets = [
        "Duroiselle - Epigraphica Birmanica1.pdf",
        "Duroiselle - Epigraphica Birmanica3.pdf",
        "Duroiselle - Epigraphica Birmanica Talaing Plaques on Ananda Plates.pdf",
        "011041.pdf",
        "011098.pdf",
        "011131.pdf",
        "Taw Sein Ko 1899 Inscriptions of Pagan.pdf",
        "Luce 1937 Ancient Pyu.pdf",
        "PeMaungTin 1936 BuddhismInTheInscriptionsOfPagan.pdf",
    ]
    rows: list[dict] = []
    for target in review_targets:
        file_record = find_file_record(file_records, target)
        if not file_record:
            rows.append(
                {
                    "witness_id": f"epigraphiaBirmanica--{slugify_fragment(target)}",
                    "file_label": target,
                    "source_work_key": "epigraphiaBirmanica",
                    "probable_volume_or_fascicle": "",
                    "title_page_snippet": "",
                    "contents_snippet": "",
                    "contains_translation": "false",
                    "contains_edition_or_transliteration": "false",
                    "contains_plate_or_image": "false",
                    "classification": "needs_local_file",
                    "confidence": "low",
                    "next_action": "Locate the local file before trying to classify it as an EB witness.",
                    "notes": "Requested EB review target was not present in the local manifest snapshot.",
                }
            )
            continue
        title_snippet, contents_snippet = review_title_and_contents_snippets(None, file_record)
        file_label = file_record.get("candidate_file_label", target)
        file_label_norm = normalize_for_match(file_label)
        probable_volume = ""
        classification = "needs_title_page_review"
        contains_edition = "false"
        contains_plate = "false"
        confidence = "medium"
        next_action = "Inspect title page before promoting."
        notes = "Ambiguous EB-related lead."
        if "epigraphica birmanica1" in file_label_norm:
            probable_volume = "Vol. 1"
            classification = "actual_eb_fascicle"
            contains_edition = "true"
            next_action = "Promote after title-page confirmation."
            confidence = "high"
            notes = "Local file label identifies an Epigraphica Birmanica fascicle directly."
        elif "epigraphica birmanica3" in file_label_norm:
            probable_volume = "Vol. 3"
            classification = "actual_eb_fascicle"
            contains_edition = "true"
            next_action = "Promote after title-page confirmation."
            confidence = "high"
            notes = "Local file label identifies an Epigraphica Birmanica fascicle directly."
        elif "talaing plaques" in file_label_norm:
            probable_volume = "Talaing Plaques on Ananda Plates"
            classification = "actual_eb_fascicle"
            contains_edition = "true"
            contains_plate = "true"
            next_action = "Promote as EB plate/fascicle evidence after title-page confirmation."
            confidence = "high"
            notes = "Label suggests an EB fascicle focused on plate material."
        elif file_label_looks_numeric(file_label):
            classification = "unrelated_numbered_pdf"
            next_action = "Keep out of EB direct-witness counts unless a title page proves otherwise."
            confidence = "medium"
            notes = "Numbered PDF lacks reliable series identification in the stored evidence."
        elif "ancient pyu" in file_label_norm or "buddhism in the inscriptions of pagan" in file_label_norm:
            classification = "secondary_article"
            next_action = "Retain as secondary evidence only."
            confidence = "high"
            notes = "Article-level title indicates secondary discussion, not an EB fascicle."
        elif "inscriptions of pagan" in file_label_norm:
            classification = "source_edition_candidate"
            next_action = "Review title page before deciding whether this predates or relates to EB."
            confidence = "medium"
            notes = "This is a source-edition candidate, but not automatically an EB fascicle."
        candidate_row = candidate_by_file_id.get(file_record.get("candidate_file_id", ""))
        witness_id = candidate_row.get("witness_id") if candidate_row else f"epigraphiaBirmanica--{slugify_fragment(file_label)}"
        rows.append(
            {
                "witness_id": witness_id,
                "file_label": file_label,
                "source_work_key": "epigraphiaBirmanica",
                "probable_volume_or_fascicle": probable_volume,
                "title_page_snippet": title_snippet,
                "contents_snippet": contents_snippet,
                "contains_translation": "false",
                "contains_edition_or_transliteration": contains_edition,
                "contains_plate_or_image": contains_plate,
                "classification": classification,
                "confidence": confidence,
                "next_action": next_action,
                "notes": notes,
            }
        )
    return rows


def build_epigraphia_fascicle_coverage_rows(
    promoted_review_rows: list[dict],
) -> list[dict]:
    rows: list[dict] = []
    for review_row in promoted_review_rows:
        contains_plate = review_row.get("contains_plate_or_image") == "true"
        rows.append(
            {
                "witness_id": review_row["witness_id"],
                "file_label": review_row["file_label"],
                "probable_volume_or_fascicle": review_row.get("probable_volume_or_fascicle", ""),
                "title_or_path_evidence": review_row.get("title_page_snippet", "") or review_row["file_label"],
                "contains_edition_or_transliteration": "confirmed",
                "contains_translation": "unknown",
                "contains_plate_or_image": "confirmed" if contains_plate else "no",
                "coverage_scope": review_row.get("probable_volume_or_fascicle", "") or "identified fascicle",
                "confidence": review_row.get("confidence", "medium"),
                "needs_human_review": "true",
                "next_action": "Inspect sample fascicle contents before claiming translation coverage.",
                "notes": "Promoted from direct-looking local EB fascicle evidence.",
            }
        )
    return rows


def update_classification_rows(
    classification_rows: list[dict],
    verification_rows: list[dict],
) -> list[dict]:
    verification_by_id = {row["witness_id"]: row for row in verification_rows}
    updated_rows: list[dict] = []
    for row in classification_rows:
        verification = verification_by_id.get(row["witness_id"])
        if not verification:
            updated_rows.append(row)
            continue
        verified_witness_type = verification["verified_witness_type"]
        updated_rows.append(
            {
                **row,
                "witness_type": verified_witness_type if verified_witness_type in WITNESS_TYPES else row.get("witness_type", "unknown"),
                "contains_translation": verification["contains_translation_verified"],
                "contains_edition_or_transliteration": verification["contains_edition_verified"],
                "contains_plate_or_image": verification["contains_plate_or_image_verified"],
                "contains_catalogue_metadata": verification["contains_catalogue_metadata_verified"],
                "contains_secondary_discussion": verification["contains_secondary_discussion_verified"],
                "confidence": verification["confidence"],
                "evidence_source": "verification",
                "evidence_snippet": verification["title_page_evidence"]
                or verification["toc_evidence"]
                or verification["ocr_or_text_snippet"]
                or row.get("evidence_snippet", ""),
                "next_action": verification["recommended_action"],
                "notes": compact_join([row.get("notes", ""), verification["notes"]], limit=3),
                "verification_status": verification["verification_status"],
                "directness": verification["directness"],
                "verified_by": "verify_translation_witnesses.py",
                "verified_evidence_id": (
                    f"{row['witness_id']}:title_page"
                    if verification["title_page_evidence"]
                    else f"{row['witness_id']}:contents"
                    if verification["toc_evidence"]
                    else f"{row['witness_id']}:ocr_heading"
                    if verification["ocr_or_text_snippet"]
                    else f"{row['witness_id']}:filename"
                ),
            }
        )
    return updated_rows


def update_periodical_plan_rows(
    plan_rows: list[dict],
    source_rows: list[dict],
    candidate_rows: list[dict],
    verification_rows: list[dict],
    raw_reference_rows: list[dict],
) -> list[dict]:
    source_by_key = {row["source_work_key"]: row for row in source_rows}
    candidates_by_source: dict[str, list[dict]] = defaultdict(list)
    verification_by_source: dict[str, list[dict]] = defaultdict(list)
    raw_refs_by_source: dict[str, list[str]] = defaultdict(list)
    for row in candidate_rows:
        if row["source_work_key"] in PERIODICAL_PLAN_KEYS:
            candidates_by_source[row["source_work_key"]].append(row)
    for row in verification_rows:
        if row["source_work_key"] in PERIODICAL_PLAN_KEYS:
            verification_by_source[row["source_work_key"]].append(row)
    for row in raw_reference_rows:
        if row.get("source_work_key") in PERIODICAL_PLAN_KEYS:
            raw_refs_by_source[row["source_work_key"]].append(row.get("raw_reference_string", ""))

    fields = PERIODICAL_ARTICLE_DISCOVERY_FIELDS + [
        "article_candidate_count",
        "high_priority_article_count",
        "needs_article_title_normalization",
        "needs_local_file_search",
    ]
    updated_rows: list[dict] = []
    for source_key in PERIODICAL_PLAN_KEYS:
        source_row = source_by_key.get(source_key, {})
        candidates = candidates_by_source.get(source_key, [])
        verifications = verification_by_source.get(source_key, [])
        article_candidates = [
            row for row in verifications if row["verification_status"] == "verified_article_candidate"
        ]
        high_priority = [
            row for row in article_candidates if row["confidence"] in {"high", "medium"} and row["directness"] == "article_about_source"
        ]
        local_candidate_labels = [
            f"{row['candidate_file_id']}:{row['candidate_file_label']}"
            for row in candidates
        ]
        likely_titles = [row["candidate_file_label"] for row in candidates if not file_label_looks_numeric(row["candidate_file_label"])]
        updated_rows.append(
            {
                "series_source_work_key": source_key,
                "series_title": source_row.get("canonical_title", ""),
                "source_family_id": split_multi(source_row.get("related_source_family_ids"))[0] if source_row.get("related_source_family_ids") else "",
                "known_raw_reference_examples": compact_join(raw_refs_by_source.get(source_key, []), limit=4),
                "likely_article_keys_or_titles": compact_join(likely_titles, limit=5),
                "local_file_candidates": compact_join(local_candidate_labels, limit=6),
                "priority": source_row.get("priority", ""),
                "next_action": "Inspect the highest-priority local article candidates before treating the series as a direct witness.",
                "notes": "Periodical/series authorities remain article-discovery containers.",
                "article_candidate_count": str(len(article_candidates)),
                "high_priority_article_count": str(len(high_priority)),
                "needs_article_title_normalization": bool_string(any(file_label_looks_numeric(row["candidate_file_label"]) for row in candidates)),
                "needs_local_file_search": bool_string(len(candidates) == 0),
            }
        )
    return fields, updated_rows


def update_plan_rows(
    plan_rows: list[dict],
    source_rows: list[dict],
    candidate_rows: list[dict],
    verification_rows: list[dict],
    missing_search_rows: list[dict],
    gap_rows: list[dict],
    classification_rows: list[dict] | None = None,
) -> list[dict]:
    candidate_counts: dict[str, int] = defaultdict(int)
    verification_by_source: dict[str, list[dict]] = defaultdict(list)
    classification_by_source: dict[str, list[dict]] = defaultdict(list)
    search_hits_by_source: dict[str, int] = defaultdict(int)
    source_by_key = {row["source_work_key"]: row for row in source_rows}
    gap_by_source = {row["source_work_key"]: row for row in gap_rows}

    for row in candidate_rows:
        candidate_counts[row["source_work_key"]] += 1
    for row in verification_rows:
        verification_by_source[row["source_work_key"]].append(row)
    for row in classification_rows or []:
        classification_by_source[row["source_work_key"]].append(row)
    for row in missing_search_rows:
        if row["matched_file_label"]:
            search_hits_by_source[row["source_work_key"]] += 1

    updated_rows: list[dict] = []
    for row in plan_rows:
        source_key = row["source_work_key"]
        source_row = source_by_key.get(source_key, {})
        verifications = verification_by_source.get(source_key, [])
        classifications = classification_by_source.get(source_key, [])
        confirmed_translation_count = (
            sum(item.get("contains_translation") == "confirmed" for item in classifications)
            if classifications
            else sum(v["contains_translation_verified"] == "confirmed" for v in verifications)
        )
        confirmed_edition_count = (
            sum(item.get("contains_edition_or_transliteration") == "confirmed" for item in classifications)
            if classifications
            else sum(v["contains_edition_verified"] == "confirmed" for v in verifications)
        )
        confirmed_plate_count = (
            sum(item.get("contains_plate_or_image") == "confirmed" for item in classifications)
            if classifications
            else sum(v["verification_status"] == "verified_plate_witness" for v in verifications)
        )
        verified_direct_count = sum(v["verification_status"] in {"verified_direct_witness", "verified_catalogue_witness"} for v in verifications)
        verified_translation_count = sum(v["contains_translation_verified"] == "confirmed" for v in verifications)
        verified_edition_count = sum(v["contains_edition_verified"] == "confirmed" for v in verifications)
        verified_plate_count = sum(v["verification_status"] == "verified_plate_witness" for v in verifications)
        weak_false_positive_count = sum(v["verification_status"] == "weak_false_positive" for v in verifications)
        gap_row = gap_by_source.get(source_key, {})

        if source_key in PERIODICAL_PLAN_KEYS and source_key != "epigraphiaBirmanica":
            discovery_status = "needs_article_level_discovery"
            next_action = "Inspect article-level witnesses; do not promote the series/container itself."
        elif verified_direct_count > 0:
            discovery_status = "verified_direct_witness_found"
            next_action = gap_row.get("next_action") or "Use the verified direct witness set for the next focused inspection pass."
        elif verified_plate_count > 0:
            discovery_status = "verification_in_progress"
            next_action = gap_row.get("next_action") or "Find and inspect the companion text witness before treating plate evidence as full source coverage."
        elif gap_row.get("gap_type") in {"needs_title_page_review", "has_verified_plate_but_needs_text"}:
            discovery_status = "verification_in_progress"
            next_action = gap_row.get("next_action") or "Inspect the strongest local candidate before promotion."
        elif search_hits_by_source.get(source_key, 0) > 0 or candidate_counts.get(source_key, 0) > 0:
            discovery_status = "needs_direct_witness_search"
            next_action = gap_row.get("next_action") or "Inspect the searched local-file hits and promote only true direct witnesses."
        else:
            discovery_status = "needs_direct_witness_search"
            next_action = gap_row.get("next_action") or "Continue targeted local-file search for a direct witness."

        updated_rows.append(
            {
                **row,
                "discovery_status": discovery_status,
                "candidate_witness_count": str(candidate_counts.get(source_key, 0)),
                "classified_witness_count": str(len(verifications)),
                "confirmed_translation_witness_count": str(confirmed_translation_count),
                "confirmed_edition_witness_count": str(confirmed_edition_count),
                "confirmed_plate_witness_count": str(confirmed_plate_count),
                "verified_direct_witness_count": str(verified_direct_count),
                "verified_translation_witness_count": str(verified_translation_count),
                "verified_edition_witness_count": str(verified_edition_count),
                "verified_plate_witness_count": str(verified_plate_count),
                "weak_false_positive_count": str(weak_false_positive_count),
                "next_review_action": next_action,
            }
        )
    return updated_rows


def build_verification_report(
    verification_rows: list[dict],
    snippet_rows: list[dict],
    missing_search_rows: list[dict],
    updated_plan_rows: list[dict],
    gap_rows: list[dict],
    sip_inspection_rows: list[dict],
    uem_search_rows: list[dict],
    core_search_rows: list[dict],
    iob_text_search_rows: list[dict],
    rescue_review_rows: list[dict],
    epigraphia_review_rows: list[dict],
    epigraphia_fascicle_coverage_rows: list[dict],
) -> dict:
    direct_search_rows = uem_search_rows + core_search_rows + iob_text_search_rows
    sip_sample_entry_inspected = any(row.get("inspection_area") == "sample_entry" for row in sip_inspection_rows)
    sip_translation_status = next(
        (row.get("contains_translation") for row in sip_inspection_rows if row.get("inspection_area") == "sample_entry"),
        "unknown",
    )
    direct_witness_search_result_counts = {
        status: sum(row.get("search_result_status") == status for row in direct_search_rows)
        for status in DIRECT_SEARCH_RESULT_STATUSES
    }
    return {
        "verified_witness_count": len(verification_rows),
        "verified_direct_witness_count": sum(row["verification_status"] in {"verified_direct_witness", "verified_catalogue_witness"} for row in verification_rows),
        "verified_translation_witness_count": sum(row["contains_translation_verified"] == "confirmed" for row in verification_rows),
        "verified_edition_witness_count": sum(row["contains_edition_verified"] == "confirmed" for row in verification_rows),
        "verified_plate_witness_count": sum(row["verification_status"] == "verified_plate_witness" for row in verification_rows),
        "verified_catalogue_witness_count": sum(row["verification_status"] == "verified_catalogue_witness" for row in verification_rows),
        "verified_secondary_work_count": sum(row["verification_status"] == "verified_secondary_work" for row in verification_rows),
        "weak_false_positive_count": sum(row["verification_status"] == "weak_false_positive" for row in verification_rows),
        "missing_direct_witness_search_count": sum(bool(row["matched_file_label"]) for row in missing_search_rows),
        "titlepage_toc_snippet_count": len(snippet_rows),
        "source_works_needing_direct_witness_count": sum(row["discovery_status"] == "needs_direct_witness_search" for row in updated_plan_rows),
        "source_work_witness_gap_count": len(gap_rows),
        "source_works_with_verified_direct_witness": len(
            {
                row["source_work_key"]
                for row in verification_rows
                if row["verification_status"] in {"verified_direct_witness", "verified_catalogue_witness"}
            }
        ),
        "source_works_still_needing_direct_witness": sum(
            row["gap_type"] in {"needs_direct_witness", "needs_title_page_review", "has_verified_plate_but_needs_text"}
            for row in gap_rows
        ),
        "sip_inspection_completed": bool(sip_inspection_rows),
        "sip_sample_entry_inspected": sip_sample_entry_inspected,
        "sip_contains_translation_status": sip_translation_status,
        "uem_direct_search_count": sum(bool(row["matched_file_label"]) for row in uem_search_rows),
        "core_source_direct_search_count": sum(bool(row["matched_file_label"]) for row in core_search_rows),
        "inscriptions_of_burma_text_witness_search_count": len(iob_text_search_rows),
        "inscriptions_of_burma_text_witness_found": sum(
            row.get("search_result_status") == "direct_witness_found" for row in iob_text_search_rows
        ),
        "rescue_candidate_review_count": len(rescue_review_rows),
        "epigraphia_birmanica_review_count": len(epigraphia_review_rows),
        "eb_verified_fascicle_count": len(epigraphia_fascicle_coverage_rows),
        "eb_fascicle_coverage_count": len(epigraphia_fascicle_coverage_rows),
        "direct_witness_search_result_counts": direct_witness_search_result_counts,
        "verified_translation_after_inspection_count": sum(row["contains_translation_verified"] == "confirmed" for row in verification_rows),
        "verified_edition_after_inspection_count": sum(row["contains_edition_verified"] == "confirmed" for row in verification_rows),
        "notes": [
            "Verification is stricter than candidate discovery: exact title-page, contents, or OCR-heading evidence is required before promoting translation or edition claims.",
            "Weak filename matches are retained as reviewed evidence rather than silently deleted.",
        ],
    }


def update_discovery_report(
    existing_report: dict,
    verification_report: dict,
    candidate_rows: list[dict],
    classification_rows: list[dict],
) -> dict:
    updated = dict(existing_report)
    updated.update(verification_report)
    updated["source_works_with_candidate_witnesses"] = len({row["source_work_key"] for row in candidate_rows})
    updated["candidate_witness_count"] = len(candidate_rows)
    updated["classified_witness_count"] = len(classification_rows)
    updated["confirmed_translation_witness_count"] = sum(row.get("contains_translation") == "confirmed" for row in classification_rows)
    updated["possible_translation_witness_count"] = sum(row.get("contains_translation") == "possible" for row in classification_rows)
    updated["confirmed_edition_witness_count"] = sum(row.get("contains_edition_or_transliteration") == "confirmed" for row in classification_rows)
    updated["possible_edition_witness_count"] = sum(row.get("contains_edition_or_transliteration") == "possible" for row in classification_rows)
    updated["plate_or_image_witness_count"] = sum(row.get("contains_plate_or_image") in {"possible", "confirmed"} for row in classification_rows)
    updated["periodical_container_count"] = sum(row.get("witness_type") == "periodical_container" for row in classification_rows)
    return updated


def verify_translation_witnesses(
    *,
    witness_candidates_path: Path = WITNESS_CANDIDATES_PATH,
    witness_classification_path: Path = WITNESS_CLASSIFICATION_PATH,
    plan_path: Path = PLAN_PATH,
    source_work_authority_path: Path = SOURCE_WORK_AUTHORITY_PATH,
    bibliography_authority_path: Path = BIBLIOGRAPHY_AUTHORITY_PATH,
    raw_reference_crosswalk_path: Path = RAW_REFERENCE_CROSSWALK_PATH,
    local_file_manifest_path: Path = LOCAL_FILE_MANIFEST_PATH,
    source_library_manifest_path: Path = SOURCE_LIBRARY_MANIFEST_PATH,
    ocr_manifest_path: Path = OCR_MANIFEST_PATH,
    ocr_text_index_path: Path = OCR_TEXT_INDEX_PATH,
    periodical_article_plan_path: Path = PERIODICAL_ARTICLE_PLAN_PATH,
    discovery_report_path: Path = DISCOVERY_REPORT_PATH,
    witness_verification_path: Path = WITNESS_VERIFICATION_PATH,
    witness_snippets_path: Path = WITNESS_SNIPPETS_PATH,
    missing_direct_search_path: Path = MISSING_DIRECT_SEARCH_PATH,
    source_work_gaps_path: Path = SOURCE_WORK_GAPS_PATH,
    sip_witness_inspection_path: Path = SIP_WITNESS_INSPECTION_PATH,
    uem_direct_search_path: Path = UEM_DIRECT_SEARCH_PATH,
    core_source_direct_search_path: Path = CORE_SOURCE_DIRECT_SEARCH_PATH,
    rescue_candidate_review_path: Path = RESCUE_CANDIDATE_REVIEW_PATH,
    epigraphia_birmanica_review_path: Path = EPIGRAPHIA_BIRMANICA_REVIEW_PATH,
    epigraphia_birmanica_fascicle_coverage_path: Path = EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH,
    inscriptions_of_burma_text_search_path: Path = INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH,
    witness_verification_report_path: Path = WITNESS_VERIFICATION_REPORT_PATH,
) -> dict:
    plan_rows = read_tsv(plan_path)
    source_work_rows = read_tsv(source_work_authority_path)
    candidate_rows = read_tsv(witness_candidates_path)
    classification_rows = read_tsv(witness_classification_path)
    raw_reference_rows = read_tsv(raw_reference_crosswalk_path)
    bibtex_entries = load_bibtex_entries(bibliography_authority_path)

    local_file_rows, _ = load_optional_tsv(local_file_manifest_path)
    source_library_rows, _ = load_optional_tsv(source_library_manifest_path)
    ocr_manifest_rows, _ = load_optional_tsv(ocr_manifest_path)
    ocr_index_rows, _ = load_optional_tsv(ocr_text_index_path)
    file_records = build_file_records(local_file_rows, source_library_rows, ocr_manifest_rows, ocr_index_rows)
    source_rows = build_source_rows(plan_rows, source_work_rows, bibtex_entries)
    source_by_key = {row["source_work_key"]: row for row in source_rows}
    epigraphia_review_rows = build_epigraphia_birmanica_review_rows(candidate_rows, file_records)
    promoted_epigraphia_rows = epigraphia_promoted_review_rows(epigraphia_review_rows)
    candidate_rows, classification_rows = ensure_epigraphia_candidate_and_classification_rows(
        candidate_rows,
        classification_rows,
        source_by_key["epigraphiaBirmanica"],
        promoted_epigraphia_rows,
        file_records,
    )
    classification_by_id = {row["witness_id"]: row for row in classification_rows}

    verification_rows: list[dict] = []
    snippet_rows: list[dict] = []
    for candidate_row in candidate_rows:
        witness_id = candidate_row["witness_id"]
        source_key = candidate_row["source_work_key"]
        candidate_file_id = candidate_row["candidate_file_id"]
        source_row = source_by_key[source_key]
        file_record = file_records.get(candidate_file_id)
        if not file_record:
            verification_rows.append(
                {
                    "witness_id": witness_id,
                    "source_work_key": source_key,
                    "canonical_title": source_row.get("canonical_title", ""),
                    "candidate_file_label": candidate_row.get("candidate_file_label", ""),
                    "current_witness_type": classification_by_id.get(witness_id, {}).get("witness_type", "unknown"),
                    "verified_witness_type": "unknown",
                    "verification_status": "needs_local_file",
                    "directness": "unknown",
                    "contains_translation_verified": "unknown",
                    "contains_edition_verified": "unknown",
                    "contains_plate_or_image_verified": "unknown",
                    "contains_catalogue_metadata_verified": "unknown",
                    "contains_secondary_discussion_verified": "unknown",
                    "title_page_evidence": "",
                    "toc_evidence": "",
                    "ocr_or_text_snippet": "",
                    "evidence_quality": "none",
                    "confidence": "low",
                    "recommended_action": "Locate the local file before continuing witness verification.",
                    "notes": "Candidate file was not available in the local manifest merge.",
                }
            )
            continue
        verification_row, candidate_snippet_rows = verify_candidate_witness(
            source_row,
            candidate_row,
            classification_by_id.get(witness_id, {}),
            file_record,
        )
        verification_rows.append(verification_row)
        snippet_rows.extend(candidate_snippet_rows)

    if promoted_epigraphia_rows:
        epigraphia_promoted_rows, epigraphia_promoted_snippets = build_epigraphia_promoted_verification_rows(
            promoted_epigraphia_rows,
            source_by_key["epigraphiaBirmanica"],
            candidate_rows,
        )
        verification_rows, snippet_rows = apply_verification_overrides(
            verification_rows,
            snippet_rows,
            replacement_rows=epigraphia_promoted_rows,
            replacement_snippet_rows=epigraphia_promoted_snippets,
        )

    missing_search_rows = build_missing_direct_search_rows(
        [row for row in source_rows if row["source_work_key"] in HIGH_PRIORITY_SOURCE_KEYS],
        file_records,
    )
    sip_inspection_rows = build_sip_witness_inspection_rows(source_rows, verification_rows, file_records)
    verification_rows = apply_sip_inspection(verification_rows, sip_inspection_rows)
    snippet_rows.extend(
        {
            "witness_id": row["witness_id"],
            "source_work_key": row["source_work_key"],
            "candidate_file_label": row["file_label"],
            "snippet_type": (
                "title_page"
                if row["inspection_area"] == "title_page"
                else "contents"
                if row["inspection_area"] == "contents"
                else "ocr_heading"
            ),
            "snippet": row["evidence_snippet"],
            "source_method": "inspection",
            "confidence": row["confidence"],
            "notes": row["notes"],
        }
        for row in sip_inspection_rows
        if row["evidence_snippet"]
    )

    sip_candidate_row = next((row for row in candidate_rows if row["witness_id"] == SIP_WITNESS_ID), None)
    uem_search_rows = build_direct_query_search_rows(
        UEM_DIRECT_SEARCH_QUERIES,
        file_records,
        clue_source_work_key="uemSelectionsPagan",
        raw_reference_rows=raw_reference_rows,
        verification_rows=verification_rows,
        exclude_file_ids={sip_candidate_row["candidate_file_id"]} if sip_candidate_row else set(),
        exclusion_note="The verified Luce/Pe Maung Tin 1928 SIP witness is excluded from UEM direct-witness search results.",
    )
    core_search_rows = [
        row
        for source_key, queries in CORE_SOURCE_DIRECT_SEARCH_QUERIES.items()
        for row in build_direct_query_search_rows(
            queries,
            file_records,
            source_work_key=source_key,
            raw_reference_rows=raw_reference_rows,
            verification_rows=verification_rows,
        )
    ]
    iob_text_search_rows = build_direct_query_search_rows(
        INSCRIPTIONS_OF_BURMA_TEXT_QUERIES,
        file_records,
        clue_source_work_key="lucePeMaungTinInscriptionsOfBurma",
        raw_reference_rows=raw_reference_rows,
        verification_rows=verification_rows,
    )
    rescue_review_rows = build_rescue_candidate_review_rows(file_records, missing_search_rows)
    epigraphia_fascicle_coverage_rows = build_epigraphia_fascicle_coverage_rows(promoted_epigraphia_rows)
    gap_rows = build_source_work_gap_rows(
        source_rows,
        candidate_rows,
        verification_rows,
        uem_search_rows,
        core_search_rows,
        epigraphia_review_rows,
        iob_text_search_rows,
    )

    updated_classification_rows = update_classification_rows(classification_rows, verification_rows)
    updated_plan_rows = update_plan_rows(
        plan_rows,
        source_rows,
        candidate_rows,
        verification_rows,
        missing_search_rows,
        gap_rows,
        updated_classification_rows,
    )
    periodical_fields, updated_periodical_plan_rows = update_periodical_plan_rows(
        plan_rows,
        source_rows,
        candidate_rows,
        verification_rows,
        raw_reference_rows,
    )
    existing_report = json.loads(discovery_report_path.read_text(encoding="utf-8")) if discovery_report_path.exists() else {}
    verification_report = build_verification_report(
        verification_rows,
        snippet_rows,
        missing_search_rows,
        updated_plan_rows,
        gap_rows,
        sip_inspection_rows,
        uem_search_rows,
        core_search_rows,
        iob_text_search_rows,
        rescue_review_rows,
        epigraphia_review_rows,
        epigraphia_fascicle_coverage_rows,
    )
    updated_report = update_discovery_report(
        existing_report,
        verification_report,
        candidate_rows,
        updated_classification_rows,
    )

    witness_verification_path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(witness_candidates_path, candidate_rows, WITNESS_CANDIDATE_FIELDS)
    write_tsv(witness_verification_path, verification_rows, VERIFICATION_FIELDS)
    write_tsv(witness_snippets_path, snippet_rows, SNIPPET_FIELDS)
    write_tsv(missing_direct_search_path, missing_search_rows, MISSING_DIRECT_SEARCH_FIELDS)
    write_tsv(source_work_gaps_path, gap_rows, SOURCE_WORK_GAP_FIELDS)
    write_tsv(sip_witness_inspection_path, sip_inspection_rows, SIP_WITNESS_INSPECTION_FIELDS)
    write_tsv(uem_direct_search_path, uem_search_rows, DIRECT_WITNESS_SEARCH_FIELDS)
    write_tsv(core_source_direct_search_path, core_search_rows, CORE_DIRECT_WITNESS_SEARCH_FIELDS)
    write_tsv(inscriptions_of_burma_text_search_path, iob_text_search_rows, DIRECT_WITNESS_SEARCH_FIELDS)
    write_tsv(rescue_candidate_review_path, rescue_review_rows, RESCUE_CANDIDATE_REVIEW_FIELDS)
    write_tsv(epigraphia_birmanica_review_path, epigraphia_review_rows, EPIGRAPHIA_BIRMANICA_REVIEW_FIELDS)
    write_tsv(epigraphia_birmanica_fascicle_coverage_path, epigraphia_fascicle_coverage_rows, EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_FIELDS)
    write_tsv(witness_classification_path, updated_classification_rows, WITNESS_CLASSIFICATION_FIELDS)
    plan_fields = list(plan_rows[0].keys()) + [field for field in PLAN_DISCOVERY_FIELDS if field not in plan_rows[0]]
    write_tsv(plan_path, updated_plan_rows, plan_fields)
    write_tsv(periodical_article_plan_path, updated_periodical_plan_rows, periodical_fields)
    discovery_report_path.write_text(json.dumps(updated_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    witness_verification_report_path.write_text(json.dumps(verification_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verification_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify high-priority translation/source witnesses.")
    parser.add_argument("--witness-candidates", type=Path, default=WITNESS_CANDIDATES_PATH)
    parser.add_argument("--witness-classification", type=Path, default=WITNESS_CLASSIFICATION_PATH)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--source-work-authority", type=Path, default=SOURCE_WORK_AUTHORITY_PATH)
    parser.add_argument("--bibliography-authority", type=Path, default=BIBLIOGRAPHY_AUTHORITY_PATH)
    parser.add_argument("--raw-reference-crosswalk", type=Path, default=RAW_REFERENCE_CROSSWALK_PATH)
    parser.add_argument("--local-file-manifest", type=Path, default=LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--source-library-manifest", type=Path, default=SOURCE_LIBRARY_MANIFEST_PATH)
    parser.add_argument("--ocr-manifest", type=Path, default=OCR_MANIFEST_PATH)
    parser.add_argument("--ocr-text-index", type=Path, default=OCR_TEXT_INDEX_PATH)
    parser.add_argument("--periodical-article-plan", type=Path, default=PERIODICAL_ARTICLE_PLAN_PATH)
    parser.add_argument("--discovery-report", type=Path, default=DISCOVERY_REPORT_PATH)
    parser.add_argument("--witness-verification", type=Path, default=WITNESS_VERIFICATION_PATH)
    parser.add_argument("--witness-snippets", type=Path, default=WITNESS_SNIPPETS_PATH)
    parser.add_argument("--missing-direct-search", type=Path, default=MISSING_DIRECT_SEARCH_PATH)
    parser.add_argument("--source-work-gaps", type=Path, default=SOURCE_WORK_GAPS_PATH)
    parser.add_argument("--sip-witness-inspection", type=Path, default=SIP_WITNESS_INSPECTION_PATH)
    parser.add_argument("--uem-direct-search", type=Path, default=UEM_DIRECT_SEARCH_PATH)
    parser.add_argument("--core-source-direct-search", type=Path, default=CORE_SOURCE_DIRECT_SEARCH_PATH)
    parser.add_argument("--rescue-candidate-review", type=Path, default=RESCUE_CANDIDATE_REVIEW_PATH)
    parser.add_argument("--epigraphia-birmanica-review", type=Path, default=EPIGRAPHIA_BIRMANICA_REVIEW_PATH)
    parser.add_argument("--epigraphia-birmanica-fascicle-coverage", type=Path, default=EPIGRAPHIA_BIRMANICA_FASCICLE_COVERAGE_PATH)
    parser.add_argument("--inscriptions-of-burma-text-search", type=Path, default=INSCRIPTIONS_OF_BURMA_TEXT_SEARCH_PATH)
    parser.add_argument("--witness-verification-report", type=Path, default=WITNESS_VERIFICATION_REPORT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = verify_translation_witnesses(
        witness_candidates_path=args.witness_candidates,
        witness_classification_path=args.witness_classification,
        plan_path=args.plan,
        source_work_authority_path=args.source_work_authority,
        bibliography_authority_path=args.bibliography_authority,
        raw_reference_crosswalk_path=args.raw_reference_crosswalk,
        local_file_manifest_path=args.local_file_manifest,
        source_library_manifest_path=args.source_library_manifest,
        ocr_manifest_path=args.ocr_manifest,
        ocr_text_index_path=args.ocr_text_index,
        periodical_article_plan_path=args.periodical_article_plan,
        discovery_report_path=args.discovery_report,
        witness_verification_path=args.witness_verification,
        witness_snippets_path=args.witness_snippets,
        missing_direct_search_path=args.missing_direct_search,
        source_work_gaps_path=args.source_work_gaps,
        sip_witness_inspection_path=args.sip_witness_inspection,
        uem_direct_search_path=args.uem_direct_search,
        core_source_direct_search_path=args.core_source_direct_search,
        rescue_candidate_review_path=args.rescue_candidate_review,
        epigraphia_birmanica_review_path=args.epigraphia_birmanica_review,
        epigraphia_birmanica_fascicle_coverage_path=args.epigraphia_birmanica_fascicle_coverage,
        inscriptions_of_burma_text_search_path=args.inscriptions_of_burma_text_search,
        witness_verification_report_path=args.witness_verification_report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
