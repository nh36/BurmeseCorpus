from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from corpus_common import normalize_whitespace, parse_number_token, read_jsonl, read_tsv, write_tsv
from jbrs_workflow_common import (
    CORPUS_CITATION_EXTRACTION_STATUSES,
    CORPUS_CITATION_INVENTORY_FIELDS,
    CORPUS_CITATION_INVENTORY_PATH,
    CORPUS_CITATION_LANGUAGE_SCOPES,
    CORPUS_CITATION_MATCH_STATUSES,
    CORPUS_CITATION_SOURCE_FILE_MATCH_FIELDS,
    CORPUS_CITATION_SOURCE_FILE_MATCH_PATH,
    CORPUS_CITATION_SOURCE_TYPES,
    CORPUS_CITATION_TARGET_FIELDS,
    CORPUS_CITATION_TARGET_PRIORITIES,
    CORPUS_CITATION_TARGETS_PATH,
    CORPUS_CITED_SOURCE_OCR_QUEUE_FIELDS,
    CORPUS_CITED_SOURCE_OCR_QUEUE_PATH,
    CORPUS_TRANSLATION_SOURCE_DASHBOARD_FIELDS,
    CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH,
    EXTRACTED_SOURCE_TEXT_UNIT_FIELDS,
    EXTRACTED_TRANSLATION_UNIT_FIELDS,
    JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH,
    JBRS_EXTRACTED_TRANSLATION_UNITS_PATH,
    JBRS_LOCAL_FILE_MANIFEST_PATH,
    JBRS_OCR_TEXT_INDEX_PATH,
    LOCAL_FILE_MANIFEST_PATH,
    SOURCE_LIBRARY_MANIFEST_PATH,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_INSCRIPTIONS_PATH = REPO_ROOT / "data/release/corpus_release_v0_3/inscriptions.jsonl"
RAW_REFERENCE_TO_BIBTEX_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv"
SOURCE_WORK_AUTHORITY_PATH = REPO_ROOT / "data/working/bibliography/bibtex_authority/source_work_authority.tsv"

STOP_WORDS = {
    "a",
    "an",
    "and",
    "article",
    "burma",
    "burmese",
    "for",
    "from",
    "in",
    "inscription",
    "inscriptions",
    "journal",
    "of",
    "on",
    "or",
    "society",
    "study",
    "studies",
    "the",
    "to",
    "vol",
    "volume",
}
TRANSLATION_KEYWORDS = ("translation", "translated", "version in", "english version", "four languages")
TEXT_KEYWORDS = (
    "inscription",
    "inscriptions",
    "text",
    "texts",
    "source text",
    "transliteration",
    "transcription",
    "romanized",
    "edition",
)
TRANSCRIPTION_KEYWORDS = ("transcription", "transliteration", "romanized")
EDITION_KEYWORDS = ("edition", "edited", "corpus", "selections from", "inscriptions of", "epigraphia")
PLATE_KEYWORDS = ("plate", "plates", "pl.", "rubbing", "facsimile")
COMMENTARY_KEYWORDS = (
    "history",
    "survey",
    "notes on",
    "buddhism",
    "civilization",
    "geography",
    "chapter",
)
NON_BURMESE_SCOPES = {"Pali", "Mon", "Pyu"}
BURMESE_RELEVANT_SCOPES = {"Burmese", "Old Burmese", "Mixed Burmese/Pali"}


def normalize(value: str | None) -> str:
    return normalize_whitespace(value or "")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def safe_slug(value: str) -> str:
    lowered = re.sub(r"[^0-9a-z]+", "-", normalize(value).casefold()).strip("-")
    return lowered or "unknown"


def citation_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", normalize(value).casefold())
        if len(token) >= 3 and token not in STOP_WORDS
    }
    return tokens


def first_year(*values: str) -> str:
    for value in values:
        match = re.search(r"(1[89][0-9]{2}|20[0-9]{2})", value or "")
        if match:
            return match.group(1)
    return ""


def source_abbreviation(raw_row: dict[str, str], source_row: dict[str, str] | None, citation_raw: str) -> str:
    if source_row:
        acronym = normalize(source_row.get("related_acronyms", ""))
        if acronym:
            return acronym.split("|", 1)[0].split(",", 1)[0].strip()
        short_title = normalize(source_row.get("short_title", ""))
        if short_title:
            return short_title
    locator = normalize(raw_row.get("locator", ""))
    for candidate in (citation_raw, locator):
        match = re.match(r"([A-Z][A-Z.0-9 -]{1,20})", candidate)
        if match:
            return match.group(1).strip(" ,;-")
    return ""


def split_locator(locator: str) -> tuple[str, str]:
    locator = normalize(locator)
    if not locator:
        return "", ""
    match = re.search(r"\b(p(?:p)?\.|page|pages|plate|plates|pl\.)\b", locator, flags=re.IGNORECASE)
    if not match:
        return locator, ""
    index = match.start()
    volume_issue = normalize(locator[:index].strip(" ,;"))
    page_or_plate = normalize(locator[index:])
    return volume_issue, page_or_plate


