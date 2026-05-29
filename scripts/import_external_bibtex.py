from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bibtex_common import duplicate_keys, parse_bibtex_text, sha256_file, sha256_text, slugify
from corpus_common import REPO_ROOT, write_tsv


ENTRY_FIELDS = [
    "bibtex_key",
    "entry_type",
    "author",
    "editor",
    "year",
    "title",
    "booktitle",
    "journal",
    "publisher",
    "address",
    "doi",
    "url",
    "isbn",
    "raw_entry_hash",
    "source_label",
    "notes",
]


def redact_input_path(path: Path) -> str:
    relative = repo_relative_or_none(path)
    if relative:
        return relative
    home = Path.home()
    try:
        home_relative = path.relative_to(home)
        return f"local:~/{home_relative.as_posix()}"
    except ValueError:
        return f"local:{path.name}"


def repo_relative_or_none(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def import_external_bibtex(input_bibtex: Path, source_label: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_stem = Path(source_label).stem if source_label.lower().endswith(".bib") else source_label
    slug = slugify(label_stem)
    copied_path = output_dir / f"{slug}.bib"
    report_path = output_dir / f"{slug}_import_report.json"
    entries_path = output_dir / f"{slug}_entries.tsv"

    text = input_bibtex.read_text(encoding="utf-8")
    copied_path.write_text(text, encoding="utf-8")
    entries, warnings = parse_bibtex_text(text, source_label=source_label)

    rows = []
    entry_type_counter: Counter[str] = Counter()
    for entry in entries:
        fields = entry["fields"]
        entry_type_counter[entry["entry_type"]] += 1
        rows.append(
            {
                "bibtex_key": entry["bibtex_key"],
                "entry_type": entry["entry_type"],
                "author": fields.get("author", ""),
                "editor": fields.get("editor", ""),
                "year": fields.get("year", ""),
                "title": fields.get("title", ""),
                "booktitle": fields.get("booktitle", ""),
                "journal": fields.get("journal", ""),
                "publisher": fields.get("publisher", ""),
                "address": fields.get("address", ""),
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
                "isbn": fields.get("isbn", ""),
                "raw_entry_hash": sha256_text(entry["raw_entry"]),
                "source_label": source_label,
                "notes": "Malformed BibTeX entry salvaged without explicit type" if entry["entry_type"] == "unknown" else "",
            }
        )
    write_tsv(entries_path, rows, ENTRY_FIELDS)

    report = {
        "source_label": source_label,
        "input_path": redact_input_path(input_bibtex),
        "copied_path": repo_relative_or_none(copied_path) or copied_path.name,
        "sha256": sha256_file(copied_path),
        "entry_count": len(entries),
        "entry_types": dict(sorted(entry_type_counter.items())),
        "duplicate_keys": duplicate_keys(entries),
        "parse_warnings": warnings,
        "import_date": datetime.now(timezone.utc).isoformat(),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an external BibTeX file into bibliography working data.")
    parser.add_argument("--input-bibtex", required=True, type=Path)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    report = import_external_bibtex(args.input_bibtex, args.source_label, args.output_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
