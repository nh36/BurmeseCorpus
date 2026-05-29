from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bibtex_common import make_bibtex_key, sha256_text, write_bibtex
from corpus_common import REPO_ROOT, read_tsv, write_tsv
from local_bibliography_common import extract_text_from_path


FRASCH_FIELDS = [
    "frasch_ref_id",
    "raw_reference",
    "author",
    "editor",
    "year",
    "title",
    "publication",
    "journal",
    "volume",
    "number",
    "pages",
    "publisher",
    "place",
    "language",
    "script",
    "confidence",
    "detected_entry_type",
    "looks_like_bibliographic_reference",
    "looks_like_catalogue_note",
    "looks_like_body_text",
    "has_author_signal",
    "has_year_signal",
    "has_title_signal",
    "has_publication_signal",
    "length",
    "recommended_action",
    "source_location_hint",
    "extraction_source_file",
    "notes",
]

QUALITY_FIELDS = [
    "frasch_ref_id",
    "raw_reference",
    "source_file",
    "detected_entry_type",
    "looks_like_bibliographic_reference",
    "looks_like_catalogue_note",
    "looks_like_body_text",
    "length",
    "has_author_signal",
    "has_year_signal",
    "has_title_signal",
    "has_publication_signal",
    "confidence",
    "recommended_action",
    "notes",
]

BAGAN_ABBREVIATION_FIELDS = [
    "abbreviation",
    "expansion",
    "raw_definition",
    "source_location_hint",
    "evidence_type",
    "confidence",
    "notes",
]

BAGAN_BIBLIOGRAPHY_FIELDS = [
    "ref_id",
    "raw_reference",
    "author",
    "year",
    "title",
    "publication",
    "pages",
    "publisher",
    "place",
    "confidence",
    "notes",
]

KNOWN_JOURNALS = {
    "jbrs": "Journal of the Burma Research Society",
    "jras": "Journal of the Royal Asiatic Society",
    "bbhc": "Burma Historical Commission Bulletin",
    "rdasb": "Report of the Director, Archaeological Survey of Burma",
    "eb": "Epigraphia Birmanica",
    "arasi": "Annual Report of the Archaeological Survey of India",
}

KNOWN_PUBLICATIONS = {
    "list": "List of Inscriptions Found in Burma",
    "obi": "Old Burmese Inscriptions",
    "ippa": "IPPA source family",
    "uem": "UEM catalogue family",
    "ppa": "PPA catalogue family",
    "tn": "Than Tun catalogue family",
    "sip": "SIP catalogue family",
    "mm": "MM catalogue family",
    "or": "OR catalogue family",
    "mp": "MP source family",
    "ub": "UB source family",
    "bed": "Bagan Epigraphic Database",
    "bed b": "Bagan Epigraphic Database, Part B",
    "iob": "Inscriptions of Burma",
    "pl": "Plate reference family",
    "u min hswe": "U Min Hswe source family",
    "luce d": "Luce D source family",
    "luce j": "Luce J source family",
}

REFERENCE_LABEL = re.compile(r"^References?:\s*(.+)$", flags=re.IGNORECASE)
BIBLIOGRAPHY_HEADING = re.compile(r"^Bibliography\b", flags=re.IGNORECASE)
PART_HEADING = re.compile(r"^PART\s+([A-Z])\s*:\s*(.+)$")
STOP_MARKER = re.compile(
    r"\b(?:Number(?:\s+Name)?|Description|Text|Translation|Location|Contents|Date|Donor|Remarks?)\s*:",
    flags=re.IGNORECASE,
)
BODY_SIGNAL = re.compile(
    r"\b(?:illegible|fragmentary|inscription|description|translation|transcription|lines?|donor|contents|location)\b",
    flags=re.IGNORECASE,
)
CATALOGUE_PREFIX = re.compile(
    r"^(?:Pl\.?|List|OBI|IOB|BED(?:\s+[AB])?|A|B|UB|MP|PPA|TN|IPPA|UEM|SIP|MM|OR|ARASI|Luce D|Luce J)\b",
    flags=re.IGNORECASE,
)
NAME_TOKEN = r"[A-Z][A-Za-z'.-]*[a-z][A-Za-z'.-]*"
AUTHOR_PREFIX = re.compile(rf"^(?:U\s+)?{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,4}},")
YEAR_PATTERN = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
PAGE_PATTERN = re.compile(r"\bp+\.\s*([0-9-]+)", flags=re.IGNORECASE)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = REPO_ROOT / value
    return candidate if candidate.exists() else path