def language_scope_from_record(record: dict[str, str]) -> str:
    value = normalize(record.get("language_original", ""))
    lowered = value.casefold()
    if "mya" in lowered or "burmese" in lowered:
        return "Old Burmese"
    if "pali" in lowered:
        return "Pali"
    if "mon" in lowered:
        return "Mon"
    if "pyu" in lowered:
        return "Pyu"
    if not lowered:
        return "unknown"
    return "mixed_or_uncertain"


def aggregate_language_scope(scopes: set[str]) -> str:
    filtered = {scope for scope in scopes if scope}
    if not filtered:
        return "unknown"
    if filtered <= {"Old Burmese", "Burmese"}:
        return "Old Burmese" if "Old Burmese" in filtered else "Burmese"
    if filtered <= {"Old Burmese", "Burmese", "Pali", "Mixed Burmese/Pali"}:
        return "Mixed Burmese/Pali"
    if len(filtered) == 1:
        return next(iter(filtered))
    return "mixed_or_uncertain"


def citation_content_flags(citation_raw: str, title: str, source_type: str) -> dict[str, str]:
    raw_haystack = citation_raw.casefold()
    title_haystack = title.casefold()
    haystack = f"{raw_haystack} {title_haystack}"
    title_looks_commentary = (
        any(keyword in title_haystack for keyword in COMMENTARY_KEYWORDS)
        and not any(keyword in title_haystack for keyword in TEXT_KEYWORDS)
        and not any(keyword in title_haystack for keyword in TRANSLATION_KEYWORDS)
    )
    if title_looks_commentary and source_type in {"article", "book", "unclear"}:
        mentions_translation = False
        mentions_transcription = False
        mentions_rubbing = any(keyword in title_haystack for keyword in PLATE_KEYWORDS)
        mentions_edition = False
        mentions_text = False
        mentions_commentary_only = True
    else:
        mentions_translation = any(keyword in haystack for keyword in TRANSLATION_KEYWORDS)
        mentions_transcription = any(keyword in haystack for keyword in TRANSCRIPTION_KEYWORDS)
        mentions_rubbing = any(keyword in haystack for keyword in PLATE_KEYWORDS)
        mentions_edition = any(keyword in haystack for keyword in EDITION_KEYWORDS) or source_type in {
            "corpus_volume",
            "catalogue",
        }
        mentions_text = any(keyword in haystack for keyword in TEXT_KEYWORDS) or mentions_transcription or mentions_edition
        mentions_commentary_only = (
            not mentions_translation
            and not mentions_text
            and not mentions_rubbing
            and (
                any(keyword in haystack for keyword in COMMENTARY_KEYWORDS)
                or source_type in {"article", "book", "unclear"}
            )
        )
    return {
        "mentions_translation": bool_text(mentions_translation),
        "mentions_text": bool_text(mentions_text),
        "mentions_transcription": bool_text(mentions_transcription),
        "mentions_edition": bool_text(mentions_edition),
        "mentions_rubbing_or_plate": bool_text(mentions_rubbing),
        "mentions_commentary_only": bool_text(mentions_commentary_only),
    }


def classify_source_type(raw_row: dict[str, str], source_row: dict[str, str] | None, citation_raw: str) -> str:
    work_type = normalize((source_row or {}).get("work_type", "")).casefold()
    title = normalize((source_row or {}).get("canonical_title", "")) or normalize(citation_raw)
    lowered = f"{title} {work_type}".casefold()
    if any(keyword in lowered for keyword in ("plate", "rubbing", "facsimile")):
        return "plate_or_rubbing"
    if "thesis" in lowered or "dissertation" in lowered:
        return "dissertation_or_thesis"
    if any(keyword in lowered for keyword in ("list", "catalogue", "catalog")):
        return "catalogue"
    if any(keyword in lowered for keyword in ("corpus", "selections from", "inscriptions of", "epigraphia")):
        return "corpus_volume"
    if work_type in {"article", "periodical"}:
        return "article"
    if work_type in {"book", "series"}:
        return "book"
    locator = normalize(raw_row.get("locator_type", "")).casefold()
    if "page" in locator and normalize(raw_row.get("locator", "")):
        return "article"
    return "unclear"


def normalized_source_key(raw_row: dict[str, str]) -> str:
    for key in ("source_work_key", "bibtex_key", "source_family_id", "family_id", "work_candidate_id"):
        value = normalize(raw_row.get(key, ""))
        if value:
            return value
    return f"raw-{safe_slug(raw_row.get('raw_reference_string', ''))}"


