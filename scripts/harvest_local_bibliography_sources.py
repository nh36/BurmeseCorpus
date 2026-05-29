from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from bibtex_common import sha256_file
from corpus_common import read_tsv, write_tsv
from local_bibliography_common import (
    FRASCH_TERMS,
    HIGH_PRIORITY_TERMS,
    configured_roots,
    copy_to_local_cache,
    discover_candidate_files,
    filename_metadata,
    missing_root_instructions,
    probable_relevance,
    safe_source_path,
    source_file_id,
)

BURMA_DOMAIN_TERMS = [
    "burma",
    "burmese",
    "myanmar",
    "pagan",
    "bagan",
    "luce",
    "duroiselle",
    "blagden",
    "than tun",
    "pe maung tin",
    "frasch",
    "jbrs",
    "bbhc",
    "jras",
    "rdasb",
]


FRASCH_FIELDS = [
    "candidate_id",
    "match_type",
    "name",
    "original_path",
    "file_type",
    "file_size",
    "modified_time",
    "sha256",
    "probable_relevance",
    "copy_status",
    "copied_path",
    "extraction_status",
    "notes",
]

HIGH_PRIORITY_FIELDS = [
    "candidate_id",
    "search_term",
    "name",
    "original_path",
    "file_type",
    "file_size",
    "sha256",
    "probable_work_label",
    "probable_author",
    "probable_year",
    "match_confidence",
    "copy_status",
    "copied_path",
    "notes",
]

MANIFEST_FIELDS = [
    "canonical_local_file_id",
    "sha256",
    "file_name",
    "file_size",
    "primary_original_path",
    "all_original_paths",
    "copied_path",
    "duplicate_count",
    "source_folder_hints",
    "file_type",
    "evidence_priority",
    "copy_status",
    "copy_date",
    "notes",
]

PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}
ROOT_RANK = {"OBI_AUTHOR_ALPHA_ROOT": 3, "OBI_LOCAL_BIB_ROOT": 2, "OBI_LIBRARY_ROOT": 1}
FILETYPE_RANK = {"bib": 5, "ris": 5, "enl": 5, "docx": 4, "doc": 4, "rtf": 4, "txt": 3, "xml": 3, "pdf": 2, "djvu": 1}


def merge_pipe_values(left: str, right: str) -> str:
    values = {value for value in (left.split(" | ") + right.split(" | ")) if value}
    return " | ".join(sorted(values))


def normalize_manifest_row(row: dict) -> dict:
    primary_original_path = row.get("primary_original_path") or row.get("original_path", "")
    all_original_paths = row.get("all_original_paths") or primary_original_path
    source_folder_hints = row.get("source_folder_hints") or row.get("source_folder_hint", "")
    duplicate_count = row.get("duplicate_count")
    if not duplicate_count:
        duplicate_count = str(max(0, len([value for value in all_original_paths.split(" | ") if value]) - 1))
    return {
        "canonical_local_file_id": row.get("canonical_local_file_id") or row.get("source_file_id", ""),
        "sha256": row.get("sha256", ""),
        "file_name": row.get("file_name", ""),
        "file_size": row.get("file_size", ""),
        "primary_original_path": primary_original_path,
        "all_original_paths": all_original_paths,
        "copied_path": row.get("copied_path", ""),
        "duplicate_count": duplicate_count,
        "source_folder_hints": source_folder_hints,
        "file_type": row.get("file_type", ""),
        "evidence_priority": row.get("evidence_priority", "medium"),
        "copy_status": row.get("copy_status", "reused_existing"),
        "copy_date": row.get("copy_date", ""),
        "notes": row.get("notes", ""),
        "_root_label": row.get("_root_label", ""),
    }


