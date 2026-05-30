# Phase 2 local bibliography source harvest

The main route to improving the BibTeX authority layer is now **local-source evidence**, not broader fuzzy matching over raw corpus bibliography strings.

This workflow is designed to harvest likely bibliography-bearing local files, cache approved copies in a gitignored project area, extract structured evidence from Frasch materials, and feed that evidence back into `data/working/bibliography/bibtex_authority/`.

It does **not** modify `data/release/corpus_release_v0_3/`.

## Configure local roots

Set whichever of these roots are available on the local machine:

```bash
export OBI_LIBRARY_ROOT="/Volumes/ExternalDrive/Library"
export OBI_AUTHOR_ALPHA_ROOT="/Volumes/ExternalDrive/Authors alphabetical"
export OBI_LOCAL_BIB_ROOT="$HOME/Downloads"
```

- `OBI_LIBRARY_ROOT`: broad Burma/resource library root.
- `OBI_AUTHOR_ALPHA_ROOT`: author-alphabetical external-drive folder.
- `OBI_LOCAL_BIB_ROOT`: optional local bibliography/input folder such as `Downloads` or a staging directory containing `asia 2.bib`.

If one or more variables are unset, the harvester reports that clearly and continues with the available roots.

## What gets copied and what stays local-only

The harvester may copy likely relevant local files into:

- `data/local/bibliography_sources/`

That cache is gitignored. The copied local PDFs, Word files, scans, and similar source files should normally **not** be committed.

Commit the metadata instead:

- `data/working/bibliography/local_sources/frasch_source_candidates.tsv`
- `data/working/bibliography/local_sources/high_priority_local_candidates.tsv`
- `data/working/bibliography/local_sources/local_file_manifest.tsv`
- `data/working/bibliography/local_sources/local_source_harvest_report.json`
- `data/working/bibliography/local_sources/frasch_reference_entries.tsv`
- `data/working/bibliography/local_sources/frasch_reference_quality.tsv`
- `data/working/bibliography/local_sources/frasch_bibliography.bib`
- `data/working/bibliography/local_sources/frasch_extraction_report.json`
- `data/working/bibliography/local_sources/frasch_extraction_qa_report.json`
- `data/working/bibliography/local_sources/frasch_bagan_epig_database_abbreviations.tsv`
- `data/working/bibliography/local_sources/frasch_bagan_epig_database_bibliography.tsv`
- `data/working/bibliography/local_sources/frasch_bagan_epig_database_report.json`
- `data/working/bibliography/local_sources/corpus_documentation_candidates.tsv`
- `data/working/bibliography/local_sources/acronym_definition_candidates.tsv`
- `data/working/bibliography/local_sources/acronym_definition_report.json`
- `data/working/bibliography/local_sources/frasch_stadt_staat_acronyms.tsv`
- `data/working/bibliography/local_sources/bagan_epig_database_acronym_contexts.tsv`

## Practical run order

```bash
python3 scripts/harvest_local_bibliography_sources.py --mode frasch
python3 scripts/extract_frasch_bibliography.py
python3 scripts/harvest_local_bibliography_sources.py --mode high-priority
python3 scripts/match_local_bibliography_sources.py
python3 scripts/extract_bibliography_acronyms.py
python3 scripts/build_bibtex_authority.py
python3 scripts/validate_bibtex_authority.py
python3 -m unittest tests.test_bibtex_authority
```

## Frasch-first search

Run:

```bash
python3 scripts/harvest_local_bibliography_sources.py --mode frasch
```

The script searches configured roots case-insensitively for `Frasch`, `Frosch`, `Tilman`, and `Tillman`, then writes:

- `frasch_source_candidates.tsv`
- `local_file_manifest.tsv`
- `local_source_harvest_report.json`

The priority is bibliography-bearing files such as `.doc`, `.docx`, `.rtf`, `.pdf`, `.txt`, `.bib`, `.ris`, `.enl`, and `.xml`.

## Luce and other high-priority searches

Run:

```bash
python3 scripts/harvest_local_bibliography_sources.py --mode high-priority
python3 scripts/match_local_bibliography_sources.py
```

The high-priority mode searches for Luce and other frequently cited Burma-related names and abbreviations, then records candidate files in:

- `high_priority_local_candidates.tsv`
- `local_bibliography_match_report.json`
- `source_library_manifest.tsv`

This is still a reviewable evidence layer. It is intended to guide authority confirmation, not to bulk-ingest entire folders.

## Frasch extraction

Run:

```bash
python3 scripts/extract_frasch_bibliography.py
```

The extractor reads copied Frasch files from the local cache and writes:

- `frasch_extracted_text.txt`
- `frasch_reference_entries.tsv`
- `frasch_reference_quality.tsv`
- `frasch_bibliography.bib`
- `frasch_extraction_report.json`
- `frasch_extraction_qa_report.json`

### Bibliography evidence vs body or catalogue text

The Frasch QA layer now separates several kinds of extracted material:

- `bibliographic_reference`: short citation-like rows with usable author/title/year/publication signals;
- `catalogue_note`: shorthand source locators such as `List 90`, `Pl. II`, `UB 1`, `MP 2`, or similar catalogue-style references;
- `body_text`: long descriptive prose, transcription fragments, or other non-bibliographic passages;
- `unclear`: rows kept for review but not trusted as authority evidence.

