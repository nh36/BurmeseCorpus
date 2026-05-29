# Corpus Release v0_3

Corpus release v0_3 is the first whole-corpus release candidate for this repository. It combines the override-aware unified OBI release with the parsed Sagaing release while preserving stable record identifiers, explicit provenance, and the existing editorial relations for the Recently Found / Volume 7 exceptions.

## What this release contains

- **Structured OBI base:** 1121 inscription records and 23696 lines carried forward from `data/release/unified_release_v0_2/`.
- **Sagaing supplementary layer:** 31 inscription records and 603 lines carried forward from `data/release/sagaing_v0_1/`, with existing `sagaing-` identifiers preserved.
- **Recently Found contribution:** 0 independent inscription records, 0 lines, and 3 editorial relations carried forward from `unified_release_v0_2`.

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