def choose_priority(left: dict, right: dict) -> dict:
    left_score = (
        PRIORITY_RANK.get(left.get("evidence_priority", "low"), 0),
        ROOT_RANK.get(left.get("_root_label", ""), 0),
        FILETYPE_RANK.get(left.get("file_type", ""), 0),
        -len(left.get("primary_original_path", "")),
    )
    right_score = (
        PRIORITY_RANK.get(right.get("evidence_priority", "low"), 0),
        ROOT_RANK.get(right.get("_root_label", ""), 0),
        FILETYPE_RANK.get(right.get("file_type", ""), 0),
        -len(right.get("primary_original_path", "")),
    )
    return right if right_score > left_score else left


def merge_manifest_rows(manifest_path: Path, new_rows: list[dict]) -> list[dict]:
    existing = [normalize_manifest_row(row) for row in read_tsv(manifest_path)] if manifest_path.exists() else []
    by_sha = {row["sha256"]: row for row in existing}
    for row in new_rows:
        previous = by_sha.get(row["sha256"])
        if previous is None:
            by_sha[row["sha256"]] = row
            continue
        preferred = choose_priority(
            {**previous, "_root_label": previous.get("_root_label", "")},
            {**row, "_root_label": row.get("_root_label", "")},
        )
        merged = {**preferred}
        merged["all_original_paths"] = merge_pipe_values(previous.get("all_original_paths", ""), row.get("all_original_paths", ""))
        merged["source_folder_hints"] = merge_pipe_values(previous.get("source_folder_hints", ""), row.get("source_folder_hints", ""))
        merged["duplicate_count"] = str(max(0, len([value for value in merged["all_original_paths"].split(" | ") if value]) - 1))
        if previous.get("copied_path") and row.get("copy_status") != "copied":
            merged["copied_path"] = previous["copied_path"]
        by_sha[row["sha256"]] = merged
    merged_rows = sorted(by_sha.values(), key=lambda row: (row["file_name"], row["primary_original_path"]))
    write_tsv(manifest_path, merged_rows, MANIFEST_FIELDS)
    return merged_rows


def is_burma_relevant(path: Path) -> bool:
    haystack = f"{path.as_posix()} {path.parent.as_posix()}".casefold()
    return any(term in haystack for term in BURMA_DOMAIN_TERMS)


def evidence_priority(root_label: str, path: Path, relevance: str) -> str:
    haystack = f"{path.name} {path.parent.as_posix()}".casefold()
    score = ROOT_RANK.get(root_label, 0)
    if relevance == "high":
        score += 2
    elif relevance == "medium":
        score += 1
    if path.suffix.casefold().lstrip(".") in {"bib", "ris", "enl", "doc", "docx", "rtf"}:
        score += 2
    if any(term in haystack for term in {"bibliography", "database", "epig", "inscription", "jbrs", "jras", "rdasb", "bbhc"}):
        score += 2
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def candidate_descriptor(mode: str, root, path: Path, match_type: str, search_terms: list[str]) -> dict:
    metadata = filename_metadata(path)
    safe_path = safe_source_path(path, root)
    relevance = probable_relevance(path, search_terms)
    return {
        "mode": mode,
        "root_label": root.label,
        "path": path,
        "match_type": match_type,
        "search_term": next((term for term in search_terms if term in path.name.casefold() or term in path.parent.name.casefold()), ""),
        "primary_original_path": safe_path,
        "all_original_paths": safe_path,
        "file_name": path.name,
        "file_type": path.suffix.casefold().lstrip("."),
        "file_size": str(path.stat().st_size),
        "modified_time": str(path.stat().st_mtime),
        "sha256": sha256_file(path),
        "probable_relevance": relevance,
        "evidence_priority": evidence_priority(root.label, path, relevance),
        "source_folder_hint": path.parent.name,
        **metadata,
    }