def load_frasch_files(manifest_path: Path) -> list[tuple[str, Path]]:
    rows = read_tsv(manifest_path)
    files: list[tuple[str, Path]] = []
    seen_paths: set[str] = set()
    for row in rows:
        combined_paths = " ".join(
            [
                row.get("primary_original_path", ""),
                row.get("all_original_paths", ""),
                row.get("file_name", ""),
            ]
        ).casefold()
        if not any(term in combined_paths for term in ("frasch", "tilman", "frosch", "bagan epig")):
            continue
        copied_path = resolve_repo_path(row.get("copied_path", ""))
        if not copied_path.exists():
            continue
        if str(copied_path) in seen_paths:
            continue
        seen_paths.add(str(copied_path))
        files.append((row.get("canonical_local_file_id", row.get("source_file_id", copied_path.stem)), copied_path))
    return files


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def trim_at_stop_markers(value: str) -> str:
    match = STOP_MARKER.search(value)
    if match:
        value = value[: match.start()]
    return re.sub(r"\s+", " ", value).strip(" ;,")


def extract_reference_candidates(text: str, source_file: str) -> list[dict]:
    lines = [clean_line(line) for line in text.splitlines()]
    candidates: list[dict] = []
    index = 0
    in_bibliography = False
    while index < len(lines):
        line = lines[index]
        if not line:
            if in_bibliography:
                index += 1
                continue
            index += 1
            continue
        if BIBLIOGRAPHY_HEADING.match(line):
            in_bibliography = True
            index += 1
            continue
        if in_bibliography and STOP_MARKER.match(line):
            in_bibliography = False
        reference_match = REFERENCE_LABEL.match(line)
        if reference_match:
            current = reference_match.group(1)
            start_index = index + 1
            index += 1
            continuation_count = 0
            while index < len(lines):
                next_line = lines[index]
                if not next_line or REFERENCE_LABEL.match(next_line) or BIBLIOGRAPHY_HEADING.match(next_line):
                    break
                if STOP_MARKER.match(next_line) or PART_HEADING.match(next_line):
                    break
                current = f"{current} {next_line}"
                continuation_count += 1
                if continuation_count >= 4 and len(current) > 400:
                    break
                index += 1
            current = trim_at_stop_markers(current)
            if current:
                candidates.append(
                    {
                        "raw_reference": current,
                        "source_location_hint": f"References line {start_index}",
                        "extraction_source_file": source_file,
                    }
                )
            continue
        if in_bibliography:
            bibliography_line = trim_at_stop_markers(line)
            if bibliography_line:
                candidates.append(
                    {
                        "raw_reference": bibliography_line,
                        "source_location_hint": f"Bibliography line {index + 1}",
                        "extraction_source_file": source_file,
                    }
                )
        index += 1
    return candidates


def split_reference_segments(reference_line: str) -> list[str]:
    normalized = reference_line.replace(" = ", "; ")
    pieces = [piece.strip(" ;,") for piece in re.split(r";|•", normalized) if piece.strip(" ;,")]
    return pieces or [reference_line.strip()]


