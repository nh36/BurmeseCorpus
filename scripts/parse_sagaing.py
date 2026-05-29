from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from corpus_common import (
    REPO_ROOT,
    TODAY,
    build_sagaing_record_id,
    first_int,
    myanmar_digits_to_ascii,
    normalize_face,
    normalize_whitespace,
    write_jsonl,
)


BLOCK_MARKER_PATTERN = re.compile(r"^\++([၀-၉]+)\+\s*$")
METADATA_PATTERN = re.compile(r"^(?P<label>[^-\t]+?)\s*-\s*(?P<value>.*)$")
LINE_PATTERN = re.compile(r"^(?P<number>[၀-၉]+)\s*[။၊.]?\s*(?P<text>.+)$")
VARIANT_NUMBER_LABELS = {"ကျောက်စာတိုင်အမှတ်", "ကျောက်တိုင်အမှတ်", "ကျေက်တိုင်အမှတ်"}
FACE_LABELS = {"ကျောက်စာတိုင်မျက်နှာ", "ကျောက်စာမျက်နှာ"}


def split_blocks(text: str) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    current_page: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        marker_match = BLOCK_MARKER_PATTERN.match(raw_line.strip())
        if marker_match:
            if current_page is not None and current_lines:
                blocks.append((current_page, current_lines))
            current_page = marker_match.group(1)
            current_lines = []
            continue
        if current_page is not None:
            current_lines.append(raw_line)

    if current_page is not None and current_lines:
        blocks.append((current_page, current_lines))
    return blocks


def parse_metadata_line(line: str) -> tuple[str, str] | None:
    cleaned = line.replace("\t", " ")
    match = METADATA_PATTERN.match(cleaned)
    if not match:
        return None
    return normalize_whitespace(match.group("label")), normalize_whitespace(match.group("value"))


def parse_sagaing_block(page_marker: str, block_lines: list[str], block_index: int) -> tuple[dict, list[dict], str]:
    metadata: dict[str, str] = {}
    line_records: list[dict] = []
    continuous_lines: list[str] = []
    parse_warnings: list[str] = []
    in_line_section = False
    title_fallback: str | None = None

    for raw_line in block_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue

        metadata_match = parse_metadata_line(stripped)
        if metadata_match and not in_line_section:
            label, value = metadata_match
            metadata[label] = value
            continue

        line_match = LINE_PATTERN.match(stripped)
        if line_match:
            in_line_section = True
            line_number_original = line_match.group("number")
            line_number_arabic = int(myanmar_digits_to_ascii(line_number_original))
            line_records.append(
                {
                    "line_number_original": line_number_original,
                    "line_number_arabic": line_number_arabic,
                    "text_original": normalize_whitespace(line_match.group("text")),
                }
            )
            continue

        if stripped.startswith("မှတ်ချက်"):
            note_match = parse_metadata_line(stripped)
            if note_match:
                metadata[note_match[0]] = note_match[1]
            else:
                metadata["မှတ်ချက်"] = stripped.removeprefix("မှတ်ချက်").strip(" -")
            continue

        if in_line_section:
            continuous_lines.append(stripped)
        elif title_fallback is None:
            title_fallback = normalize_whitespace(stripped)

    title = metadata.get("ကျောက်စာအမည်") or title_fallback
    if not title:
        parse_warnings.append("missing_title")

    face_value = None
    for label in FACE_LABELS:
        if label in metadata:
            face_value = metadata[label]
            break
    face_normalized, _ = normalize_face(face_value)
    record_id = build_sagaing_record_id(block_index, face_value, page_marker)

    number_of_faces = None
    if face_value:
        face_count = first_int(face_value)
        if face_count is not None:
            number_of_faces = str(face_count)
        elif "တစ်မျက်နှာ" in face_value:
            number_of_faces = "1"

    stone_number = None
    for label in VARIANT_NUMBER_LABELS:
        if label in metadata:
            stone_number = metadata[label]
            break

    if not line_records:
        parse_warnings.append("missing_lines")

    record = {
        "record_id": record_id,
        "source_deposit": "zenodo_1203709",
        "source_volume": None,
        "source_part": None,
        "source_inscription_number": str(block_index),
        "source_page": myanmar_digits_to_ascii(page_marker),
        "face": face_normalized,
        "number_of_faces": number_of_faces,
        "title_original": title,
        "title_transliteration": None,
        "date_original": metadata.get("ကောဇာသက္ကရာဇ်") or None,
        "date_normalized": None,
        "place_of_origin_original": metadata.get("မူလတည်ရာဌာန") or None,
        "place_id": None,
        "current_location_original": metadata.get("ယခုတည်ရာဌာန") or None,
        "donor_original": metadata.get("လှူဒါန်းသူ") or None,
        "subject_original": metadata.get("အလှူပစ္စည်း") or None,
        "language_original": None,
        "references_original": None,
        "notes_original": metadata.get("မှတ်ချက်") or None,
        "full_transliteration": None,
        "source_file": "1203709/စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.txt",
        "reference_number_original": stone_number or None,
        "information_source": "စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ (Zenodo 1203709)",
        "inscription_source_original": metadata.get("မူလ/ဆင့်ထိုး/စပ်ထိုး") or None,
        "footnotes_original": None,
        "source_section_marker": myanmar_digits_to_ascii(page_marker),
        "continuous_text_original": normalize_whitespace(" ".join(continuous_lines)) or None,
        "parse_warnings": parse_warnings,
        "provenance": {
            "created_from": "Sagaing source txt",
            "created_by_script": "parse_sagaing.py",
            "created_date": TODAY,
        },
    }

    line_number_counts: dict[int, int] = {}
    lines: list[dict] = []
    for line_record in line_records:
        line_number = line_record["line_number_arabic"]
        line_number_counts[line_number] = line_number_counts.get(line_number, 0) + 1
        occurrence = line_number_counts[line_number]
        line_id = f"{record_id}-l{line_number:03d}"
        if occurrence > 1:
            line_id = f"{line_id}-{occurrence:02d}"
        lines.append(
            {
                "record_id": record_id,
                "line_id": line_id,
                "line_number_original": line_record["line_number_original"],
                "line_number_arabic": line_number,
                "text_original": line_record["text_original"],
                "transliteration": None,
                "page_break_before": None,
                "footnote_refs": [],
                "uncertain": ". ." in line_record["text_original"],
            }
        )
    return record, lines, build_structured_txt(record, lines)


