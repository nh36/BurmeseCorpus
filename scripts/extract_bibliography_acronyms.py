#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from corpus_common import REPO_ROOT, read_tsv, write_tsv
from local_bibliography_common import extract_text_from_path, repo_relative_or_none, sha256_file, source_file_id

PRIORITY_ACRONYMS = [
    "A",
    "ARASI",
    "B",
    "BBHC",
    "BED B",
    "EB",
    "IOB",
    "IPPA",
    "JBRS",
    "JRAS",
    "List",
    "Luce D",
    "Luce J",
    "MM",
    "MP",
    "OBI",
    "OR",
    "PPA",
    "Pl.",
    "RDASB",
    "SIP",
    "TN",
    "UB",
    "UEM",
    "U Min Hswe",
]

SUPPLEMENTAL_ACRONYMS: list[str] = []

STRONG_DEFINITION_EVIDENCE_TYPES = {
    "explicit_abbreviation_list",
    "explicit_parenthetical_definition",
    "bibliography_heading",
    "source_list_entry",
    "footnote_definition",
}

MAX_STRONG_DEFINITION_QUOTE_LENGTH = 200
SECTION_HEADINGS = [
    "Abbreviations",
    "Abkürzungen",
    "Sigla",
    "Bibliography",
    "References",
    "Sources",
    "Quellen",
    "Literatur",
    "Verzeichnis",
    "List of abbreviations",
    "Bibliographic information",
    "Source abbreviations",
    "Works cited",
]
ABBREVIATION_SECTION_HEADINGS = {
    "abbreviations",
    "abkürzungen",
    "sigla",
    "list of abbreviations",
    "bibliographic information",
    "source abbreviations",
}
GENERIC_BIBLIOGRAPHY_HEADINGS = {
    "bibliography",
    "references",
    "sources",
    "quellen",
    "literatur",
    "verzeichnis",
    "works cited",
}

CANDIDATE_FIELDS = [
    "candidate_id",
    "file_name",
    "original_path",
    "copied_path",
    "file_type",
    "sha256",
    "size",
    "match_reason",
    "probable_role",
    "extraction_status",
    "notes",
]

DEFINITION_FIELDS = [
    "candidate_id",
    "acronym",
    "candidate_expansion",
    "raw_definition",
    "definition_context",
    "source_file_id",
    "source_file_label",
    "source_location_hint",
    "evidence_type",
    "confidence",
    "definition_quality",
    "needs_human_review",
    "notes",
]

FRASCH_FIELDS = [
    "candidate_id",
    "acronym",
    "candidate_expansion",
    "raw_context",
    "source_file_id",
    "source_file_label",
    "page_or_location",
    "evidence_type",
    "confidence",
    "notes",
]

BAGAN_CONTEXT_FIELDS = [
    "candidate_id",
    "acronym",
    "raw_context_before",
    "match_text",
    "raw_context_after",
    "source_location_hint",
    "looks_like_definition",
    "looks_like_usage",
    "confidence",
    "notes",
]

DOCUMENTATION_SECTION_FIELDS = [
    "source_file_id",
    "source_file_label",
    "source_origin",
    "ocr_source",
    "section_heading",
    "page_hint",
    "section_start_hint",
    "section_end_hint",
    "section_text_excerpt",
    "contains_priority_acronyms",
    "acronyms_found",
    "section_confidence",
    "extraction_confidence",
    "notes",
]

FALSE_POSITIVE_AUDIT_FIELDS = [
    "acronym",
    "candidate_id",
    "bad_candidate_expansion",
    "bad_evidence_quote",
    "source_file_label",
    "reason_rejected",
    "new_status",
    "notes",
]

OCR_QUEUE_FIELDS = [
    "source_file_id",
    "source_file_label",
    "reason_ocr_needed",
    "priority",
    "priority_reason",
    "target_acronyms",
    "expected_value",
    "notes",
]
OCR_MANIFEST_FIELDS = [
    "source_file_id",
    "source_file_label",
    "source_path",
    "local_text_path",
    "file_type",
    "extraction_method",
    "tool_used",
    "extraction_status",
    "text_sha256",
    "text_length",
    "page_scope",
    "notes",
]
OCR_INDEX_FIELDS = [
    "source_file_id",
    "source_file_label",
    "ocr_source",
    "page_hint",
    "section_start_hint",
    "section_end_hint",
    "matched_heading",
    "snippet_text",
    "acronyms_found",
    "extraction_confidence",
    "notes",
]

FILE_KEYWORDS = {
    "corpus_documentation": [
        "bibliographic information",
        "burmese inscription volumes",
        "old burmese inscriptions",
        "corpus",
        "documentation",
    ],
    "bagan_epig_database": ["bagan epig database"],
    "frasch_stadt_und_staat": [
        "pagan stadt und staat",
        "pagan city and state",
        "englishtransalation",
        "machineenglishtranslation",
        "frasc",
    ],
    "luce_local_source": ["luce"],
}

