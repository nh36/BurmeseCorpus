from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from corpus_common import (
    REPO_ROOT,
    TODAY,
    build_obi_record_id,
    build_recently_found_record_id,
    normalize_match_text,
    normalize_face,
    normalize_whitespace,
    read_jsonl,
    write_jsonl,
)
from recently_found_common import (
    FACE_MARKER_PATTERN,
    LINE_PATTERN,
    build_source_entries,
    title_only_page,
)


SOURCE_FILE = "1302525/Recently Found Burmese Inscriptiosn text.txt"


def split_entry_into_segments(entry: dict) -> list[dict]:
    segments: list[dict] = []
    current_segment = {"face_label": None, "lines": [], "pages": []}
    explicit_suffix_entry = bool(re.search(r"[a-z]$", entry["source_entry_key"]))

    def flush() -> None:
        nonlocal current_segment
        if current_segment["lines"]:
            segments.append(current_segment)
        current_segment = {"face_label": None, "lines": [], "pages": []}

    for page in entry["page_blocks"]:
        current_page = page["page_number"]
        if title_only_page(page["lines"]) is not None:
            continue
        if current_segment["lines"] or current_segment["pages"]:
            current_segment["pages"].append(current_page)
        for raw_line in page["lines"]:
            stripped = raw_line.strip()
            if not stripped:
                continue

            face_match = FACE_MARKER_PATTERN.match(stripped)
            if face_match:
                if explicit_suffix_entry:
                    continue
                flush()
                current_segment["face_label"] = normalize_whitespace(face_match.group(1))
                current_segment["pages"] = [current_page]
                continue

            line_match = LINE_PATTERN.match(stripped)
            if line_match:
                if not current_segment["pages"]:
                    current_segment["pages"].append(current_page)
                current_segment["lines"].append(
                    {
                        "page_number": current_page,
                        "line_number_original": line_match.group("number"),
                        "line_number_arabic": int(line_match.group("number").translate(str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789"))),
                        "text_original": normalize_whitespace(line_match.group("text")),
                    }
                )
                continue

            if current_segment["lines"]:
                current_segment["lines"][-1]["text_original"] = normalize_whitespace(
                    current_segment["lines"][-1]["text_original"] + " " + stripped
                )

    flush()
    if not segments:
        segments.append({"face_label": None, "lines": [], "pages": entry["page_span"]})
    return segments


def base_inscription_number(value: str | None) -> str:
    if not value:
        return ""
    match = re.match(r"([0-9]+)", value)
    return match.group(1) if match else value


def build_volume7_indexes(vol7_entries: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    by_base_number: dict[str, list[dict]] = defaultdict(list)
    by_title: dict[str, list[dict]] = defaultdict(list)
    for record in vol7_entries:
        by_base_number[base_inscription_number(record.get("source_inscription_number"))].append(record)
        by_title[normalize_match_text(record.get("title_original"))].append(record)
    for records in by_base_number.values():
        records.sort(key=lambda record: (int(record.get("source_page") or 0), record.get("record_id") or ""))
    return by_base_number, by_title


def resolve_structured_candidates(
    entry: dict,
    vol7_by_base_number: dict[str, list[dict]] | None,
    vol7_by_title: dict[str, list[dict]] | None,
) -> list[dict]:
    if vol7_by_base_number is None or vol7_by_title is None:
        return []
    source_number = str(entry["source_entry_number"])
    title_key = entry["source_title_normalized"]
    number_candidates = vol7_by_base_number.get(source_number, [])
    exact_candidates = [record for record in number_candidates if normalize_match_text(record.get("title_original")) == title_key]
    title_only_candidates = [record for record in vol7_by_title.get(title_key, []) if record not in exact_candidates]
    return exact_candidates or number_candidates or title_only_candidates


def build_inscriptions_and_lines(entries: list[dict], vol7_entries: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    inscriptions: list[dict] = []
    lines: list[dict] = []
    vol7_by_base_number, vol7_by_title = build_volume7_indexes(vol7_entries or []) if vol7_entries else (None, None)

    for entry in entries:
        segments = split_entry_into_segments(entry)
        structured_candidates = resolve_structured_candidates(entry, vol7_by_base_number, vol7_by_title)
        face_count = len(structured_candidates) if len(structured_candidates) > 1 else len([segment for segment in segments if segment["lines"]])
        number_of_faces = str(face_count) if face_count > 1 else None
        for segment_index, segment in enumerate(segments, start=1):
            face_label = segment["face_label"]
            source_page = segment["pages"][0] if segment["pages"] else entry["source_page"]
            structured_match = structured_candidates[segment_index - 1] if segment_index <= len(structured_candidates) else None

            segment_key = entry["source_entry_key"]
            resolved_face = face_label
            if structured_match is not None:
                segment_key = structured_match.get("source_inscription_number") or segment_key
                resolved_face = structured_match.get("face") or face_label
                canonical_record_id = structured_match["record_id"]
            else:
                if len(segments) > 1 and not any(character.isalpha() for character in segment_key):
                    segment_key = f"{segment_key}{chr(ord('a') + segment_index - 1)}"
                canonical_record_id = build_obi_record_id("7", segment_key, face_label, str(source_page))

            face_normalized, _ = normalize_face(resolved_face)
            source_record_id = build_recently_found_record_id(segment_key, resolved_face, source_page)

            inscriptions.append(
                {
                    "record_id": source_record_id,
                    "canonical_record_id": canonical_record_id,
                    "source_deposit": "zenodo_1302525",
                    "source_volume": "7-source",
                    "source_part": None,
                    "source_inscription_number": segment_key,
                    "source_entry_key": entry["source_entry_key"],
                    "source_page": str(source_page) if source_page is not None else None,
                    "face": face_normalized,
                    "number_of_faces": number_of_faces,
                    "title_original": entry["source_title"],
                    "title_transliteration": None,
                    "date_original": None,
                    "date_normalized": None,
                    "place_of_origin_original": None,
                    "place_id": None,
                    "current_location_original": None,
                    "donor_original": None,
                    "subject_original": None,
                    "language_original": None,
                    "references_original": None,
                    "notes_original": None,
                    "full_transliteration": None,
                    "source_file": SOURCE_FILE,
                    "reference_number_original": None,
                    "information_source": "Thein Tun. Recently Found Inscriptions. Yangon: Myanmar Historical Research Commission, 2005",
                    "inscription_source_original": None,
                    "footnotes_original": None,
                    "source_page_span": [page for page in segment["pages"] if page is not None],
                    "source_title_normalized": entry["source_title_normalized"],
                    "inferred_heading": entry["inferred_heading"],
                    "segment_index": segment_index,
                    "continuous_text_original": normalize_whitespace(
                        " ".join(line["text_original"] for line in segment["lines"])
                    )
                    or None,
                    "provenance": {
                        "created_from": "Recently Found source txt",
                        "created_by_script": "parse_recently_found_records.py",
                        "created_date": TODAY,
                    },
                }
            )

            line_number_counts: dict[int, int] = {}
            previous_page: int | None = None
            for line in segment["lines"]:
                line_number = line["line_number_arabic"]
                line_number_counts[line_number] = line_number_counts.get(line_number, 0) + 1
                occurrence = line_number_counts[line_number]
                line_id = f"{source_record_id}-l{line_number:03d}"
                if occurrence > 1:
                    line_id = f"{line_id}-{occurrence:02d}"

                page_break_before = None
                if previous_page is not None and line["page_number"] != previous_page:
                    page_break_before = str(line["page_number"])
                previous_page = line["page_number"]

                lines.append(
                    {
                        "record_id": source_record_id,
                        "canonical_record_id": canonical_record_id,
                        "line_id": line_id,
                        "line_number_original": line["line_number_original"],
                        "line_number_arabic": line_number,
                        "text_original": line["text_original"],
                        "transliteration": None,
                        "page_break_before": page_break_before,
                        "footnote_refs": [],
                        "uncertain": ". ." in line["text_original"],
                    }
                )

    return inscriptions, lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=Path,
        default=REPO_ROOT / SOURCE_FILE,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "supplementary_1302525",
    )
    parser.add_argument(
        "--structured-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current" / "inscriptions.jsonl",
    )
    args = parser.parse_args()

    text = args.input_file.read_text(encoding="utf-8")
    entries = build_source_entries(text)
    vol7_entries = [record for record in read_jsonl(args.structured_jsonl) if str(record.get("source_volume")) == "7"]
    inscriptions, lines = build_inscriptions_and_lines(entries, vol7_entries=vol7_entries)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "inscriptions.jsonl", inscriptions)
    write_jsonl(args.output_dir / "lines.jsonl", lines)
    (args.output_dir / "records_summary.json").write_text(
        json.dumps(
            {
                "entry_count": len(entries),
                "record_count": len(inscriptions),
                "line_count": len(lines),
                "inferred_headings": [entry["source_entry_key"] for entry in entries if entry["inferred_heading"]],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Parsed {len(inscriptions)} Recently Found records and {len(lines)} lines")


if __name__ == "__main__":
    main()