def detect_signals(cleaned: str) -> dict[str, bool]:
    lower = cleaned.casefold()
    has_author_signal = (
        bool(AUTHOR_PREFIX.match(cleaned))
        or bool(re.match(rf"^(?:{NAME_TOKEN}(?:/{NAME_TOKEN})?(?:\s+{NAME_TOKEN}){{0,4}}|U\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,3}}),\s+", cleaned))
    )
    has_year_signal = bool(YEAR_PATTERN.search(cleaned))
    has_publication_signal = any(term in lower for term in list(KNOWN_JOURNALS) + ["journal", "bulletin", "report", "press", "rangoon", "yangon", "mandalay", "proceedings", "epigraphia"])
    has_title_signal = "," in cleaned or "“" in cleaned or '"' in cleaned or any(token in lower for token in ["inscription", "history", "buddhism", "version", "report"])
    looks_like_catalogue_note = bool(CATALOGUE_PREFIX.match(cleaned)) and not bool(STOP_MARKER.search(cleaned))
    looks_like_body_text = bool(STOP_MARKER.search(cleaned)) or len(cleaned) > 500 or (len(cleaned) > 250 and len(BODY_SIGNAL.findall(cleaned)) >= 2)
    return {
        "has_author_signal": has_author_signal,
        "has_year_signal": has_year_signal,
        "has_title_signal": has_title_signal,
        "has_publication_signal": has_publication_signal,
        "looks_like_catalogue_note": looks_like_catalogue_note,
        "looks_like_body_text": looks_like_body_text,
    }


def classify_reference(cleaned: str) -> tuple[str, str, dict[str, bool], list[str]]:
    signals = detect_signals(cleaned)
    notes: list[str] = []
    length = len(cleaned)
    if length > 500:
        notes.append("Suspiciously long extracted reference; likely mixed body text or catalogue content.")
    if signals["looks_like_body_text"] and STOP_MARKER.search(cleaned):
        entry_type = "inscription_record"
        confidence = "low"
        recommended_action = "exclude_from_bibtex"
    elif signals["looks_like_body_text"]:
        entry_type = "body_text"
        confidence = "low"
        recommended_action = "exclude_from_bibtex"
    elif signals["has_author_signal"] and (signals["has_year_signal"] or signals["has_publication_signal"]) and (signals["has_title_signal"] or signals["has_publication_signal"]):
        entry_type = "bibliographic_reference"
        confidence = "high" if signals["has_author_signal"] and signals["has_year_signal"] and signals["has_title_signal"] else "medium"
        recommended_action = "use_for_bibliography"
    elif signals["has_author_signal"] and signals["has_title_signal"]:
        entry_type = "bibliographic_reference"
        confidence = "medium"
        recommended_action = "manual_review"
    elif signals["looks_like_catalogue_note"]:
        entry_type = "catalogue_note"
        confidence = "medium" if PAGE_PATTERN.search(cleaned) or YEAR_PATTERN.search(cleaned) else "low"
        recommended_action = "use_for_catalogue_evidence"
    else:
        entry_type = "unclear"
        confidence = "low"
        recommended_action = "manual_review"
    if length > 500 and recommended_action == "use_for_bibliography":
        confidence = "low"
        recommended_action = "manual_review"
    return entry_type, confidence, signals, notes


