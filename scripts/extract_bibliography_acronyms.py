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
    "PPA",
    "IPPA",
    "UEM",
    "SIP",
    "MP",
    "UB",
    "MM",
    "OR",
    "TN",
    "U Min Hswe",
    "Luce D",
    "Luce J",
    "Pl.",
    "A",
    "B",
    "BED B",
    "ARASI",
    "RDASB",
    "BBHC",
]

SUPPLEMENTAL_ACRONYMS = ["List", "IOB", "OBI", "JBRS", "JRAS", "EB"]

STRONG_DEFINITION_EVIDENCE_TYPES = {
    "explicit_abbreviation_list",
    "explicit_parenthetical_definition",
    "bibliography_heading",
    "source_list_entry",
    "footnote_definition",
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


def extract_explicit_definition_candidates(
    text: str,
    *,
    source_file_id: str,
    source_file_label: str,
    acronyms: Iterable[str] | None = None,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    chosen = list(acronyms or PRIORITY_ACRONYMS + SUPPLEMENTAL_ACRONYMS)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for acronym in chosen:
        if len(re.sub(r"[^A-Za-z]+", "", acronym)) < 2:
            continue
        escaped = re.escape(acronym)
        line_pattern = re.compile(rf"^\s*{escaped}\s*[:=\-]\s*(?P<expansion>.+?)\s*$", re.IGNORECASE)
        reverse_pattern = re.compile(rf"^(?P<expansion>.+?)\s*\(\s*{escaped}\s*\)\s*$", re.IGNORECASE)
        for line_number, line in enumerate(lines, start=1):
            if PLACEHOLDER_EXPANSION_PATTERN.search(line):
                continue
            match = line_pattern.match(line)
            evidence_type = "explicit_abbreviation_list"
            if not match:
                match = reverse_pattern.match(line)
                evidence_type = "explicit_parenthetical_definition"
            if not match:
                continue
            expansion = compact_text(match.group("expansion"))
            if len(expansion) < 4:
                continue
            candidates.append(
                {
                    "candidate_id": f"{source_file_id}:{normalize_acronym(acronym)}:line{line_number}",
                    "acronym": acronym,
                    "candidate_expansion": expansion,
                    "raw_definition": line,
                    "definition_context": line,
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
    return candidates


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
) -> list[dict[str, str]]:
    candidates = extract_explicit_definition_candidates(
        text,
        source_file_id=source_file_id,
        source_file_label=source_file_label,
    )
    for acronym, pattern_specs in MANUAL_DEFINITION_PATTERNS.items():
        for pattern, expansion, evidence_type, definition_quality, confidence in pattern_specs:
            for index, match in enumerate(pattern.finditer(text), start=1):
                matched_text = compact_text(match.group(0))
                candidates.append(
                    {
                        "candidate_id": f"{source_file_id}:{normalize_acronym(acronym)}:pattern{index}",
                        "acronym": acronym,
                        "candidate_expansion": expansion,
                        "raw_definition": matched_text,
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
    return sorted(deduped.values(), key=lambda row: (row["acronym"], row["source_file_label"], row["candidate_id"]))


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract bibliography acronym evidence from local documentation sources.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data/working/bibliography/local_sources",
        help="Directory for acronym evidence outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    documentation_candidates = discover_candidate_files()
    extracted_texts: dict[str, tuple[dict[str, str], str]] = {}
    definition_rows: list[dict[str, str]] = []
    frasch_rows: list[dict[str, str]] = []
    bagan_rows: list[dict[str, str]] = []
    ocr_needed: list[dict[str, str]] = []

    for candidate in documentation_candidates:
        candidate_path = REPO_ROOT / candidate["copied_path"] if candidate["copied_path"].startswith("data/") else Path(candidate["copied_path"])
        if not candidate_path.exists():
            candidate["extraction_status"] = "missing"
            candidate["notes"] = "candidate path not found"
            continue
        text, _method, warnings = extract_text_from_path(candidate_path)
        if not text.strip():
            candidate["extraction_status"] = "ocr_needed"
            candidate["notes"] = "; ".join(warnings) or "text extraction returned no content"
            ocr_needed.append(candidate)
            continue
        candidate["extraction_status"] = "extracted"
        candidate["notes"] = "; ".join(warnings)
        extracted_texts[candidate["candidate_id"]] = (candidate, text)

        definition_rows.extend(
            extract_definition_candidates_from_text(
                text,
                source_file_id=candidate["candidate_id"],
                source_file_label=candidate["file_name"],
            )
        )
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
        "documentation_files_searched_count": sum(1 for row in documentation_candidates if row["probable_role"] == "corpus_documentation" and row["extraction_status"] == "extracted"),
        "frasch_stadt_staat_files_searched_count": sum(1 for row in documentation_candidates if row["probable_role"] == "frasch_stadt_und_staat" and row["extraction_status"] == "extracted"),
        "fratsch_stadt_staat_files_searched_count": sum(1 for row in documentation_candidates if row["probable_role"] == "frasch_stadt_und_staat" and row["extraction_status"] == "extracted"),
        "bagan_database_context_matches": len(bagan_rows),
        "ocr_needed_count": len(ocr_needed),
        "files_requiring_ocr": [row["file_name"] for row in ocr_needed],
        "definition_candidate_count": len(definition_rows),
        "strong_definition_count": sum(1 for row in definition_rows if classify_definition_candidate_row(row)[1]),
        "priority_acronyms_without_strong_definition": [
            acronym for acronym in PRIORITY_ACRONYMS if acronym not in found_by_acronym
        ],
    }

    write_tsv(output_dir / "corpus_documentation_candidates.tsv", documentation_candidates, CANDIDATE_FIELDS)
    write_tsv(output_dir / "acronym_definition_candidates.tsv", definition_rows, DEFINITION_FIELDS)
    write_tsv(output_dir / "frasch_stadt_staat_acronyms.tsv", frasch_rows, FRASCH_FIELDS)
    write_tsv(output_dir / "bagan_epig_database_acronym_contexts.tsv", bagan_rows, BAGAN_CONTEXT_FIELDS)
    (output_dir / "acronym_definition_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