The important review file is `frasch_reference_quality.tsv`. It records the row type, signal flags, confidence, and `recommended_action`. Long prose should stay in the QA TSV and reports, not in BibTeX fields.

### Reviewing `frasch_reference_quality.tsv`

Use this file to answer two different questions:

1. is this row safe to use as bibliography evidence?
2. if not, is it still useful as catalogue/source-family evidence?

In practice:

- rows marked `use_for_bibliography` can feed concise authority evidence directly;
- rows marked `use_for_catalogue_evidence` can still support abbreviation/source-family review;
- rows marked `manual_review` should stay in the work queue until a human confirms them;
- rows marked `exclude_from_bibtex` should not feed the BibTeX layer.

Entries over a few hundred characters should almost always stay in the QA layer rather than in `.bib`.

### Bagan Epig Database special handling

`Bagan Epig Database.doc` now has a dedicated extraction path because it is the best local witness for Frasch abbreviation usage.

Review:

- `frasch_bagan_epig_database_abbreviations.tsv` for explicit abbreviation definitions and source hints;
- `frasch_bagan_epig_database_abbreviations.tsv` also records `evidence_type`, distinguishing `explicit_definition`, `contextual_usage`, `inferred_from_repeated_pattern`, and `manual_review_needed`;
- `frasch_bagan_epig_database_bibliography.tsv` for full bibliography-style rows extracted from the same document;
- `frasch_bagan_epig_database_report.json` for counts and parse warnings.

This material is especially important for abbreviation families such as `ARASI`, `A`, `B`, `UB`, `MP`, `Luce D`, and `Luce J`.

`frasch_reference_entries.tsv` is the broader evidence layer. `frasch_bibliography.bib` is intentionally conservative and should contain only entries that parsed with reasonable confidence.

## Acronym resolution workflow

Run:

```bash
python3 scripts/extract_bibliography_acronyms.py
```

This script inventories likely corpus documentation and Frasch witnesses, then separates:

- **definition evidence** in `acronym_definition_candidates.tsv`;
- **Frasch-specific acronym contexts** in `frasch_stadt_staat_acronyms.tsv`;
- **Bagan Epig Database usage contexts** in `bagan_epig_database_acronym_contexts.tsv`;
- and the search inventory/report in `corpus_documentation_candidates.tsv` and `acronym_definition_report.json`.

The rule is conservative: contextual usage can stabilize a source family, but it should **not** be promoted to a confirmed acronym expansion. The next goal is a correct crosswalk from raw references to source families, locators, and only then to confirmed works.

## How local evidence flows into BibTeX authority

`scripts/build_bibtex_authority.py` now treats harvested local evidence as higher-value input than generic machine stubs.

The immediate target is now a correct authority crosswalk, not maximum BibTeX output. Local evidence can support several distinct outcomes:

- a **source-family authority** row in `source_family_authority.tsv`;
- a **series-level** authority such as `JBRS`, `JRAS`, `RDASB`, `BBHC`, or `EB`;
- a **confirmed or provisional work** in `bibtex_authority.tsv`;
- or a **needs_human_review** placeholder when the abbreviation is still real but not yet bibliographically pinned down.

Important authority statuses:

- `confirmed_local_source`
- `provisional_local_source`

Important `source_of_authority` values:

- `frasch_bibliography`
- `frasch_word_document`
- `local_luce_folder`
- `local_burma_folder`

Authority rows backed by local evidence should record:

- `matched_local_source_id`
- `matched_local_source_file`
- `matched_local_reference`
- `match_confidence`
- `match_reason`

The BibTeX layer now keeps those fields short and citation-like. Longer evidence stays in:

- `data/working/bibliography/bibtex_authority/bibtex_authority_evidence.tsv`

That evidence table stores a short excerpt plus a stable evidence ID and hash, while the full raw text remains in the local-source TSV extracts.

For source-family mappings, the same evidence should also support:

- `source_family_authority.tsv`
- `raw_reference_to_bibtex.tsv`
- `high_frequency_resolution_plan.tsv`

This is how rows like `List 90`, `Pl. II 198`, `PPA, p. 55`, `RDASB 1971`, `UB 1, p. 297`, and `MP 1, p. 81` stay modeled as source-family or series references with locators instead of turning into meaningless machine-stub works.

## Reviewing unresolved high-frequency families

After rebuilding the authority layer, review:

- `data/working/bibliography/bibtex_authority/high_frequency_unresolved.tsv`
- `data/working/bibliography/bibtex_authority/high_frequency_resolution_plan.tsv`

`high_frequency_unresolved.tsv` stays sorted by descending `occurrence_count` so the remaining unresolved queue is explicit.

`high_frequency_resolution_plan.tsv` is the working review sheet for the top families first. Use it to:

- confirm which high-frequency families already map to a shared authority;
- confirm whether that mapping is source-family, series-level, work-level, or still unresolved;
- see which ones have only a suspected work/source and still need human confirmation;
- record next actions before spending time on low-frequency tail items.