def priority_from_flags(target: dict[str, str]) -> str:
    scope = target["language_scope_expected"]
    translation = target["likely_contains_translation"] == "true"
    source_text = target["likely_contains_source_text"] == "true"
    commentary_only = target["likely_contains_commentary_only"] == "true"
    if scope in BURMESE_RELEVANT_SCOPES and translation:
        return "high"
    if scope in BURMESE_RELEVANT_SCOPES and source_text:
        return "medium"
    if commentary_only or scope in NON_BURMESE_SCOPES:
        return "low"
    return "medium"


def build_inscription_id(record: dict[str, str]) -> str:
    volume = normalize(record.get("source_volume", ""))
    source_number = normalize(record.get("source_inscription_number", ""))
    if volume and source_number:
        try:
            volume_number = int(re.search(r"[0-9]+", volume).group(0))
        except AttributeError:
            volume_number = 0
        return f"obi-v{volume_number:02d}-{parse_number_token(source_number, 'n')}"
    return record["record_id"]


def choose_target_text(raw_row: dict[str, str], source_row: dict[str, str] | None, citation_raw: str) -> tuple[str, str, str]:
    author = normalize((source_row or {}).get("authors_editors", ""))
    title = normalize((source_row or {}).get("canonical_title", ""))
    year = first_year(normalize((source_row or {}).get("date_or_date_range", "")), citation_raw)
    if title:
        return author, title, year
    match = re.match(r"([^,]+),\s*(.+)", citation_raw)
    if match:
        return normalize(match.group(1)), normalize(match.group(2)), year
    return "", normalize(citation_raw), year