def dedupe_descriptors(raw_descriptors: list[dict]) -> list[dict]:
    by_sha: dict[str, dict] = {}
    for descriptor in raw_descriptors:
        sha256 = descriptor["sha256"]
        if sha256 not in by_sha:
            by_sha[sha256] = {
                **descriptor,
                "_root_label": descriptor["root_label"],
            }
            continue
        existing = by_sha[sha256]
        preferred = choose_priority(existing, {**descriptor, "_root_label": descriptor["root_label"]})
        merged = {**preferred}
        merged["all_original_paths"] = merge_pipe_values(existing.get("all_original_paths", ""), descriptor["all_original_paths"])
        merged["source_folder_hints"] = merge_pipe_values(existing.get("source_folder_hint", existing.get("source_folder_hints", "")), descriptor["source_folder_hint"])
        merged["duplicate_count"] = str(max(0, len([value for value in merged["all_original_paths"].split(" | ") if value]) - 1))
        merged["match_type"] = merge_pipe_values(existing.get("match_type", ""), descriptor["match_type"])
        merged["search_term"] = merge_pipe_values(existing.get("search_term", ""), descriptor["search_term"])
        merged["_root_label"] = preferred.get("_root_label", descriptor["root_label"])
        by_sha[sha256] = merged
    return sorted(by_sha.values(), key=lambda row: (PRIORITY_RANK.get(row["evidence_priority"], 0), row["file_name"]), reverse=True)


def build_manifest_row(descriptor: dict, copy_info: dict) -> dict:
    return {
        "canonical_local_file_id": copy_info["canonical_local_file_id"],
        "sha256": descriptor["sha256"],
        "file_name": descriptor["file_name"],
        "file_size": descriptor["file_size"],
        "primary_original_path": descriptor["primary_original_path"],
        "all_original_paths": descriptor["all_original_paths"],
        "copied_path": copy_info["copied_path"],
        "duplicate_count": descriptor.get("duplicate_count", "0"),
        "source_folder_hints": descriptor.get("source_folder_hints", descriptor["source_folder_hint"]),
        "file_type": descriptor["file_type"],
        "evidence_priority": descriptor["evidence_priority"],
        "copy_status": copy_info["copy_status"],
        "copy_date": copy_info["copy_date"],
        "notes": "",
        "_root_label": descriptor.get("_root_label", descriptor["root_label"]),
    }


def build_candidate_row(mode: str, descriptor: dict, manifest_row: dict) -> dict:
    duplicate_count = int(descriptor.get("duplicate_count", "0") or 0)
    notes = ""
    if duplicate_count:
        notes = f"Collapsed {duplicate_count} duplicate path(s) by SHA-256."
    if mode == "frasch":
        return {
            "candidate_id": manifest_row["canonical_local_file_id"],
            "match_type": descriptor.get("match_type", ""),
            "name": descriptor["file_name"],
            "original_path": descriptor["primary_original_path"],
            "file_type": descriptor["file_type"],
            "file_size": descriptor["file_size"],
            "modified_time": descriptor["modified_time"],
            "sha256": descriptor["sha256"],
            "probable_relevance": descriptor["probable_relevance"],
            "copy_status": manifest_row["copy_status"],
            "copied_path": manifest_row["copied_path"],
            "extraction_status": "pending",
            "notes": notes,
        }
    return {
        "candidate_id": manifest_row["canonical_local_file_id"],
        "search_term": descriptor.get("search_term", ""),
        "name": descriptor["file_name"],
        "original_path": descriptor["primary_original_path"],
        "file_type": descriptor["file_type"],
        "file_size": descriptor["file_size"],
        "sha256": descriptor["sha256"],
        "probable_work_label": descriptor["probable_work_label"],
        "probable_author": descriptor["probable_author"],
        "probable_year": descriptor["probable_year"],
        "match_confidence": "high" if descriptor["evidence_priority"] == "high" else "medium",
        "copy_status": manifest_row["copy_status"],
        "copied_path": manifest_row["copied_path"],
        "notes": notes,
    }


