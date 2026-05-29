from __future__ import annotations

import json
from pathlib import Path

from bibtex_common import normalize_for_match, title_keyword_tokens
from corpus_common import read_tsv, write_tsv


MANIFEST_FIELDS = [
    "bibtex_key",
    "work_candidate_id",
    "family_id",
    "candidate_label",
    "original_path",
    "copied_path",
    "file_name",
    "file_size",
    "sha256",
    "match_confidence",
    "match_reason",
    "needs_human_review",
    "notes",
]

GENERIC_TOKENS = {"burma", "burmese", "myanmar", "pagan", "bagan", "inscription", "inscriptions", "history"}


def score_match(authority_row: dict, local_row: dict) -> tuple[int, str]:
    authority_tokens = {
        token
        for token in title_keyword_tokens(
            " ".join(
                [
                    authority_row.get("author", ""),
                    authority_row.get("title", ""),
                    authority_row.get("shorttitle", ""),
                    authority_row.get("family_label", ""),
                ]
            )
        )
        if token not in GENERIC_TOKENS
    }
    local_tokens = {
        token
        for token in title_keyword_tokens(
            " ".join(
                [
                    local_row.get("probable_author", ""),
                    local_row.get("probable_work_label", ""),
                    local_row.get("name", ""),
                ]
            )
        )
        if token not in GENERIC_TOKENS
    }
    overlap = authority_tokens & local_tokens
    if not overlap:
        return 0, ""
    return len(overlap), f"Shared local-authority tokens: {', '.join(sorted(overlap))}"


def match_local_bibliography_sources(
    authority_tsv_path: Path = Path("data/working/bibliography/bibtex_authority/bibtex_authority.tsv"),
    local_candidates_path: Path = Path("data/working/bibliography/local_sources/high_priority_local_candidates.tsv"),
    output_dir: Path = Path("data/working/bibliography/local_sources"),
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "source_library_manifest.tsv"
    report_path = output_dir / "local_bibliography_match_report.json"

    if not local_candidates_path.exists():
        write_tsv(manifest_path, [], MANIFEST_FIELDS)
        report = {
            "available": False,
            "matched_file_count": 0,
            "instructions": "Run scripts/harvest_local_bibliography_sources.py --mode high-priority first.",
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    authority_rows = read_tsv(authority_tsv_path)
    local_rows = read_tsv(local_candidates_path)
    manifest_rows = []

    for authority_row in authority_rows:
        if authority_row.get("authority_status") not in {"confirmed_local_source", "provisional_local_source"}:
            continue
        best_row = None
        best_score = 0
        best_reason = ""
        for local_row in local_rows:
            score, reason = score_match(authority_row, local_row)
            if score > best_score:
                best_score = score
                best_row = local_row
                best_reason = reason
        if best_row is None or best_score < 2:
            continue
        manifest_rows.append(
            {
                "bibtex_key": authority_row["bibtex_key"],
                "work_candidate_id": "",
                "family_id": authority_row.get("family_id", ""),
                "candidate_label": authority_row.get("title", "") or authority_row.get("family_label", ""),
                "original_path": best_row.get("original_path", ""),
                "copied_path": best_row.get("copied_path", ""),
                "file_name": best_row.get("name", ""),
                "file_size": best_row.get("file_size", ""),
                "sha256": best_row.get("sha256", ""),
                "match_confidence": "high" if best_score >= 3 else "medium",
                "match_reason": best_reason,
                "needs_human_review": "false" if authority_row.get("authority_status") == "confirmed_local_source" else "true",
                "notes": authority_row.get("match_reason", ""),
            }
        )

    write_tsv(manifest_path, manifest_rows, MANIFEST_FIELDS)
    report = {
        "available": True,
        "matched_file_count": len(manifest_rows),
        "manifest_path": manifest_path.as_posix(),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = match_local_bibliography_sources()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
