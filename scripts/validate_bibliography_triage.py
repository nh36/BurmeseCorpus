from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from corpus_common import REPO_ROOT, read_tsv


ALLOWED_REVIEW_STATUS = {"unreviewed", "needs_human_review", "reviewed_provisional", "reviewed_stable"}
ALLOWED_TRANSLATION_RELEVANCE = {"likely_translation", "possible_translation", "unlikely_translation", "unknown"}
ALLOWED_LIKELY_TRANSLATION = {"yes", "no", "possible", "unknown"}
ALLOWED_FAMILY_TYPES = {"source_catalogue", "publication", "article", "book", "internal_reference", "unclear"}
ABSOLUTE_PATH_PATTERN = re.compile(r"(^/(?:Users|home|var|private|tmp|opt|Volumes)\b|^[A-Za-z]:\\\\)")


def contains_absolute_path(value: str) -> bool:
    return bool(ABSOLUTE_PATH_PATTERN.search(value))


def validate_bibliography_triage(bibliography_dir: Path) -> dict:
    required_files = [
        "reference_families.tsv",
        "reference_family_members.tsv",
        "bibliographic_work_candidates.tsv",
        "bibliography_triage_report.json",
    ]
    errors: list[str] = []
    missing_files = [name for name in required_files if not (bibliography_dir / name).exists()]
    if missing_files:
        return {"ok": False, "errors": [f"missing bibliography triage files: {', '.join(missing_files)}"]}

    families = read_tsv(bibliography_dir / "reference_families.tsv")
    members = read_tsv(bibliography_dir / "reference_family_members.tsv")
    work_candidates = read_tsv(bibliography_dir / "bibliographic_work_candidates.tsv")
    report = json.loads((bibliography_dir / "bibliography_triage_report.json").read_text(encoding="utf-8"))

    family_ids = set()
    for index, family in enumerate(families, start=1):
        family_id = family.get("family_id", "")
        if family_id in family_ids:
            errors.append(f"duplicate family_id {family_id}")
        else:
            family_ids.add(family_id)
        try:
            member_count = int(family.get("member_count", ""))
            occurrence_count = int(family.get("occurrence_count", ""))
            if member_count < 0 or occurrence_count < 0:
                errors.append(f"reference_families[{index}] has negative counts")
        except ValueError:
            errors.append(f"reference_families[{index}] has non-integer counts")
        if family.get("family_type") not in ALLOWED_FAMILY_TYPES:
            errors.append(f"reference_families[{index}] has invalid family_type {family.get('family_type')}")
        if family.get("likely_contains_translation") not in ALLOWED_LIKELY_TRANSLATION:
            errors.append(
                "reference_families["
                f"{index}] has invalid likely_contains_translation {family.get('likely_contains_translation')}"
            )
        if family.get("review_status") not in ALLOWED_REVIEW_STATUS:
            errors.append(f"reference_families[{index}] has invalid review_status {family.get('review_status')}")
        for value in family.values():
            if isinstance(value, str) and contains_absolute_path(value):
                errors.append(f"reference_families[{index}] contains an absolute local path")

    for index, member in enumerate(members, start=1):
        if member.get("family_id") not in family_ids:
            errors.append(f"reference_family_members[{index}] references unknown family_id {member.get('family_id')}")
        try:
            occurrence_count = int(member.get("occurrence_count", ""))
            if occurrence_count < 0:
                errors.append(f"reference_family_members[{index}] has negative occurrence_count")
        except ValueError:
            errors.append(f"reference_family_members[{index}] has non-integer occurrence_count")
        for value in member.values():
            if isinstance(value, str) and contains_absolute_path(value):
                errors.append(f"reference_family_members[{index}] contains an absolute local path")

    for index, candidate in enumerate(work_candidates, start=1):
        if candidate.get("family_id") not in family_ids:
            errors.append(
                f"bibliographic_work_candidates[{index}] references unknown family_id {candidate.get('family_id')}"
            )
        if candidate.get("review_status") not in ALLOWED_REVIEW_STATUS:
            errors.append(
                f"bibliographic_work_candidates[{index}] has invalid review_status {candidate.get('review_status')}"
            )
        if candidate.get("translation_relevance") not in ALLOWED_TRANSLATION_RELEVANCE:
            errors.append(
                "bibliographic_work_candidates["
                f"{index}] has invalid translation_relevance {candidate.get('translation_relevance')}"
            )
        for value in candidate.values():
            if isinstance(value, str) and contains_absolute_path(value):
                errors.append(f"bibliographic_work_candidates[{index}] contains an absolute local path")

    report_values = json.dumps(report, ensure_ascii=False)
    if contains_absolute_path(report_values):
        errors.append("bibliography_triage_report.json contains an absolute local path")

    return {
        "ok": not errors,
        "errors": errors,
        "counts": {
            "families": len(families),
            "members": len(members),
            "work_candidates": len(work_candidates),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bibliography-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography",
    )
    args = parser.parse_args()

    result = validate_bibliography_triage(args.bibliography_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
