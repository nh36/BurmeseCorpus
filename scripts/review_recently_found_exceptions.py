from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl, write_tsv
from recently_found_common import LINE_PATTERN, build_source_entries, title_only_page


CASE_CONFIG = {
    "12": {
        "case_id": "rfi-v07-12",
        "candidate_record_id": "obi-v07-n0011-tx-p0030",
        "expected_disposition": "embedded_in_previous_vol7_record",
    },
    "21": {
        "case_id": "rfi-v07-21",
        "candidate_record_id": "obi-v07-n0021-tx-p0064",
        "expected_disposition": "title_variant_same_record",
    },
    "37": {
        "case_id": "rfi-v07-37",
        "candidate_record_id": "obi-v07-n0036-tx-p0121",
        "expected_disposition": "embedded_in_previous_vol7_record",
    },
}


def base_inscription_number(value: str | None) -> str:
    if not value:
        return ""
    match = re.match(r"([0-9]+)", value)
    return match.group(1) if match else value


def strip_ftn_markup(text: str) -> str:
    return re.sub(r"<ftn>.*?</ftn>", "", text)


def normalize_line_text(text: str) -> str:
    return re.sub(r"\s+", " ", strip_ftn_markup(text)).strip()


def load_crosswalk(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["source_entry_number"]: row for row in csv.DictReader(handle, delimiter="\t")}


def source_line_texts(entry: dict) -> list[dict]:
    results: list[dict] = []
    for raw_line in entry["content_lines"]:
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = LINE_PATTERN.match(stripped)
        if not match:
            continue
        results.append(
            {
                "line_number_original": match.group("number"),
                "text_original": match.group("text").strip(),
                "normalized_text": normalize_line_text(match.group("text")),
            }
        )
    return results


def duplicate_suffix_lines(lines: list[dict]) -> list[dict]:
    return [line for line in lines if line["line_id"].endswith("-02")]


def neighbor_titles(entries: list[dict], source_number: int) -> list[dict]:
    results = []
    for entry in entries:
        candidate_number = int(entry["source_entry_number"])
        if abs(candidate_number - source_number) <= 1:
            results.append(
                {
                    "source_entry_number": entry["source_entry_number"],
                    "source_entry_key": entry["source_entry_key"],
                    "source_title": entry["source_title"],
                    "source_page": entry["source_page"],
                }
            )
    return results


def structured_neighbors(vol7_entries: list[dict], source_number: int) -> list[dict]:
    results = []
    for entry in vol7_entries:
        number = base_inscription_number(entry.get("source_inscription_number"))
        if number.isdigit() and abs(int(number) - source_number) <= 1:
            results.append(
                {
                    "record_id": entry["record_id"],
                    "source_inscription_number": entry.get("source_inscription_number"),
                    "title_original": entry.get("title_original"),
                    "face": entry.get("face"),
                    "source_page": entry.get("source_page"),
                }
            )
    return results


def matching_duplicate_lines(entry: dict, structured_duplicate_lines: list[dict]) -> tuple[list[dict], int]:
    duplicate_by_normalized = {normalize_line_text(line["text_original"]): line for line in structured_duplicate_lines}
    matches = []
    for source_line in source_line_texts(entry):
        duplicate_line = duplicate_by_normalized.get(source_line["normalized_text"])
        if duplicate_line is None:
            continue
        matches.append(
            {
                "source_line_number_original": source_line["line_number_original"],
                "source_text_original": source_line["text_original"],
                "structured_line_id": duplicate_line["line_id"],
                "structured_line_number_original": duplicate_line["line_number_original"],
                "structured_text_original": duplicate_line["text_original"],
                "page_break_before": duplicate_line.get("page_break_before"),
            }
        )
    return matches, len(source_line_texts(entry))


def title_only_pages(entry: dict) -> list[dict]:
    pages = []
    for page in entry["page_blocks"]:
        title = title_only_page(page["lines"])
        if title is not None:
            pages.append({"page_number": page["page_number"], "title": title})
    return pages