MANUAL_DEFINITION_PATTERNS = {
    "PPA": [
        (
            re.compile(r"Inscriptions of Pagan,\s*Pinya and Ava\s*\(PPA\)", re.IGNORECASE),
            "Inscriptions of Pagan, Pinya and Ava",
            "explicit_parenthetical_definition",
            "explicit",
            "high",
        )
    ],
    "UB": [
        (
            re.compile(r"Inscriptions collected in Upper Burma\s*\(UB\s*1,\s*UB\s*2\)", re.IGNORECASE),
            "Inscriptions Collected in Upper Burma",
            "explicit_parenthetical_definition",
            "explicit",
            "high",
        )
    ],
    "UEM": [
        (
            re.compile(r"U E Maung'?s selection\s*\(UEM\)", re.IGNORECASE),
            "U E Maung selection",
            "explicit_parenthetical_definition",
            "strong",
            "high",
        )
    ],
    "BBHC": [
        (
            re.compile(r"Bulletin of the Burma Historical Commission\s*\(BBHC\)", re.IGNORECASE),
            "Bulletin of the Burma Historical Commission",
            "explicit_parenthetical_definition",
            "explicit",
            "high",
        )
    ],
    "A": [
        (
            re.compile(
                r"Original Inscriptions Collected by King Bodawpaya and now placed near the Patodawgyi Pagoda,\s*Amarapura\s*\(A\)",
                re.IGNORECASE,
            ),
            "Original Inscriptions Collected by King Bodawpaya and now placed near the Patodawgyi Pagoda, Amarapura",
            "explicit_parenthetical_definition",
            "explicit",
            "high",
        )
    ],
    "B": [
        (
            re.compile(
                r"Inscriptions Copied from the Stones Collected by King Bodawpaya and Placed near the Aracan\s+Pagoda\s*\(B\s*1,\s*B\s*2\)",
                re.IGNORECASE | re.DOTALL,
            ),
            "Inscriptions Copied from the Stones Collected by King Bodawpaya and Placed near the Aracan Pagoda",
            "explicit_parenthetical_definition",
            "explicit",
            "high",
        )
    ],
    "BED B": [
        (
            re.compile(r"Bagan Epigraphic Database\s*\(BED\).*?PART B", re.IGNORECASE | re.DOTALL),
            "Bagan Epigraphic Database, Part B",
            "source_list_entry",
            "strong",
            "medium",
        )
    ],
}

PLACEHOLDER_EXPANSION_PATTERN = re.compile(
    r"\b(source family|catalogue family|publication family|series family|source family attested|unexpanded)\b",
    re.IGNORECASE,
)
LOCATOR_USAGE_PATTERN = re.compile(
    r"\b(?:p{1,2}\.?|page|pages|plate|plates|pl\.|vol\.|volume|no\.|nr\.)\s*[0-9ivxlcdm]",
    re.IGNORECASE,
)
NOTE_PREFIX_PATTERN = re.compile(
    r"^(?:date|remark|remarks|spelling|location|contents?|inscription\s+number|lines?|page|pages|face|obverse|reverse|catalogue)\b",
    re.IGNORECASE,
)
BAD_EXPANSION_PHRASES = (
    "spelling of inscription",
    "spelling variant",
    "date:",
    "date of inscription",
    "catalogue body",
    "ordinary reading",
)
TITLE_HINT_WORDS = {
    "inscriptions",
    "pagan",
    "pinya",
    "ava",
    "upper burma",
    "burma",
    "burmese",
    "journal",
    "report",
    "archaeological",
    "survey",
    "database",
    "historical commission",
    "historical",
    "commission",
    "bulletin",
    "selections",
    "comparative",
    "list",
}


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def snippet(text: str, start: int, end: int, radius: int = 220) -> str:
    return compact_text(text[max(0, start - radius) : min(len(text), end + radius)])


def infer_probable_role(file_name: str, path_hint: str) -> str:
    haystack = f"{file_name} {path_hint}".casefold()
    for role, keywords in FILE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return role
    return "supporting_local_source"


def infer_match_reason(file_name: str, role: str) -> str:
    if role == "corpus_documentation":
        return "matched corpus documentation keywords"
    if role == "bagan_epig_database":
        return "matched Bagan Epigraphic Database title"
    if role == "frasch_stadt_und_staat":
        return "matched Frasch Pagan/Stadt-und-Staat title"
    if role == "luce_local_source":
        return "matched Luce local-source keyword"
    return f"matched bibliography-source file name {file_name}"


def normalize_acronym(value: str) -> str:
    return re.sub(r"[\s.]+", "", value or "").casefold()


def canonical_false_positive_status(acronym: str) -> str:
    if acronym == "OBI":
        return "internal_reference"
    if acronym == "BED B":
        return "probable_expansion"
    return "source_family_only"


def short_definition_quote(acronym: str, matched_text: str) -> str:
    compact = compact_text(matched_text)
    if acronym == "BED B":
        bed_match = re.search(r"Bagan Epigraphic Database\s*\(BED\)", matched_text, re.IGNORECASE)
        part_match = re.search(r"PART\s+B[^.\n]{0,120}", matched_text, re.IGNORECASE)
        if bed_match and part_match:
            return compact_text(f"{bed_match.group(0)} — {part_match.group(0)}")
    return compact[:MAX_STRONG_DEFINITION_QUOTE_LENGTH]


def starts_definition_entry(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        re.match(r"^[A-Z][A-Za-z. ]{0,24}(?:\s*[:=–—-]\s+|\s{2,}\S+|\t+\S+)", stripped)
    )


