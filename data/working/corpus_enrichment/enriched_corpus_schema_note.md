# Enriched corpus schema note (minimal SIP-first design)

## Current `inscriptions.jsonl` schema (as implemented)

The current `data/release/corpus_release_v0_3/inscriptions.jsonl` records store inscription-level metadata and full transliteration, with line-by-line content in `lines.jsonl`.

Key fields in current inscription records:

- identity and source: `record_id`, `source_deposit`, `source_volume`, `source_inscription_number`, `source_page`, `source_file`
- title and language: `title_original`, `title_transliteration`, `language_original`
- inscription transcription at inscription level: `full_transliteration`
- bibliography/citation string: `references_original`
- notes: `notes_original`
- provenance: `provenance` object
- release/source status fields such as `source_layer`, `release_status`, `merge_status`

The current schema has no structured inscription-level source-witness array and no structured translation array/status field.

## Minimal enrichment fields to add on inscription records

### 1. `source_text_witnesses`

Array of witness objects for source editions that preserve/quote inscription text.

Per witness object (minimal required):

- `source_key`
- `source_bibliographic_label`
- `source_locator`
- `witness_text_raw`
- `witness_text_cleaned`
- `witness_status`
- `comparison_status`
- `notes`

For SIP-derived witnesses, include `sip_inscription_unit_id` for direct provenance back-linking.

### 2. `bibliographic_crossrefs`

Array of structured cross-reference objects derived from the IOB plate index and related citation targets.

Per cross-reference object (minimal required):

- `source_key`
- `source_label`
- `source_locator`
- `source_role`
- `status`
- `basis`

Examples include:

- `lucePeMaungTinInscriptionsOfBurma` with `source_role = cross_reference_or_plate_witness`
- `duroiselle1921list` with `source_role = catalogue_or_list`
- `ppaCatalogue` with `source_role = source_text_or_edition_candidate`
- `tnInscriptionsPaganPinyaAva` with `source_role = translation_candidate`

### 3. `translation_status`

Record-level translation availability status:

- `no_translation_known`
- `translation_source_missing`
- `translation_available_unintegrated`
- `translation_integrated`
- `translation_needs_review`

### 4. `translations`

Whole-inscription translation array. The first working slice is already populated for the Shwegugyi record:

- `language`
- `text`
- `source_key`
- `source_bibliographic_label`
- `source_locator`
- `translation_status` (`published_translation`, `draft_translation`, `machine_assisted_draft`, `needs_translation_review`)
- `notes`

### 5. `translation_source_candidates`

Optional array used when translation evidence is cited but source is missing.

- `source_key`
- `source_bibliographic_label`
- `source_locator_hint`
- `status` (currently `missing_high_value_source`)
- `basis`

### 6. `enrichment_status` and `enrichment_notes`

Lightweight record-level enrichment marker and note:

- `enrichment_status` values used now: `baseline_no_enrichment`, `enriched_with_bibliographic_crossrefs`, `enriched_with_bibliographic_crossrefs_and_candidates`, `enriched_with_sip_witnesses`, `enriched_with_sip_and_crossrefs`, `enriched_with_sip_and_candidates`, `enriched_with_translation`
- `enrichment_notes` is a short provenance note for enrichment decisions

## SIP-first, then cross-reference enrichment

- Build `inscriptions_enriched_candidate.jsonl` from `corpus_release_v0_3/inscriptions.jsonl`.
- Enrich records linked by `sip_accepted_witness_units.tsv` with `source_text_witnesses`.
- Enrich records linked by `inscriptions_of_burma_cross_reference_index.tsv` with `bibliographic_crossrefs`.
- Enrich records linked to a reviewed local translation unit with `translations` and `translation_status = translation_integrated`.
- Preserve all existing corpus fields exactly (no overwrite of existing transcription or metadata fields).
- Leave unlinked records unchanged.

## Translation-forward compatibility (TN path)

When TN witness text is acquired and extracted:

1. Keep existing SIP `source_text_witnesses` entries.
2. Add TN translation entries directly to `translations`, alongside any existing Shwegugyi-style integrated translations.
3. Update `translation_status` to `translation_integrated` or `translation_needs_review`.
4. Remove/resolve corresponding `translation_source_candidates` rows as they become integrated.

This avoids schema redesign: TN fits directly into the proposed translation fields.
