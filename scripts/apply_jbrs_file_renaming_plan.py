#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from corpus_common import ensure_parent, read_tsv
from jbrs_workflow_common import JBRS_FILE_RENAMING_PLAN_PATH

DEFAULT_RUNTIME_PATH_MAP = Path("data_local/ocr/jbrs/manifest/jbrs_runtime_path_map.json")
DEFAULT_OUTPUT_ROOT = Path("data_local/sources/jbrs_canonical_pdfs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the JBRS canonical-PDF renaming plan without touching committed OCR artifacts."
    )
    parser.add_argument("--plan", type=Path, default=JBRS_FILE_RENAMING_PLAN_PATH)
    parser.add_argument("--runtime-path-map", type=Path, default=DEFAULT_RUNTIME_PATH_MAP)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--copy", action="store_true")
    mode_group.add_argument("--symlink", action="store_true")
    mode_group.add_argument("--rename-originals", action="store_true")
    return parser.parse_args()


def action_name(args: argparse.Namespace) -> str:
    if args.copy:
        return "copy"
    if args.symlink:
        return "symlink"
    if args.rename_originals:
        return "rename-originals"
    return "dry-run"


def eligible_plan_rows(plan_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in plan_rows
        if row.get("proposed_pdf_file_name")
        and row.get("identity_confidence") in {"high", "medium"}
    ]


def resolve_source_path(
    local_file_id: str,
    runtime_path_map: dict[str, str],
) -> Path | None:
    raw = runtime_path_map.get(local_file_id, "")
    if not raw:
        return None
    return Path(raw)


def apply_action(source_path: Path, destination_path: Path, action: str) -> str:
    if action == "dry-run":
        return "dry-run"
    ensure_parent(destination_path)
    if destination_path.exists() or destination_path.is_symlink():
        return "skipped-existing-destination"
    if action == "copy":
        shutil.copy2(source_path, destination_path)
        return "copied"
    if action == "symlink":
        destination_path.symlink_to(source_path)
        return "symlinked"
    if action == "rename-originals":
        source_path.rename(destination_path)
        return "renamed-original"
    raise ValueError(f"Unsupported action: {action}")


def main() -> int:
    args = parse_args()
    action = action_name(args)
    plan_rows = read_tsv(args.plan)
    runtime_path_map = json.loads(args.runtime_path_map.read_text(encoding="utf-8"))
    output_root = args.output_root
    eligible_rows = eligible_plan_rows(plan_rows)

    completed = 0
    skipped = 0
    missing = 0
    for row in eligible_rows:
        source_path = resolve_source_path(row["local_file_id"], runtime_path_map)
        if not source_path or not source_path.exists():
            missing += 1
            print(f"MISSING\t{row['local_file_id']}\t{row['proposed_pdf_file_name']}")
            continue
        destination_path = output_root / row["proposed_pdf_file_name"]
        result = apply_action(source_path, destination_path, action)
        if result in {"dry-run", "copied", "symlinked", "renamed-original"}:
            completed += 1
        else:
            skipped += 1
        print(
            "\t".join(
                [
                    result,
                    row["local_file_id"],
                    source_path.as_posix(),
                    destination_path.as_posix(),
                ]
            )
        )

    print(
        json.dumps(
            {
                "plan": args.plan.as_posix(),
                "action": action,
                "eligible_rows": len(eligible_rows),
                "completed_or_previewed": completed,
                "skipped": skipped,
                "missing_sources": missing,
                "output_root": output_root.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
