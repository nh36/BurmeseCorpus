from __future__ import annotations

import argparse
import json
import sqlite3
import textwrap
from pathlib import Path

from corpus_common import REPO_ROOT, TODAY, read_jsonl, write_jsonl
from validate_corpus import validate_dataset


REQUIRED_INSCRIPTION_FIELDS = [
    "record_id",
    "source_deposit",
    "source_layer",
    "source_volume",
    "source_part",
    "source_inscription_number",
    "source_page",
    "face",
    "number_of_faces",
    "title_original",
    "title_transliteration",
    "date_original",
    "date_normalized",
    "place_of_origin_original",
    "place_id",
    "current_location_original",
    "donor_original",
    "subject_original",
    "language_original",
    "references_original",
    "notes_original",
    "full_transliteration",
    "source_file",
    "information_source",
    "provenance",
    "release_status",
]


RELEASE_README_FILENAME = "README.md"


def repo_relative_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def ensure_release_input(dataset_dir: Path, required_files: list[str], error_message: str) -> None:
    missing = [name for name in required_files if not (dataset_dir / name).exists()]
    if missing:
        raise SystemExit(f"{error_message} Missing files: {', '.join(missing)}")


def classify_unified_record(record: dict) -> tuple[str, str]:
    if record.get("merge_status") == "added_from_source_only" or record.get("source_deposit") == "zenodo_1302525":
        return "recently_found_aligned", "supplementary"
    if record.get("editorial_relation_ids"):
        return "structured_obi", "editorial_relation_target"
    return "structured_obi", "canonical"


def normalize_inscription_record(record: dict, *, source_layer: str, release_status: str, source_release: str) -> dict:
    normalized: dict = {}
    for field in REQUIRED_INSCRIPTION_FIELDS:
        if field == "source_layer":
            normalized[field] = source_layer
        elif field == "release_status":
            normalized[field] = release_status
        elif field == "provenance":
            provenance = dict(record.get("provenance") or {})
            provenance.update(
                {
                    "release_builder_script": "build_corpus_release.py",
                    "release_id": "corpus_release_v0_3",
                    "source_release": source_release,
                }
            )
            normalized[field] = provenance
        else:
            normalized[field] = record.get(field)
    for key, value in record.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def build_sqlite_table(conn: sqlite3.Connection, table_name: str, records: list[dict]) -> None:
    if not records:
        return
    columns: list[str] = []
    for record in records:
        for key in record:
            if key not in columns:
                columns.append(key)

    column_types: dict[str, str] = {}
    for column in columns:
        values = [record.get(column) for record in records if record.get(column) is not None]
        if values and all(isinstance(value, bool) for value in values):
            column_types[column] = "INTEGER"
        elif values and all(isinstance(value, int) for value in values):
            column_types[column] = "INTEGER"
        elif values and all(isinstance(value, (int, float)) for value in values):
            column_types[column] = "REAL"
        else:
            column_types[column] = "TEXT"

    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(
        f'CREATE TABLE "{table_name}" ('
        + ", ".join(f'"{column}" {column_types[column]}' for column in columns)
        + ")"
    )

    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f'INSERT INTO "{table_name}" (' + ", ".join(f'"{column}"' for column in columns) + f") VALUES ({placeholders})"
    rows: list[list[object]] = []
    for record in records:
        row: list[object] = []
        for column in columns:
            value = record.get(column)
            if isinstance(value, bool):
                row.append(int(value))
            elif isinstance(value, (dict, list)):
                row.append(json.dumps(value, ensure_ascii=False))
            else:
                row.append(value)
        rows.append(row)
    conn.executemany(insert_sql, rows)