def build_structured_txt(record: dict, lines: list[dict]) -> str:
    inscription_text = "\n".join(
        f"{line['line_number_original']}\t{line['text_original']}"
        for line in lines
    )
    full_transcription = record.get("continuous_text_original") or ""
    fields = [
        ("OBI CORPUS REF", f"Sagaing 1203709 block {record['source_inscription_number']} p{record['source_page']}"),
        ("INFORMATION SOURCE", record.get("information_source") or ""),
        ("VOLUME", ""),
        ("PART", ""),
        ("INSCRIPTION NUMBER", record.get("source_inscription_number") or ""),
        ("PAGE NUMBER", record.get("source_page") or ""),
        ("NUMBER OF FACES", record.get("number_of_faces") or ""),
        ("FACE", record.get("face") or ""),
        ("LANGUAGE", record.get("language_original") or ""),
        ("INSCRIPTION SOURCE", record.get("inscription_source_original") or ""),
        ("PLACE OF ORIGIN", record.get("place_of_origin_original") or ""),
        ("CURRENT LOCATION", record.get("current_location_original") or ""),
        ("REFERENCE NUMBER", record.get("reference_number_original") or ""),
        ("REFERENCES", ""),
        ("TITLE", record.get("title_original") or ""),
        ("DATE", record.get("date_original") or ""),
        ("DONOR", record.get("donor_original") or ""),
        ("SUBJECT", record.get("subject_original") or ""),
        ("LENGTH", ""),
        ("NOTES", record.get("notes_original") or ""),
        ("FOOTNOTES", ""),
        ("INSCRIPTION", inscription_text),
        ("FULL TRANSCRIPTION", full_transcription),
        ("FULL TRANSLITERATION", ""),
    ]
    return "\n".join(f"{key}: {value}" for key, value in fields) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=Path,
        default=REPO_ROOT / "1203709" / "စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "supplementary_1203709",
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "sagaing_v0_1",
    )
    args = parser.parse_args()

    text = args.input_file.read_text(encoding="utf-8")
    blocks = split_blocks(text)

    inscriptions: list[dict] = []
    lines: list[dict] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    structured_txt_dir = args.output_dir / "structured_txt"
    structured_txt_dir.mkdir(parents=True, exist_ok=True)

    for block_index, (page_marker, block_lines) in enumerate(blocks, start=1):
        record, block_lines_out, structured_txt = parse_sagaing_block(page_marker, block_lines, block_index)
        inscriptions.append(record)
        lines.extend(block_lines_out)
        (structured_txt_dir / f"{record['record_id']}.txt").write_text(structured_txt, encoding="utf-8")

    write_jsonl(args.output_dir / "inscriptions.jsonl", inscriptions)
    write_jsonl(args.output_dir / "lines.jsonl", lines)

    args.release_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.release_dir / "inscriptions.jsonl", inscriptions)
    write_jsonl(args.release_dir / "lines.jsonl", lines)
    (args.release_dir / "release_manifest.json").write_text(
        json.dumps(
            {
                "release_id": "sagaing_v0_1",
                "source_deposit": "zenodo_1203709",
                "record_count": len(inscriptions),
                "line_count": len(lines),
                "generated_by": "parse_sagaing.py",
                "generated_on": TODAY,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Parsed {len(inscriptions)} Sagaing records and {len(lines)} lines")


if __name__ == "__main__":
    main()
