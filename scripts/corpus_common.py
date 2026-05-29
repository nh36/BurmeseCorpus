from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()

MYANMAR_TO_ARABIC = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
ARABIC_TO_MYANMAR = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")

STRUCTURED_HEADERS = [
    "OBI CORPUS REF",
    "OBI REF",
    "INFORMATION SOURCE",
    "VOLUME",
    "PART",
    "INSCRIPTION NUMBER",
    "PAGE NUMBER",
    "NUMBER OF FACES",
    "FACE",
    "LANGUAGE",
    "INSCRIPTION SOURCE",
    "PLACE OF ORIGIN",
    "CURRENT LOCATION",
    "REFERENCE NUMBER",
    "REFERENCES",
    "TITLE",
    "DATE",
    "DONOR",
    "SUBJECT",
    "LENGTH",
    "NOTES",
    "FOOTNOTES",
    "INSCRIPTION",
    "FULL TRANSLITERATION",
]

HEADER_PATTERN = re.compile(
    r"^(?P<key>"
    + "|".join(re.escape(header) for header in sorted(STRUCTURED_HEADERS, key=len, reverse=True))
    + r"):\s*(?P<value>.*)$"
)

STRUCTURED_LINE_PATTERN = re.compile(r"^(?P<number>[0-9၀-၉]+)\s*[။.]?\s+(?P<text>.+)$")
TRANSLIT_LINE_PATTERN = re.compile(r"^¤\s*(?P<number>[0-9၀-၉]+)\s+(?P<text>.+)$")
PAGE_BREAK_PATTERN = re.compile(r"<pg>(.*?)</pg>")
FOOTNOTE_PATTERN = re.compile(r"<ftn>(.*?)</ftn>")
MYANMAR_NUMBER_PATTERN = re.compile(r"[0-9၀-၉]+")


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def myanmar_digits_to_ascii(value: str) -> str:
    return value.translate(MYANMAR_TO_ARABIC)


def ascii_digits_to_myanmar(value: str) -> str:
    return value.translate(ARABIC_TO_MYANMAR)


def first_int(value: str | None) -> int | None:
    if not value:
        return None
    match = MYANMAR_NUMBER_PATTERN.search(value)
    if not match:
        return None
    return int(myanmar_digits_to_ascii(match.group(0)))


def split_title_fields(title_value: str) -> tuple[str, str | None]:
    if "¤" not in title_value:
        return normalize_whitespace(title_value), None
    original, transliteration = title_value.split("¤", 1)
    return normalize_whitespace(original), normalize_whitespace(transliteration) or None


def normalize_match_text(value: str | None) -> str:
    if not value:
        return ""
    original, _ = split_title_fields(value)
    normalized = unicodedata.normalize("NFKC", original).casefold()
    return re.sub(r"[^0-9a-z\u1000-\u109f]+", "", normalized)