def parse_reference_segment(raw_reference: str, source_file: str, source_location_hint: str) -> dict:
    cleaned = re.sub(r"\s+", " ", raw_reference).strip()
    detected_entry_type, confidence, signals, notes = classify_reference(cleaned)
    lower = cleaned.casefold()
    author = ""
    year = ""
    title = ""
    publication = ""
    journal = ""
    volume = ""
    number = ""
    pages = ""
    publisher = ""
    place = ""

    year_match = YEAR_PATTERN.search(cleaned)
    if year_match:
        year = year_match.group(1)
    page_match = PAGE_PATTERN.search(cleaned)
    if page_match:
        pages = page_match.group(1)

    if detected_entry_type == "bibliographic_reference":
        author_match = re.match(r"^(?P<author>[^,]{2,80}),\s*(?P<remainder>.+)$", cleaned)
        remainder = cleaned
        if author_match and not CATALOGUE_PREFIX.match(author_match.group("author")):
            author = author_match.group("author").strip()
            remainder = author_match.group("remainder").strip()
        for short, expanded in KNOWN_JOURNALS.items():
            if short in lower:
                journal = expanded
                publication = expanded
                volume_match = re.search(rf"{short.upper()}\s*([0-9]+(?:\s*\([0-9]+\))?)", cleaned, flags=re.IGNORECASE)
                if volume_match:
                    volume = volume_match.group(1)
                break
        stripped_remainder = re.sub(r"\b(JBRS|JRAS|BBHC|RDASB|EB|ARASI)\b.*$", "", remainder, flags=re.IGNORECASE).strip(" ,")
        stripped_remainder = re.sub(r",\s*[A-Z][A-Za-z .'-]+\s+(1[0-9]{3}|20[0-9]{2})$", "", stripped_remainder).strip(" ,")
        title = stripped_remainder or remainder
        if publication and not title:
            title = publication
    elif detected_entry_type == "catalogue_note":
        for short, expanded in sorted(KNOWN_PUBLICATIONS.items(), key=lambda item: len(item[0]), reverse=True):
            if re.match(rf"^{re.escape(short)}\b", cleaned, flags=re.IGNORECASE):
                publication = expanded
                title = expanded
                break

    if publication and not title:
        title = publication

    return {
        "raw_reference": cleaned,
        "author": author,
        "editor": "",
        "year": year,
        "title": title,
        "publication": publication,
        "journal": journal,
        "volume": volume,
        "number": number,
        "pages": pages,
        "publisher": publisher,
        "place": place,
        "language": "latin",
        "script": "Latn",
        "confidence": confidence,
        "detected_entry_type": detected_entry_type,
        "looks_like_bibliographic_reference": bool_text(detected_entry_type == "bibliographic_reference"),
        "looks_like_catalogue_note": bool_text(detected_entry_type == "catalogue_note"),
        "looks_like_body_text": bool_text(detected_entry_type in {"body_text", "inscription_record"}),
        "has_author_signal": bool_text(signals["has_author_signal"]),
        "has_year_signal": bool_text(signals["has_year_signal"]),
        "has_title_signal": bool_text(signals["has_title_signal"]),
        "has_publication_signal": bool_text(signals["has_publication_signal"]),
        "length": str(len(cleaned)),
        "recommended_action": "exclude_from_bibtex" if len(cleaned) > 500 and detected_entry_type != "bibliographic_reference" else ("manual_review" if len(cleaned) > 500 else ("use_for_bibliography" if detected_entry_type == "bibliographic_reference" else ("use_for_catalogue_evidence" if detected_entry_type == "catalogue_note" else ("exclude_from_bibtex" if detected_entry_type in {"body_text", "inscription_record"} else "manual_review")))),
        "source_location_hint": source_location_hint,
        "extraction_source_file": source_file,
        "notes": " ".join(notes).strip(),
    }


def reference_to_bibtex_row(row: dict, existing_keys: set[str]) -> dict | None:
    if row["detected_entry_type"] != "bibliographic_reference":
        return None
    if row["recommended_action"] != "use_for_bibliography":
        return None
    if row["confidence"] != "high":
        return None
    if not row["author"] or not row["title"]:
        return None
    key = make_bibtex_key(
        author=row["author"],
        year=row["year"],
        title=row["title"],
        existing_keys=existing_keys,
    )
    existing_keys.add(key)
    entry_type = "article" if row["journal"] else "misc"
    fields = {
        "author": row["author"],
        "title": row["title"],
        "journal": row["journal"],
        "year": row["year"],
        "pages": row["pages"],
        "note": "Extracted from local Frasch bibliography evidence; review before final authority use.",
    }
    return {
        "entry_type": entry_type,
        "bibtex_key": key,
        "fields": {name: value for name, value in fields.items() if value},
    }


