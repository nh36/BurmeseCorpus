# Phase 2 BibTeX authority layer

Phase 2 now has two linked bibliography layers:

1. **triage files** under `data/working/bibliography/`, which cluster raw reference strings conservatively;
2. **BibTeX authority files** under `data/working/bibliography/bibtex_authority/`, which turn confirmed or plausibly identified works into reusable BibTeX records.

This layer is still provisional. It is meant to separate **works**, **source abbreviations**, and **locators** so later bibliography authority review and published-translation discovery can proceed on cleaner data.

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

## Local library matching

`scripts/match_local_bibliography_sources.py` uses `OBI_LIBRARY_ROOT` to scan a local Burma bibliography tree for likely matches:

```bash
OBI_LIBRARY_ROOT=/path/to/local/library python3 scripts/match_local_bibliography_sources.py
```

The script never modifies the external library. It records filename-based matches, checksums, and relative paths under the library root in a manifest. If `OBI_LIBRARY_ROOT` is unset, it exits cleanly with a report explaining how to enable the step.

## Authority vs candidate BibTeX

- `bibliography_authority.bib` holds conservative authority entries supported by imported external BibTeX, repository-backed source identification, or strong manual/source-family seeds.
- `bibliography_candidates.bib` holds provisional stubs for unresolved families and weakly inferred candidates.

Every provisional or machine-generated candidate should carry an explicit note that it still requires human review.

## Why this matters for translation discovery

Published translations are often tied to identifiable works, not to raw locator strings. By separating:

- journal or catalogue families,
- specific identified works,
- and locators within those works,

the BibTeX authority layer makes it easier to ask later questions like:

- which references plausibly point to editions with translations;
- which references are just source catalogues or inscription lists;
- which journal/article families need detailed human disambiguation before translation discovery can proceed.
