from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from bibtex_common import make_bibtex_key, write_bibtex
from corpus_common import read_tsv, write_tsv
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
    "extraction_source_file",
    "notes",
]

KNOWN_JOURNALS = {
    "jbrs": "Journal of the Burma Research Society",
    "jras": "Journal of the Royal Asiatic Society",
    "bbhc": "Burma Historical Commission bulletin",
    "rdasb": "Report of the Director, Archaeological Survey of Burma",
    "eb": "Epigraphia Birmanica",
}

KNOWN_PUBLICATIONS = {
    "list": "List of Inscriptions",
    "obi": "Old Burmese Inscriptions",
    "uem": "UEM catalogue",
    "ppa": "PPA catalogue",
    "tn": "Than Tun catalogue",
    "sip": "SIP catalogue",
    "mm": "MM catalogue",
    "or": "OR catalogue",
    "mp": "MP source family",
    "ub": "UB source family",
    "bed": "Bagan Epigraphic Database",
    "iob": "Inscriptions of Burma",
}

ABBREVIATION_LIKE = re.compile(r"^(?:[A-Z]{1,5}(?:\s+[0-9A-Za-z().-]+)*)$")


def load_frasch_files(manifest_path: Path) -> list[tuple[str, Path]]:
    rows = read_tsv(manifest_path)
    files: list[tuple[str, Path]] = []
    for row in rows:
        original = row["original_path"].casefold()
        if "frasch" in original or "tilman" in original or "frosch" in original or "bagan epig" in original:
            copied_path = Path(row["copied_path"])
            if copied_path.exists():
                files.append((row["source_file_id"], copied_path))
    return files


def collect_reference_lines(text: str) -> list[str]:
    raw_lines = text.splitlines()
    collected: list[str] = []
    index = 0
    while index < len(raw_lines):
        line = raw_lines[index].strip()
        if not line.startswith("References:"):
            index += 1
            continue
        current = line.removeprefix("References:").strip()
        index += 1
        while index < len(raw_lines):
            next_line = raw_lines[index].strip()
            if not next_line or re.match(r"^(Number|Date|Donor|Contents|Location|Remarks):", next_line):
                break
            current += " " + next_line
            index += 1
        collected.append(re.sub(r"\s+", " ", current).strip())
    return collected


def split_reference_segments(reference_line: str) -> list[str]:
    normalized = reference_line.replace(" = ", "; ").replace(" and ", "; ")
    pieces = [piece.strip(" ;,") for piece in re.split(r";", normalized) if piece.strip(" ;,")]
    return pieces


def parse_reference_segment(raw_reference: str, source_file: str) -> dict:
    cleaned = re.sub(r"\s+", " ", raw_reference).strip()
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
    confidence = "low"

    year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", cleaned)
    if year_match:
        year = year_match.group(1)
    page_match = re.search(r"\bp+\.\s*([0-9-]+)", cleaned, flags=re.IGNORECASE)
    if page_match:
        pages = page_match.group(1)
    if "," in cleaned:
        first, remainder = cleaned.split(",", 1)
        if (
            re.search(r"[A-Za-z]", first)
            and first.casefold() not in KNOWN_PUBLICATIONS
            and not ABBREVIATION_LIKE.match(first.strip())
        ):
            author = first.strip()
            title_candidate = remainder.strip()
            title_candidate = re.sub(r"\b(JBRS|JRAS|BBHC|RDASB|EB)\b.*$", "", title_candidate).strip(" ,")
            title = title_candidate
            confidence = "medium" if title else "low"
    for short, expanded in KNOWN_JOURNALS.items():
        if short in lower:
            journal = expanded
            if not publication:
                publication = expanded
            confidence = "medium"
            volume_match = re.search(rf"{short.upper()}\s*([0-9]+(?:\s*\([0-9]+\))?)", cleaned, flags=re.IGNORECASE)
            if volume_match:
                volume = volume_match.group(1)
    for short, expanded in KNOWN_PUBLICATIONS.items():
        if re.match(rf"^{short.upper()}\b", cleaned, flags=re.IGNORECASE) or f" {short} " in f" {lower} ":
            publication = expanded
            confidence = "medium" if short in {"list", "obi", "iob", "bed", "mp", "ub"} else confidence
            break
    if author and title and year:
        confidence = "high"
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
        "extraction_source_file": source_file,
        "notes": "",
    }


def reference_to_bibtex_row(row: dict, existing_keys: set[str]) -> dict | None:
    if row["confidence"] != "high":
        return None
    if not row["author"]:
        return None
    key = make_bibtex_key(
        author=row["author"] or row["publication"],
        year=row["year"],
        title=row["title"] or row["publication"],
        existing_keys=existing_keys,
    )
    existing_keys.add(key)
    entry_type = "article" if row["journal"] else "misc"
    fields = {
        "author": row["author"],
        "title": row["title"] or row["publication"],
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


def run_extraction(manifest_path: Path, output_dir: Path, input_file: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / "frasch_extracted_text.txt"
    tsv_path = output_dir / "frasch_reference_entries.tsv"
    bib_path = output_dir / "frasch_bibliography.bib"
    report_path = output_dir / "frasch_extraction_report.json"

    source_files = [("direct-input", input_file)] if input_file else load_frasch_files(manifest_path)
    extracted_chunks: list[str] = []
    rows: list[dict] = []
    warnings: list[str] = []

    for source_file_id, path in source_files:
        if path is None:
            continue
        text, method, file_warnings = extract_text_from_path(path)
        warnings.extend(file_warnings)
        if not text.strip():
            continue
        extracted_chunks.append(f"=== {source_file_id} | {path.name} | {method} ===\n{text}\n")
        for reference_line in collect_reference_lines(text):
            for segment in split_reference_segments(reference_line):
                rows.append(parse_reference_segment(segment, path.name))

    for index, row in enumerate(rows, start=1):
        row["frasch_ref_id"] = f"frasch-ref-{index:05d}"

    write_tsv(text_path.with_suffix(".tsv"), [], []) if False else None
    text_path.write_text("\n".join(extracted_chunks), encoding="utf-8")
    write_tsv(tsv_path, rows, FRASCH_FIELDS)

    existing_keys: set[str] = set()
    bib_entries = [entry for row in rows if (entry := reference_to_bibtex_row(row, existing_keys))]
    write_bibtex(bib_path, bib_entries)

    report = {
        "source_file_count": len(source_files),
        "reference_entry_count": len(rows),
        "bibtex_entry_count": len(bib_entries),
        "parse_warnings": warnings,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