def build_sqlite_export(sqlite_path: Path, inscriptions: list[dict], lines: list[dict], editorial_relations: list[dict], sources: list[dict]) -> None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as conn:
        build_sqlite_table(conn, "inscriptions", inscriptions)
        build_sqlite_table(conn, "lines", lines)
        build_sqlite_table(conn, "editorial_relations", editorial_relations)
        build_sqlite_table(conn, "sources", sources)
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_inscriptions_record_id" ON inscriptions(record_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_inscriptions_source_deposit" ON inscriptions(source_deposit)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_inscriptions_source_layer" ON inscriptions(source_layer)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_inscriptions_source_inscription_number" ON inscriptions(source_inscription_number)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_lines_record_id" ON lines(record_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_lines_line_id" ON lines(line_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_editorial_relations_target_record_id" ON editorial_relations(target_record_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS "idx_editorial_relations_source_entry_number" ON editorial_relations(source_entry_number)')
        conn.commit()


def build_sqlite_export_from_jsonl(output_dir: Path) -> None:
    build_sqlite_export(
        output_dir / "corpus_release.sqlite",
        read_jsonl(output_dir / "inscriptions.jsonl"),
        read_jsonl(output_dir / "lines.jsonl"),
        read_jsonl(output_dir / "editorial_relations.jsonl"),
        read_jsonl(output_dir / "sources.jsonl"),
    )


def count_lines_by_source(inscriptions: list[dict], lines: list[dict]) -> dict[str, int]:
    source_by_record_id = {record["record_id"]: record["source_deposit"] for record in inscriptions}
    counts: dict[str, int] = {}
    for line in lines:
        source_id = source_by_record_id.get(line["record_id"])
        if source_id is None:
            continue
        counts[source_id] = counts.get(source_id, 0) + 1
    return counts


def infer_relation_source_id(relation: dict) -> str | None:
    source_record_id = relation.get("source_record_id") or ""
    if source_record_id.startswith("rfi-z1302525-"):
        return "zenodo_1302525"
    if source_record_id.startswith("sagaing-z1203709-"):
        return "zenodo_1203709"
    if source_record_id.startswith("obi-"):
        return "zenodo_4321314"
    return None


def count_editorial_relations_by_source(editorial_relations: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relation in editorial_relations:
        source_id = infer_relation_source_id(relation)
        if source_id is None:
            continue
        counts[source_id] = counts.get(source_id, 0) + 1
    return counts


def source_entry(
    *,
    source_id: str,
    source_type: str,
    title_original: str,
    title_english: str,
    zenodo_doi: str,
    local_source_path: str,
    release_role: str,
    inscription_record_count: int,
    line_record_count: int,
    editorial_relation_count: int,
    parser_script: str,
    source_status: str,
    notes: str,
) -> dict:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "title_original": title_original,
        "title_english": title_english,
        "zenodo_doi": zenodo_doi,
        "local_source_path": local_source_path,
        "release_role": release_role,
        "inscription_record_count": inscription_record_count,
        "line_record_count": line_record_count,
        "editorial_relation_count": editorial_relation_count,
        "record_count": inscription_record_count,
        "line_count": line_record_count,
        "parser_script": parser_script,
        "source_status": source_status,
        "notes": notes,
    }


def build_sources_registry(inscriptions: list[dict], lines: list[dict], editorial_relations: list[dict]) -> list[dict]:
    inscription_counts: dict[str, int] = {}
    for record in inscriptions:
        source_id = record["source_deposit"]
        inscription_counts[source_id] = inscription_counts.get(source_id, 0) + 1
    line_counts = count_lines_by_source(inscriptions, lines)
    editorial_relation_counts = count_editorial_relations_by_source(editorial_relations)

    return [
        source_entry(
            source_id="zenodo_4321314",
            source_type="zenodo_deposit",
            title_original="OBI Corpus",
            title_english="Structured Corpus of Old Burmese Stone Inscriptions",
            zenodo_doi="10.5281/zenodo.4321314",
            local_source_path="4321314/",
            release_role="canonical_release_base",
            inscription_record_count=inscription_counts.get("zenodo_4321314", 0),
            line_record_count=line_counts.get("zenodo_4321314", 0),
            editorial_relation_count=editorial_relation_counts.get("zenodo_4321314", 0),
            parser_script="scripts/extract_structured_corpus.py; scripts/merge_unified_release.py; scripts/build_corpus_release.py",
            source_status="canonical_structured_source",
            notes="Structured OBI records remain the canonical corpus base in corpus_release_v0_3.",
        ),
        source_entry(
            source_id="zenodo_1302525",
            source_type="zenodo_deposit",
            title_original="Recently Found Burmese Inscriptions",
            title_english="Thein Tun / Recently Found Inscriptions",
            zenodo_doi="10.5281/zenodo.1302525",
            local_source_path="1302525/Recently Found Burmese Inscriptiosn text.txt",
            release_role="editorial_relation_source",
            inscription_record_count=inscription_counts.get("zenodo_1302525", 0),
            line_record_count=line_counts.get("zenodo_1302525", 0),
            editorial_relation_count=editorial_relation_counts.get("zenodo_1302525", 0),
            parser_script="scripts/parse_recently_found.py; scripts/parse_recently_found_records.py; scripts/merge_unified_release.py; scripts/build_corpus_release.py",
            source_status="aligned_supplementary_source",
            notes="Recently Found contributes editorial relations in this release rather than duplicate canonical inscription rows for embedded cases 12 and 37.",
        ),
        source_entry(
            source_id="zenodo_1203709",
            source_type="zenodo_deposit",
            title_original="စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ",
            title_english="Sagaing Region newly found inscriptions",
            zenodo_doi="10.5281/zenodo.1203709",
            local_source_path="1203709/စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.txt",
            release_role="supplementary_release_component",
            inscription_record_count=inscription_counts.get("zenodo_1203709", 0),
            line_record_count=line_counts.get("zenodo_1203709", 0),
            editorial_relation_count=editorial_relation_counts.get("zenodo_1203709", 0),
            parser_script="scripts/parse_sagaing.py; scripts/build_corpus_release.py",
            source_status="supplementary_unaligned_source",
            notes="Sagaing records are included as supplementary structured data and retain their sagaing- identifiers pending any reviewed crosswalk.",
        ),
    ]


def build_source_contribution_counts(sources: list[dict]) -> dict[str, dict]:
    return {
        record["source_id"]: {
            "inscription_records": record["inscription_record_count"],
            "line_records": record["line_record_count"],
            "editorial_relations": record["editorial_relation_count"],
        }
        for record in sources
    }


def build_release_manifest(
    inscriptions: list[dict],
    lines: list[dict],
    editorial_relations: list[dict],
    sources: list[dict],
    *,
    output_dir: Path,
    input_releases: list[Path],
    input_working_files: list[Path],
    validation_status: str,
) -> dict:
    record_counts_by_source = {record["source_id"]: record["record_count"] for record in sources}
    line_counts_by_source = {record["source_id"]: record["line_count"] for record in sources}
    source_contribution_counts = build_source_contribution_counts(sources)
    return {
        "release_id": "corpus_release_v0_3",
        "release_date": TODAY,
        "created_by_script": "scripts/build_corpus_release.py",
        "input_releases": [repo_relative_path(path) for path in input_releases],
        "input_working_files": [repo_relative_path(path) for path in input_working_files],
        "record_counts_by_source": record_counts_by_source,
        "line_counts_by_source": line_counts_by_source,
        "source_contribution_counts": source_contribution_counts,
        "total_inscription_count": len(inscriptions),
        "total_line_count": len(lines),
        "editorial_relation_count": len(editorial_relations),
        "source_count": len(sources),
        "sqlite_export": repo_relative_path(output_dir / "corpus_release.sqlite"),
        "validation_status": validation_status,
        "known_limitations": [
            "Sagaing has been parsed into structured form but not yet reconciled against the main OBI numbering or other inscription catalogues.",
            "Recently Found entries 12 and 37 are represented as embedded editorial relations, not split as separate canonical OBI records.",
            "Translation fields remain empty or absent; translation is a later layer.",
            "Bibliography normalization remains preliminary.",
        ],
        "recommended_next_steps": [
            "Build bibliography and place authority tables on top of corpus_release_v0_3.",
            "Review source-specific reference coverage before full bibliography normalization.",
            "Start published-translation discovery only after source and bibliography normalization stabilize.",
            "Add lexical and search-oriented exports after the release baseline is stable.",
        ],
    }


def build_release_notes(manifest: dict, sources: list[dict]) -> str:
    source_counts = manifest["source_contribution_counts"]
    return textwrap.dedent(
        f"""\
        # Corpus Release v0_3

        Corpus release v0_3 is the first whole-corpus release candidate for this repository. It combines the override-aware unified OBI release with the parsed Sagaing release while preserving stable record identifiers, explicit provenance, and the existing editorial relations for the Recently Found / Volume 7 exceptions.

        ## What this release contains

        - **Structured OBI base:** {source_counts["zenodo_4321314"]["inscription_records"]} inscription records and {source_counts["zenodo_4321314"]["line_records"]} lines carried forward from `data/release/unified_release_v0_2/`.
        - **Sagaing supplementary layer:** {source_counts["zenodo_1203709"]["inscription_records"]} inscription records and {source_counts["zenodo_1203709"]["line_records"]} lines carried forward from `data/release/sagaing_v0_1/`, with existing `sagaing-` identifiers preserved.
        - **Recently Found contribution:** {source_counts["zenodo_1302525"]["inscription_records"]} independent inscription records, {source_counts["zenodo_1302525"]["line_records"]} lines, and {source_counts["zenodo_1302525"]["editorial_relations"]} editorial relations carried forward from `unified_release_v0_2`.

        ## What changed from earlier releases

        - `unified_release_v0_1` merged the structured corpus with Recently Found but still counted embedded cases `12` and `37` as additional source-only canonical records.
        - `unified_release_v0_2` introduced explicit editorial relations so those embedded cases are preserved without being counted twice, and it preserved entry `21` as a title-variant relation.
        - `corpus_release_v0_3` keeps the v0_2 OBI release intact, adds Sagaing as a supplementary release component, and adds a release manifest, source registry, release notes, validation report, and a derived SQLite export.

        ## Recently Found / Volume 7 ambiguity

        Recently Found entries `12` and `37` are not treated here as separate canonical OBI inscriptions. They remain visible through `editorial_relations.jsonl`, where they are linked to their structured target records as embedded-in-previous-record cases. Entry `21` remains aligned to its structured target and is preserved as a title-variant relation rather than normalized away.

        ## How Sagaing is included

        Sagaing is included as supplementary structured data. Its records and lines are appended to the corpus release without renumbering them into the OBI sequence. No claim is made here that Sagaing has been fully reconciled against the OBI numbering or any external inscription catalogue.

        ## What is not yet done

        - translation remains a later layer;
        - bibliography normalization remains preliminary;
        - place normalization is still a working scaffold rather than a reviewed authority table;
        - Sagaing crosswalk work has not yet been completed.

        ## Safe uses for this release

        Researchers can use this release for stable record-level citation within the current repository, line-level querying across the structured OBI and Sagaing releases, and explicit inspection of the current editorial handling of the Recently Found / Volume 7 exceptions.

        ## What not to infer

        Researchers should not infer that Sagaing has been canonically folded into the OBI numbering, that embedded Recently Found cases have been split into separate canonical inscriptions, that bibliography and place identifiers are final authority data, or that translation is complete.
        """
    )


def build_release_readme(manifest: dict) -> str:
    source_counts = manifest["source_contribution_counts"]
    return textwrap.dedent(
        f"""\
        # corpus_release_v0_3

        `corpus_release_v0_3` is the current whole-corpus release candidate and the stable Phase 1 baseline for later authority work.

        Start with **`inscriptions.jsonl`**. Pair it with **`lines.jsonl`** for line-level work. Those two JSONL files are the canonical release data.

        ## Files in this directory

        - `inscriptions.jsonl` — canonical inscription-level release data across structured OBI and Sagaing.
        - `lines.jsonl` — canonical line-level release data keyed by `record_id` and `line_id`.
        - `editorial_relations.jsonl` — conservative editorial relationships, especially the Recently Found / Volume 7 cases `12`, `21`, and `37`.
        - `sources.jsonl` — source registry for the three Zenodo deposits and their release-layer contribution counts.
        - `release_manifest.json` — release metadata, input paths, counts, known limitations, and next-step notes.
        - `release_notes.md` — human-readable overview of what this release contains and what it does not claim.
        - `validation_report.json` — release-local validation output.
        - `corpus_release.sqlite` — derived convenience export; not authoritative.

        ## Practical notes

        - Canonical data: `inscriptions.jsonl` and `lines.jsonl`
        - Derived convenience export: `corpus_release.sqlite`
        - Structured OBI contributes {source_counts["zenodo_4321314"]["inscription_records"]} inscription rows and {source_counts["zenodo_4321314"]["line_records"]} line rows.
        - Recently Found contributes {source_counts["zenodo_1302525"]["editorial_relations"]} editorial relations in this release and no separate canonical inscription rows.
        - Sagaing contributes {source_counts["zenodo_1203709"]["inscription_records"]} supplementary inscription rows and retains `sagaing-` identifiers.
        - This release does not yet contain completed translations or final bibliography/place authority data.
        """
    )


def build_corpus_release(
    *,
    unified_dir: Path,
    sagaing_dir: Path,
    overrides_file: Path,
    release_policy_file: Path,
    exception_review_file: Path,
    output_dir: Path,
) -> dict:
    ensure_release_input(
        unified_dir,
        ["inscriptions.jsonl", "lines.jsonl", "editorial_relations.jsonl"],
        "unified_release_v0_2 is required before corpus_release_v0_3 can be built. Run python3 scripts/merge_unified_release.py first.",
    )
    ensure_release_input(
        sagaing_dir,
        ["inscriptions.jsonl", "lines.jsonl"],
        "sagaing_v0_1 is required before corpus_release_v0_3 can be built. Run python3 scripts/parse_sagaing.py first.",
    )
    for required_file in (overrides_file, release_policy_file, exception_review_file):
        if not required_file.exists():
            raise SystemExit(f"Required working file missing: {repo_relative_path(required_file)}")

    unified_inscriptions = read_jsonl(unified_dir / "inscriptions.jsonl")
    unified_lines = read_jsonl(unified_dir / "lines.jsonl")
    editorial_relations = read_jsonl(unified_dir / "editorial_relations.jsonl")
    sagaing_inscriptions = read_jsonl(sagaing_dir / "inscriptions.jsonl")
    sagaing_lines = read_jsonl(sagaing_dir / "lines.jsonl")

    inscriptions = [
        normalize_inscription_record(
            record,
            source_layer=classify_unified_record(record)[0],
            release_status=classify_unified_record(record)[1],
            source_release=repo_relative_path(unified_dir),
        )
        for record in unified_inscriptions
    ]
    inscriptions.extend(
        normalize_inscription_record(
            record,
            source_layer="sagaing_supplementary",
            release_status="supplementary",
            source_release=repo_relative_path(sagaing_dir),
        )
        for record in sagaing_inscriptions
    )
    lines = [dict(record) for record in unified_lines]
    lines.extend(dict(record) for record in sagaing_lines)

    sources = build_sources_registry(inscriptions, lines, editorial_relations)
    input_releases = [unified_dir, sagaing_dir]
    input_working_files = [overrides_file, release_policy_file, exception_review_file]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "inscriptions.jsonl", inscriptions)
    write_jsonl(output_dir / "lines.jsonl", lines)
    write_jsonl(output_dir / "editorial_relations.jsonl", editorial_relations)
    write_jsonl(output_dir / "sources.jsonl", sources)
    build_sqlite_export(output_dir / "corpus_release.sqlite", inscriptions, lines, editorial_relations, sources)

    manifest = build_release_manifest(
        inscriptions,
        lines,
        editorial_relations,
        sources,
        output_dir=output_dir,
        input_releases=input_releases,
        input_working_files=input_working_files,
        validation_status="pending",
    )
    (output_dir / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "release_notes.md").write_text(build_release_notes(manifest, sources), encoding="utf-8")
    (output_dir / RELEASE_README_FILENAME).write_text(build_release_readme(manifest), encoding="utf-8")

    validation_result = validate_dataset(output_dir, allow_missing_dataset_validation_report=True)
    validation_report = {"datasets": [validation_result], "ok": not validation_result["errors"]}
    (output_dir / "validation_report.json").write_text(
        json.dumps(validation_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest["validation_status"] = "valid" if validation_report["ok"] else "invalid"
    (output_dir / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if not validation_report["ok"]:
        raise SystemExit(
            "corpus_release_v0_3 was built but failed validation. "
            f"See {repo_relative_path(output_dir / 'validation_report.json')}."
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--unified-dir",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "unified_release_v0_2",
    )
    parser.add_argument(
        "--sagaing-dir",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "sagaing_v0_1",
    )
    parser.add_argument(
        "--editorial-overrides",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_editorial_overrides.tsv",
    )
    parser.add_argument(
        "--release-policy",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_release_policy.tsv",
    )
    parser.add_argument(
        "--exception-review",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "inventory" / "recently_found_exception_review.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "corpus_release_v0_3",
    )
    args = parser.parse_args()

    manifest = build_corpus_release(
        unified_dir=args.unified_dir,
        sagaing_dir=args.sagaing_dir,
        overrides_file=args.editorial_overrides,
        release_policy_file=args.release_policy,
        exception_review_file=args.exception_review,
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