def parse_reference_number(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = normalize_whitespace(value)
    return stripped or None


def parse_number_token(value: str | None, prefix: str) -> str:
    if not value:
        return f"{prefix}unknown"
    stripped = normalize_whitespace(value).lower()
    match = re.fullmatch(r"([0-9]+)([a-z]+)?", myanmar_digits_to_ascii(stripped))
    if match:
        digits = int(match.group(1))
        suffix = match.group(2) or ""
        return f"{prefix}{digits:04d}{suffix}"
    safe = re.sub(r"[^0-9a-z]+", "-", myanmar_digits_to_ascii(stripped)).strip("-")
    return f"{prefix}{safe or 'unknown'}"


def format_page_token(value: str | None) -> str:
    page_number = first_int(value)
    if page_number is None:
        return "punknown"
    return f"p{page_number:04d}"


def normalize_face(value: str | None) -> tuple[str | None, str]:
    if not value:
        return None, "tx"
    lowered = normalize_whitespace(value).casefold()
    if "obverse" in lowered or "မျက်နှာဘက်" in value:
        return "obverse", "ob"
    if "reverse" in lowered or "ကျောဘက်" in value:
        return "reverse", "re"
    if "တစ်မျက်နှာ" in value or "single" in lowered:
        return "single_face", "sf"
    return normalize_whitespace(value), "tx"


def build_obi_record_id(volume: str | None, inscription_number: str | None, face: str | None, page: str | None) -> str:
    volume_number = first_int(volume) or 0
    _, face_code = normalize_face(face)
    return f"obi-v{volume_number:02d}-{parse_number_token(inscription_number, 'n')}-{face_code}-{format_page_token(page)}"


def build_sagaing_record_id(block_index: int, face: str | None, page: str | None) -> str:
    _, face_code = normalize_face(face)
    return f"sagaing-z1203709-b{block_index:04d}-{face_code}-{format_page_token(page)}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_tsv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def parse_date_normalized(date_original: str | None) -> dict | None:
    if not date_original:
        return None
    cleaned = normalize_whitespace(date_original)
    cs_ce = re.search(r"CS\s*([0-9]+)\s*=\s*CE\s*([0-9]+)", cleaned)
    if cs_ce:
        return {
            "calendar": "CS/CE",
            "cs_year": int(cs_ce.group(1)),
            "ce_year": int(cs_ce.group(2)),
            "confidence": "high",
        }
    year_only = re.search(r"([0-9၀-၉]{3,4})\s*-\s*ခု", cleaned)
    if year_only:
        return {
            "calendar": "CS",
            "cs_year": int(myanmar_digits_to_ascii(year_only.group(1))),
            "ce_year": None,
            "confidence": "medium",
        }
    return None


@dataclass
class ParsedStructuredCorpus:
    inscription: dict
    lines: list[dict]


def parse_structured_corpus_text(
    text: str,
    *,
    source_file: str,
    created_by_script: str,
    source_deposit: str = "zenodo_4321314",
) -> ParsedStructuredCorpus:
    metadata: dict[str, str] = {}
    inscription_lines: list[str] = []
    full_transliteration_lines: list[str] = []
    mode = "metadata"

    for raw_line in text.splitlines():
        header_match = HEADER_PATTERN.match(raw_line.strip())
        if header_match:
            key = header_match.group("key")
            value = header_match.group("value")
            if key == "INSCRIPTION":
                mode = "inscription"
                if value:
                    inscription_lines.append(value)
            elif key == "FULL TRANSLITERATION":
                mode = "full_transliteration"
                if value:
                    full_transliteration_lines.append(value)
            else:
                mode = "metadata"
                metadata[key] = value
            continue

        if mode == "inscription":
            inscription_lines.append(raw_line)
        elif mode == "full_transliteration":
            full_transliteration_lines.append(raw_line)

    title_original, title_transliteration = split_title_fields(metadata.get("TITLE", ""))
    date_original = normalize_whitespace(metadata.get("DATE", "")) or None
    face_original = normalize_whitespace(metadata.get("FACE", "")) or None
    face_normalized, _ = normalize_face(face_original)
    record_id = build_obi_record_id(
        metadata.get("VOLUME"),
        metadata.get("INSCRIPTION NUMBER"),
        face_original,
        metadata.get("PAGE NUMBER"),
    )

    lines: list[dict] = []
    current_line: dict | None = None
    pending_page_break: str | None = None
    line_number_counts: dict[int, int] = {}

    for raw_line in inscription_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if "<pg>" in stripped:
            page_breaks = PAGE_BREAK_PATTERN.findall(stripped)
            if page_breaks:
                pending_page_break = myanmar_digits_to_ascii(page_breaks[-1])
            continue

        translit_match = TRANSLIT_LINE_PATTERN.match(stripped)
        if translit_match and current_line is not None:
            current_line["transliteration"] = normalize_whitespace(translit_match.group("text"))
            continue

        line_match = STRUCTURED_LINE_PATTERN.match(stripped)
        if line_match:
            number_original = line_match.group("number")
            line_number = int(myanmar_digits_to_ascii(number_original))
            line_text = normalize_whitespace(line_match.group("text"))
            line_number_counts[line_number] = line_number_counts.get(line_number, 0) + 1
            occurrence = line_number_counts[line_number]
            line_id = f"{record_id}-l{line_number:03d}"
            if occurrence > 1:
                line_id = f"{line_id}-{occurrence:02d}"
            current_line = {
                "record_id": record_id,
                "line_id": line_id,
                "line_number_original": number_original,
                "line_number_arabic": line_number,
                "text_original": line_text,
                "transliteration": None,
                "page_break_before": pending_page_break,
                "footnote_refs": FOOTNOTE_PATTERN.findall(line_text),
                "uncertain": ". ." in line_text or "[...]" in line_text,
            }
            pending_page_break = None
            lines.append(current_line)

    inscription = {
        "record_id": record_id,
        "source_deposit": source_deposit,
        "source_volume": normalize_whitespace(metadata.get("VOLUME", "")) or None,
        "source_part": normalize_whitespace(metadata.get("PART", "")) or None,
        "source_inscription_number": normalize_whitespace(metadata.get("INSCRIPTION NUMBER", "")) or None,
        "source_page": normalize_whitespace(metadata.get("PAGE NUMBER", "")) or None,
        "face": face_normalized,
        "number_of_faces": normalize_whitespace(metadata.get("NUMBER OF FACES", "")) or None,
        "title_original": title_original or None,
        "title_transliteration": title_transliteration,
        "date_original": date_original,
        "date_normalized": parse_date_normalized(date_original),
        "place_of_origin_original": normalize_whitespace(metadata.get("PLACE OF ORIGIN", "")) or None,
        "place_id": None,
        "current_location_original": normalize_whitespace(metadata.get("CURRENT LOCATION", "")) or None,
        "donor_original": normalize_whitespace(metadata.get("DONOR", "")) or None,
        "subject_original": normalize_whitespace(metadata.get("SUBJECT", "")) or None,
        "language_original": normalize_whitespace(metadata.get("LANGUAGE", "")) or None,
        "references_original": normalize_whitespace(metadata.get("REFERENCES", "")) or None,
        "notes_original": normalize_whitespace(metadata.get("NOTES", "")) or None,
        "full_transliteration": normalize_whitespace(" ".join(full_transliteration_lines)) or None,
        "source_file": source_file,
        "reference_number_original": parse_reference_number(metadata.get("REFERENCE NUMBER")),
        "information_source": normalize_whitespace(metadata.get("INFORMATION SOURCE", "")) or None,
        "inscription_source_original": normalize_whitespace(metadata.get("INSCRIPTION SOURCE", "")) or None,
        "footnotes_original": normalize_whitespace(metadata.get("FOOTNOTES", "")) or None,
        "provenance": {
            "created_from": "structured corpus txt",
            "created_by_script": created_by_script,
            "created_date": TODAY,
        },
    }

    return ParsedStructuredCorpus(inscription=inscription, lines=lines)
