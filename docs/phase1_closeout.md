# Phase 1 closeout

## Phase 1 goal

Phase 1 was the release-foundation phase: parse the three Zenodo source layers, separate parser facts from editorial judgment and release policy, and produce a stable whole-corpus release candidate that later authority work can rely on.

## What is now stable

- the structured OBI extraction workflow;
- the Recently Found parsing, audit, override, and release-policy layers;
- the Sagaing supplementary parsing workflow;
- the release chain from `unified_release_v0_2/` to `corpus_release_v0_3/`;
- release-level metadata, validation, and the derived SQLite convenience export.

## Current release baseline

`data/release/corpus_release_v0_3/` is now the stable Phase 1 baseline.

- JSONL files remain authoritative;
- `corpus_release.sqlite` is derived;
- structured OBI remains the canonical base;
- Recently Found entries `12`, `21`, and `37` are represented conservatively through editorial relations;
- Sagaing remains supplementary and is not yet reconciled into OBI numbering.

## Known limitations

- bibliography normalization is still preliminary;
- place, date, and name authority layers are not yet stabilized;
- published translation discovery has not yet begun;
- Sagaing crosswalk work remains future work.

## What Phase 2 should begin with

1. bibliography/source authority work;
2. place, date, and name authority tables;
3. published translation discovery and ingestion;
4. only later, translation generation or public interface work.

## What should not be started yet

Do not redesign the release layer without an explicit reason. Do not begin translation generation, public website work, or interface-first work until the authority layers are materially more stable.
