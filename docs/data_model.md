# Initial release data model

The first release model uses JSONL so every derived dataset stays easy to diff, validate, and query before any TEI or database layer is introduced.

## Core release files

### `inscriptions.jsonl`

One record per inscription text unit or face. The current scripts populate this for:

- `data/extracted/structured_corpus_current/`
- `data/extracted/supplementary_1302525/`
- `data/extracted/supplementary_1203709/`
- `data/release/sagaing_v0_1/`
- `data/release/unified_release_v0_1/`
- `data/release/unified_release_v0_2/`

Key fields:

- `record_id`: stable ASCII identifier such as `obi-v07-n0010a-ob-p0026`, `rfi-z1302525-n0010a-ob-p0026`, or `sagaing-z1203709-b0003-ob-p0007`
- `canonical_record_id`: the structured-corpus-aligned identifier used when a supplementary source record maps onto an OBI canonical record
- source coordinates: `source_deposit`, `source_volume`, `source_inscription_number`, `source_page`
- text-unit metadata: `face`, `number_of_faces`, `title_original`, `title_transliteration`
- research metadata: `date_original`, `date_normalized`, `place_of_origin_original`, `current_location_original`, `donor_original`, `subject_original`
- provenance and source traceability: `source_file`, `reference_number_original`, `information_source`, `inscription_source_original`, `provenance`

Sagaing records also preserve:

- `source_section_marker`
- `continuous_text_original`
- `parse_warnings`

### `lines.jsonl`

One record per inscription line. Key fields:

- `record_id`
- `canonical_record_id`
- `line_id`
- `line_number_original`
- `line_number_arabic`
- `text_original`
- `transliteration`
- `page_break_before`
- `footnote_refs`
- `uncertain`

## Placeholder schemas for later layers

The repository now defines JSON schemas for:

- `bibliography`
- `translation`
- `place`

Those files establish the minimum field contracts for later bibliography and translation work without forcing that layer into the first parsed release. The current normalization scaffolds now write working files under:

- `data/working/bibliography/`
- `data/working/places/`
- `data/working/translations/`

## ID conventions

- Existing structured corpus records use `obi-v{volume}-{inscription-number}-{face}-{page}`.
- Recently Found parsed source records use `rfi-z1302525-{inscription-number}-{face}-{page}` and also carry `canonical_record_id` when they align to volume 7.
- Sagaing conversion records use `sagaing-z1203709-b{block}-{face}-{page}` until they are integrated into a unified corpus numbering scheme.
- Line IDs append `-lNNN` to the parent `record_id`.

## Validation boundary

`data/release/` is reserved for validated release candidates. The current release candidates are:

- `data/release/sagaing_v0_1/`
- `data/release/unified_release_v0_1/`
- `data/release/unified_release_v0_2/`

The unified releases currently have two distinct semantics:

- `data/release/unified_release_v0_1/` is the first merged release. It preserves structured records as canonical where they already exist and adds source-only Recently Found entries as independent canonical records when no structured match is present.
- `data/release/unified_release_v0_2/` is the override-aware release. It still preserves structured records as canonical, but uses `data/working/inventory/recently_found_release_policy.tsv` plus the editorial override audit to avoid emitting embedded Recently Found entries as duplicate canonical records.

`unified_release_v0_2/` adds a third release file:

- `editorial_relations.jsonl`

Each editorial relation preserves a conservative relationship between a Recently Found source entry and a structured target record without splitting or rewriting the canonical inscription. This is now used for:

- embedded-in-previous-record cases such as source entries `12` and `37`, which are preserved as editorial relations instead of standalone canonical inscription records;
- title-variant cases such as source entry `21`, which remain aligned to the structured record while preserving the alternate source title as editorial metadata rather than normalizing it away.

The target inscription rows in `unified_release_v0_2/inscriptions.jsonl` carry compact `editorial_relation_ids` annotations, while full relation metadata lives in `editorial_relations.jsonl`.

`scripts/validate_corpus.py` now checks:

- `data/extracted/structured_corpus_current/`
- `data/extracted/supplementary_1302525/`
- `data/extracted/supplementary_1203709/`
- `data/release/sagaing_v0_1/`
- `data/release/unified_release_v0_1/`
- `data/release/unified_release_v0_2/`
