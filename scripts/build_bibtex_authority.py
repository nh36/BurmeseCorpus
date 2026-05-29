from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from bibtex_common import (
    make_bibtex_key,
    normalize_for_match,
    surname_token,
    title_keyword_tokens,
    write_bibtex,
)
from corpus_common import read_tsv, write_tsv


AUTHORITY_FIELDS = [
    "bibtex_key",
    "entry_type",
    "authority_status",
    "source_of_authority",
    "matched_external_key",
    "matched_local_source_id",
    "matched_local_source_file",
    "matched_local_reference",
    "match_confidence",
    "match_reason",
    "family_id",
    "family_label",
    "family_type",
    "author",
    "editor",
    "year",
    "title",
    "shorttitle",
    "journal",
    "booktitle",
    "publisher",
    "address",
    "volume",
    "number",
    "pages",
    "doi",
    "url",
    "isbn",
    "language",
    "script",
    "translation_relevance",
    "review_status",
    "evidence",
    "notes",
]

CROSSWALK_FIELDS = [
    "raw_reference_string",
    "family_id",
    "work_candidate_id",
    "bibtex_key",
    "match_type",
    "match_confidence",
    "locator",
    "locator_type",
    "evidence",
    "needs_human_review",
    "notes",
]

HIGH_FREQUENCY_FIELDS = [
    "family_id",
    "family_label",
    "family_type",
    "member_count",
    "occurrence_count",
    "sample_raw_references",
    "current_bibtex_key",
    "current_status",
    "suggested_local_search_terms",
    "notes",
]

STATUS_RANK = {
    "confirmed_external_bibtex": 5,
    "confirmed_local_source": 4,
    "provisional_local_source": 3,
    "provisional_catalogue": 2,
    "provisional_publication": 2,
    "needs_human_review": 1,
}

GENERIC_MATCH_TOKENS = {
    "burma",
    "burmese",
    "myanmar",
    "pagan",
    "bagan",
    "inscription",
    "inscriptions",
    "history",
    "article",
    "study",
    "old",
    "first",
    "report",
    "references",
}

SOURCE_FAMILY_LIBRARY = {
    "list": {
        "author": "Charles Duroiselle",
        "year": "1921",
        "title": "List of Inscriptions Found in Burma",
        "shorttitle": "List",
        "entry_type": "book",
        "preferred_key": "duroiselle1921list",
        "local_search_terms": ["list of inscriptions"],
        "frasch_search_terms": ["list"],
    },
    "iob": {
        "author": "G. H. Luce and U Pe Maung Tin",
        "year": "",
        "title": "Inscriptions of Burma",
        "shorttitle": "IOB",
        "entry_type": "book",
        "preferred_key": "lucePeMaungTinInscriptionsOfBurma",
        "local_search_terms": ["inscriptions of burma"],
        "frasch_search_terms": ["iob"],
    },
    "obi": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Old Burmese Inscriptions structured corpus",
        "shorttitle": "OBI",
        "entry_type": "misc",
        "preferred_key": "obiCorpusSource",
        "local_search_terms": ["old burmese inscriptions", "bagan epig database"],
        "frasch_search_terms": ["obi", "old burmese inscriptions"],
    },
    "bed b": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part B",
        "shorttitle": "BED B",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartB",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": ["bed b", "bagan epig database"],
    },
    "a": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part A",
        "shorttitle": "A",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartA",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": [" a, p.", "bagan epig database"],
    },
    "b": {
        "author": "Tilman Frasch",
        "year": "",
        "title": "Bagan Epigraphic Database, Part B",
        "shorttitle": "B",
        "entry_type": "misc",
        "preferred_key": "fraschBaganEpigraphicDatabasePartBShort",
        "local_search_terms": ["bagan epig database", "bagan epigraphic database"],
        "frasch_search_terms": [" b 1", " b 2", "bagan epig database"],
    },
    "mp": {
        "author": "",
        "year": "",
        "title": "MP source family attested in Frasch bibliography evidence",
        "shorttitle": "MP",
        "entry_type": "misc",
        "preferred_key": "mpSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["mp"],
    },
    "ub": {
        "author": "",
        "year": "",
        "title": "UB source family attested in Frasch bibliography evidence",
        "shorttitle": "UB",
        "entry_type": "misc",
        "preferred_key": "ubSourceFamily",
        "local_search_terms": [],
        "frasch_search_terms": ["ub"],
    },
    "uem": {
        "author": "",
        "year": "",
        "title": "UEM catalogue family",
        "shorttitle": "UEM",
        "entry_type": "misc",
        "preferred_key": "uemCatalogue",
        "local_search_terms": [],
        "frasch_search_terms": ["uem"],
    },
    "ppa": {
        "author": "",
        "year": "",
        "title": "PPA catalogue family",
        "shorttitle": "PPA",
        "entry_type": "misc",
        "preferred_key": "ppaCatalogue",
        "local_search_terms": [],
        "frasch_search_terms": ["ppa"],
    },
    "tn": {
        "author": "Than Tun",
        "year": "",
        "title": "Than Tun catalogue family",
        "shorttitle": "TN",
        "entry_type": "misc",
        "preferred_key": "thanTunCatalogue",
        "local_search_terms": ["than tun"],
        "frasch_search_terms": ["tn", "than tun"],
    },
    "jbrs": {
        "author": "",
        "year": "",
        "title": "Journal of the Burma Research Society",
        "shorttitle": "JBRS",
        "entry_type": "periodical",
        "preferred_key": "journalBurmaResearchSociety",
        "local_search_terms": ["jbrs", "burma jbrs"],
        "frasch_search_terms": ["jbrs"],
    },
    "bbhc": {
        "author": "",
        "year": "",
        "title": "Burma Historical Commission bulletin",
        "shorttitle": "BBHC",
        "entry_type": "periodical",
        "preferred_key": "burmaHistoricalCommissionBulletin",
        "local_search_terms": [],
        "frasch_search_terms": ["bbhc"],
    },
    "jras": {
        "author": "",
        "year": "",
        "title": "Journal of the Royal Asiatic Society",
        "shorttitle": "JRAS",
        "entry_type": "periodical",
        "preferred_key": "journalRoyalAsiaticSociety",
        "local_search_terms": ["jras"],
        "frasch_search_terms": ["jras"],
    },
    "rdasb": {
        "author": "",
        "year": "",
        "title": "Report of the Director, Archaeological Survey of Burma",
        "shorttitle": "RDASB",
        "entry_type": "periodical",
        "preferred_key": "reportDirectorArchaeologicalSurveyBurma",
        "local_search_terms": [],
        "frasch_search_terms": ["rdasb"],
    },
    "eb": {
        "author": "",
        "year": "",
        "title": "Epigraphia Birmanica",
        "shorttitle": "EB",
        "entry_type": "periodical",
        "preferred_key": "epigraphiaBirmanica",
        "local_search_terms": ["epigraphia birmanica"],
        "frasch_search_terms": ["eb", "epigraphia birmanica"],
    },
}

