# Phase 2 BibTeX authority layer

Phase 2 now has two linked bibliography layers:

1. **triage files** under `data/working/bibliography/`, which cluster raw reference strings conservatively;
2. **BibTeX authority files** under `data/working/bibliography/bibtex_authority/`, which turn confirmed or plausibly identified works into reusable BibTeX records.

This layer is still provisional, but it is no longer meant to depend mainly on fuzzy matching. The main route to improvement is now **evidence-backed local-source harvesting**, especially Frasch materials and other Burma bibliography folders. The layer is meant to separate **works**, **source abbreviations**, and **locators** so later bibliography authority review and published-translation discovery can proceed on cleaner data.

## Distinctions

- **Raw reference string**: the literal string extracted from a corpus record, such as `OBI 3, p. 2` or `Luce, Myanmar's Debt, JBRS 1932, p. 125`.
- **Locator**: the part of the raw string that points into a work or source family, such as `3, p. 2`, `90`, or `Pl. II 198`.
- **Reference family**: a conservative triage cluster of related raw strings, often based on an abbreviation, author/title pattern, or recurring source label.
- **Work candidate**: a provisional bibliographic candidate inferred from a family.
- **BibTeX authority record**: a reusable BibTeX entry in either `bibliography_authority.bib` or `bibliography_candidates.bib`.

Not every raw string should become its own BibTeX work. `OBI 3, p. 2`, `List 90`, and `Pl. II 198` are usually better treated as a source-family match plus a locator.

## External BibTeX import

`scripts/import_external_bibtex.py` imports `asia 2.bib` or another local BibTeX file reproducibly:

```bash
python3 scripts/import_external_bibtex.py \
  --input-bibtex "$HOME/Downloads/asia 2.bib" \
  --source-label "asia 2.bib" \
  --output-dir data/working/bibliography/external_bibtex
```

The script:

- copies the raw BibTeX file into the chosen output directory;
- records a SHA-256 checksum;
- parses entries conservatively and reports parse warnings instead of silently dropping malformed data;
- writes a flat entries TSV for downstream matching.

The copied `.bib` file is gitignored by default. Commit the import report and TSV metadata, not the raw local BibTeX copy, unless there is a clear reason and explicit approval to track it.

## Local-source harvest and matching

Use the local-source harvest workflow first:

```bash
export OBI_AUTHOR_ALPHA_ROOT="/path/to/Authors alphabetical"
export OBI_LIBRARY_ROOT="/path/to/Library"
export OBI_LOCAL_BIB_ROOT="$HOME/Downloads"

python3 scripts/harvest_local_bibliography_sources.py --mode frasch
python3 scripts/extract_frasch_bibliography.py
python3 scripts/harvest_local_bibliography_sources.py --mode high-priority
python3 scripts/match_local_bibliography_sources.py
```

This workflow:

- searches local roots for likely Frasch/Luce/Burma bibliography material;
- copies approved files into gitignored `data/local/bibliography_sources/`;
- commits manifests, checksums, extracted reference tables, and reports rather than the copied source files themselves;
- feeds Frasch-derived and other local evidence into the authority builder.

See `docs/phase2_local_source_harvest.md` for the full workflow and path conventions.

## Authority vs candidate BibTeX

- `bibliography_authority.bib` holds conservative authority entries supported by imported external BibTeX, Frasch/local-source evidence, repository-backed source identification, or strong manual/source-family seeds.
- `bibliography_candidates.bib` holds provisional stubs for unresolved families and weakly inferred candidates.

Every provisional or machine-generated candidate should carry an explicit note that it still requires human review.

Rows backed by local evidence should prefer:

- `confirmed_local_source` when the local match is strong;
- `provisional_local_source` when the evidence is promising but still uncertain.

## Keep BibTeX concise; keep raw evidence elsewhere

The authority layer now separates **authority metadata** from **full evidence text**.

- `bibliography_authority.bib` and `bibliography_candidates.bib` should contain short citation-like fields only.
- Long Frasch passages, catalogue notes, or descriptive prose should stay in TSV/JSON evidence files.
- `matchedlocalreference`, `evidence`, and `note` must stay short enough to be readable as citation support, not as document excerpts.

The main supporting table is:

- `data/working/bibliography/bibtex_authority/bibtex_authority_evidence.tsv`

Each row links a `bibtex_key` to a short excerpt, evidence ID, source file, source ref ID, confidence, and a hash of the full evidence context. The full long-form text remains in the local-source extraction layer.

## Reviewing source abbreviations

`data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv` is now both a seed table and a review worksheet.

Important review columns:

- `evidence_source_file`
- `evidence_ref_id`
- `evidence_quote_short`
- `confidence`
- `needs_human_review`

Use these rows to confirm or keep provisional expansions for abbreviations such as `A`, `B`, `MP`, `UB`, `PPA`, `TN`, `IPPA`, `UEM`, `SIP`, `MM`, `OR`, `Pl.`, `ARASI`, `Luce D`, and `Luce J`.

If an expansion is still uncertain, keep the seed row but leave `needs_human_review = true`.

## Reviewing high-frequency families first

Two files now work together:

- `high_frequency_unresolved.tsv`
- `high_frequency_resolution_plan.tsv`

The first is the remaining unresolved queue, sorted by descending `occurrence_count`.

The second is the explicit review sheet for the top families first. It records:

- the suspected work or source;
- the shared or candidate BibTeX key;
- the evidence source and confidence;
- the next action required before final confirmation.

This is the main mechanism for improving the authority layer without creating more machine stubs for low-value tail cases.

## Why this matters for translation discovery

Published translations are often tied to identifiable works, not to raw locator strings. By separating:

- journal or catalogue families,
- specific identified works,
- and locators within those works,

the BibTeX authority layer makes it easier to ask later questions like:

- which references plausibly point to editions with translations;
- which references are just source catalogues or inscription lists;
- which journal/article families need detailed human disambiguation before translation discovery can proceed.