def build_case_review(
    key: str,
    entry: dict,
    crosswalk_row: dict,
    candidate_record: dict,
    candidate_lines: list[dict],
    source_entries: list[dict],
    vol7_entries: list[dict],
) -> dict:
    candidate_duplicate_lines = duplicate_suffix_lines(candidate_lines)
    matched_lines, source_line_count = matching_duplicate_lines(entry, candidate_duplicate_lines)
    explicit_title_only_pages = title_only_pages(entry)

    if CASE_CONFIG[key]["expected_disposition"] == "embedded_in_previous_vol7_record":
        evidence_summary = (
            f"Source entry {key} is currently labeled as missing from volume 7, but "
            f"{len(matched_lines)} of {source_line_count} parsed source lines match duplicate-suffix lines inside "
            f"{candidate_record['record_id']}."
        )
        disposition = "embedded_in_previous_vol7_record"
        downstream_impact = (
            "The unified release likely duplicates this inscription: once as a source-only addition and once as "
            "embedded text inside the previous structured volume 7 record."
        )
        recommended_next_step = (
            "Do not treat this as a simple omission. Review whether volume 7 record segmentation should be split "
            "editorially or overridden during audit/merge."
        )
        confidence = "high"
    else:
        title_line_matches = [
            {
                "structured_line_id": line["line_id"],
                "text_original": line["text_original"],
                "page_break_before": line.get("page_break_before"),
            }
            for line in candidate_lines
            if "ဆင်ဖြူသိခင်" in normalize_line_text(line["text_original"])
        ]
        evidence_summary = (
            f"Source entry {key} and {candidate_record['record_id']} share inscription number 21 and source page 64. "
            "The source uses the title variant 'ဆင်ဖြူသိခင်ကျောက်စာ', while the structured title is "
            "'ဆင်ပြူ့သိခင်ကျောက်စာ'; the source spelling also appears inside the structured text."
        )
        disposition = "title_variant_same_record"
        downstream_impact = (
            "This case looks like a title normalization/variant issue, not a missing or duplicated inscription."
        )
        recommended_next_step = (
            "Keep the alignment, but preserve both title forms in the review data so future authority work can record "
            "the variant explicitly."
        )
        confidence = "high"
        matched_lines = title_line_matches

    return {
        "case_id": CASE_CONFIG[key]["case_id"],
        "source_entry_number": entry["source_entry_number"],
        "source_entry_key": entry["source_entry_key"],
        "source_title": entry["source_title"],
        "source_page": entry["source_page"],
        "source_page_span": entry["page_span"],
        "inferred_heading": entry["inferred_heading"],
        "title_only_pages": explicit_title_only_pages,
        "current_crosswalk": {
            "match_status": crosswalk_row["match_status"],
            "match_confidence": crosswalk_row["match_confidence"],
            "review_decision": crosswalk_row["review_decision"],
            "evidence": crosswalk_row["evidence"],
            "notes": crosswalk_row["notes"],
            "vol7_record_id": crosswalk_row["vol7_record_id"],
            "vol7_inscription_number": crosswalk_row["vol7_inscription_number"],
            "vol7_title": crosswalk_row["vol7_title"],
        },
        "exploratory_disposition": disposition,
        "confidence": confidence,
        "candidate_structured_record": {
            "record_id": candidate_record["record_id"],
            "source_inscription_number": candidate_record.get("source_inscription_number"),
            "title_original": candidate_record.get("title_original"),
            "face": candidate_record.get("face"),
            "source_page": candidate_record.get("source_page"),
        },
        "source_excerpt_lines": entry["content_lines"][:8],
        "structured_evidence_lines": matched_lines[:12],
        "neighboring_source_entries": neighbor_titles(source_entries, int(entry["source_entry_number"])),
        "neighboring_structured_entries": structured_neighbors(vol7_entries, int(entry["source_entry_number"])),
        "evidence_summary": evidence_summary,
        "downstream_impact": downstream_impact,
        "recommended_next_step": recommended_next_step,
    }