MANUAL_LOCAL_MATCHES = {
    "fam-raw-luce-u-tin-htway-15th-century-library": {
        "filename_terms": ["15th century inscription and library at pagan"],
        "confidence": "high",
    },
    "fam-raw-u-tin-htway-first-burmese-royal-inscription": {
        "filename_terms": ["oldest burmese inscription"],
        "confidence": "high",
    },
    "fam-raw-u-tha-myat-the-pali-version-of-the-myazedi-inscription-rangoon-1958": {
        "filename_terms": ["tha myat 1958 myazedi"],
        "confidence": "high",
    },
    "fam-raw-u-pe-maung-tin-the-myazedi-inscription-in-nava-rat-kui-svay-rangoon-1966": {
        "filename_terms": ["pemaungtin 1974 myazediinscription", "myazediinscription"],
        "confidence": "medium",
    },
}


def parse_locator(raw_reference: str, family_id: str, family_label: str) -> tuple[str, str]:
    text = raw_reference.strip()
    if not text:
        return "", "none"
    if family_label.startswith("Pl"):
        return text.replace("Pl.", "").strip(), "plate"
    if family_label and text.casefold().startswith(family_label.casefold()):
        locator = text[len(family_label) :].strip(" ,")
        if locator:
            if "catalogue" in family_id and re.fullmatch(r"[0-9A-Za-z.-]+", locator):
                return locator, "catalogue_number"
            if any(char.isdigit() for char in locator):
                return locator, "volume_page"
            return locator, "text"
    page_match = re.search(r"\bp+\.\s*([0-9-]+)", text, flags=re.IGNORECASE)
    if page_match:
        return page_match.group(1), "page"
    number_match = re.search(r"\b(?:no\.?|nr\.?)\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)
    if number_match:
        return number_match.group(1), "catalogue_number"
    year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
    if year_match:
        return year_match.group(1), "year"
    return text, "text"


def normalize_title(value: str) -> str:
    return normalize_for_match(value)


def local_source_kind(row: dict) -> str:
    original = row.get("original_path", "").casefold()
    if "frasch" in original or "bagan epig" in original:
        return "frasch_word_document"
    if "luce" in original:
        return "local_luce_folder"
    return "local_burma_folder"


def row_to_bibtex_entry(row: dict) -> dict:
    fields = {
        "author": row.get("author", ""),
        "editor": row.get("editor", ""),
        "title": row.get("title", ""),
        "shorttitle": row.get("shorttitle", ""),
        "journal": row.get("journal", ""),
        "booktitle": row.get("booktitle", ""),
        "publisher": row.get("publisher", ""),
        "address": row.get("address", ""),
        "year": row.get("year", ""),
        "volume": row.get("volume", ""),
        "number": row.get("number", ""),
        "pages": row.get("pages", ""),
        "doi": row.get("doi", ""),
        "url": row.get("url", ""),
        "isbn": row.get("isbn", ""),
        "language": row.get("language", ""),
        "script": row.get("script", ""),
        "reviewstatus": row.get("review_status", ""),
        "translationrelevance": row.get("translation_relevance", ""),
        "evidence": row.get("evidence", ""),
        "sourceofauthority": row.get("source_of_authority", ""),
        "matchedexternalkey": row.get("matched_external_key", ""),
        "familyid": row.get("family_id", ""),
        "note": row.get("notes", ""),
        "matchedlocalsourceid": row.get("matched_local_source_id", ""),
        "matchedlocalsourcefile": row.get("matched_local_source_file", ""),
        "matchedlocalreference": row.get("matched_local_reference", ""),
    }
    return {
        "entry_type": row["entry_type"],
        "bibtex_key": row["bibtex_key"],
        "fields": {name: value for name, value in fields.items() if value},
    }


def dedupe_local_candidates(rows: list[dict]) -> list[dict]:
    by_candidate: dict[str, dict] = {}
    for row in rows:
        candidate_id = row.get("candidate_id") or row.get("sha256") or row.get("name")
        existing = by_candidate.get(candidate_id)
        if existing is None or ("OBI_AUTHOR_ALPHA_ROOT" in row.get("original_path", "") and "OBI_AUTHOR_ALPHA_ROOT" not in existing.get("original_path", "")):
            by_candidate[candidate_id] = row
    return list(by_candidate.values())


def build_external_index(external_rows: list[dict]) -> list[dict]:
    indexed = []
    for row in external_rows:
        indexed.append(
            {
                **row,
                "_title": normalize_title(row.get("title", "")),
                "_author": surname_token(row.get("author", "")),
                "_year": row.get("year", ""),
            }
        )
    return indexed


def find_external_match(candidate: dict, external_index: list[dict]) -> dict | None:
    title = normalize_title(candidate.get("title_original", ""))
    author = surname_token(candidate.get("author_original", ""))
    year = candidate.get("year", "")
    if not title:
        return None
    for row in external_index:
        if row["_title"] != title:
            continue
        if year and row["_year"] and row["_year"] != year:
            continue
        if author and row["_author"] and author != row["_author"]:
            continue
        return row
    return None


def candidate_search_blob(candidate: dict, family: dict, members: list[dict]) -> str:
    parts = [
        family.get("family_label", ""),
        family.get("sample_raw_references", ""),
        candidate.get("title_original", ""),
        candidate.get("author_original", ""),
        candidate.get("provisional_short_label", ""),
        candidate.get("evidence_raw_references", ""),
    ]
    parts.extend(member.get("raw_reference_string", "") for member in members[:5])
    return normalize_title(" ".join(part for part in parts if part))


def score_local_candidate(local_row: dict, candidate: dict, family: dict, members: list[dict]) -> tuple[int, str]:
    search_blob = candidate_search_blob(candidate, family, members)
    local_title = normalize_title(local_row.get("probable_work_label", "") or local_row.get("name", ""))
    local_author = surname_token(local_row.get("probable_author", "") or local_row.get("name", ""))
    local_year = local_row.get("probable_year", "")
    title_overlap = {
        token
        for token in set(title_keyword_tokens(local_title)) & set(title_keyword_tokens(search_blob))
        if token not in GENERIC_MATCH_TOKENS
    }
    score = 0
    reasons: list[str] = []
    if len(title_overlap) >= 2:
        score += min(len(title_overlap) * 2, 6)
        reasons.append(f"title-token overlap: {', '.join(sorted(title_overlap))}")
    if local_title and len(title_keyword_tokens(local_title)) >= 3 and (local_title in search_blob or search_blob in local_title):
        score += 4
        reasons.append("title substring match")
    if local_author and local_author in search_blob:
        score += 2
        reasons.append(f"author surname match: {local_author}")
    if local_year and (local_year == candidate.get("year") or local_year in family.get("sample_raw_references", "")):
        score += 1
        reasons.append(f"year match: {local_year}")
    if local_row.get("search_term") and normalize_title(local_row["search_term"]) not in GENERIC_MATCH_TOKENS and normalize_title(local_row["search_term"]) in search_blob:
        score += 1
        reasons.append(f"search term match: {local_row['search_term']}")
    if score and not (local_author or len(title_overlap) >= 2 or "title substring match" in reasons):
        return 0, ""
    return score, "; ".join(reasons)


def build_seed_authority(
    seed_row: dict,
    family_row: dict,
    frasch_rows: list[dict],
    local_candidate_rows: list[dict],
    existing_keys: set[str],
) -> dict:
    abbreviation = seed_row.get("abbreviation", "")
    normalized_abbreviation = abbreviation.casefold()
    defaults = SOURCE_FAMILY_LIBRARY.get(normalized_abbreviation, {})
    frasch_search_terms = defaults.get("frasch_search_terms", [abbreviation.casefold(), seed_row.get("provisional_label", "").casefold()])
    local_search_terms = defaults.get("local_search_terms", frasch_search_terms)
    frasch_matches = [
        row
        for row in frasch_rows
        if any(term and term in normalize_title(f"{row.get('raw_reference', '')} {row.get('publication', '')} {row.get('title', '')}") for term in frasch_search_terms)
    ]
    local_matches = [
        row
        for row in local_candidate_rows
        if local_search_terms
        and any(term and term in normalize_title(f"{row.get('probable_work_label', '')} {row.get('name', '')} {row.get('original_path', '')}") for term in local_search_terms)
    ]
    source_of_authority = ""
    matched_local_source_id = ""
    matched_local_source_file = ""
    matched_local_reference = ""
    match_reason = ""
    match_confidence = "low"

    if local_matches:
        match = local_matches[0]
        source_of_authority = local_source_kind(match)
        matched_local_source_id = match.get("candidate_id", "")
        matched_local_source_file = match.get("original_path", "")
        matched_local_reference = match.get("probable_work_label", "") or match.get("name", "")
        match_reason = f"Matched harvested local file for {abbreviation or family_row['family_label']}."
        match_confidence = "high"
        authority_status = "confirmed_local_source"
    elif frasch_matches:
        match = frasch_matches[0]
        source_of_authority = "frasch_bibliography"
        matched_local_source_id = match.get("frasch_ref_id", "")
        matched_local_source_file = match.get("extraction_source_file", "")
        matched_local_reference = match.get("raw_reference", "")
        match_reason = f"Attested in extracted Frasch bibliography evidence for {abbreviation or family_row['family_label']}."
        match_confidence = "medium"
        authority_status = "provisional_local_source"
    else:
        source_of_authority = "corpus_reference"
        authority_status = "provisional_catalogue" if family_row.get("family_type") == "source_catalogue" else "provisional_publication"
        match_reason = "Seeded from bibliography abbreviation table; local evidence not yet confirmed."

    title = defaults.get("title") or seed_row.get("provisional_label") or family_row.get("family_label")
    shorttitle = defaults.get("shorttitle") or abbreviation or family_row.get("family_label")
    author = defaults.get("author", "")
    year = defaults.get("year", "")
    preferred_key = defaults.get("preferred_key") or seed_row.get("probable_bibtex_key") or None
    bibtex_key = make_bibtex_key(
        author=author,
        year=year,
        title=title,
        preferred=preferred_key,
        fallback_prefix="sourceUnresolved",
        existing_keys=existing_keys,
    )
    return {
        "bibtex_key": bibtex_key,
        "entry_type": defaults.get("entry_type", "misc"),
        "authority_status": authority_status,
        "source_of_authority": source_of_authority,
        "matched_external_key": "",
        "matched_local_source_id": matched_local_source_id,
        "matched_local_source_file": matched_local_source_file,
        "matched_local_reference": matched_local_reference,
        "match_confidence": match_confidence,
        "match_reason": match_reason,
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": author,
        "editor": "",
        "year": year,
        "title": title,
        "shorttitle": shorttitle,
        "journal": title if defaults.get("entry_type") == "periodical" else "",
        "booktitle": "",
        "publisher": "",
        "address": "",
        "volume": "",
        "number": "",
        "pages": "",
        "doi": "",
        "url": "",
        "isbn": "",
        "language": "",
        "script": "Latn",
        "translation_relevance": "unknown",
        "review_status": "reviewed_provisional" if authority_status == "confirmed_local_source" else "needs_human_review",
        "evidence": seed_row.get("evidence", ""),
        "notes": seed_row.get("notes", ""),
    }


def choose_better_row(existing: dict | None, candidate: dict) -> dict:
    if existing is None:
        return candidate
    existing_rank = STATUS_RANK.get(existing["authority_status"], 0)
    candidate_rank = STATUS_RANK.get(candidate["authority_status"], 0)
    if candidate_rank > existing_rank:
        return candidate
    return existing


def build_specific_authority(
    candidate_row: dict,
    family_row: dict,
    local_row: dict | None,
    external_row: dict | None,
    existing_keys: set[str],
) -> dict:
    if external_row is not None:
        bibtex_key = make_bibtex_key(
            author=external_row.get("author", ""),
            year=external_row.get("year", ""),
            title=external_row.get("title", ""),
            preferred=None,
            fallback_prefix="authorityResolved",
            existing_keys=existing_keys,
        )
        return {
            "bibtex_key": bibtex_key,
            "entry_type": external_row.get("entry_type", "book"),
            "authority_status": "confirmed_external_bibtex",
            "source_of_authority": "external_bibtex",
            "matched_external_key": external_row.get("bibtex_key", ""),
            "matched_local_source_id": "",
            "matched_local_source_file": "",
            "matched_local_reference": "",
            "match_confidence": "high",
            "match_reason": "Matched imported external BibTeX metadata by normalized title, author, and year.",
            "family_id": family_row["family_id"],
            "family_label": family_row["family_label"],
            "family_type": family_row["family_type"],
            "author": external_row.get("author", ""),
            "editor": external_row.get("editor", ""),
            "year": external_row.get("year", ""),
            "title": external_row.get("title", ""),
            "shorttitle": candidate_row.get("provisional_short_label", "") or family_row["family_label"],
            "journal": external_row.get("journal", ""),
            "booktitle": external_row.get("booktitle", ""),
            "publisher": external_row.get("publisher", ""),
            "address": external_row.get("address", ""),
            "volume": external_row.get("volume", ""),
            "number": external_row.get("number", ""),
            "pages": external_row.get("pages", ""),
            "doi": external_row.get("doi", ""),
            "url": external_row.get("url", ""),
            "isbn": external_row.get("isbn", ""),
            "language": candidate_row.get("language", ""),
            "script": candidate_row.get("script", ""),
            "translation_relevance": candidate_row.get("translation_relevance", "unknown"),
            "review_status": "reviewed_confirmed",
            "evidence": candidate_row.get("evidence_raw_references", ""),
            "notes": candidate_row.get("notes", ""),
        }

    local_title = local_row.get("probable_work_label", "") if local_row else candidate_row.get("title_original", "")
    local_author = local_row.get("probable_author", "") if local_row else candidate_row.get("author_original", "")
    local_year = local_row.get("probable_year", "") if local_row else candidate_row.get("year", "")
    bibtex_key = make_bibtex_key(
        author=local_author or candidate_row.get("author_original", ""),
        year=local_year or candidate_row.get("year", ""),
        title=local_title or candidate_row.get("title_original", "") or family_row["family_label"],
        preferred=None,
        fallback_prefix="authorityResolved",
        existing_keys=existing_keys,
    )
    if local_row:
        confidence = local_row.get("_match_confidence", "medium")
        authority_status = "confirmed_local_source" if confidence == "high" else "provisional_local_source"
        source_of_authority = local_source_kind(local_row)
        match_reason = local_row.get("_match_reason", "Matched harvested local bibliography file.")
    else:
        authority_status = "provisional_publication"
        source_of_authority = "corpus_reference"
        confidence = "low"
        match_reason = "Built from corpus reference candidate only."
    return {
        "bibtex_key": bibtex_key,
        "entry_type": "book" if family_row.get("family_type") in {"book", "source_catalogue"} else "article",
        "authority_status": authority_status,
        "source_of_authority": source_of_authority,
        "matched_external_key": "",
        "matched_local_source_id": local_row.get("candidate_id", "") if local_row else "",
        "matched_local_source_file": local_row.get("original_path", "") if local_row else "",
        "matched_local_reference": local_row.get("probable_work_label", "") if local_row else "",
        "match_confidence": confidence,
        "match_reason": match_reason,
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": local_author or candidate_row.get("author_original", ""),
        "editor": "",
        "year": local_year or candidate_row.get("year", ""),
        "title": local_title or candidate_row.get("title_original", "") or family_row["family_label"],
        "shorttitle": candidate_row.get("provisional_short_label", "") or family_row["family_label"],
        "journal": "",
        "booktitle": "",
        "publisher": "",
        "address": "",
        "volume": "",
        "number": "",
        "pages": "",
        "doi": "",
        "url": "",
        "isbn": "",
        "language": candidate_row.get("language", ""),
        "script": candidate_row.get("script", ""),
        "translation_relevance": candidate_row.get("translation_relevance", "unknown"),
        "review_status": "reviewed_confirmed" if authority_status == "confirmed_local_source" else "needs_human_review",
        "evidence": candidate_row.get("evidence_raw_references", ""),
        "notes": candidate_row.get("notes", ""),
    }


def build_machine_stub(family_row: dict, candidate_row: dict | None, existing_keys: set[str]) -> dict:
    title = candidate_row.get("title_original", "") if candidate_row else family_row["family_label"]
    bibtex_key = make_bibtex_key(
        author=candidate_row.get("author_original", "") if candidate_row else "",
        year=candidate_row.get("year", "") if candidate_row else "",
        title=title,
        preferred=None,
        fallback_prefix="workUnresolved",
        existing_keys=existing_keys,
    )
    return {
        "bibtex_key": bibtex_key,
        "entry_type": "misc",
        "authority_status": "machine_stub",
        "source_of_authority": "corpus_reference",
        "matched_external_key": "",
        "matched_local_source_id": "",
        "matched_local_source_file": "",
        "matched_local_reference": "",
        "match_confidence": "low",
        "match_reason": "Machine-generated fallback stub from bibliography triage.",
        "family_id": family_row["family_id"],
        "family_label": family_row["family_label"],
        "family_type": family_row["family_type"],
        "author": candidate_row.get("author_original", "") if candidate_row else "",
        "editor": "",
        "year": candidate_row.get("year", "") if candidate_row else "",
        "title": title,
        "shorttitle": candidate_row.get("provisional_short_label", "") if candidate_row else family_row["family_label"],
        "journal": "",
        "booktitle": "",
        "publisher": "",
        "address": "",
        "volume": "",
        "number": "",
        "pages": "",
        "doi": "",
        "url": "",
        "isbn": "",
        "language": candidate_row.get("language", "") if candidate_row else "",
        "script": candidate_row.get("script", "") if candidate_row else "",
        "translation_relevance": candidate_row.get("translation_relevance", "unknown") if candidate_row else "unknown",
        "review_status": candidate_row.get("review_status", "unreviewed") if candidate_row else family_row.get("review_status", "unreviewed"),
        "evidence": candidate_row.get("evidence_raw_references", "") if candidate_row else family_row.get("sample_raw_references", ""),
        "notes": "Provisional entry generated from corpus reference triage; requires human review.",
    }


def build_authority(
    *,
    reference_families_path: Path,
    reference_members_path: Path,
    work_candidates_path: Path,
    seed_path: Path,
    external_entries_path: Path | None = None,
    output_dir: Path,
    frasch_references_path: Path | None = None,
    local_candidates_path: Path | None = None,
    local_manifest_path: Path | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    frasch_references_path = frasch_references_path or Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv")
    local_candidates_path = local_candidates_path or Path("data/working/bibliography/local_sources/high_priority_local_candidates.tsv")
    local_manifest_path = local_manifest_path or Path("data/working/bibliography/local_sources/local_file_manifest.tsv")

    family_rows = read_tsv(reference_families_path)
    member_rows = read_tsv(reference_members_path)
    work_candidate_rows = read_tsv(work_candidates_path)
    seed_rows = read_tsv(seed_path)
    external_rows = read_tsv(external_entries_path) if external_entries_path and external_entries_path.exists() else []
    frasch_rows = read_tsv(frasch_references_path) if frasch_references_path.exists() else []
    local_candidate_rows = dedupe_local_candidates(read_tsv(local_candidates_path)) if local_candidates_path.exists() else []
    local_manifest_rows = read_tsv(local_manifest_path) if local_manifest_path.exists() else []

    family_by_id = {row["family_id"]: row for row in family_rows}
    members_by_family: dict[str, list[dict]] = defaultdict(list)
    for row in member_rows:
        members_by_family[row["family_id"]].append(row)
    candidates_by_family: dict[str, list[dict]] = defaultdict(list)
    for row in work_candidate_rows:
        candidates_by_family[row["family_id"]].append(row)
    seed_by_family = {row["family_id"]: row for row in seed_rows if row.get("family_id")}
    external_index = build_external_index(external_rows)

    authority_by_family: dict[str, dict] = {}
    candidate_rows_by_family: dict[str, dict] = {}
    existing_keys: set[str] = set()

    for family_id, seed_row in seed_by_family.items():
        family_row = family_by_id.get(family_id)
        if family_row is None:
            continue
        authority_by_family[family_id] = choose_better_row(
            authority_by_family.get(family_id),
            build_seed_authority(seed_row, family_row, frasch_rows, local_candidate_rows, existing_keys),
        )

    for family_row in family_rows:
        family_id = family_row["family_id"]
        if family_id in seed_by_family:
            continue
        best_candidate = candidates_by_family.get(family_id, [{}])[0]
        manual_match = MANUAL_LOCAL_MATCHES.get(family_id)
        if manual_match:
            manual_local = next(
                (
                    {
                        **row,
                        "_match_reason": "Matched explicit local file rule for a high-priority bibliography work.",
                        "_match_confidence": manual_match["confidence"],
                    }
                    for row in local_candidate_rows
                    if any(term in normalize_title(f"{row.get('probable_work_label', '')} {row.get('name', '')} {row.get('original_path', '')}") for term in manual_match["filename_terms"])
                ),
                None,
            )
            if manual_local is not None:
                authority_by_family[family_id] = choose_better_row(
                    authority_by_family.get(family_id),
                    build_specific_authority(best_candidate, family_row, manual_local, None, existing_keys),
                )
                continue
        external_match = find_external_match(best_candidate, external_index) if best_candidate else None
        best_local: dict | None = None
        best_score = 0
        for local_row in local_candidate_rows:
            score, reason = score_local_candidate(local_row, best_candidate, family_row, members_by_family.get(family_id, []))
            if score > best_score:
                best_score = score
                best_local = {**local_row, "_match_reason": reason, "_match_confidence": "high" if score >= 6 else "medium"}
        if external_match is not None:
            authority_by_family[family_id] = choose_better_row(
                authority_by_family.get(family_id),
                build_specific_authority(best_candidate, family_row, None, external_match, existing_keys),
            )
            continue
        if best_local is not None and best_score >= 6:
            authority_by_family[family_id] = choose_better_row(
                authority_by_family.get(family_id),
                build_specific_authority(best_candidate, family_row, best_local, None, existing_keys),
            )

    authority_rows = sorted(authority_by_family.values(), key=lambda row: (row["family_label"], row["bibtex_key"]))

    for family_row in family_rows:
        family_id = family_row["family_id"]
        if family_id in authority_by_family:
            continue
        best_candidate = candidates_by_family.get(family_id, [{}])[0]
        candidate_rows_by_family[family_id] = build_machine_stub(family_row, best_candidate, existing_keys)

    candidate_rows = sorted(candidate_rows_by_family.values(), key=lambda row: (row["family_label"], row["bibtex_key"]))

    authority_bib_entries = [row_to_bibtex_entry(row) for row in authority_rows]
    candidate_bib_entries = [row_to_bibtex_entry(row) for row in candidate_rows]
    write_bibtex(output_dir / "bibliography_authority.bib", authority_bib_entries)
    write_bibtex(output_dir / "bibliography_candidates.bib", candidate_bib_entries)
    write_tsv(output_dir / "bibtex_authority.tsv", authority_rows + candidate_rows, AUTHORITY_FIELDS)

    crosswalk_rows = []
    unresolved_rows = []
    for family_row in family_rows:
        family_id = family_row["family_id"]
        resolved = authority_by_family.get(family_id) or candidate_rows_by_family.get(family_id)
        members = members_by_family.get(family_id, []) or [
            {
                "raw_reference_string": family_row.get("sample_raw_references", ""),
                "occurrence_count": family_row.get("occurrence_count", "0"),
                "notes": "",
            }
        ]
        for member in members:
            locator, locator_type = parse_locator(member.get("raw_reference_string", ""), family_id, family_row["family_label"])
            if resolved["authority_status"] == "confirmed_external_bibtex":
                match_type = "external_title_author_year_match"
            elif resolved["authority_status"] == "confirmed_local_source":
                match_type = "local_source_family_match" if family_id in seed_by_family else "local_title_author_year_match"
            elif resolved["authority_status"] == "provisional_local_source":
                match_type = "frasch_source_match" if resolved["source_of_authority"].startswith("frasch") else "provisional_local_source_match"
            elif family_id in seed_by_family:
                match_type = "abbreviation_catalogue_match"
            else:
                match_type = "machine_stub_match"
            crosswalk_rows.append(
                {
                    "raw_reference_string": member.get("raw_reference_string", ""),
                    "family_id": family_id,
                    "work_candidate_id": candidates_by_family.get(family_id, [{}])[0].get("work_candidate_id", ""),
                    "bibtex_key": resolved["bibtex_key"],
                    "match_type": match_type,
                    "match_confidence": resolved.get("match_confidence", "low"),
                    "locator": locator,
                    "locator_type": locator_type,
                    "evidence": resolved.get("match_reason", ""),
                    "needs_human_review": "false" if resolved["authority_status"] in {"confirmed_external_bibtex", "confirmed_local_source"} else "true",
                    "notes": member.get("notes", ""),
                }
            )
        if resolved["authority_status"] in {"machine_stub", "provisional_catalogue", "provisional_publication", "needs_human_review"}:
            unresolved_rows.append(
                {
                    "family_id": family_id,
                    "family_label": family_row["family_label"],
                    "family_type": family_row["family_type"],
                    "member_count": family_row.get("member_count", ""),
                    "occurrence_count": family_row.get("occurrence_count", "0"),
                    "sample_raw_references": family_row.get("sample_raw_references", ""),
                    "current_bibtex_key": resolved["bibtex_key"],
                    "current_status": resolved["authority_status"],
                    "suggested_local_search_terms": ", ".join(
                        token
                        for token in [
                            family_row["family_label"],
                            candidates_by_family.get(family_id, [{}])[0].get("author_original", ""),
                            candidates_by_family.get(family_id, [{}])[0].get("title_original", ""),
                        ]
                        if token
                    ),
                    "notes": "Prioritize local library or Frasch-preface evidence review.",
                }
            )

    crosswalk_rows.sort(key=lambda row: (row["family_id"], row["raw_reference_string"]))
    write_tsv(output_dir / "raw_reference_to_bibtex.tsv", crosswalk_rows, CROSSWALK_FIELDS)

    unresolved_rows.sort(key=lambda row: int(row["occurrence_count"] or 0), reverse=True)
    write_tsv(output_dir / "high_frequency_unresolved.tsv", unresolved_rows, HIGH_FREQUENCY_FIELDS)

    report = {
        "authority_entry_count": len(authority_rows),
        "candidate_entry_count": len(candidate_rows),
        "machine_stub_count": sum(1 for row in candidate_rows if row["authority_status"] == "machine_stub"),
        "confirmed_external_bibtex_count": sum(1 for row in authority_rows if row["authority_status"] == "confirmed_external_bibtex"),
        "confirmed_local_source_count": sum(1 for row in authority_rows if row["authority_status"] == "confirmed_local_source"),
        "provisional_local_source_count": sum(1 for row in authority_rows if row["authority_status"] == "provisional_local_source"),
        "frasch_reference_count": len(frasch_rows),
        "frasch_matched_count": sum(1 for row in authority_rows if row["source_of_authority"].startswith("frasch")),
        "luce_candidate_count": sum(1 for row in local_candidate_rows if "luce" in row.get("original_path", "").casefold()),
        "local_file_count": len({row.get("source_file_id", row.get("sha256", "")) for row in local_manifest_rows}),
        "unresolved_high_frequency_family_count": len(unresolved_rows),
        "top_unresolved_families": [
            {"family_id": row["family_id"], "family_label": row["family_label"], "occurrence_count": int(row["occurrence_count"] or 0)}
            for row in unresolved_rows[:10]
        ],
    }
    (output_dir / "bibtex_authority_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bibliography authority files from triage, external BibTeX, and local evidence.")
    parser.add_argument("--reference-families", type=Path, default=Path("data/working/bibliography/reference_families.tsv"))
    parser.add_argument("--reference-members", type=Path, default=Path("data/working/bibliography/reference_family_members.tsv"))
    parser.add_argument("--work-candidates", type=Path, default=Path("data/working/bibliography/bibliographic_work_candidates.tsv"))
    parser.add_argument("--seed-path", type=Path, default=Path("data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv"))
    parser.add_argument("--external-entries", type=Path, default=Path("data/working/bibliography/external_bibtex/asia_2_entries.tsv"))
    parser.add_argument("--frasch-references", type=Path, default=Path("data/working/bibliography/local_sources/frasch_reference_entries.tsv"))
    parser.add_argument("--local-candidates", type=Path, default=Path("data/working/bibliography/local_sources/high_priority_local_candidates.tsv"))
    parser.add_argument("--local-manifest", type=Path, default=Path("data/working/bibliography/local_sources/local_file_manifest.tsv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/working/bibliography/bibtex_authority"))
    args = parser.parse_args()

    report = build_authority(
        reference_families_path=args.reference_families,
        reference_members_path=args.reference_members,
        work_candidates_path=args.work_candidates,
        seed_path=args.seed_path,
        external_entries_path=args.external_entries,
        frasch_references_path=args.frasch_references,
        local_candidates_path=args.local_candidates,
        local_manifest_path=args.local_manifest,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
