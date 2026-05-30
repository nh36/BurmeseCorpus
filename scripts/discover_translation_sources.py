from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from bibtex_common import normalize_for_match, parse_bibtex_text, surname_token, title_keyword_tokens
from corpus_common import REPO_ROOT, read_tsv, write_tsv


DISCOVERY_DIRECTORY = REPO_ROOT / "data/working/bibliography/translation_source_discovery"
PLAN_PATH = REPO_ROOT / "data/working/bibliography/translation_source_discovery_plan.tsv"
SOURCE_WORK_AUTHORITY_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/source_work_authority.tsv"
SOURCE_WORK_LOCATOR_SYSTEMS_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/source_work_locator_systems.tsv"
BIBLIOGRAPHY_AUTHORITY_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/bibliography_authority.bib"
RAW_REFERENCE_CROSSWALK_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv"
LOCAL_FILE_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/local_file_manifest.tsv"
SOURCE_LIBRARY_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/source_library_manifest.tsv"
OCR_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv"
OCR_TEXT_INDEX_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv"

WITNESS_CANDIDATE_FIELDS = [
    "witness_id",
    "source_work_key",
    "canonical_title",
    "candidate_file_label",
    "candidate_file_id",
    "candidate_path_or_redacted_path",
    "file_type",
    "match_type",
    "match_confidence",
    "match_reason",
    "sha256_if_available",
    "local_cache_status",
    "needs_human_review",
    "notes",
]

WITNESS_CLASSIFICATION_FIELDS = [
    "witness_id",
    "source_work_key",
    "canonical_title",
    "candidate_file_label",
    "witness_type",
    "contains_translation",
    "contains_edition_or_transliteration",
    "contains_plate_or_image",
    "contains_catalogue_metadata",
    "contains_secondary_discussion",
    "coverage_scope",
    "confidence",
    "evidence_source",
    "evidence_snippet",
    "needs_human_review",
    "next_action",
    "notes",
]

PERIODICAL_ARTICLE_DISCOVERY_FIELDS = [
    "series_source_work_key",
    "series_title",
    "source_family_id",
    "known_raw_reference_examples",
    "likely_article_keys_or_titles",
    "local_file_candidates",
    "priority",
    "next_action",
    "notes",
]

PLAN_DISCOVERY_FIELDS = [
    "discovery_status",
    "candidate_witness_count",
    "classified_witness_count",
    "confirmed_translation_witness_count",
    "confirmed_edition_witness_count",
    "confirmed_plate_witness_count",
    "next_review_action",
]

DISCOVERY_STATUSES = {
    "not_started",
    "candidate_witnesses_found",
    "classified_provisional",
    "needs_local_file",
    "needs_article_level_discovery",
    "blocked",
}

LIKELIHOOD_VALUES = {"unknown", "no", "possible", "confirmed"}
WITNESS_TYPES = {
    "source_edition",
    "translation_source",
    "edition_and_translation",
    "plate_volume",
    "catalogue",
    "periodical_container",
    "article_candidate",
    "secondary_work",
    "locator_collection",
    "unknown",
}
CONTAINER_TYPES = {"series", "periodical"}
HIGH_PRIORITY_SOURCE_KEYS = {
    "lucePeMaungTinInscriptionsOfBurma",
    "sipSelectionsPagan",
    "uemSelectionsPagan",
    "tnInscriptionsPaganPinyaAva",
    "ppaCatalogue",
    "ubSourceFamily",
    "duroiselle1921list",
    "epigraphiaBirmanica",
    "journalBurmaResearchSociety",
    "journalRoyalAsiaticSociety",
    "bulletinBurmaHistoricalCommission",
    "annualReportsArchaeologicalSurveyIndia",
}
PERIODICAL_PLAN_KEYS = [
    "journalBurmaResearchSociety",
    "journalRoyalAsiaticSociety",
    "bulletinBurmaHistoricalCommission",
    "annualReportsArchaeologicalSurveyIndia",
    "epigraphiaBirmanica",
]
ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")