def write_review_summary(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "case_id",
        "source_entry_number",
        "source_title",
        "source_page_span",
        "inferred_heading",
        "current_review_decision",
        "exploratory_disposition",
        "confidence",
        "candidate_record_id",
        "candidate_inscription_number",
        "candidate_title",
        "evidence_summary",
        "downstream_impact",
        "recommended_next_step",
    ]
    flattened = []
    for row in rows:
        flattened.append(
            {
                "case_id": row["case_id"],
                "source_entry_number": row["source_entry_number"],
                "source_title": row["source_title"],
                "source_page_span": ",".join(str(page) for page in row["source_page_span"]),
                "inferred_heading": row["inferred_heading"],
                "current_review_decision": row["current_crosswalk"]["review_decision"],
                "exploratory_disposition": row["exploratory_disposition"],
                "confidence": row["confidence"],
                "candidate_record_id": row["candidate_structured_record"]["record_id"],
                "candidate_inscription_number": row["candidate_structured_record"]["source_inscription_number"],
                "candidate_title": row["candidate_structured_record"]["title_original"],
                "evidence_summary": row["evidence_summary"],
                "downstream_impact": row["downstream_impact"],
                "recommended_next_step": row["recommended_next_step"],
            }
        )
    write_tsv(path, flattened, fieldnames)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-text",
        type=Path,
        default=REPO_ROOT / "1302525" / "Recently Found Burmese Inscriptiosn text.txt",
    )
    parser.add_argument(
        "--structured-inscriptions",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--structured-lines",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current" / "lines.jsonl",
    )
    parser.add_argument(
        "--crosswalk-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_to_vol7_crosswalk.tsv",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_exception_review.json",
    )
    parser.add_argument(
        "--output-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_exception_review.tsv",
    )
    args = parser.parse_args()

    source_entries = build_source_entries(args.source_text.read_text(encoding="utf-8"))
    source_by_num = {str(entry["source_entry_number"]): entry for entry in source_entries}
    crosswalk = load_crosswalk(args.crosswalk_tsv)

    vol7_entries = [record for record in read_jsonl(args.structured_inscriptions) if str(record.get("source_volume")) == "7"]
    vol7_by_record_id = {record["record_id"]: record for record in vol7_entries}
    vol7_lines_by_record: dict[str, list[dict]] = {}
    for line in read_jsonl(args.structured_lines):
        vol7_lines_by_record.setdefault(line["record_id"], []).append(line)

    reviews = []
    for key, config in CASE_CONFIG.items():
        entry = source_by_num[key]
        candidate_record = vol7_by_record_id[config["candidate_record_id"]]
        candidate_lines = vol7_lines_by_record.get(candidate_record["record_id"], [])
        reviews.append(
            build_case_review(
                key=key,
                entry=entry,
                crosswalk_row=crosswalk[key],
                candidate_record=candidate_record,
                candidate_lines=candidate_lines,
                source_entries=source_entries,
                vol7_entries=vol7_entries,
            )
        )

    summary = {
        "scope": (
            "Exploratory review of the remaining 1302525 versus volume 7 exception cases. "
            "This artifact records evidence and provisional dispositions only; it does not change parser or merge behavior."
        ),
        "case_count": len(reviews),
        "disposition_counts": dict(Counter(review["exploratory_disposition"] for review in reviews)),
        "recommendation": (
            "Treat entry 21 as a title-variant match to volume 7 record 21. Treat entries 12 and 37 as segmentation "
            "problems inside volume 7 records 11 and 36 rather than as clean source-only omissions. Review audit and "
            "merge policy only after that editorial decision is accepted."
        ),
        "cases": reviews,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_review_summary(args.output_tsv, reviews)
    print(json.dumps({"case_count": len(reviews), "disposition_counts": summary["disposition_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