def looks_like_section_heading(line: str) -> str | None:
    stripped = compact_text(line)
    if not stripped or len(stripped) > 80:
        return None
    lowered = stripped.casefold()
    for heading in SECTION_HEADINGS:
        heading_lower = heading.casefold()
        if lowered == heading_lower:
            return heading
        if lowered.startswith(f"{heading_lower}:"):
            remainder = stripped[len(heading) + 1 :].strip()
            if remainder and len(remainder) <= 24 and not re.search(r"[=;]|\d", remainder):
                return heading
    return None


def section_heading_kind(heading: str) -> str:
    lowered = heading.casefold()
    if lowered in ABBREVIATION_SECTION_HEADINGS:
        return "abbreviation"
    if lowered in GENERIC_BIBLIOGRAPHY_HEADINGS:
        return "bibliography"
    return "other"


def line_has_definition_pattern(line: str, acronym: str) -> bool:
    escaped = re.escape(acronym)
    return any(
        pattern.search(line)
        for pattern in (
            re.compile(rf"^\s*{escaped}\s*[:=–—-]\s+\S+"),
            re.compile(rf"^\s*{escaped}(?:\t+|\s{{2,}})\S+"),
            re.compile(rf"\(\s*{escaped}\s*\)"),
        )
    )


def section_definition_hits(excerpt: str) -> list[str]:
    lines = [compact_text(line) for line in excerpt.splitlines() if compact_text(line)]
    hits: list[str] = []
    for acronym in PRIORITY_ACRONYMS:
        letters_only = re.sub(r"[^A-Za-z]+", "", acronym)
        if len(letters_only) < 2:
            if not any(line_has_definition_pattern(line, acronym) for line in lines):
                continue
        elif not any(line_has_definition_pattern(line, acronym) for line in lines):
            continue
        hits.append(acronym)
    return sorted(dict.fromkeys(hits), key=lambda value: value.casefold())


def looks_like_irrelevant_tibetan_material(source_file_label: str, excerpt: str) -> bool:
    lowered = f"{source_file_label} {excerpt}".casefold()
    if not any(token in lowered for token in ("tibet", "tibetan", "richardson")):
        return False
    return not any(token in lowered for token in ("burma", "burmese", "bagan", "pagan", "obi"))


def evaluate_documentation_section(
    *,
    source_file_label: str,
    heading: str,
    excerpt_lines: list[str],
) -> tuple[bool, list[str], str, str]:
    excerpt = "\n".join(excerpt_lines)
    if looks_like_irrelevant_tibetan_material(source_file_label, excerpt):
        return False, [], "low", "irrelevant Tibetan bibliography material"

    explicit_hits = section_definition_hits(excerpt)
    heading_kind = section_heading_kind(heading)
    if heading_kind == "bibliography" and not explicit_hits:
        return False, [], "low", "ordinary bibliography section without explicit abbreviation patterns"

    if explicit_hits:
        confidence = "high" if heading_kind == "abbreviation" else "medium"
        return True, explicit_hits, confidence, ""

    contextual_hits = [
        acronym
        for acronym in PRIORITY_ACRONYMS
        if len(re.sub(r"[^A-Za-z]+", "", acronym)) >= 2 and acronym in excerpt
    ]
    contextual_hits = sorted(dict.fromkeys(contextual_hits), key=lambda value: value.casefold())
    if heading_kind == "abbreviation" and contextual_hits:
        return True, contextual_hits, "medium", "section heading suggests abbreviation list; explicit row not yet isolated"
    return False, [], "low", "no explicit abbreviation evidence in inspected section"


def should_continue_definition(expansion: str) -> bool:
    compact = compact_text(expansion)
    if not compact:
        return False
    if compact.endswith((",", ":", ";", "-", "–", "—")):
        return True
    tail = re.findall(r"[A-Za-z]+", compact.casefold())
    if not tail:
        return False
    return tail[-1] in {"the", "of", "from", "and", "for", "in", "on", "to"}


def clean_definition_expansion(expansion: str) -> str:
    compact = compact_text(expansion)
    compact = re.sub(r"(?<=[A-Za-z])~(?=[A-Za-z])", "s", compact)
    compact = re.sub(r";\s*[A-Z][A-Z0-9 ]{1,8}$", "", compact)
    return compact.strip(" ;,")


def extend_definition_line(lines: list[str], index: int, line: str, expansion: str) -> tuple[str, str]:
    raw_lines = [line]
    expanded = clean_definition_expansion(expansion)
    for next_line in lines[index + 1 : index + 3]:
        next_compact = compact_text(next_line)
        if not next_compact or looks_like_section_heading(next_compact) or starts_definition_entry(next_compact):
            break
        if not should_continue_definition(expanded):
            break
        if NOTE_PREFIX_PATTERN.match(next_compact):
            break
        candidate = compact_text(f"{expanded} {next_compact}")
        if len(candidate) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
            break
        expanded = clean_definition_expansion(candidate)
        raw_lines.append(next_compact)
    return expanded, compact_text(" ".join(raw_lines))


