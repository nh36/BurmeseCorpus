# Copilot Instructions

## Tooling

- The repository now uses small Python scripts with no third-party dependency layer or build system.
- Full extraction/audit/validation run:
  - `python3 scripts/extract_structured_corpus.py`
  - `python3 scripts/parse_recently_found.py`
  - `python3 scripts/parse_recently_found_records.py`
  - `python3 scripts/audit_inventory.py`
  - `python3 scripts/parse_sagaing.py`
  - `python3 scripts/merge_unified_release.py`
  - `python3 scripts/build_corpus_release.py`
  - `python3 scripts/extract_bibliography.py`
  - `python3 scripts/triage_bibliography.py`
  - `python3 scripts/validate_bibliography_triage.py`
  - `python3 scripts/extract_places.py`
  - `python3 scripts/init_translation_scaffold.py`
  - `python3 scripts/validate_corpus.py`
- Full test suite: `python3 -m unittest tests.test_parsers tests.test_recently_found_overrides tests.test_merge_unified_release tests.test_corpus_release tests.test_bibliography_triage`
- Single test: `python3 -m unittest tests.test_parsers.RecentlyFoundParserTests.test_recently_found_parser_finds_entries_and_pages`
- There is still no dedicated lint configuration checked in.

## Repository architecture

- The repository is organized around three Zenodo deposits, each kept in a top-level directory named after the deposit ID:
  - `4321314/` is the structured corpus release and the main working source.
  - `1302525/` is Thein Tun's *Recently Found Burmese Inscriptions* source deposit.
  - `1203709/` is the Sagaing-region newly found inscriptions source deposit.
- The active derived-data workflow now lives under:
  - `data/extracted/structured_corpus_current/` for parsed JSONL and inventory extracted from the OBI ZIP volumes.
  - `data/extracted/supplementary_1302525/` for parsed Recently Found source-entry inventory plus full inscription/line JSONL aligned to volume 7 canonical IDs where possible.
  - `data/extracted/supplementary_1203709/` for parsed Sagaing inscription records, line records, and corpus-style per-record text files.
  - `data/working/inventory/` for the volume 7/source crosswalk and audit summaries.
  - `data/working/bibliography/`, `data/working/places/`, and `data/working/translations/` for normalization scaffolds and authority candidates.
  - `data/release/sagaing_v0_1/` for the validated Sagaing release candidate.
  - `data/release/unified_release_v0_1/` for the first merged structured-plus-1302525 release candidate.
  - `data/release/unified_release_v0_2/` for the override-aware merged release candidate with explicit editorial relations.
  - `data/release/corpus_release_v0_3/` for the main whole-corpus release candidate, combining override-aware OBI plus Sagaing with manifest, source registry, validation report, and SQLite export.
- `obi_next_phase_project_init.md` is the project brief for the next phase. It describes the intended future normalized layout (`data/raw`, `data/extracted`, `data/working`, `data/release`) and the workflow expectations for derived data. Treat that layout as the target state, not the current on-disk structure.
- `scripts/` contains the current repository workflow:
  - `extract_structured_corpus.py` parses the structured OBI ZIP files into JSONL plus inventory TSV.
  - `parse_recently_found.py` segments the 1302525 source into source-entry inventory records.
  - `parse_recently_found_records.py` turns the 1302525 source into inscription/line JSONL and resolves canonical volume 7 IDs when clear matches exist.
  - `audit_inventory.py` compares the parsed source inventory against volume 7, optionally applies `data/working/inventory/recently_found_editorial_overrides.tsv`, and writes the crosswalk summary with review decisions.
  - `review_recently_found_exceptions.py` creates an exploratory case file for the remaining 1302525 versus volume 7 exception cases without changing parser or merge logic.
  - `parse_sagaing.py` converts the Sagaing source into per-record JSONL plus corpus-style text files and writes the `sagaing_v0_1` release candidate.
  - `merge_unified_release.py` now defaults to `data/release/unified_release_v0_2/`, reads `data/working/inventory/recently_found_release_policy.tsv`, suppresses duplicate-like source-only emission where policy says `annotate_target_only`, and writes `editorial_relations.jsonl`.
  - `build_corpus_release.py` assembles `data/release/corpus_release_v0_3/` from `unified_release_v0_2` and `sagaing_v0_1`, writes the release manifest, source registry, release notes, validation report, and derived SQLite export.
  - `extract_bibliography.py` now defaults to `data/release/corpus_release_v0_3/inscriptions.jsonl`, writes the raw-reference working files, and reports reference coverage by source.
  - `triage_bibliography.py` groups raw reference fragments into conservative reference families, writes provisional bibliographic work candidates, and produces `bibliography_triage_report.json`.
  - `validate_bibliography_triage.py` validates the bibliography triage files and their family/work candidate linkage.
  - `extract_places.py` and `init_translation_scaffold.py` now default to `data/release/corpus_release_v0_3/inscriptions.jsonl` and initialize the downstream working layers under `data/working/`.
  - `validate_corpus.py` checks generated JSONL datasets for ID, shape, linkage, source-registry, manifest, SQLite-export, and editorial-relation errors, including full release validation for `corpus_release_v0_3`.
