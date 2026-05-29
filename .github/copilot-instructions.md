# Copilot Instructions

## Tooling

- The repository now uses small Python scripts with no third-party dependency layer or build system.
- Full extraction/audit/validation run:
  - `python3 scripts/extract_structured_corpus.py`
  - `python3 scripts/parse_recently_found.py`
  - `python3 scripts/audit_inventory.py`
  - `python3 scripts/parse_sagaing.py`
  - `python3 scripts/validate_corpus.py`
- Full test suite: `python3 -m unittest tests.test_parsers`
- Single test: `python3 -m unittest tests.test_parsers.RecentlyFoundParserTests.test_recently_found_parser_finds_entries_and_pages`
- There is still no dedicated lint configuration checked in.

## Repository architecture

- The repository is organized around three Zenodo deposits, each kept in a top-level directory named after the deposit ID:
  - `4321314/` is the structured corpus release and the main working source.
  - `1302525/` is Thein Tun's *Recently Found Burmese Inscriptions* source deposit.
  - `1203709/` is the Sagaing-region newly found inscriptions source deposit.
- The active derived-data workflow now lives under:
  - `data/extracted/structured_corpus_current/` for parsed JSONL and inventory extracted from the OBI ZIP volumes.
  - `data/extracted/supplementary_1302525/` for parsed source-entry inventory from the Recently Found source text.
  - `data/extracted/supplementary_1203709/` for parsed Sagaing inscription records, line records, and corpus-style per-record text files.
  - `data/working/inventory/` for the volume 7/source crosswalk and audit summaries.
  - `data/release/sagaing_v0_1/` for the validated Sagaing release candidate.
- `obi_next_phase_project_init.md` is the project brief for the next phase. It describes the intended future normalized layout (`data/raw`, `data/extracted`, `data/working`, `data/release`) and the workflow expectations for derived data. Treat that layout as the target state, not the current on-disk structure.
- `scripts/` contains the current repository workflow:
  - `extract_structured_corpus.py` parses the structured OBI ZIP files into JSONL plus inventory TSV.
  - `parse_recently_found.py` segments the 1302525 source into source-entry inventory records.
  - `audit_inventory.py` compares the parsed source inventory against volume 7 and writes the crosswalk summary.
  - `parse_sagaing.py` converts the Sagaing source into per-record JSONL plus corpus-style text files and writes the `sagaing_v0_1` release candidate.
  - `validate_corpus.py` checks generated JSONL datasets for ID, shape, and linkage errors.
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
- Treat `data/working/inventory/recently_found_to_vol7_summary.json` as the current authority for that audit. It presently reports 25 direct matches, 20 face-split matches, 1 source entry missing from volume 7, and 4 extra volume 7 entries with no source match.
- Translation is a new layer, not a correction pass over the current corpus. The structured `.txt` entries include inscription text and transliteration fields but no `TRANSLATION:` field, so any translation workflow should preserve the existing transcription/transliteration data and record provenance separately.
- Preserve exact source strings and provenance when transforming data. The project brief distinguishes diplomatic transcription, normalized forms, transliteration, translation, and editorial notes; future scripts should keep those layers separate instead of collapsing them into one cleaned text field.
- Keep generated IDs stable and collision-safe. `record_id` and `line_id` are the join keys across extracted and release datasets; repeated line numbers or duplicated structured keys are handled with suffixes rather than by altering source content.
- Expect source-specific parsing rules rather than one parser for every file:
  - structured corpus records use English uppercase metadata keys and face/page-oriented filenames;
  - the Sagaing text uses Burmese metadata labels and mixed line-level plus continuous transcription;
  - the Recently Found Inscriptions text is closer to a monolithic source edition and needs segmentation before it can be compared with structured records.