def looks_like_titleish_text(value: str) -> bool:
    compact = compact_text(value)
    if len(compact) < 4 or len(compact) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
        return False
    if NOTE_PREFIX_PATTERN.match(compact):
        return False
    if any(phrase in compact.casefold() for phrase in BAD_EXPANSION_PHRASES):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'.-]*", compact)
    if len(words) < 2:
        return False
    significant = [word for word in words if len(word) > 2 and word.casefold() not in {"and", "the", "of", "from", "for", "in", "on", "to"}]
    if not significant:
        return False
    if any(keyword in compact.casefold() for keyword in TITLE_HINT_WORDS):
        return True
    capitalized = sum(1 for word in significant if word[0].isupper())
    return capitalized >= max(1, len(significant) // 2)


def validate_definition_candidate(acronym: str, expansion: str, raw_definition: str) -> str | None:
    compact_expansion = compact_text(expansion)
    compact_raw = compact_text(raw_definition)
    if PLACEHOLDER_EXPANSION_PATTERN.search(compact_expansion):
        return "placeholder expansion text is not a real definition"
    if compact_expansion.casefold() == "or":
        return "ordinary English 'or' is not the OR acronym"
    if re.search(
        rf"\b{re.escape(acronym)}\b\s*,?\s*(?:p{{1,2}}\.?|page|pages|plate|plates|pl\.|vol\.|volume|no\.|nr\.)\s*[0-9ivxlcdm]",
        compact_raw,
        re.IGNORECASE,
    ):
        return "contextual locator usage is not a definition"
    if len(compact_raw) > MAX_STRONG_DEFINITION_QUOTE_LENGTH:
        return "definition quote exceeds maximum length"
    if not looks_like_titleish_text(compact_expansion):
        return "candidate expansion does not look like a title or source name"
    return None


def build_false_positive_row(
    *,
    acronym: str,
    candidate_id: str,
    bad_candidate_expansion: str,
    bad_evidence_quote: str,
    source_file_label: str,
    reason_rejected: str,
    new_status: str | None = None,
    notes: str = "",
) -> dict[str, str]:
    return {
        "acronym": acronym,
        "candidate_id": candidate_id,
        "bad_candidate_expansion": compact_text(bad_candidate_expansion),
        "bad_evidence_quote": compact_text(bad_evidence_quote)[:MAX_STRONG_DEFINITION_QUOTE_LENGTH],
        "source_file_label": source_file_label,
        "reason_rejected": reason_rejected,
        "new_status": new_status or canonical_false_positive_status(acronym),
        "notes": notes,
    }


def extract_documentation_sections(
    text: str,
    *,
    source_file_id: str,
    source_file_label: str,
    source_origin: str = "direct_text",
    ocr_source: str = "",
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [line.rstrip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        heading = looks_like_section_heading(line)
        if not heading:
            continue
        excerpt_lines = [compact_text(line)]
        for next_line in lines[index + 1 :]:
            if looks_like_section_heading(next_line):
                break
            next_compact = compact_text(next_line)
            if not next_compact:
                if len(excerpt_lines) > 1:
                    break
                continue
            excerpt_lines.append(next_compact)
            if len(" ".join(excerpt_lines)) >= 600 or len(excerpt_lines) >= 14:
                break
        include_row, acronyms_found, section_confidence, notes = evaluate_documentation_section(
            source_file_label=source_file_label,
            heading=heading,
            excerpt_lines=excerpt_lines,
        )
        if not include_row:
            continue
        excerpt = compact_text(" ".join(excerpt_lines))
        rows.append(
            {
                "source_file_id": source_file_id,
                "source_file_label": source_file_label,
                "source_origin": source_origin,
                "ocr_source": ocr_source,
                "section_heading": heading,
                "page_hint": "",
                "section_start_hint": f"line {index + 1}",
                "section_end_hint": f"line {index + len(excerpt_lines)}",
                "section_text_excerpt": excerpt[:600],
                "contains_priority_acronyms": "true" if acronyms_found else "false",
                "acronyms_found": ", ".join(acronyms_found),
                "section_confidence": section_confidence,
                "extraction_confidence": "high" if compact_text(line).casefold() == heading.casefold() else "medium",
                "notes": notes,
            }
        )
    return rows


def documentation_sections_from_ocr_index(index_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index_row in index_rows:
        heading = index_row.get("matched_heading", "").strip()
        excerpt_lines = [heading, index_row.get("snippet_text", "")]
        include_row, acronyms_found, section_confidence, notes = evaluate_documentation_section(
            source_file_label=index_row.get("source_file_label", ""),
            heading=heading,
            excerpt_lines=[compact_text(line) for line in excerpt_lines if compact_text(line)],
        )
        if not include_row:
            continue
        rows.append(
            {
                "source_file_id": index_row.get("source_file_id", ""),
                "source_file_label": index_row.get("source_file_label", ""),
                "source_origin": "targeted_ocr",
                "ocr_source": index_row.get("ocr_source", ""),
                "section_heading": heading,
                "page_hint": index_row.get("page_hint", ""),
                "section_start_hint": index_row.get("section_start_hint", ""),
                "section_end_hint": index_row.get("section_end_hint", ""),
                "section_text_excerpt": compact_text(index_row.get("snippet_text", ""))[:600],
                "contains_priority_acronyms": "true" if acronyms_found else "false",
                "acronyms_found": ", ".join(acronyms_found),
                "section_confidence": section_confidence,
                "extraction_confidence": index_row.get("extraction_confidence", section_confidence),
                "notes": notes or index_row.get("notes", ""),
            }
        )
    deduped: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        deduped.setdefault(
            (row["source_file_id"], row["section_heading"], row["section_text_excerpt"]),
            row,
        )
    return sorted(deduped.values(), key=lambda row: (row["source_file_label"].casefold(), row["section_heading"].casefold()))


def build_ocr_priority_queue(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in candidates:
        if row.get("extraction_status") != "ocr_needed":
            continue
        role = row.get("probable_role", "")
        file_name = row.get("file_name", "")
        lowered = file_name.casefold()
        priority = "low"
        priority_reason = "supporting source may contain contextual references"
        target_acronyms = "A, ARASI, B, BBHC, EB, IOB, IPPA, JBRS, JRAS, List, Luce D, Luce J, MM, MP, OBI, OR, PPA, Pl., RDASB, SIP, TN, UB, UEM"
        expected_value = "possible abbreviation list or bibliography evidence"
        if role in {"corpus_documentation", "frasch_stadt_und_staat"}:
            priority = "high"
            priority_reason = "core documentary witness for explicit acronym definitions"
            expected_value = "explicit abbreviation list, bibliography heading, or source-list entry"
        elif role == "luce_local_source" and any(token in lowered for token in ("luce", "pe maung tin", "comparative", "inscriptions")):
            priority = "high"
            priority_reason = "likely to define Luce or SIP-style source abbreviations"
            target_acronyms = "A, B, ARASI, EB, IOB, JBRS, JRAS, Luce D, Luce J, OBI, PPA, Pl., RDASB, SIP, UB"
            expected_value = "abbreviation definitions or source-list titles"
        elif role == "bagan_epig_database":
            priority = "medium"
            priority_reason = "useful for catalogue-part acronyms but mostly contextual"
            target_acronyms = "A, B, BED B, PPA, MP, UB"
            expected_value = "section heading or abbreviation-list evidence"
        queue.append(
            {
                "source_file_id": row["candidate_id"],
                "source_file_label": file_name,
                "reason_ocr_needed": row.get("notes", "") or "text extraction returned no content",
                "priority": priority,
                "priority_reason": priority_reason,
                "target_acronyms": target_acronyms,
                "expected_value": expected_value,
                "notes": "",
            }
        )
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(queue, key=lambda row: (priority_order.get(row["priority"], 9), row["source_file_label"].casefold()))


def extract_explicit_definition_candidates(
    text: str,
    *,
    source_file_id: str,
    source_file_label: str,
    acronyms: Iterable[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    candidates: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    chosen = list(acronyms or PRIORITY_ACRONYMS + SUPPLEMENTAL_ACRONYMS)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for acronym in chosen:
        if len(re.sub(r"[^A-Za-z]+", "", acronym)) < 2:
            continue
        escaped = re.escape(acronym)
        line_pattern = re.compile(rf"^\s*{escaped}\s*[:=–—-]\s*(?P<expansion>.+?)\s*$")
        list_pattern = re.compile(rf"^\s*{escaped}(?:\t+|\s{{2,}})(?P<expansion>.+?)\s*$")
        reverse_pattern = re.compile(rf"^(?P<expansion>.+?)\s*\(\s*{escaped}\s*\)\s*$")
        for line_index, line in enumerate(lines):
            line_number = line_index + 1
            if PLACEHOLDER_EXPANSION_PATTERN.search(line):
                continue
            if acronym.isupper() and re.match(rf"^\s*{re.escape(acronym.casefold())}\s*[:=–—-]\s*", line):
                rejected.append(
                    build_false_positive_row(
                        acronym=acronym,
                        candidate_id=f"{source_file_id}:{normalize_acronym(acronym)}:line{line_number}",
                        bad_candidate_expansion=line.split("=", 1)[-1] if "=" in line else line.split(":", 1)[-1],
                        bad_evidence_quote=line,
                        source_file_label=source_file_label,
                        reason_rejected=f"lowercase {acronym.casefold()!r} is not the {acronym} acronym",
                    )
                )
                continue
            match = line_pattern.match(line)
            evidence_type = "explicit_abbreviation_list"
            if not match:
                match = list_pattern.match(line)
            if not match:
                match = reverse_pattern.match(line)
                evidence_type = "explicit_parenthetical_definition"
            if not match:
                continue
            expansion = clean_definition_expansion(match.group("expansion"))
            raw_definition = compact_text(line)
            if evidence_type == "explicit_abbreviation_list":
                expansion, raw_definition = extend_definition_line(lines, line_index, line, expansion)
                raw_definition = f"{acronym} = {expansion}"
            if len(expansion) < 4:
                continue
            rejection_reason = validate_definition_candidate(acronym, expansion, raw_definition)
            candidate_id = f"{source_file_id}:{normalize_acronym(acronym)}:line{line_number}"
            if rejection_reason:
                rejected.append(
                    build_false_positive_row(
                        acronym=acronym,
                        candidate_id=candidate_id,
                        bad_candidate_expansion=expansion,
                        bad_evidence_quote=raw_definition,
                        source_file_label=source_file_label,
                        reason_rejected=rejection_reason,
                    )
                )
                continue
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "acronym": acronym,
                    "candidate_expansion": expansion,
                    "raw_definition": raw_definition,
                    "definition_context": snippet(text, text.find(line), text.find(line) + len(line)),
                    "source_file_id": source_file_id,
                    "source_file_label": source_file_label,
                    "source_location_hint": f"line {line_number}",
                    "evidence_type": evidence_type,
                    "confidence": "high",
                    "definition_quality": "explicit",
                    "needs_human_review": "false",
                    "notes": "",
                }
            )
    return candidates, rejected


def classify_definition_candidate_row(row: dict[str, str]) -> tuple[str, bool]:
    evidence_type = row.get("evidence_type", "")
    if evidence_type in STRONG_DEFINITION_EVIDENCE_TYPES:
        return row.get("definition_quality", "strong") or "strong", True
    return row.get("definition_quality", "context_only") or "context_only", False


def discover_candidate_files() -> list[dict[str, str]]:
    manifest_path = REPO_ROOT / "data/working/bibliography/local_sources/local_file_manifest.tsv"
    candidates: list[dict[str, str]] = []
    seen_paths: set[Path] = set()
    if manifest_path.exists():
        for row in read_tsv(manifest_path):
            copied_path = REPO_ROOT / row["copied_path"] if row.get("copied_path") else None
            original_path = REPO_ROOT / row["original_path"] if row.get("original_path", "").startswith("data/") else copied_path
            path = copied_path or original_path
            if not path or not path.exists() or path in seen_paths:
                continue
            role = infer_probable_role(row.get("file_name", path.name), row.get("original_path", ""))
            if role == "supporting_local_source" and "frasch" not in row.get("file_name", "").casefold():
                continue
            seen_paths.add(path)
            candidates.append(
                {
                    "candidate_id": row.get("source_file_id") or source_file_id(path),
                    "file_name": row.get("file_name") or path.name,
                    "original_path": row.get("original_path") or repo_relative_or_none(path) or str(path),
                    "copied_path": row.get("copied_path") or repo_relative_or_none(path) or str(path),
                    "file_type": row.get("file_type") or path.suffix.lstrip(".").lower(),
                    "sha256": row.get("sha256") or sha256_file(path),
                    "size": row.get("file_size") or str(path.stat().st_size),
                    "match_reason": infer_match_reason(row.get("file_name", path.name), role),
                    "probable_role": role,
                    "extraction_status": "pending",
                    "notes": "",
                }
            )
    return sorted(candidates, key=lambda row: (row["probable_role"], row["file_name"].casefold()))


def extract_definition_candidates_from_text(
    text: str,
    *,
    source_file_id: str,
    source_file_label: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    candidates, rejected = extract_explicit_definition_candidates(
        text,
        source_file_id=source_file_id,
        source_file_label=source_file_label,
    )
    for acronym, pattern_specs in MANUAL_DEFINITION_PATTERNS.items():
        for pattern, expansion, evidence_type, definition_quality, confidence in pattern_specs:
            for index, match in enumerate(pattern.finditer(text), start=1):
                matched_text = match.group(0)
                concise_quote = short_definition_quote(acronym, matched_text)
                candidate_id = f"{source_file_id}:{normalize_acronym(acronym)}:pattern{index}"
                if compact_text(matched_text) != concise_quote:
                    rejected.append(
                        build_false_positive_row(
                            acronym=acronym,
                            candidate_id=candidate_id,
                            bad_candidate_expansion=expansion,
                            bad_evidence_quote=matched_text,
                            source_file_label=source_file_label,
                            reason_rejected="long catalogue-body match was replaced by a concise documentary quote",
                            notes="Superseded by a shortened quote drawn from the same match.",
                        )
                    )
                rejection_reason = validate_definition_candidate(acronym, expansion, concise_quote)
                if rejection_reason:
                    rejected.append(
                        build_false_positive_row(
                            acronym=acronym,
                            candidate_id=candidate_id,
                            bad_candidate_expansion=expansion,
                            bad_evidence_quote=concise_quote,
                            source_file_label=source_file_label,
                            reason_rejected=rejection_reason,
                        )
                    )
                    continue
                candidates.append(
                    {
                        "candidate_id": candidate_id,
                        "acronym": acronym,
                        "candidate_expansion": expansion,
                        "raw_definition": concise_quote,
                        "definition_context": snippet(text, match.start(), match.end()),
                        "source_file_id": source_file_id,
                        "source_file_label": source_file_label,
                        "source_location_hint": "full-text pattern hit",
                        "evidence_type": evidence_type,
                        "confidence": confidence,
                        "definition_quality": definition_quality,
                        "needs_human_review": "false" if definition_quality == "explicit" else "true",
                        "notes": "",
                    }
                )
    deduped: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in candidates:
        key = (row["source_file_id"], row["acronym"], row["candidate_expansion"])
        deduped.setdefault(key, row)
    deduped_rejected: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rejected:
        key = (row["acronym"], row["source_file_label"], row["reason_rejected"])
        deduped_rejected.setdefault(key, row)
    return (
        sorted(deduped.values(), key=lambda row: (row["acronym"], row["source_file_label"], row["candidate_id"])),
        sorted(deduped_rejected.values(), key=lambda row: (row["acronym"], row["source_file_label"], row["candidate_id"])),
    )


def extract_bagan_context_rows(text: str, *, source_file_id: str, source_file_label: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    acronyms = PRIORITY_ACRONYMS + SUPPLEMENTAL_ACRONYMS
    for acronym in acronyms:
        for index, match in enumerate(re.finditer(re.escape(acronym), text), start=1):
            before = compact_text(text[max(0, match.start() - 140) : match.start()])
            after = compact_text(text[match.end() : min(len(text), match.end() + 140)])
            looks_like_definition = "true" if any(token in f"{before} {after}".casefold() for token in ("abbreviations", "bibliography", "references")) else "false"
            rows.append(
                {
                    "candidate_id": f"{source_file_id}:{normalize_acronym(acronym)}:context{index}",
                    "acronym": acronym,
                    "raw_context_before": before,
                    "match_text": acronym,
                    "raw_context_after": after,
                    "source_location_hint": f"context hit {index}",
                    "looks_like_definition": looks_like_definition,
                    "looks_like_usage": "false" if looks_like_definition == "true" else "true",
                    "confidence": "medium" if looks_like_definition == "true" else "low",
                    "notes": "",
                }
            )
            if index >= 4:
                break
    return rows


def extract_frasch_rows(text: str, *, source_file_id: str, source_file_label: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for acronym in PRIORITY_ACRONYMS + SUPPLEMENTAL_ACRONYMS:
        found = False
        for pattern, expansion, evidence_type, _definition_quality, confidence in MANUAL_DEFINITION_PATTERNS.get(acronym, []):
            for match in pattern.finditer(text):
                rows.append(
                    {
                        "candidate_id": f"{source_file_id}:{normalize_acronym(acronym)}:frasch",
                        "acronym": acronym,
                        "candidate_expansion": expansion,
                        "raw_context": snippet(text, match.start(), match.end()),
                        "source_file_id": source_file_id,
                        "source_file_label": source_file_label,
                        "page_or_location": "full-text pattern hit",
                        "evidence_type": evidence_type,
                        "confidence": confidence,
                        "notes": "",
                    }
                )
                found = True
        if found:
            continue
        for index, match in enumerate(re.finditer(re.escape(acronym), text), start=1):
            rows.append(
                {
                    "candidate_id": f"{source_file_id}:{normalize_acronym(acronym)}:frasch-context{index}",
                    "acronym": acronym,
                    "candidate_expansion": "",
                    "raw_context": snippet(text, match.start(), match.end()),
                    "source_file_id": source_file_id,
                    "source_file_label": source_file_label,
                    "page_or_location": f"context hit {index}",
                    "evidence_type": "contextual_usage",
                    "confidence": "low",
                    "notes": "",
                }
            )
            if index >= 2:
                break
    return rows


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_ocr_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {
        row["source_file_id"]: row
        for row in read_tsv(path)
        if row.get("source_file_id")
    }


def load_ocr_index(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {}
    rows_by_source: dict[str, list[dict[str, str]]] = {}
    for row in read_tsv(path):
        source_id = row.get("source_file_id", "")
        if not source_id:
            continue
        rows_by_source.setdefault(source_id, []).append(row)
    return rows_by_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract bibliography acronym evidence from local documentation sources.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data/working/bibliography/local_sources",
        help="Directory for acronym evidence outputs.",
    )
    parser.add_argument(
        "--ocr-manifest",
        type=Path,
        default=REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_manifest.tsv",
        help="Targeted OCR manifest TSV.",
    )
    parser.add_argument(
        "--ocr-index",
        type=Path,
        default=REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_text_index.tsv",
        help="Targeted OCR snippet index TSV.",
    )
    parser.add_argument(
        "--ocr-report",
        type=Path,
        default=REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs/ocr_report.json",
        help="Targeted OCR report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    ocr_manifest_by_source = load_ocr_manifest(args.ocr_manifest)
    ocr_index_by_source = load_ocr_index(args.ocr_index)
    ocr_report = load_json(args.ocr_report)

    documentation_candidates = discover_candidate_files()
    definition_rows: list[dict[str, str]] = []
    frasch_rows: list[dict[str, str]] = []
    bagan_rows: list[dict[str, str]] = []
    documentation_sections: list[dict[str, str]] = []
    false_positive_rows: list[dict[str, str]] = []
    ocr_needed: list[dict[str, str]] = []

    for candidate in documentation_candidates:
        candidate_path = REPO_ROOT / candidate["copied_path"] if candidate["copied_path"].startswith("data/") else Path(candidate["copied_path"])
        if not candidate_path.exists():
            candidate["extraction_status"] = "missing"
            candidate["notes"] = "candidate path not found"
            continue
        text, extraction_method, warnings = extract_text_from_path(candidate_path)
        source_origin = "direct_text"
        ocr_source = ""
        ocr_manifest_row = ocr_manifest_by_source.get(candidate["candidate_id"])
        if not text.strip() and ocr_manifest_row and ocr_manifest_row.get("extraction_status") in {"success", "extracted", "ocr_complete"}:
            local_text_path = REPO_ROOT / ocr_manifest_row["local_text_path"]
            if local_text_path.exists():
                text = local_text_path.read_text(encoding="utf-8")
                source_origin = "targeted_ocr"
                ocr_source = ocr_manifest_row.get("tool_used", "")
                warnings = [warning for warning in warnings if warning]
                if ocr_manifest_row.get("notes"):
                    warnings.append(ocr_manifest_row["notes"])
        if not text.strip():
            candidate["extraction_status"] = "ocr_needed"
            candidate["notes"] = "; ".join(warnings) or "text extraction returned no content"
            ocr_needed.append(candidate)
            continue
        candidate["extraction_status"] = "ocr_extracted" if source_origin == "targeted_ocr" else "extracted"
        candidate_notes = [warning for warning in warnings if warning]
        if source_origin == "targeted_ocr":
            candidate_notes.append(f"targeted OCR via {ocr_source or 'local OCR manifest'}")
        elif extraction_method:
            candidate_notes.append(f"text extraction via {extraction_method}")
        candidate["notes"] = "; ".join(dict.fromkeys(candidate_notes))
        if source_origin == "targeted_ocr" and candidate["candidate_id"] in ocr_index_by_source:
            documentation_sections.extend(
                documentation_sections_from_ocr_index(ocr_index_by_source[candidate["candidate_id"]])
            )
        else:
            documentation_sections.extend(
                extract_documentation_sections(
                    text,
                    source_file_id=candidate["candidate_id"],
                    source_file_label=candidate["file_name"],
                    source_origin=source_origin,
                    ocr_source=ocr_source,
                )
            )
        candidate_rows, candidate_rejections = extract_definition_candidates_from_text(
            text,
            source_file_id=candidate["candidate_id"],
            source_file_label=candidate["file_name"],
        )
        definition_rows.extend(candidate_rows)
        false_positive_rows.extend(candidate_rejections)
        if candidate["probable_role"] == "frasch_stadt_und_staat":
            frasch_rows.extend(
                extract_frasch_rows(
                    text,
                    source_file_id=candidate["candidate_id"],
                    source_file_label=candidate["file_name"],
                )
            )
        if candidate["probable_role"] == "bagan_epig_database":
            bagan_rows.extend(
                extract_bagan_context_rows(
                    text,
                    source_file_id=candidate["candidate_id"],
                    source_file_label=candidate["file_name"],
                )
            )

    found_by_acronym = {row["acronym"] for row in definition_rows if classify_definition_candidate_row(row)[1]}
    deduped_sections: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in documentation_sections:
        deduped_sections.setdefault(
            (row["source_file_id"], row["section_heading"], row["section_text_excerpt"]),
            row,
        )
    documentation_sections = sorted(
        deduped_sections.values(),
        key=lambda row: (row["source_file_label"].casefold(), row["section_heading"].casefold(), row["section_text_excerpt"].casefold()),
    )
    for acronym in PRIORITY_ACRONYMS:
        if acronym not in found_by_acronym:
            definition_rows.append(
                {
                    "candidate_id": f"negative:{normalize_acronym(acronym)}",
                    "acronym": acronym,
                    "candidate_expansion": "",
                    "raw_definition": "",
                    "definition_context": "",
                    "source_file_id": "",
                    "source_file_label": "",
                    "source_location_hint": "searched documentation corpus",
                    "evidence_type": "negative_evidence",
                    "confidence": "low",
                    "definition_quality": "not_found",
                    "needs_human_review": "true",
                    "notes": "No strong definition candidate found in searched corpus documentation or Frasch files.",
                }
            )

    report = {
        "documentation_files_searched_count": sum(
            1
            for row in documentation_candidates
            if row["probable_role"] == "corpus_documentation" and row["extraction_status"] in {"extracted", "ocr_extracted"}
        ),
        "frasch_stadt_staat_files_searched_count": sum(
            1
            for row in documentation_candidates
            if row["probable_role"] == "frasch_stadt_und_staat" and row["extraction_status"] in {"extracted", "ocr_extracted"}
        ),
        "fratsch_stadt_staat_files_searched_count": sum(
            1
            for row in documentation_candidates
            if row["probable_role"] == "frasch_stadt_und_staat" and row["extraction_status"] in {"extracted", "ocr_extracted"}
        ),
        "bagan_database_context_matches": len(bagan_rows),
        "ocr_needed_count": len(ocr_needed),
        "ocr_priority_queue_count": len(build_ocr_priority_queue(documentation_candidates)),
        "files_requiring_ocr": [row["file_name"] for row in ocr_needed],
        "definition_candidate_count": len(definition_rows),
        "strong_definition_count": sum(1 for row in definition_rows if classify_definition_candidate_row(row)[1]),
        "false_positive_audit_count": len(false_positive_rows),
        "documentation_abbreviation_sections_count": len(documentation_sections),
        "abbreviation_sections_from_ocr_count": sum(1 for row in documentation_sections if row["source_origin"] == "targeted_ocr"),
        "ocr_files_attempted": ocr_report.get("files_attempted", 0),
        "ocr_files_successful": ocr_report.get("files_successful", 0),
        "ocr_files_failed": ocr_report.get("files_failed", 0),
        "priority_acronyms_without_strong_definition": [
            acronym for acronym in PRIORITY_ACRONYMS if acronym not in found_by_acronym
        ],
    }

    write_tsv(output_dir / "corpus_documentation_candidates.tsv", documentation_candidates, CANDIDATE_FIELDS)
    write_tsv(output_dir / "acronym_definition_candidates.tsv", definition_rows, DEFINITION_FIELDS)
    write_tsv(output_dir / "frasch_stadt_staat_acronyms.tsv", frasch_rows, FRASCH_FIELDS)
    write_tsv(output_dir / "bagan_epig_database_acronym_contexts.tsv", bagan_rows, BAGAN_CONTEXT_FIELDS)
    write_tsv(output_dir / "documentation_abbreviation_sections.tsv", documentation_sections, DOCUMENTATION_SECTION_FIELDS)
    write_tsv(output_dir / "acronym_false_positive_audit.tsv", false_positive_rows, FALSE_POSITIVE_AUDIT_FIELDS)
    write_tsv(output_dir / "ocr_priority_queue.tsv", build_ocr_priority_queue(documentation_candidates), OCR_QUEUE_FIELDS)
    (output_dir / "acronym_definition_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
