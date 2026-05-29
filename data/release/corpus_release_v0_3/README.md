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
- Structured OBI contributes 1121 inscription rows and 23696 line rows.
- Recently Found contributes 3 editorial relations in this release and no separate canonical inscription rows.
- Sagaing contributes 31 supplementary inscription rows and retains `sagaing-` identifiers.
- This release does not yet contain completed translations or final bibliography/place authority data.
