from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from corpus_common import REPO_ROOT, parse_structured_corpus_text, write_jsonl, write_tsv


DEFAULT_ZIPS = [REPO_ROOT / "4321314" / f"OBI_Corpus_Vol{volume}.zip" for volume in range(1, 8)]


def extract_structured_corpus(output_dir: Path) -> dict:
    inscriptions: list[dict] = []
    lines: list[dict] = []
    record_id_counts: dict[str, int] = {}

    for zip_path in DEFAULT_ZIPS:
        with zipfile.ZipFile(zip_path) as archive:
            for member in sorted(name for name in archive.namelist() if name.endswith(".txt")):
                text = archive.read(member).decode("utf-8", errors="replace")
                parsed = parse_structured_corpus_text(
                    text,
                    source_file=member,
                    created_by_script="extract_structured_corpus.py",
                )
                record_id = parsed.inscription["record_id"]
                record_id_counts[record_id] = record_id_counts.get(record_id, 0) + 1
                if record_id_counts[record_id] > 1:
                    deduped_record_id = f"{record_id}-r{record_id_counts[record_id]:02d}"
                    old_record_id = parsed.inscription["record_id"]
                    parsed.inscription["record_id"] = deduped_record_id
                    for line in parsed.lines:
                        line["record_id"] = deduped_record_id
                        line["line_id"] = line["line_id"].replace(old_record_id, deduped_record_id, 1)
                inscriptions.append(parsed.inscription)
                lines.extend(parsed.lines)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "inscriptions.jsonl", inscriptions)
    write_jsonl(output_dir / "lines.jsonl", lines)
    write_tsv(
        output_dir / "inventory.tsv",
        (
            {
                "record_id": record["record_id"],
                "source_volume": record["source_volume"],
                "source_inscription_number": record["source_inscription_number"],
                "source_page": record["source_page"],
                "face": record["face"],
                "title_original": record["title_original"],
                "source_file": record["source_file"],
            }
            for record in inscriptions
        ),
        [
            "record_id",
            "source_volume",
            "source_inscription_number",
            "source_page",
            "face",
            "title_original",
            "source_file",
        ],
    )
    return {"inscriptions": len(inscriptions), "lines": len(lines)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "extracted" / "structured_corpus_current",
    )
    args = parser.parse_args()

    summary = extract_structured_corpus(args.output_dir)
    print(f"Extracted {summary['inscriptions']} inscriptions and {summary['lines']} lines")


if __name__ == "__main__":
    main()