def text_overlap_score(target_row: dict[str, str], candidate: dict[str, str]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    target_year = normalize(target_row.get("normalized_year", ""))
    candidate_year = normalize(candidate.get("year", ""))
    if target_year and candidate_year and target_year == candidate_year:
        score += 4
        reasons.append("year")
    author_overlap = citation_tokens(target_row.get("normalized_author", "")) & citation_tokens(candidate.get("author", ""))
    if author_overlap:
        score += 4 + min(len(author_overlap), 2)
        reasons.append(f"author:{','.join(sorted(author_overlap))}")
    title_overlap = citation_tokens(target_row.get("normalized_title", "")) & citation_tokens(candidate.get("title", ""))
    if len(title_overlap) >= 2:
        score += 5 + min(len(title_overlap) - 2, 2)
        reasons.append(f"title:{','.join(sorted(title_overlap))}")
    elif len(title_overlap) == 1:
        score += 2
        reasons.append(f"title:{next(iter(title_overlap))}")
    source_abbrev = target_row.get("source_abbreviation", "").casefold()
    if source_abbrev.startswith("jbrs") and candidate.get("is_probable_jbrs", "false") == "true":
        score += 1
        reasons.append("jbrs-context")
    if target_row.get("normalized_volume_issue", "") and target_row.get("normalized_volume_issue", "") in candidate.get("volume_issue", ""):
        score += 1
        reasons.append("volume-issue")
    return score, reasons


def build_jbrs_candidate_pool(
    jbrs_manifest_rows: list[dict[str, str]],
    ocr_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    candidates_by_local_id: dict[str, dict[str, str]] = {}
    for row in jbrs_manifest_rows:
        local_file_id = row.get("local_file_id", "")
        if not local_file_id:
            continue
        candidates_by_local_id[local_file_id] = {
            "local_file_id": local_file_id,
            "file_name": row.get("file_name", ""),
            "canonical_file_name": row.get("file_name", ""),
            "title": row.get("probable_title_from_filename", ""),
            "author": row.get("probable_author_from_path", ""),
            "year": row.get("probable_year_from_filename", "") or row.get("probable_year_from_folder", ""),
            "volume_issue": row.get("probable_volume_issue_from_filename", ""),
            "batch_id": "",
            "ocr_text_path": "",
            "metadata_path": "",
            "ocr_status": "",
            "is_probable_jbrs": row.get("is_probable_jbrs", ""),
            "match_basis": "jbrs_manifest_metadata",
        }
    for row in ocr_rows:
        local_file_id = row.get("local_file_id", "")
        if not local_file_id:
            continue
        candidates_by_local_id[local_file_id] = {
            "local_file_id": local_file_id,
            "file_name": row.get("file_name", ""),
            "canonical_file_name": row.get("canonical_file_name", "") or row.get("file_name", ""),
            "title": row.get("probable_article_title", "") or candidates_by_local_id.get(local_file_id, {}).get("title", ""),
            "author": row.get("probable_author", "") or candidates_by_local_id.get(local_file_id, {}).get("author", ""),
            "year": row.get("year", "") or candidates_by_local_id.get(local_file_id, {}).get("year", ""),
            "volume_issue": "",
            "batch_id": row.get("batch_id", ""),
            "ocr_text_path": row.get("ocr_text_path", ""),
            "metadata_path": row.get("metadata_path", ""),
            "ocr_status": row.get("ocr_status", ""),
            "is_probable_jbrs": "true",
            "match_basis": "jbrs_ocr_index",
        }
    return list(candidates_by_local_id.values())


def link_extraction_units(
    translation_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
    match_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    dashboard_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    target_by_id = {row["citation_target_id"]: row for row in target_rows}
    target_ids_by_local_file: dict[str, set[str]] = defaultdict(set)
    for row in match_rows:
        local_file_id = row.get("matched_local_file_id", "")
        target_id = row.get("citation_target_id", "")
        if local_file_id and target_id:
            target_ids_by_local_file[local_file_id].add(target_id)
    dashboard_by_target_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in dashboard_rows:
        dashboard_by_target_id[row["citation_target_id"]].append(row)

    def choose_target(unit_row: dict[str, str]) -> str:
        local_file_id = unit_row.get("source_local_file_id", "")
        target_ids = sorted(target_ids_by_local_file.get(local_file_id, set()))
        if len(target_ids) <= 1:
            return target_ids[0] if target_ids else ""
        unit_tokens = citation_tokens(unit_row.get("article_title", "") or unit_row.get("notes", ""))
        best_target_id = ""
        best_score = -1
        for target_id in target_ids:
            target = target_by_id[target_id]
            score = len(unit_tokens & citation_tokens(target.get("normalized_title", "")))
            if score > best_score:
                best_target_id = target_id
                best_score = score
        return best_target_id

    translation_language_by_source_unit: dict[str, str] = {}
    linked_translation_rows: list[dict[str, str]] = []
    for row in translation_rows:
        linked = dict(row)
        target_id = choose_target(row)
        target = target_by_id.get(target_id, {})
        dashboard_for_target = dashboard_by_target_id.get(target_id, [])
        inscription_ids = sorted({item["inscription_id"] for item in dashboard_for_target if item["inscription_id"]})
        record_ids = sorted({item["corpus_record_id"] for item in dashboard_for_target if item["corpus_record_id"]})
        linked["citation_target_id"] = target_id
        linked["normalized_source_key"] = target.get("normalized_source_key", "")
        linked["source_page_or_plate"] = target.get("normalized_page_or_plate", "") or row.get("page_marker", "")
        linked["inscription_id"] = inscription_ids[0] if len(inscription_ids) == 1 else ""
        linked["corpus_record_id"] = record_ids[0] if len(record_ids) == 1 else ""
        if target_id and linked["inscription_id"] and linked["corpus_record_id"]:
            linked["alignment_confidence"] = "exact_source_work_and_corpus_record"
        elif target_id:
            linked["alignment_confidence"] = "matched_source_work_needs_inscription_linkage"
        else:
            linked["alignment_confidence"] = "needs_manual_source_linkage"
        linked_translation_rows.append(linked)
        if linked.get("source_text_unit_id"):
            translation_language_by_source_unit[linked["source_text_unit_id"]] = linked.get("translation_language", "")

    linked_source_rows: list[dict[str, str]] = []
    for row in source_rows:
        linked = dict(row)
        target_id = choose_target(row)
        target = target_by_id.get(target_id, {})
        dashboard_for_target = dashboard_by_target_id.get(target_id, [])
        inscription_ids = sorted({item["inscription_id"] for item in dashboard_for_target if item["inscription_id"]})
        record_ids = sorted({item["corpus_record_id"] for item in dashboard_for_target if item["corpus_record_id"]})
        linked["citation_target_id"] = target_id
        linked["normalized_source_key"] = target.get("normalized_source_key", "")
        linked["source_page_or_plate"] = target.get("normalized_page_or_plate", "") or row.get("page_marker", "")
        linked["translation_language"] = translation_language_by_source_unit.get(row.get("source_text_unit_id", ""), "")
        linked["inscription_id"] = inscription_ids[0] if len(inscription_ids) == 1 else ""
        linked["corpus_record_id"] = record_ids[0] if len(record_ids) == 1 else ""
        if target_id and linked["inscription_id"] and linked["corpus_record_id"]:
            linked["alignment_confidence"] = "exact_source_work_and_corpus_record"
        elif target_id:
            linked["alignment_confidence"] = "matched_source_work_needs_inscription_linkage"
        else:
            linked["alignment_confidence"] = "needs_manual_source_linkage"
        linked_source_rows.append(linked)
    return linked_translation_rows, linked_source_rows


def main() -> None:
    corpus_rows = [
        row
        for row in read_jsonl(CORPUS_INSCRIPTIONS_PATH)
        if row.get("source_layer") == "structured_obi" and normalize(row.get("references_original", ""))
    ]
    raw_reference_rows = read_tsv(RAW_REFERENCE_TO_BIBTEX_PATH)
    raw_reference_by_string = {row["raw_reference_string"]: row for row in raw_reference_rows}
    source_work_rows = read_tsv(SOURCE_WORK_AUTHORITY_PATH)
    source_work_by_key = {row["source_work_key"]: row for row in source_work_rows if row.get("source_work_key")}
    source_library_rows = read_tsv(SOURCE_LIBRARY_MANIFEST_PATH)
    source_library_by_bibtex = defaultdict(list)
    source_library_by_family = defaultdict(list)
    source_library_by_work_candidate = defaultdict(list)
    for row in source_library_rows:
        if row.get("bibtex_key"):
            source_library_by_bibtex[row["bibtex_key"]].append(row)
        if row.get("family_id"):
            source_library_by_family[row["family_id"]].append(row)
        if row.get("work_candidate_id"):
            source_library_by_work_candidate[row["work_candidate_id"]].append(row)
    local_manifest_rows = read_tsv(LOCAL_FILE_MANIFEST_PATH)
    local_manifest_by_copied_path = {row["copied_path"]: row for row in local_manifest_rows if row.get("copied_path")}
    jbrs_manifest_rows = read_tsv(JBRS_LOCAL_FILE_MANIFEST_PATH)
    jbrs_manifest_by_local_id = {row["local_file_id"]: row for row in jbrs_manifest_rows if row.get("local_file_id")}
    ocr_rows = read_tsv(JBRS_OCR_TEXT_INDEX_PATH)
    ocr_by_local_id = {row["local_file_id"]: row for row in ocr_rows if row.get("local_file_id")}
    jbrs_candidate_pool = build_jbrs_candidate_pool(jbrs_manifest_rows, ocr_rows)

    pending_inventory_rows: list[dict[str, str]] = []
    target_buckets: dict[str, dict[str, object]] = {}
    for record in corpus_rows:
        citation_fragments = [normalize(fragment) for fragment in record["references_original"].split(";") if normalize(fragment)]
        for citation_raw in citation_fragments:
            raw_row = raw_reference_by_string[citation_raw]
            source_row = source_work_by_key.get(raw_row.get("source_work_key", ""))
            citation_key = normalized_source_key(raw_row)
            target_id = ""
            source_type = classify_source_type(raw_row, source_row, citation_raw)
            author, title, year = choose_target_text(raw_row, source_row, citation_raw)
            locator_volume_issue, locator_page_or_plate = split_locator(raw_row.get("locator", ""))
            flags = citation_content_flags(citation_raw, title, source_type)
            inventory_row = {
                "corpus_record_id": record["record_id"],
                "inscription_id": build_inscription_id(record),
                "corpus_title_or_label": normalize(record.get("title_original", "")),
                "corpus_date_or_period": normalize(record.get("date_original", "")),
                "corpus_language_field": normalize(record.get("language_original", "")),
                "citation_raw": citation_raw,
                "citation_type_if_given": normalize(raw_row.get("locator_type", "")),
                "source_abbreviation": source_abbreviation(raw_row, source_row, citation_raw),
                "source_author": author,
                "source_title": title,
                "source_year": year,
                "source_volume_issue": locator_volume_issue,
                "source_page_or_plate": locator_page_or_plate,
                **flags,
                "language_scope_from_corpus": language_scope_from_record(record),
                "citation_target_id": target_id,
                "notes": normalize(raw_row.get("notes", "")),
            }
            pending_inventory_rows.append(inventory_row)
            bucket = target_buckets.setdefault(
                citation_key,
                {
                    "citation_rows": [],
                    "raw_rows": [],
                    "source_row": source_row,
                    "source_abbreviation": inventory_row["source_abbreviation"],
                    "author": author,
                    "title": title,
                    "year": year,
                    "volume_issues": set(),
                    "page_or_plates": set(),
                    "language_scopes": set(),
                    "flags": Counter(),
                    "source_type": source_type,
                },
            )
            bucket["citation_rows"].append(inventory_row)
            bucket["raw_rows"].append(raw_row)
            if locator_volume_issue:
                bucket["volume_issues"].add(locator_volume_issue)
            if locator_page_or_plate:
                bucket["page_or_plates"].add(locator_page_or_plate)
            bucket["language_scopes"].add(inventory_row["language_scope_from_corpus"])
            for key, value in flags.items():
                if value == "true":
                    bucket["flags"][key] += 1

    target_rows: list[dict[str, str]] = []
    target_id_by_key: dict[str, str] = {}
    for index, citation_key in enumerate(sorted(target_buckets), start=1):
        bucket = target_buckets[citation_key]
        target_row = {
            "citation_target_id": f"corpus-citation-target-{index:04d}",
            "normalized_source_key": citation_key,
            "source_abbreviation": bucket["source_abbreviation"],
            "normalized_author": bucket["author"],
            "normalized_title": bucket["title"],
            "normalized_year": bucket["year"],
            "normalized_volume_issue": " | ".join(sorted(bucket["volume_issues"])),
            "normalized_page_or_plate": " | ".join(sorted(bucket["page_or_plates"])),
            "source_type": bucket["source_type"],
            "likely_contains_translation": bool_text(bucket["flags"]["mentions_translation"] > 0),
            "likely_contains_source_text": bool_text(
                bucket["flags"]["mentions_text"] > 0
                or bucket["flags"]["mentions_transcription"] > 0
                or bucket["flags"]["mentions_edition"] > 0
            ),
            "likely_contains_edition_only": bool_text(
                bucket["flags"]["mentions_edition"] > 0 and bucket["flags"]["mentions_translation"] == 0
            ),
            "likely_contains_commentary_only": bool_text(
                bucket["flags"]["mentions_commentary_only"] > 0
                and bucket["flags"]["mentions_translation"] == 0
                and bucket["flags"]["mentions_text"] == 0
            ),
            "language_scope_expected": aggregate_language_scope(bucket["language_scopes"]),
            "target_priority": "medium",
            "notes": f"{len(bucket['citation_rows'])} corpus citation rows",
        }
        target_row["target_priority"] = priority_from_flags(target_row)
        target_rows.append(target_row)
        target_id_by_key[citation_key] = target_row["citation_target_id"]

    inventory_rows: list[dict[str, str]] = []
    for row in pending_inventory_rows:
        inventory = dict(row)
        inventory["citation_target_id"] = target_id_by_key[normalized_source_key(raw_reference_by_string[row["citation_raw"]])]
        inventory_rows.append(inventory)

    match_rows: list[dict[str, str]] = []
    target_rows_by_id = {row["citation_target_id"]: row for row in target_rows}
    for target_row in target_rows:
        citation_key = target_row["normalized_source_key"]
        raw_row = target_buckets[citation_key]["raw_rows"][0]
        source_library_candidates = []
        for lookup in (
            source_library_by_bibtex.get(normalize(raw_row.get("bibtex_key", "")), []),
            source_library_by_work_candidate.get(normalize(raw_row.get("work_candidate_id", "")), []),
            source_library_by_family.get(normalize(raw_row.get("family_id", "")), []),
            source_library_by_family.get(normalize(raw_row.get("source_family_id", "")), []),
        ):
            source_library_candidates.extend(lookup)
        chosen_candidate: dict[str, str] | None = None
        match_status = "no_local_candidate_found"
        match_confidence = "low"
        match_basis = ""
        notes = ""
        if source_library_candidates:
            unique_candidates = []
            seen_copied_paths = set()
            for candidate in source_library_candidates:
                copied_path = candidate.get("copied_path", "")
                if copied_path and copied_path not in seen_copied_paths:
                    unique_candidates.append(candidate)
                    seen_copied_paths.add(copied_path)
            if len(unique_candidates) == 1:
                chosen_candidate = unique_candidates[0]
                match_status = "exact_or_near_exact_match"
                match_confidence = chosen_candidate.get("match_confidence", "") or "high"
                match_basis = f"source_library:{chosen_candidate.get('match_reason', '')}"
            else:
                match_status = "multiple_candidates"
                match_confidence = "medium"
                notes = "Multiple source-library candidates share the same bibliography authority mapping."
        if not chosen_candidate and match_status in {"no_local_candidate_found", "multiple_candidates"}:
            scored_candidates = []
            for candidate in jbrs_candidate_pool:
                score, reasons = text_overlap_score(target_row, candidate)
                if score >= 6:
                    scored_candidates.append((score, reasons, candidate))
            scored_candidates.sort(key=lambda item: (-item[0], item[2].get("local_file_id", "")))
            if scored_candidates:
                top_score = scored_candidates[0][0]
                top_candidates = [item for item in scored_candidates if item[0] == top_score]
                if len(top_candidates) == 1:
                    _, reasons, candidate = top_candidates[0]
                    chosen_candidate = candidate
                    match_status = "already_ocr_available" if candidate.get("ocr_status") == "completed" else "plausible_match"
                    match_confidence = "high" if top_score >= 10 else "medium"
                    match_basis = f"{candidate.get('match_basis', 'heuristic')}:{'|'.join(reasons)}"
                else:
                    match_status = "multiple_candidates"
                    match_confidence = "medium"
                    notes = "Multiple JBRS candidates scored equally on author/year/title overlap."

        matched_local_file_id = ""
        matched_batch_id = ""
        matched_file_name = ""
        matched_canonical_file_name = ""
        matched_ocr_text_path = ""
        matched_metadata_path = ""
        ocr_status = ""
        needs_ocr = "false"
        needs_manual_file_hunt = "false"
        if chosen_candidate and "copied_path" in chosen_candidate:
            local_manifest_row = local_manifest_by_copied_path.get(chosen_candidate.get("copied_path", ""))
            matched_local_file_id = (local_manifest_row or {}).get("canonical_local_file_id", "")
            matched_file_name = chosen_candidate.get("file_name", "")
            matched_canonical_file_name = chosen_candidate.get("file_name", "")
            ocr_row = ocr_by_local_id.get(matched_local_file_id, {})
            matched_batch_id = ocr_row.get("batch_id", "")
            matched_ocr_text_path = ocr_row.get("ocr_text_path", "")
            matched_metadata_path = ocr_row.get("metadata_path", "")
            ocr_status = ocr_row.get("ocr_status", "")
        elif chosen_candidate:
            matched_local_file_id = chosen_candidate.get("local_file_id", "")
            matched_batch_id = chosen_candidate.get("batch_id", "")
            matched_file_name = chosen_candidate.get("file_name", "")
            matched_canonical_file_name = chosen_candidate.get("canonical_file_name", "") or chosen_candidate.get("file_name", "")
            matched_ocr_text_path = chosen_candidate.get("ocr_text_path", "")
            matched_metadata_path = chosen_candidate.get("metadata_path", "")
            ocr_status = chosen_candidate.get("ocr_status", "")

        if matched_ocr_text_path and match_status != "multiple_candidates":
            match_status = "already_ocr_available"
        elif matched_local_file_id and match_status == "exact_or_near_exact_match":
            if target_row["likely_contains_translation"] == "true" or target_row["likely_contains_source_text"] == "true":
                match_status = "needs_ocr"
                needs_ocr = "true"
            else:
                ocr_status = ocr_status or "not_requested"
        elif matched_local_file_id and match_status == "plausible_match":
            ocr_status = ocr_status or "not_requested"
        elif match_status == "no_local_candidate_found":
            needs_manual_file_hunt = "true"

        match_rows.append(
            {
                "citation_target_id": target_row["citation_target_id"],
                "normalized_source_key": citation_key,
                "matched_local_file_id": matched_local_file_id,
                "matched_batch_id": matched_batch_id,
                "matched_file_name": matched_file_name,
                "matched_canonical_file_name": matched_canonical_file_name,
                "matched_ocr_text_path": matched_ocr_text_path,
                "matched_metadata_path": matched_metadata_path,
                "match_status": match_status,
                "match_confidence": match_confidence,
                "match_basis": match_basis,
                "ocr_status": ocr_status,
                "needs_ocr": needs_ocr,
                "needs_manual_file_hunt": needs_manual_file_hunt,
                "notes": notes,
            }
        )

    match_row_by_target_id = {row["citation_target_id"]: row for row in match_rows}
    extracted_translation_rows = read_tsv(JBRS_EXTRACTED_TRANSLATION_UNITS_PATH)
    extracted_source_rows = read_tsv(JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH)
    linked_translation_rows, linked_source_rows = link_extraction_units(
        extracted_translation_rows,
        extracted_source_rows,
        match_rows,
        target_rows,
        [],
    )
    extracted_by_target_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in linked_translation_rows + linked_source_rows:
        if row.get("citation_target_id"):
            extracted_by_target_id[row["citation_target_id"]].append(row)

    dashboard_rows: list[dict[str, str]] = []
    for index, inventory_row in enumerate(inventory_rows, start=1):
        target_row = target_rows_by_id[inventory_row["citation_target_id"]]
        match_row = match_row_by_target_id[inventory_row["citation_target_id"]]
        is_burmese_relevant = target_row["language_scope_expected"] in BURMESE_RELEVANT_SCOPES
        if target_row["citation_target_id"] in extracted_by_target_id:
            extraction_status = "extracted_verified" if any(
                row.get("review_status") == "verified_translation_coverage"
                for row in extracted_by_target_id[target_row["citation_target_id"]]
            ) else "extracted_needs_review"
            next_action = "review_extracted_units"
        elif not is_burmese_relevant:
            extraction_status = "out_of_scope_non_burmese"
            next_action = "retain_as_non_burmese_support"
        elif target_row["likely_contains_translation"] != "true" and target_row["likely_contains_source_text"] != "true":
            extraction_status = "citation_not_translation"
            next_action = "no_extraction_action"
        elif match_row["match_status"] == "already_ocr_available":
            extraction_status = "ready_for_extraction"
            next_action = "review_existing_ocr"
        elif match_row["match_status"] == "needs_ocr":
            extraction_status = "ready_for_ocr"
            next_action = "queue_targeted_ocr"
        elif match_row["match_status"] == "no_local_candidate_found":
            extraction_status = "source_not_found"
            next_action = "manual_file_hunt"
        else:
            extraction_status = "unclear_needs_manual_review"
            next_action = "manual_citation_review"
        dashboard_rows.append(
            {
                "dashboard_id": f"corpus-dashboard-{index:05d}",
                "inscription_id": inventory_row["inscription_id"],
                "corpus_record_id": inventory_row["corpus_record_id"],
                "corpus_title_or_label": inventory_row["corpus_title_or_label"],
                "corpus_language_field": inventory_row["corpus_language_field"],
                "citation_target_id": inventory_row["citation_target_id"],
                "citation_raw": inventory_row["citation_raw"],
                "normalized_source_key": target_row["normalized_source_key"],
                "matched_local_file_id": match_row["matched_local_file_id"],
                "matched_ocr_text_path": match_row["matched_ocr_text_path"],
                "translation_status_from_citation": (
                    "likely_translation_source"
                    if target_row["likely_contains_translation"] == "true"
                    else "no_translation_indicator"
                ),
                "source_text_status_from_citation": (
                    "likely_source_text"
                    if target_row["likely_contains_source_text"] == "true"
                    else "no_source_text_indicator"
                ),
                "language_scope_expected": target_row["language_scope_expected"],
                "is_burmese_relevant": bool_text(is_burmese_relevant),
                "source_match_status": match_row["match_status"],
                "ocr_status": match_row["ocr_status"],
                "extraction_status": extraction_status,
                "next_action": next_action,
                "notes": inventory_row["notes"],
            }
        )

    linked_translation_rows, linked_source_rows = link_extraction_units(
        extracted_translation_rows,
        extracted_source_rows,
        match_rows,
        target_rows,
        dashboard_rows,
    )

    dashboard_by_target_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in dashboard_rows:
        dashboard_by_target_id[row["citation_target_id"]].append(row)

    def queue_sort_key(row: dict[str, str]) -> tuple[int, str]:
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        target = target_rows_by_id[row["citation_target_id"]]
        return (priority_rank[target["target_priority"]], row["citation_target_id"])

    ocr_queue_rows: list[dict[str, str]] = []
    queue_candidates = [
        row
        for row in match_rows
        if row["needs_ocr"] == "true" and row["citation_target_id"] in dashboard_by_target_id
    ]
    queue_candidates.sort(key=queue_sort_key)
    for index, match_row in enumerate(queue_candidates, start=1):
        target_row = target_rows_by_id[match_row["citation_target_id"]]
        dashboard_target_rows = dashboard_by_target_id[match_row["citation_target_id"]]
        inscription_ids = sorted({row["inscription_id"] for row in dashboard_target_rows if row["inscription_id"]})
        inscription_id_or_count = inscription_ids[0] if len(inscription_ids) == 1 else f"{len(inscription_ids)} inscriptions"
        reason_bits = []
        if target_row["likely_contains_translation"] == "true":
            reason_bits.append("cited source likely contains translation")
        if target_row["likely_contains_source_text"] == "true":
            reason_bits.append("cited source likely contains source text")
        ocr_queue_rows.append(
            {
                "ocr_queue_id": f"corpus-cited-ocr-{index:04d}",
                "citation_target_id": match_row["citation_target_id"],
                "inscription_id_or_count": inscription_id_or_count,
                "matched_local_file_id": match_row["matched_local_file_id"],
                "batch_id": match_row["matched_batch_id"],
                "file_name": match_row["matched_file_name"],
                "canonical_file_name": match_row["matched_canonical_file_name"],
                "reason_for_ocr": "; ".join(reason_bits) or "cited translation-bearing source requires OCR",
                "priority": target_row["target_priority"],
                "ocr_status": "queued_targeted_ocr",
                "notes": f"{len(inscription_ids)} linked inscriptions in structured corpus.",
            }
        )

    write_tsv(CORPUS_CITATION_INVENTORY_PATH, inventory_rows, CORPUS_CITATION_INVENTORY_FIELDS)
    write_tsv(CORPUS_CITATION_TARGETS_PATH, target_rows, CORPUS_CITATION_TARGET_FIELDS)
    write_tsv(CORPUS_CITATION_SOURCE_FILE_MATCH_PATH, match_rows, CORPUS_CITATION_SOURCE_FILE_MATCH_FIELDS)
    write_tsv(CORPUS_TRANSLATION_SOURCE_DASHBOARD_PATH, dashboard_rows, CORPUS_TRANSLATION_SOURCE_DASHBOARD_FIELDS)
    write_tsv(CORPUS_CITED_SOURCE_OCR_QUEUE_PATH, ocr_queue_rows, CORPUS_CITED_SOURCE_OCR_QUEUE_FIELDS)
    write_tsv(JBRS_EXTRACTED_TRANSLATION_UNITS_PATH, linked_translation_rows, EXTRACTED_TRANSLATION_UNIT_FIELDS)
    write_tsv(JBRS_EXTRACTED_SOURCE_TEXT_UNITS_PATH, linked_source_rows, EXTRACTED_SOURCE_TEXT_UNIT_FIELDS)

    print(f"Structured OBI records with citations: {len(corpus_rows)}")
    print(f"Corpus citation inventory rows: {len(inventory_rows)}")
    print(f"Distinct citation targets: {len(target_rows)}")
    print(f"Cited targeted-OCR queue rows: {len(ocr_queue_rows)}")


if __name__ == "__main__":
    main()
