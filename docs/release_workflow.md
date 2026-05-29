# Release workflow

## Phase 2 BibTeX authority addendum

After `corpus_release_v0_3` has been regenerated and the bibliography triage files exist, the BibTeX authority workflow continues with:

1. `python3 scripts/triage_bibliography.py`
2. `python3 scripts/validate_bibliography_triage.py`
3. `python3 scripts/import_external_bibtex.py --input-bibtex "$HOME/Downloads/asia 2.bib" --source-label "asia 2.bib" --output-dir data/working/bibliography/external_bibtex`
4. `python3 scripts/build_bibtex_authority.py`
5. `python3 scripts/validate_bibtex_authority.py`
6. `OBI_LIBRARY_ROOT=/path/to/local/library python3 scripts/match_local_bibliography_sources.py` *(optional local-library evidence step)*

These steps build working bibliography authority artifacts under `data/working/bibliography/`. They do **not** modify `data/release/corpus_release_v0_3/`.

This repository builds the current release layer through a small set of Python scripts. The workflow is deliberately linear at the release level even though some source-specific parsing steps are independent.

## Conceptual dependency order

1. **Structured OBI extraction** creates the canonical structured base.
2. **Recently Found parsing and audit** creates the supplementary source inventory, record/line extraction, audit crosswalk, and diagnostic review materials.
3. **Sagaing parsing** creates the supplementary Sagaing release candidate.
4. **Unified OBI release build** creates `unified_release_v0_2/` from the structured corpus plus the reviewed Recently Found policy layer.
5. **Whole-corpus release build** creates `corpus_release_v0_3/` from `unified_release_v0_2/` plus `sagaing_v0_1/`.
6. **Phase 2 bibliography triage** derives bibliography working files and conservative reference-family triage outputs from the whole-corpus release.
7. **Other post-release scaffolds** derive place and translation working files from the same release baseline.
8. **Validation** checks the extracted datasets, release datasets, release metadata, derived SQLite export, and bibliography triage layer.

## Command sequence

Run these commands from the repository root:

```bash
python3 scripts/extract_structured_corpus.py
python3 scripts/parse_recently_found.py
python3 scripts/parse_recently_found_records.py
python3 scripts/audit_inventory.py
python3 scripts/review_recently_found_exceptions.py
python3 scripts/parse_sagaing.py
python3 scripts/merge_unified_release.py
python3 scripts/build_corpus_release.py
python3 scripts/extract_bibliography.py
python3 scripts/triage_bibliography.py
python3 scripts/validate_bibliography_triage.py
python3 scripts/extract_places.py
python3 scripts/init_translation_scaffold.py
python3 scripts/validate_corpus.py
```

### Notes on order and optionality

- `review_recently_found_exceptions.py` is **diagnostic**, not a release-builder prerequisite in the narrow technical sense. It is still part of the documented workflow because the accepted override and release-policy files for entries `12`, `21`, and `37` are grounded in that review artifact.
- `parse_sagaing.py` is independent of the Recently Found audit path, but `build_corpus_release.py` needs its `sagaing_v0_1/` outputs, so it must run before the whole-corpus release is rebuilt.
- `extract_bibliography.py`, `triage_bibliography.py`, `validate_bibliography_triage.py`, `extract_places.py`, and `init_translation_scaffold.py` are **post-release working-layer steps**. They do not redefine `corpus_release_v0_3/`; they build Phase 2 authority scaffolds on top of that stable release baseline.

## What each script produces

| Step | Script | Main outputs |
| --- | --- | --- |
| 1 | `scripts/extract_structured_corpus.py` | `data/extracted/structured_corpus_current/inscriptions.jsonl`, `lines.jsonl`, inventory files |
| 2 | `scripts/parse_recently_found.py` | `data/extracted/supplementary_1302525/source_entries.jsonl` and related inventory outputs |
| 3 | `scripts/parse_recently_found_records.py` | `data/extracted/supplementary_1302525/inscriptions.jsonl`, `lines.jsonl` |
| 4 | `scripts/audit_inventory.py` | `data/working/inventory/recently_found_to_vol7_crosswalk.tsv`, `recently_found_to_vol7_summary.json` |
| 5 | `scripts/review_recently_found_exceptions.py` | `data/working/inventory/recently_found_exception_review.json`, `recently_found_exception_review.tsv` |
| 6 | `scripts/parse_sagaing.py` | `data/extracted/supplementary_1203709/`, `data/release/sagaing_v0_1/` |
| 7 | `scripts/merge_unified_release.py` | `data/release/unified_release_v0_2/inscriptions.jsonl`, `lines.jsonl`, `editorial_relations.jsonl`, `merge_report.json` |
| 8 | `scripts/build_corpus_release.py` | `data/release/corpus_release_v0_3/` including `sources.jsonl`, `release_manifest.json`, `release_notes.md`, `README.md`, `validation_report.json`, `corpus_release.sqlite` |
| 9 | `scripts/extract_bibliography.py` | `data/working/bibliography/` including `reference_coverage_by_source.tsv` |
| 10 | `scripts/triage_bibliography.py` | `data/working/bibliography/reference_families.tsv`, `reference_family_members.tsv`, `bibliographic_work_candidates.tsv`, `bibliography_triage_report.json` |
| 11 | `scripts/validate_bibliography_triage.py` | CLI validation of the bibliography triage layer |
| 12 | `scripts/extract_places.py` | `data/working/places/` |
| 13 | `scripts/init_translation_scaffold.py` | `data/working/translations/translation_targets.tsv` |
| 14 | `scripts/validate_corpus.py` | `data/working/qa/validation_report.json` |

## Authoritative vs derived files

### Authoritative release files

- `data/release/corpus_release_v0_3/inscriptions.jsonl`
- `data/release/corpus_release_v0_3/lines.jsonl`
- `data/release/corpus_release_v0_3/editorial_relations.jsonl`
- `data/release/corpus_release_v0_3/sources.jsonl`
- `data/release/corpus_release_v0_3/release_manifest.json`
- `data/release/corpus_release_v0_3/release_notes.md`
- `data/release/corpus_release_v0_3/README.md`

### Derived release files

- `data/release/corpus_release_v0_3/corpus_release.sqlite`
- `data/release/corpus_release_v0_3/validation_report.json`

### Working-layer files that inform the release but are not themselves release outputs

- `data/working/inventory/recently_found_editorial_overrides.tsv`
- `data/working/inventory/recently_found_release_policy.tsv`
- `data/working/inventory/recently_found_exception_review.json`

## What to check after regeneration

1. `python3 scripts/validate_corpus.py` returns `ok: true`.
2. `data/release/corpus_release_v0_3/release_manifest.json` still reports:
   - `total_inscription_count = 1152`
   - `total_line_count = 24299`
   - `editorial_relation_count = 3`
3. `data/release/corpus_release_v0_3/sources.jsonl` shows:
   - structured OBI inscription and line counts under `zenodo_4321314`
   - zero independent inscription rows but non-zero `editorial_relation_count` for `zenodo_1302525`
   - supplementary Sagaing counts under `zenodo_1203709`
4. `python3 scripts/validate_bibliography_triage.py` passes after bibliography triage outputs are regenerated.
5. `data/release/corpus_release_v0_3/README.md` and `release_notes.md` contain no absolute local machine paths.
6. `inscriptions.jsonl` and `lines.jsonl` remain the authoritative data; `corpus_release.sqlite` remains a derived convenience export.