def split_multi(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def normalize_token_set(value: str | None) -> set[str]:
    return set(title_keyword_tokens(value))


def safe_path_value(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    if ABSOLUTE_PATH_PATTERN.search(value):
        return Path(value).name or fallback
    return value


def compact_join(values: list[str], *, limit: int = 4) -> str:
    items: list[str] = []
    for value in values:
        if value and value not in items:
            items.append(value)
        if len(items) >= limit:
            break
    return " | ".join(items)


def truncate_snippet(value: str | None, *, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def bool_string(value: bool) -> str:
    return "true" if value else "false"


def confidence_label(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.7:
        return "medium"
    return "low"


def is_abbreviation_like(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return bool(re.fullmatch(r"[A-Z0-9.()-]{2,}", text))


def slugify_fragment(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "witness"


def load_optional_tsv(path: Path) -> tuple[list[dict], bool]:
    if not path.exists():
        return [], False
    return read_tsv(path), True


def load_bibtex_entries(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    entries, _warnings = parse_bibtex_text(path.read_text(encoding="utf-8"), source_label=path.name)
    return {entry.get("bibtex_key", ""): entry for entry in entries if entry.get("bibtex_key")}


def build_source_rows(plan_rows: list[dict], source_work_rows: list[dict], bibtex_entries: dict[str, dict]) -> list[dict]:
    source_by_key = {row["source_work_key"]: row for row in source_work_rows}
    merged_rows: list[dict] = []
    for plan_row in plan_rows:
        key = plan_row["source_work_key"]
        source_row = source_by_key.get(key, {})
        merged = {**plan_row, **source_row}
        merged["source_work_key"] = key
        merged["canonical_title"] = merged.get("canonical_title") or plan_row.get("canonical_title") or source_row.get("canonical_title", "")
        merged["source_family_ids"] = split_multi(merged.get("source_family_ids") or merged.get("related_source_family_ids"))
        merged["acronyms"] = split_multi(merged.get("related_acronyms"))
        merged["bibtex_entry"] = bibtex_entries.get(merged.get("bibtex_key", ""))
        merged["title_tokens"] = title_keyword_tokens(merged.get("canonical_title"))
        merged["author_surname"] = surname_token(merged.get("authors_editors"))
        merged["is_container"] = merged.get("authority_level") in CONTAINER_TYPES or merged.get("work_type") in CONTAINER_TYPES
        merged_rows.append(merged)
    return merged_rows


def build_file_records(
    local_file_rows: list[dict],
    source_library_rows: list[dict],
    ocr_manifest_rows: list[dict],
    ocr_index_rows: list[dict],
) -> dict[str, dict]:
    records: dict[str, dict] = {}
    path_to_id: dict[str, str] = {}
    sha_to_id: dict[str, str] = {}

    for row in local_file_rows:
        file_id = row.get("canonical_local_file_id") or slugify_fragment(row.get("file_name") or row.get("copied_path") or "")
        record = {
            "candidate_file_id": file_id,
            "candidate_file_label": row.get("file_name") or Path(row.get("copied_path") or "").name or file_id,
            "candidate_path_or_redacted_path": safe_path_value(row.get("copied_path") or row.get("primary_original_path"), row.get("file_name") or file_id),
            "file_type": row.get("file_type") or Path(row.get("file_name") or "").suffix.lstrip("."),
            "sha256_if_available": row.get("sha256", ""),
            "local_cache_status": row.get("copy_status") or "unknown",
            "source_folder_hints": row.get("source_folder_hints", ""),
            "all_original_paths": row.get("all_original_paths", ""),
            "primary_original_path": row.get("primary_original_path", ""),
            "evidence_priority": row.get("evidence_priority", ""),
            "source_library_rows": [],
            "ocr_manifest_row": None,
            "ocr_snippets": [],
        }
        record["search_blob"] = " || ".join(
            [
                record["candidate_file_label"],
                record["candidate_path_or_redacted_path"],
                record["source_folder_hints"],
                record["all_original_paths"],
            ]
        )
        records[file_id] = record
        if row.get("copied_path"):
            path_to_id[row["copied_path"]] = file_id
        if row.get("sha256"):
            sha_to_id[row["sha256"]] = file_id

    for row in source_library_rows:
        file_id = ""
        copied_path = row.get("copied_path", "")
        sha256_value = row.get("sha256", "")
        if copied_path and copied_path in path_to_id:
            file_id = path_to_id[copied_path]
        elif sha256_value and sha256_value in sha_to_id:
            file_id = sha_to_id[sha256_value]
        else:
            file_id = slugify_fragment(row.get("file_name") or row.get("original_path") or row.get("bibtex_key"))
            records[file_id] = {
                "candidate_file_id": file_id,
                "candidate_file_label": row.get("file_name") or Path(copied_path or row.get("original_path") or "").name or file_id,
                "candidate_path_or_redacted_path": safe_path_value(copied_path or row.get("original_path"), row.get("file_name") or file_id),
                "file_type": Path(row.get("file_name") or "").suffix.lstrip("."),
                "sha256_if_available": sha256_value,
                "local_cache_status": "matched_only",
                "source_folder_hints": "",
                "all_original_paths": row.get("original_path", ""),
                "primary_original_path": row.get("original_path", ""),
                "evidence_priority": row.get("match_confidence", ""),
                "source_library_rows": [],
                "ocr_manifest_row": None,
                "ocr_snippets": [],
                "search_blob": " || ".join(
                    [
                        row.get("file_name", ""),
                        row.get("original_path", ""),
                        copied_path,
                    ]
                ),
            }
        records[file_id]["source_library_rows"].append(row)

    for row in ocr_manifest_rows:
        file_id = row.get("source_file_id", "")
        if not file_id:
            continue
        if file_id not in records:
            records[file_id] = {
                "candidate_file_id": file_id,
                "candidate_file_label": row.get("source_file_label") or file_id,
                "candidate_path_or_redacted_path": safe_path_value(row.get("source_path"), row.get("source_file_label") or file_id),
                "file_type": row.get("file_type", ""),
                "sha256_if_available": "",
                "local_cache_status": row.get("extraction_status") or "ocr_only",
                "source_folder_hints": "",
                "all_original_paths": row.get("source_path", ""),
                "primary_original_path": row.get("source_path", ""),
                "evidence_priority": "",
                "source_library_rows": [],
                "ocr_manifest_row": None,
                "ocr_snippets": [],
                "search_blob": " || ".join([row.get("source_file_label", ""), row.get("source_path", "")]),
            }
        records[file_id]["ocr_manifest_row"] = row
        if row.get("source_path"):
            records[file_id]["search_blob"] += " || " + row["source_path"]

    for row in ocr_index_rows:
        file_id = row.get("source_file_id", "")
        if file_id in records:
            records[file_id]["ocr_snippets"].append(row)

    return records


def find_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.casefold()
    return [keyword for keyword in keywords if keyword in lowered]


def choose_ocr_evidence(file_record: dict) -> tuple[str, str]:
    ranked_keywords = [
        "english translation",
        "translation",
        "translated",
        "transliteration",
        "transcription",
        "inscription",
        "plate",
        "facsimile",
        "catalogue",
        "list",
        "bibliography",
        "notes",
    ]
    for row in file_record.get("ocr_snippets", []):
        snippet = row.get("snippet_text", "")
        hits = find_keyword_hits(snippet, ranked_keywords)
        if hits:
            return "ocr_text_index", truncate_snippet(snippet)
    first = next(iter(file_record.get("ocr_snippets", [])), None)
    if first:
        return "ocr_text_index", truncate_snippet(first.get("snippet_text", ""))
    return "", ""


def is_article_specific(file_record: dict) -> bool:
    paths = file_record.get("all_original_paths", "")
    for part in paths.split(" | "):
        name = Path(part.split(":", 1)[-1]).name
        if len(re.sub(r"[^A-Za-z]", "", name)) >= 8 and not re.fullmatch(r"\d+\.pdf", name.casefold()):
            return True
    label = file_record.get("candidate_file_label", "")
    return len(re.sub(r"[^A-Za-z]", "", label)) >= 8 and not re.fullmatch(r"\d+\.pdf", label.casefold())


def match_source_work_to_file(source_work: dict, file_record: dict) -> dict | None:
    raw_blob = file_record.get("search_blob", "")
    normalized_blob = normalize_for_match(raw_blob)
    title_normalized = normalize_for_match(source_work.get("canonical_title"))
    title_tokens = source_work.get("title_tokens") or title_keyword_tokens(source_work.get("canonical_title"))
    acronym_hits = []
    best_match_type = ""
    best_score = 0.0
    reasons: list[str] = []

    if title_normalized and title_normalized in normalized_blob:
        best_match_type = "exact_title_filename"
        best_score = 0.96
        reasons.append(f"Exact title match in local filename/path: {source_work.get('canonical_title')}")

    overlap_count = sum(1 for token in title_tokens if token in normalized_blob)
    overlap_ratio = overlap_count / max(len(title_tokens), 1)
    if overlap_count >= 2 and overlap_ratio >= 0.6 and best_score < 0.85:
        best_match_type = "normalized_title_filename"
        best_score = 0.83
        reasons.append(f"Normalized title-token overlap {overlap_count}/{len(title_tokens)}")

    author_surname = source_work.get("author_surname", "")
    if author_surname and author_surname in normalized_blob and overlap_count >= 1 and best_score < 0.7:
        best_match_type = "weak_keyword_match"
        best_score = 0.62
        reasons.append(f"Author surname and title keywords overlap for {author_surname}")

    for acronym in source_work.get("acronyms", []):
        if not is_abbreviation_like(acronym):
            continue
        if re.search(rf"\b{re.escape(acronym)}\b", raw_blob, flags=re.IGNORECASE):
            acronym_hits.append(acronym)
    if acronym_hits and best_score < 0.78:
        best_match_type = "source_family_match"
        best_score = 0.76
        reasons.append(f"Acronym/source-family token match: {', '.join(acronym_hits[:3])}")

    for row in file_record.get("source_library_rows", []):
        if row.get("bibtex_key") == source_work.get("bibtex_key"):
            if best_score < 0.74:
                best_match_type = "known_local_source"
                best_score = 0.74
            reasons.append("Existing source-library manifest match")
            break

    if source_work.get("is_container"):
        container_terms = [source_work.get("canonical_title", ""), source_work.get("short_title", "")] + source_work.get("acronyms", [])
        if any(term and normalize_for_match(term) in normalized_blob for term in container_terms):
            if best_score < 0.7:
                best_match_type = "series_container_match"
                best_score = 0.68
            reasons.append("Series/container title visible in local path hints")

    if best_score == 0.0:
        return None

    if file_record.get("evidence_priority") == "high":
        best_score += 0.02
    if file_record.get("ocr_manifest_row"):
        best_score += 0.02
    best_score = min(best_score, 0.99)

    return {
        "match_type": best_match_type,
        "score": best_score,
        "match_confidence": confidence_label(best_score),
        "match_reason": compact_join(reasons, limit=3),
    }


def build_witness_id(source_work_key: str, candidate_file_id: str) -> str:
    return f"{source_work_key}--{slugify_fragment(candidate_file_id)}"


def classify_candidate_witness(source_work: dict, candidate_row: dict, file_record: dict) -> dict:
    label_blob = " ".join(
        [
            candidate_row.get("candidate_file_label", ""),
            file_record.get("source_folder_hints", ""),
            file_record.get("all_original_paths", ""),
        ]
    )
    normalized_label = normalize_for_match(label_blob)
    evidence_source = "filename"
    evidence_snippet = truncate_snippet(candidate_row.get("candidate_file_label", ""))
    ocr_source, ocr_snippet = choose_ocr_evidence(file_record)
    has_ocr_evidence = bool(ocr_snippet)
    if ocr_snippet:
        evidence_source = f"{evidence_source}+{ocr_source}"
        evidence_snippet = ocr_snippet

    translation = "unknown"
    edition = "unknown"
    plates = "unknown"
    catalogue = "unknown"
    discussion = "unknown"
    witness_type = "unknown"
    coverage_scope = "unknown"
    notes: list[str] = []

    if source_work.get("is_container"):
        if is_article_specific(file_record):
            witness_type = "article_candidate"
            discussion = "possible"
            coverage_scope = "single_inscription" if "inscription" in normalized_label else "unknown"
            notes.append("Container match looks article-specific and needs article-level inspection.")
        else:
            witness_type = "periodical_container"
            discussion = "possible"
            coverage_scope = "series_container"
            notes.append("Container witness kept at series/periodical level pending article discovery.")
    elif "plate" in normalized_label or "plates" in normalized_label or "facsimile" in normalized_label:
        witness_type = "plate_volume"
        plates = "confirmed"
        edition = "unknown"
        coverage_scope = "selected_inscriptions"
        notes.append("Plate/file title indicates image or facsimile coverage.")
    elif source_work.get("work_type") == "source_catalogue" or "catalogue" in normalized_label or "list of inscriptions" in normalized_label:
        witness_type = "catalogue"
        catalogue = "confirmed"
        edition = "possible"
        coverage_scope = "whole_work"
        notes.append("Catalogue-style source work kept distinct from direct translation evidence.")
    elif candidate_row.get("match_type") == "exact_title_filename" and source_work.get("work_type") in {"book", "source_work"}:
        witness_type = "source_edition"
        edition = "possible"
        coverage_scope = "selected_inscriptions" if "selection" in normalized_label else "whole_work"
    elif candidate_row.get("match_type") == "source_family_match" and any(
        is_abbreviation_like(acronym)
        and re.search(rf"\b{re.escape(acronym)}\b", candidate_row.get("candidate_file_label", ""), flags=re.IGNORECASE)
        for acronym in source_work.get("acronyms", [])
    ):
        witness_type = "source_edition"
        edition = "possible"
        coverage_scope = "selected_inscriptions" if "selection" in normalized_label else "whole_work"
        notes.append("Filename exposes the source-work acronym directly, but edition scope still needs inspection.")
    else:
        witness_type = "secondary_work"
        discussion = "possible"
        coverage_scope = "unknown"
        notes.append("Matched witness looks related but not yet like a direct source edition.")

    translation_keywords = ["english translation", "translation", "translated"]
    if any(keyword in evidence_snippet.casefold() for keyword in translation_keywords):
        translation = "confirmed"
        if witness_type == "source_edition":
            witness_type = "edition_and_translation"
        elif witness_type not in {"periodical_container", "article_candidate"}:
            witness_type = "translation_source"
        notes.append("Short OCR/file evidence explicitly mentions translation.")
    elif source_work.get("translation_likelihood") in {"high", "possible"} and witness_type in {
        "source_edition",
        "catalogue",
        "unknown",
    }:
        translation = "possible"
        notes.append("Translation relevance remains provisional until the witness is inspected directly.")

    edition_keywords = ["transliteration", "transcription", "full text", "inscription", "edited text"]
    if has_ocr_evidence and edition != "confirmed" and any(keyword in evidence_snippet.casefold() for keyword in edition_keywords):
        edition = "confirmed"
        if translation == "confirmed":
            witness_type = "edition_and_translation"
        elif witness_type == "unknown":
            witness_type = "source_edition"
        notes.append("OCR/file evidence suggests text or transliteration content.")
    elif edition == "unknown" and source_work.get("edition_likelihood") in {"high", "possible"} and witness_type in {"source_edition", "catalogue"}:
        edition = "possible"

    if plates == "unknown" and source_work.get("plate_or_image_likelihood") in {"high", "medium"}:
        plates = "possible" if witness_type in {"source_edition", "catalogue"} else "unknown"

    if catalogue == "unknown" and source_work.get("work_type") == "source_catalogue":
        catalogue = "possible"

    if discussion == "unknown" and witness_type in {"secondary_work", "article_candidate"}:
        discussion = "possible"

    if witness_type == "periodical_container":
        translation = "unknown"
        edition = "unknown"
        plates = "possible" if source_work.get("plate_or_image_likelihood") in {"medium", "high"} else "unknown"
        catalogue = "no"

    confidence = candidate_row.get("match_confidence", "low")
    next_action = {
        "source_edition": "Inspect title page, contents, and sample pages for edition/translation boundaries.",
        "edition_and_translation": "Verify the extent of published translation coverage and map inscription scope.",
        "translation_source": "Confirm whether the translation is full, partial, or excerpted.",
        "plate_volume": "Review plates/images and confirm whether companion text volumes are also needed.",
        "catalogue": "Check whether this catalogue includes edited text or only metadata/locators.",
        "periodical_container": "Use raw references and local article files to identify article-level witnesses.",
        "article_candidate": "Inspect the article directly before promoting any translation or edition claim.",
        "secondary_work": "Confirm whether this is only secondary discussion or a lead to a better source witness.",
        "unknown": "Inspect the file directly and refine the witness classification.",
    }[witness_type]

    return {
        "witness_id": candidate_row["witness_id"],
        "source_work_key": candidate_row["source_work_key"],
        "canonical_title": candidate_row["canonical_title"],
        "candidate_file_label": candidate_row["candidate_file_label"],
        "witness_type": witness_type,
        "contains_translation": translation,
        "contains_edition_or_transliteration": edition,
        "contains_plate_or_image": plates,
        "contains_catalogue_metadata": catalogue,
        "contains_secondary_discussion": discussion,
        "coverage_scope": coverage_scope,
        "confidence": confidence,
        "evidence_source": evidence_source,
        "evidence_snippet": evidence_snippet,
        "needs_human_review": candidate_row["needs_human_review"],
        "next_action": next_action,
        "notes": compact_join(notes, limit=3),
    }


def build_periodical_article_plan(
    source_rows: list[dict],
    witness_candidates: list[dict],
    witness_classifications: list[dict],
    raw_reference_rows: list[dict],
) -> list[dict]:
    candidates_by_source: dict[str, list[dict]] = defaultdict(list)
    classification_by_id = {row["witness_id"]: row for row in witness_classifications}
    for row in witness_candidates:
        candidates_by_source[row["source_work_key"]].append(row)

    raw_refs_by_source: dict[str, list[str]] = defaultdict(list)
    for row in raw_reference_rows:
        source_key = row.get("source_work_key", "")
        if source_key:
            raw_refs_by_source[source_key].append(row.get("raw_reference_string", ""))

    rows: list[dict] = []
    for source_row in source_rows:
        if source_row["source_work_key"] not in PERIODICAL_PLAN_KEYS:
            continue
        source_key = source_row["source_work_key"]
        candidate_labels: list[str] = []
        likely_titles: list[str] = []
        for candidate in sorted(candidates_by_source.get(source_key, []), key=lambda row: row["candidate_file_label"]):
            candidate_labels.append(f'{candidate["candidate_file_id"]}:{candidate["candidate_file_label"]}')
            classification = classification_by_id.get(candidate["witness_id"])
            if classification and classification.get("witness_type") == "article_candidate":
                likely_titles.append(candidate["candidate_file_label"])
        raw_examples = raw_refs_by_source.get(source_key, [])
        if not likely_titles:
            for raw_reference in raw_examples:
                prefix = raw_reference.split(",", 1)[0].strip()
                if prefix and prefix not in likely_titles:
                    likely_titles.append(prefix)
                if len(likely_titles) >= 4:
                    break
        rows.append(
            {
                "series_source_work_key": source_key,
                "series_title": source_row.get("canonical_title", ""),
                "source_family_id": split_multi(source_row.get("related_source_family_ids"))[0] if source_row.get("related_source_family_ids") else "",
                "known_raw_reference_examples": compact_join(raw_examples, limit=4),
                "likely_article_keys_or_titles": compact_join(likely_titles, limit=4),
                "local_file_candidates": compact_join(candidate_labels, limit=5),
                "priority": source_row.get("priority", ""),
                "next_action": "Inspect article-level candidates before treating the container as a translation witness.",
                "notes": "Series/container rows remain discovery containers rather than direct translation witnesses.",
            }
        )
    return rows


def update_plan_rows(
    plan_rows: list[dict],
    source_rows: list[dict],
    witness_candidates: list[dict],
    witness_classifications: list[dict],
) -> list[dict]:
    candidate_counts: dict[str, int] = defaultdict(int)
    classified_counts: dict[str, int] = defaultdict(int)
    confirmed_translation_counts: dict[str, int] = defaultdict(int)
    confirmed_edition_counts: dict[str, int] = defaultdict(int)
    confirmed_plate_counts: dict[str, int] = defaultdict(int)
    classification_by_source: dict[str, list[dict]] = defaultdict(list)

    for row in witness_candidates:
        candidate_counts[row["source_work_key"]] += 1
    for row in witness_classifications:
        source_key = row["source_work_key"]
        classified_counts[source_key] += 1
        classification_by_source[source_key].append(row)
        if row.get("contains_translation") == "confirmed":
            confirmed_translation_counts[source_key] += 1
        if row.get("contains_edition_or_transliteration") == "confirmed":
            confirmed_edition_counts[source_key] += 1
        if row.get("contains_plate_or_image") == "confirmed":
            confirmed_plate_counts[source_key] += 1

    source_by_key = {row["source_work_key"]: row for row in source_rows}
    updated_rows: list[dict] = []
    for plan_row in plan_rows:
        source_key = plan_row["source_work_key"]
        source_row = source_by_key.get(source_key, {})
        candidates = candidate_counts.get(source_key, 0)
        classified = classified_counts.get(source_key, 0)
        if source_row.get("is_container"):
            status = "needs_article_level_discovery"
            next_action = "Review article-level files and raw references before assigning translation relevance."
        elif classified:
            status = "classified_provisional"
            next_action = "Inspect the highest-confidence witnesses to confirm edition/translation scope."
        elif candidates:
            status = "candidate_witnesses_found"
            next_action = "Classify the located witnesses conservatively and check OCR/title-page evidence."
        else:
            status = "needs_local_file"
            next_action = "Find or harvest a local witness before claiming edition or translation coverage."
        updated_rows.append(
            {
                **plan_row,
                "discovery_status": status,
                "candidate_witness_count": str(candidates),
                "classified_witness_count": str(classified),
                "confirmed_translation_witness_count": str(confirmed_translation_counts.get(source_key, 0)),
                "confirmed_edition_witness_count": str(confirmed_edition_counts.get(source_key, 0)),
                "confirmed_plate_witness_count": str(confirmed_plate_counts.get(source_key, 0)),
                "next_review_action": next_action,
            }
        )
    return updated_rows


def build_report(
    plan_rows: list[dict],
    witness_candidates: list[dict],
    witness_classifications: list[dict],
    periodical_plan_rows: list[dict],
    missing_inputs: list[str],
) -> dict:
    source_works_with_candidates = {row["source_work_key"] for row in witness_candidates}
    confirmed_translation_count = sum(row.get("contains_translation") == "confirmed" for row in witness_classifications)
    possible_translation_count = sum(row.get("contains_translation") == "possible" for row in witness_classifications)
    confirmed_edition_count = sum(row.get("contains_edition_or_transliteration") == "confirmed" for row in witness_classifications)
    possible_edition_count = sum(row.get("contains_edition_or_transliteration") == "possible" for row in witness_classifications)
    plate_count = sum(row.get("contains_plate_or_image") in {"possible", "confirmed"} for row in witness_classifications)
    periodical_container_count = sum(row.get("witness_type") == "periodical_container" for row in witness_classifications)
    blocked_count = sum(row.get("discovery_status") == "blocked" for row in plan_rows)
    return {
        "source_work_count": len(plan_rows),
        "source_works_with_candidate_witnesses": len(source_works_with_candidates),
        "candidate_witness_count": len(witness_candidates),
        "classified_witness_count": len(witness_classifications),
        "confirmed_translation_witness_count": confirmed_translation_count,
        "possible_translation_witness_count": possible_translation_count,
        "confirmed_edition_witness_count": confirmed_edition_count,
        "possible_edition_witness_count": possible_edition_count,
        "plate_or_image_witness_count": plate_count,
        "periodical_container_count": periodical_container_count,
        "article_discovery_needed_count": len(periodical_plan_rows),
        "blocked_source_work_count": blocked_count,
        "notes": [
            "Discovery output is conservative: titles and short OCR snippets guide witness classification, but they do not prove full translation coverage.",
            *[f"Missing optional input: {path}" for path in missing_inputs],
        ],
    }


def discover_translation_sources(
    *,
    plan_path: Path = PLAN_PATH,
    source_work_authority_path: Path = SOURCE_WORK_AUTHORITY_PATH,
    source_work_locator_systems_path: Path = SOURCE_WORK_LOCATOR_SYSTEMS_PATH,
    bibliography_authority_path: Path = BIBLIOGRAPHY_AUTHORITY_PATH,
    local_file_manifest_path: Path = LOCAL_FILE_MANIFEST_PATH,
    source_library_manifest_path: Path = SOURCE_LIBRARY_MANIFEST_PATH,
    ocr_manifest_path: Path = OCR_MANIFEST_PATH,
    ocr_text_index_path: Path = OCR_TEXT_INDEX_PATH,
    raw_reference_crosswalk_path: Path = RAW_REFERENCE_CROSSWALK_PATH,
    output_directory: Path = DISCOVERY_DIRECTORY,
) -> dict:
    del source_work_locator_systems_path  # kept as an explicit phase input even though matching is source-work driven
    plan_rows = read_tsv(plan_path)
    source_work_rows = read_tsv(source_work_authority_path)
    bibtex_entries = load_bibtex_entries(bibliography_authority_path)
    local_file_rows, local_manifest_exists = load_optional_tsv(local_file_manifest_path)
    source_library_rows, source_library_exists = load_optional_tsv(source_library_manifest_path)
    ocr_manifest_rows, ocr_manifest_exists = load_optional_tsv(ocr_manifest_path)
    ocr_index_rows, ocr_index_exists = load_optional_tsv(ocr_text_index_path)
    raw_reference_rows = read_tsv(raw_reference_crosswalk_path)
    missing_inputs = [
        str(path.relative_to(REPO_ROOT))
        for path, exists in [
            (local_file_manifest_path, local_manifest_exists),
            (source_library_manifest_path, source_library_exists),
            (ocr_manifest_path, ocr_manifest_exists),
            (ocr_text_index_path, ocr_index_exists),
        ]
        if not exists
    ]

    source_rows = [
        row for row in build_source_rows(plan_rows, source_work_rows, bibtex_entries) if row.get("source_work_key") in HIGH_PRIORITY_SOURCE_KEYS
    ]
    file_records = build_file_records(local_file_rows, source_library_rows, ocr_manifest_rows, ocr_index_rows)

    witness_candidates: list[dict] = []
    witness_classifications: list[dict] = []
    for source_row in source_rows:
        matched_candidates: list[tuple[dict, dict]] = []
        for file_record in file_records.values():
            match = match_source_work_to_file(source_row, file_record)
            if match:
                matched_candidates.append((match, file_record))
        matched_candidates.sort(
            key=lambda item: (
                -item[0]["score"],
                item[1].get("candidate_file_label", "").casefold(),
            )
        )
        limit = 5 if source_row.get("is_container") else 4
        kept_ids: set[str] = set()
        for match, file_record in matched_candidates:
            file_id = file_record["candidate_file_id"]
            if file_id in kept_ids:
                continue
            kept_ids.add(file_id)
            candidate_row = {
                "witness_id": build_witness_id(source_row["source_work_key"], file_id),
                "source_work_key": source_row["source_work_key"],
                "canonical_title": source_row.get("canonical_title", ""),
                "candidate_file_label": file_record.get("candidate_file_label", ""),
                "candidate_file_id": file_id,
                "candidate_path_or_redacted_path": file_record.get("candidate_path_or_redacted_path", ""),
                "file_type": file_record.get("file_type", ""),
                "match_type": match["match_type"],
                "match_confidence": match["match_confidence"],
                "match_reason": match["match_reason"],
                "sha256_if_available": file_record.get("sha256_if_available", ""),
                "local_cache_status": file_record.get("local_cache_status", ""),
                "needs_human_review": bool_string(
                    source_row.get("needs_human_review") == "true"
                    or match["match_confidence"] != "high"
                    or source_row.get("is_container")
                ),
                "notes": compact_join(
                    [
                        source_row.get("notes", ""),
                        next(
                            (row.get("notes", "") for row in file_record.get("source_library_rows", []) if row.get("bibtex_key") == source_row.get("bibtex_key")),
                            "",
                        ),
                    ],
                    limit=2,
                ),
            }
            witness_candidates.append(candidate_row)
            witness_classifications.append(classify_candidate_witness(source_row, candidate_row, file_record))
            if len(kept_ids) >= limit:
                break

    updated_plan_rows = update_plan_rows(plan_rows, source_rows, witness_candidates, witness_classifications)
    periodical_plan_rows = build_periodical_article_plan(source_rows, witness_candidates, witness_classifications, raw_reference_rows)
    report = build_report(updated_plan_rows, witness_candidates, witness_classifications, periodical_plan_rows, missing_inputs)

    output_directory.mkdir(parents=True, exist_ok=True)
    write_tsv(output_directory / "witness_candidates.tsv", witness_candidates, WITNESS_CANDIDATE_FIELDS)
    write_tsv(output_directory / "witness_classification.tsv", witness_classifications, WITNESS_CLASSIFICATION_FIELDS)
    write_tsv(output_directory / "periodical_article_discovery_plan.tsv", periodical_plan_rows, PERIODICAL_ARTICLE_DISCOVERY_FIELDS)

    plan_fields = list(plan_rows[0].keys()) + [field for field in PLAN_DISCOVERY_FIELDS if field not in plan_rows[0]]
    write_tsv(plan_path, updated_plan_rows, plan_fields)

    report_path = output_directory / "translation_source_discovery_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover local witness candidates for translation-source review.")
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--source-work-authority", type=Path, default=SOURCE_WORK_AUTHORITY_PATH)
    parser.add_argument("--source-work-locator-systems", type=Path, default=SOURCE_WORK_LOCATOR_SYSTEMS_PATH)
    parser.add_argument("--bibliography-authority", type=Path, default=BIBLIOGRAPHY_AUTHORITY_PATH)
    parser.add_argument("--local-file-manifest", type=Path, default=LOCAL_FILE_MANIFEST_PATH)
    parser.add_argument("--source-library-manifest", type=Path, default=SOURCE_LIBRARY_MANIFEST_PATH)
    parser.add_argument("--ocr-manifest", type=Path, default=OCR_MANIFEST_PATH)
    parser.add_argument("--ocr-text-index", type=Path, default=OCR_TEXT_INDEX_PATH)
    parser.add_argument("--raw-reference-crosswalk", type=Path, default=RAW_REFERENCE_CROSSWALK_PATH)
    parser.add_argument("--output-directory", type=Path, default=DISCOVERY_DIRECTORY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = discover_translation_sources(
        plan_path=args.plan,
        source_work_authority_path=args.source_work_authority,
        source_work_locator_systems_path=args.source_work_locator_systems,
        bibliography_authority_path=args.bibliography_authority,
        local_file_manifest_path=args.local_file_manifest,
        source_library_manifest_path=args.source_library_manifest,
        ocr_manifest_path=args.ocr_manifest,
        ocr_text_index_path=args.ocr_text_index,
        raw_reference_crosswalk_path=args.raw_reference_crosswalk,
        output_directory=args.output_directory,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
