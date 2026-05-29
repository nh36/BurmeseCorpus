from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bibtex_common import make_bibtex_key, normalize_for_match, surname_token, title_keyword_tokens, write_bibtex
from corpus_common import read_tsv, write_tsv


AUTHORITY_FIELDS = [
    "bibtex_key",
    "entry_type",
    "authority_status",
    "source_of_authority",
    "matched_external_key",
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

REPORT_PATH = "data/working/bibliography/bibtex_authority/bibtex_authority_report.json"

MANUAL_AUTHORITY_SEEDS = {
    "fam-obi-internal": {
        "preferred_key": "obiCorpusSource",
        "entry_type": "misc",
        "authority_status": "confirmed_local_source",
        "source_of_authority": "corpus_reference",
        "title": "Old Burmese Inscriptions Corpus structured source set",
        "shorttitle": "OBI Corpus",
        "language": "my",
        "script": "Mymr",
        "review_status": "reviewed_provisional",
        "translation_relevance": "unlikely_translation",
        "evidence": "Repository deposit 4321314 contains the structured OBI corpus volumes that underlie OBI references.",
        "notes": "Repository-backed structured corpus source set rather than a single published monograph.",
    },
    "fam-list-catalogue": {
        "preferred_key": "listCatalogueUnresolved",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "List catalogue reference used in corpus citations",
        "shorttitle": "List",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring List references in the corpus triage layer indicate a stable catalogue-style abbreviation but not yet a fully identified work.",
        "notes": "Catalogue abbreviation requires fuller bibliographic identification.",
    },
    "fam-plate-references": {
        "preferred_key": "plateReferenceSystem",
        "entry_type": "misc",
        "authority_status": "needs_human_review",
        "source_of_authority": "corpus_reference",
        "title": "Plate reference system used in corpus citations",
        "shorttitle": "Pl.",
        "review_status": "needs_human_review",
        "translation_relevance": "unlikely_translation",
        "evidence": "Recurring Pl. references act as plate locators rather than standalone works.",
        "notes": "Internal plate locator family; not a final bibliographic work claim.",
    },
    "fam-rdasb-publication": {
        "preferred_key": "rdasbSeries",
        "entry_type": "misc",
        "authority_status": "provisional_publication",
        "source_of_authority": "manual_seed",
        "title": "Report of the Director, Archaeological Survey of Burma",
        "shorttitle": "RDASB",
        "review_status": "reviewed_provisional",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring RDASB references identify a serial/report family used across the corpus.",
        "notes": "Use raw locators for year and page until issue-level identification is reviewed.",
    },
    "fam-jbrs-publication": {
        "preferred_key": "jbrsSeries",
        "entry_type": "misc",
        "authority_status": "provisional_publication",
        "source_of_authority": "manual_seed",
        "title": "Journal of the Burma Research Society",
        "shorttitle": "JBRS",
        "review_status": "reviewed_provisional",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring JBRS references identify a stable journal family in the corpus reference layer.",
        "notes": "Article-level matches are added separately when author-title evidence is strong.",
    },
    "fam-jras-publication": {
        "preferred_key": "jrasSeries",
        "entry_type": "misc",
        "authority_status": "provisional_publication",
        "source_of_authority": "manual_seed",
        "title": "Journal of the Royal Asiatic Society",
        "shorttitle": "JRAS",
        "review_status": "reviewed_provisional",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring JRAS references identify a stable journal family in the corpus reference layer.",
        "notes": "Series-level authority scaffold pending issue/article review.",
    },
    "fam-bbhc-publication": {
        "preferred_key": "bbhcSeries",
        "entry_type": "misc",
        "authority_status": "provisional_publication",
        "source_of_authority": "manual_seed",
        "title": "Burma Historical Commission bulletin and conference publication family",
        "shorttitle": "BBHC",
        "review_status": "needs_human_review",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring BBHC references point to a consistent publication family but need finer bibliographic separation.",
        "notes": "Keep locators in the crosswalk until volume-level identification stabilizes.",
    },
    "fam-eb-publication": {
        "preferred_key": "epigraphiaBirmanica",
        "entry_type": "misc",
        "authority_status": "provisional_publication",
        "source_of_authority": "manual_seed",
        "title": "Epigraphia Birmanica",
        "shorttitle": "EB",
        "review_status": "reviewed_provisional",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring EB references point to Epigraphia Birmanica as a serial publication family.",
        "notes": "Series-level authority entry pending issue and article normalization.",
    },
    "fam-ippa-catalogue": {
        "preferred_key": "ippaCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "IPPA catalogue reference family",
        "shorttitle": "IPPA",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring IPPA references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-iob-catalogue": {
        "preferred_key": "iobCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "IOB catalogue reference family",
        "shorttitle": "IOB",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring IOB references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-uem-catalogue": {
        "preferred_key": "uemCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "UEM catalogue reference family",
        "shorttitle": "UEM",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring UEM references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-bed-b-catalogue": {
        "preferred_key": "bedBCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "BED B catalogue reference family",
        "shorttitle": "BED B",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring BED B references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-or-catalogue": {
        "preferred_key": "orCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "OR catalogue reference family",
        "shorttitle": "OR",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring OR references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-mm-catalogue": {
        "preferred_key": "mmCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "MM catalogue reference family",
        "shorttitle": "MM",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring MM references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-sip-catalogue": {
        "preferred_key": "sipCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "SIP catalogue reference family",
        "shorttitle": "SIP",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring SIP references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-ppa-catalogue": {
        "preferred_key": "ppaCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "PPA catalogue reference family",
        "shorttitle": "PPA",
        "review_status": "needs_human_review",
        "translation_relevance": "unknown",
        "evidence": "Recurring PPA references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-tn-catalogue": {
        "preferred_key": "thanTunCatalogue",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "Than Tun catalogue reference family",
        "shorttitle": "TN",
        "review_status": "needs_human_review",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring TN references behave as a catalogue/source abbreviation in corpus citations.",
        "notes": "Catalogue identification remains provisional.",
    },
    "fam-u-min-hswe-catalogue": {
        "preferred_key": "uMinHsweCatalog",
        "entry_type": "misc",
        "authority_status": "provisional_catalogue",
        "source_of_authority": "manual_seed",
        "title": "U Min Hswe catalogue reference family",
        "shorttitle": "U Min Hswe",
        "review_status": "needs_human_review",
        "translation_relevance": "possible_translation",
        "evidence": "Recurring U Min Hswe references identify a named catalogue/source family in corpus citations.",
        "notes": "Named catalogue family, pending fuller bibliographic confirmation.",
    },
}

SPECIAL_MEMBER_PATTERNS = [
    {
        "pattern": re.compile(r"\bHarvey,\s*History\b", flags=re.IGNORECASE),
        "authority": {
            "preferred_key": "harvey1925history",
            "entry_type": "book",
            "authority_status": "provisional_publication",
            "source_of_authority": "corpus_reference",
            "title": "History of Burma",
            "shorttitle": "History of Burma",
            "author": "Harvey",
            "year": "1925",
            "translation_relevance": "possible_translation",
            "review_status": "reviewed_provisional",
            "notes": "Specific work extracted from broader reference families when author-title evidence is explicit; external or local confirmation still preferred.",
        },
    },
    {
        "pattern": re.compile(r"\bRay,\s*Theravada Buddhism\b", flags=re.IGNORECASE),
        "authority": {
            "preferred_key": "ray1946theravada",
            "entry_type": "book",
            "authority_status": "provisional_publication",
            "source_of_authority": "corpus_reference",
            "title": "Theravada Buddhism in Burma",
            "shorttitle": "Theravada Buddhism",
            "author": "Ray",
            "year": "1946",
            "translation_relevance": "possible_translation",
            "review_status": "reviewed_provisional",
            "notes": "Specific work extracted from broader reference families when author-title evidence is explicit; external or local confirmation still preferred.",
        },
    },
    {
        "pattern": re.compile(r"\bMyanmar's Debt\b", flags=re.IGNORECASE),
        "authority": {
            "preferred_key": "luce1932myanmarsDebt",
            "entry_type": "article",
            "authority_status": "provisional_publication",
            "source_of_authority": "corpus_reference",
            "title": "Burma's Economic Life, or Myanmar's Debt to the Mon",
            "shorttitle": "Myanmar's Debt",
            "author": "G. H. Luce",
            "year": "1932",
            "journal": "Journal of the Burma Research Society",
            "translation_relevance": "possible_translation",
            "review_status": "reviewed_provisional",
            "notes": "Specific article-level work recognized from raw reference strings; external or local confirmation still preferred.",
        },
    },
]

KNOWN_ABBREVIATION_KEYS = {
    "obi": "fam-obi-internal",
    "list": "fam-list-catalogue",
    "pl.": "fam-plate-references",
    "ppa": "fam-ppa-catalogue",
    "tn": "fam-tn-catalogue",
    "rdasb": "fam-rdasb-publication",
    "u min hswe": "fam-u-min-hswe-catalogue",
    "ippa": "fam-ippa-catalogue",
    "uem": "fam-uem-catalogue",
    "bed b": "fam-bed-b-catalogue",
    "sip": "fam-sip-catalogue",
    "mm": "fam-mm-catalogue",
    "or": "fam-or-catalogue",
    "iob": "fam-iob-catalogue",
    "jbrs": "fam-jbrs-publication",
    "bbhc": "fam-bbhc-publication",
    "jras": "fam-jras-publication",
    "eb": "fam-eb-publication",
}


def load_external_entries(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    rows = read_tsv(path)
    by_key: dict[str, dict] = {}
    for row in rows:
        by_key[row["bibtex_key"]] = row
    return by_key


def locate_external_match(authority_seed: dict, external_entries: dict[str, dict]) -> tuple[str, dict | None]:
    target_title = normalize_for_match(authority_seed.get("title"))
    target_author = surname_token(authority_seed.get("author"))
    target_year = authority_seed.get("year", "")
    best_key = ""
    best_row = None
    best_score = 0
    for key, row in external_entries.items():
        score = 0
        row_title = normalize_for_match(row.get("title", ""))
        row_author = surname_token(row.get("author", "") or row.get("editor", ""))
        row_year = row.get("year", "")
        if target_title and row_title == target_title:
            score += 4
        elif target_title and target_title and target_title in row_title:
            score += 3
        if target_author and row_author == target_author:
            score += 2
        if target_year and row_year == target_year:
            score += 1
        if score > best_score:
            best_score = score
            best_key = key
            best_row = row
    return (best_key, best_row) if best_score >= 4 else ("", None)


def family_by_id(rows: list[dict]) -> dict[str, dict]:
    return {row["family_id"]: row for row in rows}


def work_candidate_by_family(rows: list[dict]) -> dict[str, dict]:
    return {row["family_id"]: row for row in rows}


def members_by_family(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["family_id"], []).append(row)
    for group in grouped.values():
        group.sort(key=lambda row: int(row["occurrence_count"]), reverse=True)
    return grouped


def parse_locator(raw_reference: str, family_id: str, family_label: str) -> tuple[str, str]:
    text = raw_reference.strip()
    if family_id == "fam-obi-internal":
        match = re.match(r"^OBI\s*(.*)$", text, flags=re.IGNORECASE)
        locator = match.group(1).strip(" ,;") if match else text
        return locator, "volume_page" if "p." in locator.casefold() or "," in locator else "number"
    if family_id == "fam-plate-references":
        match = re.match(r"^Pl\.\s*(.*)$", text, flags=re.IGNORECASE)
        return (match.group(1).strip(" ,;") if match else text, "plate")
    if family_id == "fam-list-catalogue":
        match = re.match(r"^List\s*(.*)$", text, flags=re.IGNORECASE)
        return (match.group(1).strip(" ,;") if match else text, "catalogue_number")
    if family_id in {"fam-rdasb-publication", "fam-jbrs-publication", "fam-jras-publication", "fam-bbhc-publication", "fam-eb-publication"}:
        short = family_label.strip()
        locator = re.sub(rf"^.*?\b{re.escape(short)}\b", "", text, flags=re.IGNORECASE).strip(" ,;")
        if not locator:
            year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
            locator = year_match.group(1) if year_match else ""
        return locator, "volume_page" if locator else "none"
    if family_id in MANUAL_AUTHORITY_SEEDS:
        short = family_label.strip()
        locator = re.sub(rf"^{re.escape(short)}\s*", "", text, flags=re.IGNORECASE).strip(" ,;")
        if re.search(r"\bno\.\s*\d+\b|\b\d+[a-z]?\b", locator, flags=re.IGNORECASE):
            return locator, "catalogue_number"
        return locator, "unclear" if locator else "none"
    if re.search(r"\bp+\.\s*\d+", text, flags=re.IGNORECASE):
        page_match = re.search(r"(p+\.\s*\d+(?:-\d+)?)", text, flags=re.IGNORECASE)
        return (page_match.group(1) if page_match else "", "page")
    if re.search(r"\bPl\.\s*[A-ZIVX0-9]+", text, flags=re.IGNORECASE):
        plate_match = re.search(r"(Pl\.\s*[A-ZIVX0-9]+\s*\d*)", text, flags=re.IGNORECASE)
        return (plate_match.group(1) if plate_match else "", "plate")
    number_match = re.search(r"\b(?:no\.|number)\s*([A-Za-z0-9.-]+)", text, flags=re.IGNORECASE)
    if number_match:
        return number_match.group(1), "number"
    return "", "none"


def build_entry_dict(row: dict) -> dict:
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
    }
    return {
        "entry_type": row["entry_type"],
        "bibtex_key": row["bibtex_key"],
        "fields": {name: value for name, value in fields.items() if value},
    }


def extract_member_specific_seed(raw_reference: str) -> dict | None:
    for item in SPECIAL_MEMBER_PATTERNS:
        if item["pattern"].search(raw_reference):
            return dict(item["authority"])
    return None


def build_stub_row(
    *,
    family: dict,
    candidate: dict,
    seed_key: str | None,
    existing_keys: set[str],
    sequence_number: int,
) -> dict:
    preferred = seed_key or ""
    fallback_prefix = f"workUnresolved{sequence_number:04d}"
    key = make_bibtex_key(
        author=candidate.get("author_original", ""),
        year=candidate.get("year", ""),
        title=candidate.get("title_original") or family.get("family_label", ""),
        preferred=preferred,
        fallback_prefix=fallback_prefix,
        existing_keys=existing_keys,
    )
    authority_status = "machine_stub"
    if family["family_type"] == "source_catalogue":
        authority_status = "provisional_catalogue"
    elif family["family_type"] in {"publication", "article", "book"}:
        authority_status = "provisional_publication"
    return {
        "bibtex_key": key,
        "entry_type": family["family_type"] if family["family_type"] in {"article", "book"} else "misc",
        "authority_status": authority_status,
        "source_of_authority": "corpus_reference",
        "matched_external_key": "",
        "family_id": family["family_id"],
        "family_label": family["family_label"],
        "family_type": family["family_type"],
        "author": candidate.get("author_original", ""),
        "editor": "",
        "year": candidate.get("year", ""),
        "title": candidate.get("title_original") or family["family_label"],
        "shorttitle": family["family_label"],
        "journal": "",
        "booktitle": "",
        "publisher": candidate.get("publication_details", ""),
        "address": "",
        "volume": "",
        "number": "",
        "pages": "",
        "doi": "",
        "url": "",
        "isbn": "",
        "language": candidate.get("language", ""),
        "script": candidate.get("script", ""),
        "translation_relevance": candidate.get("translation_relevance", "unknown"),
        "review_status": candidate.get("review_status", "unreviewed"),
        "evidence": candidate.get("evidence_raw_references", ""),
        "notes": "Provisional entry generated from corpus reference triage; requires human review",
    }


def build_authority(
    *,
    reference_families_path: Path,
    reference_members_path: Path,
    work_candidates_path: Path,
    seed_path: Path,
    external_entries_path: Path | None,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    families = read_tsv(reference_families_path)
    members = read_tsv(reference_members_path)
    candidates = read_tsv(work_candidates_path)
    seeds = read_tsv(seed_path)
    external_entries = load_external_entries(external_entries_path)

    families_by_id = family_by_id(families)
    members_grouped = members_by_family(members)
    candidates_by_family = work_candidate_by_family(candidates)
    seeds_by_family = {row["family_id"]: row for row in seeds}

    authority_rows: list[dict] = []
    candidate_rows: list[dict] = []
    crosswalk_rows: list[dict] = []
    authority_entries: list[dict] = []
    candidate_entries: list[dict] = []
    existing_keys: set[str] = set()
    raw_specific_map: dict[str, tuple[str, str, str, str]] = {}
    preferred_specific_keys: dict[str, str] = {}

    for family_id, family in families_by_id.items():
        if family_id in MANUAL_AUTHORITY_SEEDS:
            seed = dict(MANUAL_AUTHORITY_SEEDS[family_id])
            external_key, external_row = locate_external_match(seed, external_entries)
            if external_row:
                seed["matched_external_key"] = external_key
                seed["author"] = external_row.get("author", "") or seed.get("author", "")
                seed["editor"] = external_row.get("editor", "")
                seed["title"] = external_row.get("title", "") or seed.get("title", "")
                seed["journal"] = external_row.get("journal", "")
                seed["booktitle"] = external_row.get("booktitle", "")
                seed["publisher"] = external_row.get("publisher", "")
                seed["address"] = external_row.get("address", "")
                seed["doi"] = external_row.get("doi", "")
                seed["url"] = external_row.get("url", "")
                seed["isbn"] = external_row.get("isbn", "")
                seed["year"] = external_row.get("year", "") or seed.get("year", "")
            key = make_bibtex_key(
                author=seed.get("author", ""),
                year=seed.get("year", ""),
                title=seed.get("title", ""),
                preferred=seed.get("preferred_key"),
                existing_keys=existing_keys,
            )
            row = {
                "bibtex_key": key,
                "entry_type": seed["entry_type"],
                "authority_status": seed["authority_status"],
                "source_of_authority": seed["source_of_authority"],
                "matched_external_key": seed.get("matched_external_key", ""),
                "family_id": family_id,
                "family_label": family["family_label"],
                "family_type": family["family_type"],
                "author": seed.get("author", ""),
                "editor": seed.get("editor", ""),
                "year": seed.get("year", ""),
                "title": seed.get("title", ""),
                "shorttitle": seed.get("shorttitle", family["family_label"]),
                "journal": seed.get("journal", ""),
                "booktitle": seed.get("booktitle", ""),
                "publisher": seed.get("publisher", ""),
                "address": seed.get("address", ""),
                "volume": "",
                "number": "",
                "pages": "",
                "doi": seed.get("doi", ""),
                "url": seed.get("url", ""),
                "isbn": seed.get("isbn", ""),
                "language": seed.get("language", ""),
                "script": seed.get("script", ""),
                "translation_relevance": seed.get("translation_relevance", "unknown"),
                "review_status": seed.get("review_status", "unreviewed"),
                "evidence": seed.get("evidence", ""),
                "notes": seed.get("notes", ""),
            }
            authority_rows.append(row)
            authority_entries.append(build_entry_dict(row))

    for family_id, member_rows in members_grouped.items():
        for member in member_rows:
            member_seed = extract_member_specific_seed(member["raw_reference_string"])
            if not member_seed:
                continue
            external_key, external_row = locate_external_match(member_seed, external_entries)
            if external_row:
                member_seed["matched_external_key"] = external_key
                member_seed["authority_status"] = "confirmed_external_bibtex"
                member_seed["source_of_authority"] = "asia_2_bib"
                member_seed["author"] = external_row.get("author", "") or member_seed.get("author", "")
                member_seed["editor"] = external_row.get("editor", "")
                member_seed["title"] = external_row.get("title", "") or member_seed.get("title", "")
                member_seed["journal"] = external_row.get("journal", member_seed.get("journal", ""))
                member_seed["booktitle"] = external_row.get("booktitle", "")
                member_seed["publisher"] = external_row.get("publisher", "")
                member_seed["address"] = external_row.get("address", "")
                member_seed["doi"] = external_row.get("doi", "")
                member_seed["url"] = external_row.get("url", "")
                member_seed["isbn"] = external_row.get("isbn", "")
                member_seed["year"] = external_row.get("year", "") or member_seed.get("year", "")
            preferred_key = member_seed.get("preferred_key", "")
            key = preferred_specific_keys.get(preferred_key)
            if not key:
                key = make_bibtex_key(
                    author=member_seed.get("author", ""),
                    year=member_seed.get("year", ""),
                    title=member_seed.get("title", ""),
                    preferred=preferred_key,
                    existing_keys=existing_keys,
                )
                if preferred_key:
                    preferred_specific_keys[preferred_key] = key
            row = {
                "bibtex_key": key,
                "entry_type": member_seed["entry_type"],
                "authority_status": member_seed["authority_status"],
                "source_of_authority": member_seed["source_of_authority"],
                "matched_external_key": member_seed.get("matched_external_key", ""),
                "family_id": family_id,
                "family_label": families_by_id[family_id]["family_label"],
                "family_type": families_by_id[family_id]["family_type"],
                "author": member_seed.get("author", ""),
                "editor": member_seed.get("editor", ""),
                "year": member_seed.get("year", ""),
                "title": member_seed.get("title", ""),
                "shorttitle": member_seed.get("shorttitle", member_seed.get("title", "")),
                "journal": member_seed.get("journal", ""),
                "booktitle": member_seed.get("booktitle", ""),
                "publisher": member_seed.get("publisher", ""),
                "address": member_seed.get("address", ""),
                "volume": "",
                "number": "",
                "pages": "",
                "doi": member_seed.get("doi", ""),
                "url": member_seed.get("url", ""),
                "isbn": member_seed.get("isbn", ""),
                "language": "",
                "script": "",
                "translation_relevance": member_seed.get("translation_relevance", "unknown"),
                "review_status": member_seed.get("review_status", "unreviewed"),
                "evidence": f"Matched specific raw reference string: {member['raw_reference_string']}",
                "notes": member_seed.get("notes", ""),
            }
            if not any(existing_row["bibtex_key"] == row["bibtex_key"] for existing_row in authority_rows):
                authority_rows.append(row)
                authority_entries.append(build_entry_dict(row))
            raw_specific_map[member["raw_reference_string"]] = (
                row["bibtex_key"],
                "title_author_year_match",
                "high",
                row["evidence"],
            )

    family_authority_map = {row["family_id"]: row["bibtex_key"] for row in authority_rows if row["family_id"]}
    sequence_number = 0
    for candidate in candidates:
        family = families_by_id[candidate["family_id"]]
        if candidate["family_id"] in family_authority_map:
            continue
        sequence_number += 1
        seed_row = seeds_by_family.get(candidate["family_id"])
        seed_key = seed_row["probable_bibtex_key"] if seed_row else ""
        row = build_stub_row(
            family=family,
            candidate=candidate,
            seed_key=seed_key,
            existing_keys=existing_keys,
            sequence_number=sequence_number,
        )
        candidate_rows.append(row)
        candidate_entries.append(build_entry_dict(row))
        family_authority_map[candidate["family_id"]] = row["bibtex_key"]

    candidate_rows.sort(key=lambda row: row["bibtex_key"])
    authority_rows.sort(key=lambda row: row["bibtex_key"])
    authority_entries.sort(key=lambda entry: entry["bibtex_key"])
    candidate_entries.sort(key=lambda entry: entry["bibtex_key"])

    for member in members:
        family = families_by_id[member["family_id"]]
        work_candidate = candidates_by_family.get(member["family_id"], {})
        locator, locator_type = parse_locator(member["raw_reference_string"], member["family_id"], family["family_label"])
        if member["raw_reference_string"] in raw_specific_map:
            bibtex_key, match_type, confidence, evidence = raw_specific_map[member["raw_reference_string"]]
        else:
            bibtex_key = family_authority_map.get(member["family_id"], "")
            if member["family_id"] in MANUAL_AUTHORITY_SEEDS:
                match_type = "abbreviation_catalogue_match"
                confidence = "medium"
                evidence = MANUAL_AUTHORITY_SEEDS[member["family_id"]]["evidence"]
            elif bibtex_key:
                match_type = "machine_stub_match"
                confidence = "low"
                evidence = "Mapped to provisional BibTeX stub generated from family-level triage data."
            else:
                match_type = "no_match"
                confidence = "low"
                evidence = "No authority or candidate match available."
        crosswalk_rows.append(
            {
                "raw_reference_string": member["raw_reference_string"],
                "family_id": member["family_id"],
                "work_candidate_id": work_candidate.get("work_candidate_id", ""),
                "bibtex_key": bibtex_key,
                "match_type": match_type,
                "match_confidence": confidence,
                "locator": locator,
                "locator_type": locator_type,
                "evidence": evidence,
                "needs_human_review": "true" if confidence != "high" or match_type != "title_author_year_match" else "false",
                "notes": "",
            }
        )

    authority_bib_path = output_dir / "bibliography_authority.bib"
    candidates_bib_path = output_dir / "bibliography_candidates.bib"
    authority_tsv_path = output_dir / "bibtex_authority.tsv"
    crosswalk_tsv_path = output_dir / "raw_reference_to_bibtex.tsv"
    report_path = output_dir / "bibtex_authority_report.json"

    write_bibtex(authority_bib_path, authority_entries)
    write_bibtex(candidates_bib_path, candidate_entries)
    write_tsv(authority_tsv_path, authority_rows + candidate_rows, AUTHORITY_FIELDS)
    write_tsv(crosswalk_tsv_path, crosswalk_rows, CROSSWALK_FIELDS)

    report = {
        "authority_entry_count": len(authority_rows),
        "candidate_entry_count": len(candidate_rows),
        "crosswalk_row_count": len(crosswalk_rows),
        "matched_external_entry_count": sum(1 for row in authority_rows if row["matched_external_key"]),
        "external_entries_available": bool(external_entries),
        "manual_seed_family_count": sum(1 for family_id in MANUAL_AUTHORITY_SEEDS if family_id in families_by_id),
        "authority_status_counts": dict(Counter(row["authority_status"] for row in authority_rows + candidate_rows)),
        "match_type_counts": dict(Counter(row["match_type"] for row in crosswalk_rows)),
        "external_entries_path": external_entries_path.as_posix() if external_entries_path and external_entries_path.exists() else "",
        "notes": [
            "bibliography_authority.bib is conservative and combines repository-backed source-family seeds with any matched external BibTeX entries when available.",
            "bibliography_candidates.bib contains provisional stubs for unresolved families and requires human review.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the BibTeX authority working layer from bibliography triage.")
    parser.add_argument(
        "--reference-families",
        type=Path,
        default=Path("data/working/bibliography/reference_families.tsv"),
    )
    parser.add_argument(
        "--reference-family-members",
        type=Path,
        default=Path("data/working/bibliography/reference_family_members.tsv"),
    )
    parser.add_argument(
        "--work-candidates",
        type=Path,
        default=Path("data/working/bibliography/bibliographic_work_candidates.tsv"),
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv"),
    )
    parser.add_argument(
        "--external-entries",
        type=Path,
        default=Path("data/working/bibliography/external_bibtex/asia_2_entries.tsv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/working/bibliography/bibtex_authority"),
    )
    args = parser.parse_args()

    report = build_authority(
        reference_families_path=args.reference_families,
        reference_members_path=args.reference_family_members,
        work_candidates_path=args.work_candidates,
        seed_path=args.seed_file,
        external_entries_path=args.external_entries,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