- `schemas/` defines the first release contracts for `inscription`, `line`, `bibliography`, `translation`, and `place`, and `docs/data_model.md` describes how those records fit together.
- `4321314/OBI_Corpus_Vol1.zip` through `4321314/OBI_Corpus_Vol7.zip` are the canonical structured corpus archives. Each archive contains one `.txt` file per inscription face or text unit, with filenames such as `OBI_Vol1_No100__ob_p167.txt` and `OBI_Vol7_No10b__re_p28.txt`.
- Structured corpus `.txt` files use a fixed record shape with uppercase metadata headers such as `OBI CORPUS REF`, `INFORMATION SOURCE`, `INSCRIPTION NUMBER`, `FACE`, `INSCRIPTION`, and `FULL TRANSLITERATION`. Inside `INSCRIPTION`, numbered Burmese source lines are interleaved with `¤` transliteration lines, and page boundaries can appear as `<pg>` markers.
- `4321314/OBI_Translit_System.tsv` is the repository's transliteration lookup table. If you add parsing, normalization, or validation logic, keep it aligned with this table instead of creating a second transliteration mapping.
- `4321314/OBI_Corpus_Source_Material.zip` contains the underlying ODT source files for the structured corpus volumes and the recently found inscriptions source. Use it for provenance checks and re-extraction work, not as a replacement for the structured `.txt` corpus.
- The two supplementary deposits are not yet in the structured corpus format:
  - `1302525/Recently Found Burmese Inscriptiosn text.txt` is a long machine-readable source text that still needs segmentation and matching against volume 7.
  - `1203709/စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.txt` is a machine-readable source with repeating Burmese metadata blocks, line-numbered transcription, a continuous transcription block, and `မှတ်ချက်` notes.

## Key conventions

- Treat the top-level deposit directories and their PDFs, ODTs, TXT files, and ZIP archives as raw source material. New work should produce derived outputs alongside them or in a new derived-data layout; do not overwrite or silently normalize the original sources in place.
- `data/raw/` is the target immutable raw-data location, but the current scripts intentionally still read from the top-level Zenodo deposit directories so the original materials stay untouched.
- Do not assume `OBI_Corpus_Vol7.zip` is complete or authoritative. The project brief explicitly treats volume 7 as likely derived from the `1302525/` source and requires a coverage audit for matches, gaps, duplicates, and face splits before relying on it.
- Treat `data/working/inventory/recently_found_to_vol7_summary.json` as the current authority for the operational audit. With the override layer enabled, the current validated result is: 28 straightforward matches, 20 split-face matches, and 3 editorial overrides (`12`, `21`, `37`).
- Treat `data/working/inventory/recently_found_editorial_overrides.tsv` as the manual editorial judgment layer for the audit only. It currently records `12` and `37` as embedded in the previous volume 7 records and `21` as a title-variant/same-record case. Merge behavior is intentionally unchanged.
- Treat `data/working/inventory/recently_found_release_policy.tsv` as the release-policy layer, separate from the audit override file. It currently suppresses standalone canonical emission for embedded entries `12` and `37`, while preserving them as editorial relations, and marks `21` as a title-variant relation on the structured target record.
- Treat `data/working/inventory/recently_found_exception_review.{json,tsv}` as the exploratory evidence layer behind those overrides.
- Treat `data/release/unified_release_v0_2/` as the current default unified release. In this release, embedded Recently Found entries are represented through `editorial_relations.jsonl` plus compact `editorial_relation_ids` on target inscriptions rather than as duplicate canonical records.
- Treat `data/release/corpus_release_v0_3/` as the stable Phase 1 whole-corpus release baseline. JSONL files remain authoritative; `corpus_release.sqlite` is a derived convenience export. Sagaing is included as supplementary structured data with `sagaing-` identifiers retained and no implied reconciliation to OBI numbering.
- Avoid release-layer redesign unless the user explicitly asks for it. New work should normally build on `corpus_release_v0_3` rather than introducing another release layout.
- Phase 2 has begun with bibliography/source authority triage under `data/working/bibliography/`. This triage layer is for reviewability, not final bibliography normalization.
- Phase 2 should continue with bibliography/source authority work and the related authority tables for places, dates, and names.
- Translation generation and public interface work should wait until the authority layers are substantially more stable.
- Translation is a new layer, not a correction pass over the current corpus. The structured `.txt` entries include inscription text and transliteration fields but no `TRANSLATION:` field, so any translation workflow should preserve the existing transcription/transliteration data and record provenance separately.
- Preserve exact source strings and provenance when transforming data. The project brief distinguishes diplomatic transcription, normalized forms, transliteration, translation, and editorial notes; future scripts should keep those layers separate instead of collapsing them into one cleaned text field.
- Keep generated IDs stable and collision-safe. `record_id` and `line_id` are the join keys across extracted and release datasets; repeated line numbers or duplicated structured keys are handled with suffixes rather than by altering source content.
- For `1302525`, prefer the parsed source record IDs (`rfi-z1302525-...`) for source-native outputs, but keep `canonical_record_id` aligned to the structured volume 7 record ID whenever the audit can resolve a match.
- Expect source-specific parsing rules rather than one parser for every file:
  - structured corpus records use English uppercase metadata keys and face/page-oriented filenames;
  - the Sagaing text uses Burmese metadata labels and mixed line-level plus continuous transcription;
  - the Recently Found Inscriptions text is closer to a monolithic source edition and needs segmentation, inferred headings, suffix-aware numbering, and explicit review of volume 7 mismatches before it can be treated as release-ready.
