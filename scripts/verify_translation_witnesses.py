from __future__ import annotations

import argparse
import json
import re
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


def search_term_match(term: str, file_record: dict) -> tuple[str, float, str] | None:
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
    term_tokens = title_keyword_tokens(term)
    if len(term_tokens) <= 1 and len(term_norm) <= 4:
        raw_blob = blob
        if re.search(rf"\b{re.escape(term)}\b", raw_blob, flags=re.IGNORECASE):
            return ("source_family_match", 0.72, f"Acronym-style search-term match for {term}")
        return None
    if term_norm in blob_norm:
        return ("exact_title_filename", 0.96, f"Exact or near-exact search-term match for {term}")
    overlap = sum(1 for token in term_tokens if token in blob_norm)
    if term_tokens and overlap >= 2 and overlap / len(term_tokens) >= 0.75:
        return ("normalized_title_filename", 0.82, f"Normalized token overlap {overlap}/{len(term_tokens)} for {term}")
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
) -> list[dict]:
    candidate_counts: dict[str, int] = defaultdict(int)
    verification_by_source: dict[str, list[dict]] = defaultdict(list)
    search_hits_by_source: dict[str, int] = defaultdict(int)
    source_by_key = {row["source_work_key"]: row for row in source_rows}

    for row in candidate_rows:
        candidate_counts[row["source_work_key"]] += 1
    for row in verification_rows:
        verification_by_source[row["source_work_key"]].append(row)
    for row in missing_search_rows:
        if row["matched_file_label"]:
            search_hits_by_source[row["source_work_key"]] += 1

    updated_rows: list[dict] = []
    for row in plan_rows:
        source_key = row["source_work_key"]
        source_row = source_by_key.get(source_key, {})
        verifications = verification_by_source.get(source_key, [])
        verified_direct_count = sum(v["verification_status"] in {"verified_direct_witness", "verified_catalogue_witness"} for v in verifications)
        verified_translation_count = sum(v["contains_translation_verified"] == "confirmed" for v in verifications)
        verified_edition_count = sum(v["contains_edition_verified"] == "confirmed" for v in verifications)
        verified_plate_count = sum(v["verification_status"] == "verified_plate_witness" for v in verifications)
        weak_false_positive_count = sum(v["verification_status"] == "weak_false_positive" for v in verifications)

        if source_key in PERIODICAL_PLAN_KEYS:
            discovery_status = "needs_article_level_discovery"
            next_action = "Inspect article-level witnesses; do not promote the series/container itself."
        elif verified_direct_count > 0:
            discovery_status = "verified_direct_witness_found"
            next_action = "Use the verified direct witness set for the next focused inspection pass."
        elif verified_plate_count > 0:
            discovery_status = "verification_in_progress"
            next_action = "Find and inspect the companion text witness before treating plate evidence as full source coverage."
        elif search_hits_by_source.get(source_key, 0) > 0 or candidate_counts.get(source_key, 0) > 0:
            discovery_status = "needs_direct_witness_search"
            next_action = "Inspect the searched local-file hits and promote only true direct witnesses."
        else:
            discovery_status = "needs_direct_witness_search"
            next_action = "Continue targeted local-file search for a direct witness."

        updated_rows.append(
            {
                **row,
                "discovery_status": discovery_status,
                "candidate_witness_count": str(candidate_counts.get(source_key, 0)),
                "classified_witness_count": str(len(verifications)),
                "confirmed_translation_witness_count": str(verified_translation_count),
                "confirmed_edition_witness_count": str(verified_edition_count),
                "confirmed_plate_witness_count": str(verified_plate_count),
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
) -> dict:
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
        "notes": [
            "Verification is stricter than candidate discovery: exact title-page, contents, or OCR-heading evidence is required before promoting translation or edition claims.",
            "Weak filename matches are retained as reviewed evidence rather than silently deleted.",
        ],
    }


def update_discovery_report(existing_report: dict, verification_report: dict) -> dict:
    updated = dict(existing_report)
    updated.update(verification_report)
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

    missing_search_rows = build_missing_direct_search_rows(
        [row for row in source_rows if row["source_work_key"] in HIGH_PRIORITY_SOURCE_KEYS],
        file_records,
    )
    updated_classification_rows = update_classification_rows(classification_rows, verification_rows)
    updated_plan_rows = update_plan_rows(plan_rows, source_rows, candidate_rows, verification_rows, missing_search_rows)
    periodical_fields, updated_periodical_plan_rows = update_periodical_plan_rows(
        plan_rows,
        source_rows,
        candidate_rows,
        verification_rows,
        raw_reference_rows,
    )
    existing_report = json.loads(discovery_report_path.read_text(encoding="utf-8")) if discovery_report_path.exists() else {}
    verification_report = build_verification_report(verification_rows, snippet_rows, missing_search_rows, updated_plan_rows)
    updated_report = update_discovery_report(existing_report, verification_report)

    witness_verification_path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(witness_verification_path, verification_rows, VERIFICATION_FIELDS)
    write_tsv(witness_snippets_path, snippet_rows, SNIPPET_FIELDS)
    write_tsv(missing_direct_search_path, missing_search_rows, MISSING_DIRECT_SEARCH_FIELDS)
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
        witness_verification_report_path=args.witness_verification_report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
