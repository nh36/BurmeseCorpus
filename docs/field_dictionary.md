# Field dictionary

This dictionary covers the main release-level fields used in `corpus_release_v0_3/`.

## Inscription and line identifiers

| Field | Meaning |
| --- | --- |
| `record_id` | Stable inscription-level identifier. Examples include `obi-...` for structured OBI and `sagaing-...` for Sagaing. |
| `line_id` | Stable line-level identifier, usually derived from `record_id` plus a line suffix. |

## Source and release tracking

| Field | Meaning |
| --- | --- |
| `source_deposit` | Source-layer identifier such as `zenodo_4321314`, `zenodo_1302525`, or `zenodo_1203709`. |
| `source_layer` | Release-layer classification for an inscription row. Current values: `structured_obi`, `sagaing_supplementary`, and `recently_found_aligned` when a Recently Found-aligned row is emitted as a standalone inscription record. |
| `release_status` | Release-layer status for an inscription row. Current values: `canonical`, `supplementary`, `editorial_relation_target`. |
| `source_volume` | Source volume identifier when the source is volume-based, such as OBI volume numbers. |
| `source_inscription_number` | Source-native inscription number string. |
| `source_page` | Source page or page anchor carried from the parsed source. |
| `face` | Face or text-unit marker such as `ob`, `re`, or `tx` when present. |

## Core descriptive fields

| Field | Meaning |
| --- | --- |
| `title_original` | Source-language title or heading string as currently carried into the release. |
| `date_original` | Date string exactly as parsed from the source or structured release. |
| `date_normalized` | Normalized date value when the current parser or release layer can express one. |
| `place_of_origin_original` | Raw place-of-origin string from the source or structured release. |
| `place_id` | Working normalized place identifier when available. |
| `references_original` | Raw bibliography/reference string from the release input. |
| `source_file` | Repo-relative file or archive member used as the immediate parse source. |
| `information_source` | Source-specific provenance field carried from the structured corpus where present. |
| `provenance` | Structured provenance object describing how the record entered the release and which script built it. |

## Editorial relation linkage

| Field | Meaning |
| --- | --- |
| `editorial_relation_ids` | Compact list of relation identifiers attached to a target inscription record. Full relation metadata lives in `editorial_relations.jsonl`. |
| `relation_id` | Stable identifier for an editorial relation row. |
| `relation_type` | Current relation type. Values in use: `embedded_in_previous_vol7_record`, `title_variant_same_record`. |
| `target_record_id` | Canonical inscription record referenced by the editorial relation. |
| `source_record_id` | Source-side record identifier behind the editorial relation, usually a `rfi-z1302525-...` record. |
| `release_action` | Release-policy action attached to an editorial relation. Current values: `annotate_target_only`, `annotate_target`. |
| `line_action` | Line-level release-policy action attached to an editorial relation. Current values: `do_not_emit_duplicate_source_lines`, `use_structured_lines`. |
| `confidence` | Editorial confidence label stored in the relation or policy layer. Current values in the tracked overrides are currently `high`. |
| `rationale` | Human-readable explanation for why the relation or policy exists. |

## Controlled-value notes

### `source_layer`

- `structured_obi` — structured OBI inscription carried into the release as part of the canonical base.
- `sagaing_supplementary` — Sagaing inscription carried into the release as supplementary structured data.
- `recently_found_aligned` — standalone Recently Found-aligned inscription row when one is emitted as a release record. This value is retained by the release builder even though the current `corpus_release_v0_3` does not contain independent Recently Found inscription rows.

### `release_status`

- `canonical` — canonical inscription row in the current release.
- `supplementary` — supplementary inscription row included without claiming canonical OBI equivalence.
- `editorial_relation_target` — canonical inscription row that is the target of one or more editorial relations.

### `relation_type`

- `embedded_in_previous_vol7_record` — source entry appears embedded within an earlier structured volume 7 record.
- `title_variant_same_record` — source entry and structured target refer to the same inscription but preserve differing title forms.

### `release_action`

- `annotate_target_only` — preserve the relationship on the target inscription without emitting a duplicate standalone inscription row.
- `annotate_target` — preserve the relationship on the target inscription while keeping the structured target as the active inscription row.

### `line_action`

- `do_not_emit_duplicate_source_lines` — do not emit source lines as duplicate canonical release lines.
- `use_structured_lines` — use the structured target lines rather than emitting a separate source-line copy.