def run_harvest(mode: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    roots = configured_roots()
    manifest_path = output_dir / "local_file_manifest.tsv"
    report_path = output_dir / "local_source_harvest_report.json"
    target_path = output_dir / ("frasch_source_candidates.tsv" if mode == "frasch" else "high_priority_local_candidates.tsv")

    if not roots:
        report = {
            "mode": mode,
            "available_roots": [],
            "raw_candidate_count": 0,
            "unique_file_count": 0,
            "duplicate_file_count": 0,
            "copied_file_count": 0,
            "skipped_existing_count": 0,
            "instructions": missing_root_instructions(),
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not manifest_path.exists():
            write_tsv(manifest_path, [], MANIFEST_FIELDS)
        if not target_path.exists():
            write_tsv(target_path, [], FRASCH_FIELDS if mode == "frasch" else HIGH_PRIORITY_FIELDS)
        return report

    search_terms = FRASCH_TERMS if mode == "frasch" else HIGH_PRIORITY_TERMS
    discovered = discover_candidate_files(roots, search_terms)
    if mode == "high-priority":
        discovered = [candidate for candidate in discovered if is_burma_relevant(candidate[1])]

    raw_descriptors = [candidate_descriptor(mode, root, path, match_type, search_terms) for root, path, match_type in discovered]
    unique_descriptors = dedupe_descriptors(raw_descriptors)

    existing_manifest_rows = {row["sha256"]: normalize_manifest_row(row) for row in read_tsv(manifest_path)} if manifest_path.exists() else {}
    manifest_rows: list[dict] = []
    candidate_rows: list[dict] = []

    copied_file_count = 0
    skipped_existing_count = 0

    for descriptor in unique_descriptors:
        existing_row = existing_manifest_rows.get(descriptor["sha256"], {})
        canonical_file_id = existing_row.get("canonical_local_file_id") or source_file_id(descriptor["path"], sha256=descriptor["sha256"])
        copy_info = copy_to_local_cache(
            descriptor["path"],
            canonical_file_id=canonical_file_id,
            sha256=descriptor["sha256"],
            existing_copied_path=existing_row.get("copied_path", ""),
            source_folder_hint=descriptor["source_folder_hint"],
        )
        if copy_info["copy_status"] == "copied":
            copied_file_count += 1
        else:
            skipped_existing_count += 1
        manifest_row = build_manifest_row(descriptor, copy_info)
        manifest_rows.append(manifest_row)
        candidate_rows.append(build_candidate_row(mode, descriptor, manifest_row))

    candidate_rows.sort(
        key=lambda row: (
            PRIORITY_RANK.get(row.get("probable_relevance", row.get("match_confidence", "medium")), 0),
            row["name"],
        ),
        reverse=True,
    )
    write_tsv(target_path, candidate_rows, FRASCH_FIELDS if mode == "frasch" else HIGH_PRIORITY_FIELDS)
    merged_manifest = merge_manifest_rows(manifest_path, manifest_rows)

    files_by_source_hint = Counter()
    for row in manifest_rows:
        for hint in row["source_folder_hints"].split(" | "):
            if hint:
                files_by_source_hint[hint] += 1

    report = {
        "mode": mode,
        "available_roots": [f"{root.label}:{root.path.name}" for root in roots],
        "raw_candidate_count": len(raw_descriptors),
        "unique_file_count": len(unique_descriptors),
        "duplicate_file_count": max(0, len(raw_descriptors) - len(unique_descriptors)),
        "copied_file_count": copied_file_count,
        "skipped_existing_count": skipped_existing_count,
        "files_by_type": dict(Counter(row["file_type"] for row in candidate_rows)),
        "files_by_source_hint": dict(files_by_source_hint),
        "manifest_row_count": len(merged_manifest),
        "output_file": target_path.as_posix(),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest local bibliography source candidates into a gitignored cache.")
    parser.add_argument("--mode", choices=["frasch", "high-priority"], required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/working/bibliography/local_sources"))
    args = parser.parse_args()
    result = run_harvest(args.mode, args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