def quality_row(row: dict) -> dict:
    return {
        "frasch_ref_id": row["frasch_ref_id"],
        "raw_reference": row["raw_reference"],
        "source_file": row["extraction_source_file"],
        "detected_entry_type": row["detected_entry_type"],
        "looks_like_bibliographic_reference": row["looks_like_bibliographic_reference"],
        "looks_like_catalogue_note": row["looks_like_catalogue_note"],
        "looks_like_body_text": row["looks_like_body_text"],
        "length": row["length"],
        "has_author_signal": row["has_author_signal"],
        "has_year_signal": row["has_year_signal"],
        "has_title_signal": row["has_title_signal"],
        "has_publication_signal": row["has_publication_signal"],
        "confidence": row["confidence"],
        "recommended_action": row["recommended_action"],
        "notes": row["notes"],
    }


def find_bagan_file(chunks: list[tuple[str, Path, str, str]]) -> tuple[str, str] | None:
    for source_file_id, path, _, text in chunks:
        if path.name == "Bagan Epig Database.doc":
            return source_file_id, text
    return None


def extract_bagan_outputs(source_file_id: str, text: str, rows: list[dict], output_dir: Path) -> dict:
    abbreviation_rows: list[dict] = []
    bibliography_rows: list[dict] = []

    def add_abbreviation(
        abbreviation: str,
        expansion: str,
        raw_definition: str,
        source_location_hint: str,
        evidence_type: str,
        confidence: str,
        notes: str = "",
    ) -> None:
        abbreviation_rows.append(
            {
                "abbreviation": abbreviation,
                "expansion": expansion,
                "raw_definition": raw_definition,
                "source_location_hint": source_location_hint,
                "evidence_type": evidence_type,
                "confidence": confidence,
                "notes": notes,
            }
        )

    if "Bagan Epig Database" in text:
        add_abbreviation(
            "BED",
            "Bagan Epigraphic Database",
            "Bagan Epig Database.doc",
            "Document title",
            "explicit_definition",
            "high",
            "Document title from the local Frasch source.",
        )

    for match in PART_HEADING.finditer(text):
        letter = match.group(1).strip()
        part_title = match.group(2).strip()
        expansion = f"Bagan Epigraphic Database, Part {letter}: {part_title}"
        add_abbreviation(
            letter,
            expansion,
            match.group(0),
            "Part heading",
            "explicit_definition",
            "high" if letter in {"A", "B"} else "medium",
        )
        if letter == "B":
            add_abbreviation(
                "BED B",
                "Bagan Epigraphic Database, Part B",
                match.group(0),
                "Part heading",
                "explicit_definition",
                "high",
            )

    bagan_rows = [row for row in rows if row["extraction_source_file"] == "Bagan Epig Database.doc"]
    for row in bagan_rows:
        if row["detected_entry_type"] == "bibliographic_reference":
            bibliography_rows.append(
                {
                    "ref_id": row["frasch_ref_id"],
                    "raw_reference": row["raw_reference"],
                    "author": row["author"],
                    "year": row["year"],
                    "title": row["title"],
                    "publication": row["publication"] or row["journal"],
                    "pages": row["pages"],
                    "publisher": row["publisher"],
                    "place": row["place"],
                    "confidence": row["confidence"],
                    "notes": row["notes"],
                }
            )

    title_backed = {
        "List": "List of Inscriptions Found in Burma",
        "IOB": "Inscriptions of Burma",
        "JBRS": "Journal of the Burma Research Society",
        "JRAS": "Journal of the Royal Asiatic Society",
        "BBHC": "Burma Historical Commission Bulletin",
        "RDASB": "Report of the Director, Archaeological Survey of Burma",
        "EB": "Epigraphia Birmanica",
        "ARASI": "Annual Report of the Archaeological Survey of India",
    }
    known_text = " ".join(row["raw_reference"] for row in bagan_rows).casefold()
    for abbreviation, expansion in title_backed.items():
        if expansion.casefold() in known_text or abbreviation.casefold() in known_text:
            add_abbreviation(
                abbreviation,
                expansion,
                expansion,
                "Bagan bibliography/references",
                "contextual_usage",
                "medium",
            )

    contextual_targets = {
        "A": "Bagan Epigraphic Database, Part A",
        "B": "Bagan Epigraphic Database, Part B",
        "BED B": "Bagan Epigraphic Database, Part B",
        "MP": KNOWN_PUBLICATIONS["mp"],
        "UB": KNOWN_PUBLICATIONS["ub"],
        "PPA": KNOWN_PUBLICATIONS["ppa"],
        "IPPA": KNOWN_PUBLICATIONS["ippa"],
        "UEM": KNOWN_PUBLICATIONS["uem"],
        "SIP": KNOWN_PUBLICATIONS["sip"],
        "TN": KNOWN_PUBLICATIONS["tn"],
        "U Min Hswe": KNOWN_PUBLICATIONS["u min hswe"],
        "Luce D": KNOWN_PUBLICATIONS["luce d"],
        "Luce J": KNOWN_PUBLICATIONS["luce j"],
        "Pl.": KNOWN_PUBLICATIONS["pl"],
        "IOB": KNOWN_PUBLICATIONS["iob"],
        "List": KNOWN_PUBLICATIONS["list"],
        "MM": KNOWN_PUBLICATIONS["mm"],
        "OR": KNOWN_PUBLICATIONS["or"],
        "ARASI": KNOWN_JOURNALS["arasi"],
        "JBRS": KNOWN_JOURNALS["jbrs"],
        "JRAS": KNOWN_JOURNALS["jras"],
        "BBHC": KNOWN_JOURNALS["bbhc"],
        "RDASB": KNOWN_JOURNALS["rdasb"],
        "EB": KNOWN_JOURNALS["eb"],
    }
    for abbreviation, expansion in contextual_targets.items():
        pattern = re.compile(rf"(^|[\\s,(;]){re.escape(abbreviation)}(?=[\\s,.;:]|$)", flags=re.IGNORECASE)
        match_row = next((row for row in bagan_rows if pattern.search(row["raw_reference"])), None)
        if match_row is None:
            continue
        confidence = "high" if abbreviation in {"List", "IOB", "JBRS", "JRAS", "RDASB"} else "medium"
        note = ""
        if abbreviation in {"MP", "UB", "PPA", "IPPA", "UEM", "SIP", "TN", "U Min Hswe", "Luce D", "Luce J", "MM", "OR"}:
            note = "Contextual usage only; expansion remains provisional."
        add_abbreviation(
            abbreviation,
            expansion,
            match_row["raw_reference"],
            match_row["source_location_hint"],
            "contextual_usage",
            confidence,
            note,
        )

    deduped_abbreviations: dict[str, dict] = {}
    for row in abbreviation_rows:
        existing = deduped_abbreviations.get(row["abbreviation"])
        if existing is None:
            deduped_abbreviations[row["abbreviation"]] = row
            continue
        if row["evidence_type"] == "explicit_definition" and existing["evidence_type"] != "explicit_definition":
            deduped_abbreviations[row["abbreviation"]] = row
            continue
        if row["confidence"] == "high" and existing["confidence"] != "high":
            deduped_abbreviations[row["abbreviation"]] = row

    abbreviation_path = output_dir / "frasch_bagan_epig_database_abbreviations.tsv"
    bibliography_path = output_dir / "frasch_bagan_epig_database_bibliography.tsv"
    report_path = output_dir / "frasch_bagan_epig_database_report.json"
    write_tsv(abbreviation_path, sorted(deduped_abbreviations.values(), key=lambda row: row["abbreviation"]), BAGAN_ABBREVIATION_FIELDS)
    write_tsv(bibliography_path, bibliography_rows, BAGAN_BIBLIOGRAPHY_FIELDS)
    report = {
        "source_file_id": source_file_id,
        "abbreviation_count": len(deduped_abbreviations),
        "bibliography_reference_count": len(bibliography_rows),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def run_extraction(manifest_path: Path, output_dir: Path, input_file: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / "frasch_extracted_text.txt"
    tsv_path = output_dir / "frasch_reference_entries.tsv"
    quality_path = output_dir / "frasch_reference_quality.tsv"
    bib_path = output_dir / "frasch_bibliography.bib"
    report_path = output_dir / "frasch_extraction_report.json"
    qa_report_path = output_dir / "frasch_extraction_qa_report.json"

    source_files = [("direct-input", input_file)] if input_file else load_frasch_files(manifest_path)
    extracted_chunks: list[str] = []
    rows: list[dict] = []
    warnings: list[str] = []
    extracted_file_rows: list[tuple[str, Path, str, str]] = []

    for source_file_id, path in source_files:
        if path is None:
            continue
        text, method, file_warnings = extract_text_from_path(path)
        warnings.extend(file_warnings)
        if not text.strip():
            continue
        extracted_file_rows.append((source_file_id, path, method, text))
        extracted_chunks.append(f"=== {source_file_id} | {path.name} | {method} ===\n{text}\n")
        for candidate in extract_reference_candidates(text, path.name):
            for segment in split_reference_segments(candidate["raw_reference"]):
                parsed = parse_reference_segment(segment, candidate["extraction_source_file"], candidate["source_location_hint"])
                rows.append(parsed)

    deduped_rows: list[dict] = []
    seen_signature: set[tuple[str, str, str]] = set()
    for row in rows:
        signature = (row["extraction_source_file"], row["source_location_hint"], row["raw_reference"])
        if signature in seen_signature:
            continue
        seen_signature.add(signature)
        deduped_rows.append(row)

    rows = deduped_rows
    for index, row in enumerate(rows, start=1):
        row["frasch_ref_id"] = f"frasch-ref-{index:05d}"

    text_path.write_text("\n".join(extracted_chunks), encoding="utf-8")
    write_tsv(tsv_path, rows, FRASCH_FIELDS)
    write_tsv(quality_path, [quality_row(row) for row in rows], QUALITY_FIELDS)

    existing_keys: set[str] = set()
    bib_entries = [entry for row in rows if (entry := reference_to_bibtex_row(row, existing_keys))]
    write_bibtex(bib_path, bib_entries)

    bagan_result = {}
    bagan_file = find_bagan_file(extracted_file_rows)
    if bagan_file is not None:
        bagan_result = extract_bagan_outputs(bagan_file[0], bagan_file[1], rows, output_dir)

    counts_by_type = Counter(row["detected_entry_type"] for row in rows)
    long_rows = [row for row in rows if int(row["length"]) > 500]
    usable_rows = [row for row in rows if row["recommended_action"] == "use_for_bibliography"]
    report = {
        "source_file_count": len(extracted_file_rows),
        "reference_entry_count": len(rows),
        "usable_reference_count": len(usable_rows),
        "excluded_body_text_count": counts_by_type.get("body_text", 0) + counts_by_type.get("inscription_record", 0),
        "bibtex_entry_count": len(bib_entries),
        "parse_warnings": warnings,
        "counts_by_type": dict(counts_by_type),
    }
    qa_report = {
        "reference_entry_count": len(rows),
        "usable_reference_count": len(usable_rows),
        "body_text_count": counts_by_type.get("body_text", 0),
        "inscription_record_count": counts_by_type.get("inscription_record", 0),
        "catalogue_note_count": counts_by_type.get("catalogue_note", 0),
        "unclear_count": counts_by_type.get("unclear", 0),
        "long_reference_count": len(long_rows),
        "long_reference_ids": [row["frasch_ref_id"] for row in long_rows[:50]],
        "bagan_epig_database": bagan_result,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    qa_report_path.write_text(json.dumps(qa_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract reference lines and bibliographic hints from local Frasch sources.")
    parser.add_argument("--manifest", type=Path, default=Path("data/working/bibliography/local_sources/local_file_manifest.tsv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/working/bibliography/local_sources"))
    parser.add_argument("--input-file", type=Path)
    args = parser.parse_args()
    result = run_extraction(args.manifest, args.output_dir, args.input_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
