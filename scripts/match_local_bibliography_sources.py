from __future__ import annotations

import json
import os
from pathlib import Path

from bibtex_common import normalize_for_match, sha256_file
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


def label_tokens(row: dict) -> list[str]:
    parts = [row.get("author", ""), row.get("title", ""), row.get("shorttitle", ""), row.get("family_label", "")]
    tokens = []
    for part in parts:
        normalized = normalize_for_match(part)
        if normalized:
            tokens.extend(token for token in normalized.split() if len(token) > 2)
    return tokens[:6]


def relative_under_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def match_local_bibliography_sources(
    authority_tsv_path: Path = Path("data/working/bibliography/bibtex_authority/bibtex_authority.tsv"),
    output_dir: Path = Path("data/working/bibliography/local_sources"),
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "source_library_manifest.tsv"
    report_path = output_dir / "source_library_match_report.json"

    library_root_value = os.environ.get("OBI_LIBRARY_ROOT", "").strip()
    if not library_root_value:
        write_tsv(manifest_path, [], MANIFEST_FIELDS)
        report = {
            "available": False,
            "matched_file_count": 0,
            "library_root": "",
            "instructions": "Set OBI_LIBRARY_ROOT to the root of the local Burma bibliography/library tree before running this script.",
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    library_root = Path(library_root_value).expanduser()
    candidate_rows = read_tsv(authority_tsv_path)
    file_index = [path for path in library_root.rglob("*") if path.is_file()]
    manifest_rows = []

    for row in candidate_rows:
        tokens = label_tokens(row)
        if not tokens:
            continue
        best_match = None
        best_score = 0
        for path in file_index:
            haystack = normalize_for_match(path.name + " " + path.parent.name)
            score = sum(1 for token in tokens if token in haystack)
            if score > best_score:
                best_score = score
                best_match = path
        if not best_match or best_score < 2:
            continue
        manifest_rows.append(
            {
                "bibtex_key": row["bibtex_key"],
                "work_candidate_id": "",
                "family_id": row.get("family_id", ""),
                "candidate_label": row.get("title", "") or row.get("family_label", ""),
                "original_path": relative_under_root(best_match, library_root),
                "copied_path": "",
                "file_name": best_match.name,
                "file_size": str(best_match.stat().st_size),
                "sha256": sha256_file(best_match),
                "match_confidence": "high" if best_score >= 4 else "medium",
                "match_reason": f"Matched {best_score} filename or directory tokens under OBI_LIBRARY_ROOT.",
                "needs_human_review": "true",
                "notes": "Filename-based local library match only; confirm bibliographic identity manually.",
            }
        )

    write_tsv(manifest_path, manifest_rows, MANIFEST_FIELDS)
    report = {
        "available": True,
        "library_root": "OBI_LIBRARY_ROOT",
        "scanned_file_count": len(file_index),
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
