# Phase 2 bibliography/source authority triage

## BibTeX authority addendum

This triage layer now feeds a first BibTeX authority scaffold under `data/working/bibliography/bibtex_authority/`.

The new BibTeX layer keeps three things separate:

- raw reference strings as extracted from the corpus;
- locators inside those strings, such as page, plate, or catalogue numbers;
- reusable BibTeX authority records for confirmed or provisional works and source families.

Additional Phase 2 working files now include:

- `bibtex_authority/source_abbreviation_seeds.tsv`
- `bibtex_authority/bibliography_authority.bib`
- `bibtex_authority/bibliography_candidates.bib`
- `bibtex_authority/bibtex_authority.tsv`
- `bibtex_authority/raw_reference_to_bibtex.tsv`
- `bibtex_authority/bibtex_authority_report.json`

This BibTeX layer is still provisional. It is a scaffold for authority review and later published-translation discovery, not a final normalized bibliography.

Phase 2 begins with bibliography/source authority because later work depends on understanding which publications, catalogues, and internal reference systems are already present in the corpus. Translation discovery, source comparison, and citation cleanup all become safer once the raw reference landscape is visible and grouped into reviewable families.

## What the triage files are

The triage layer lives under `data/working/bibliography/` and currently adds:

- `reference_families.tsv`
- `reference_family_members.tsv`
- `bibliographic_work_candidates.tsv`
- `bibliography_triage_report.json`

These files sit on top of the existing extracted bibliography working files:

- `raw_references.tsv`
- `reference_occurrences.tsv`
- `bibliography_candidates.tsv`
- `bibliography.jsonl`
- `reference_coverage_by_source.tsv`
- `bibliography_summary.json`

## What the triage layer does

- groups recurring raw reference fragments into conservative families;
- keeps the raw reference strings visible instead of normalizing them away too early;
- creates provisional work-candidate rows that can guide later authority review;
- flags which families may be relevant to published translations;
- preserves the source-coverage context that structured OBI has references while Sagaing currently does not.

## What it does not yet claim

This is **not** final bibliography normalization.

It does not claim that:

- every family corresponds to a single real-world bibliographic work;
- author, year, or title fields are complete or authoritative;
- translation relevance is settled;
- all repeated abbreviations have been fully disambiguated.

Where the data is weak, the triage layer stays vague on purpose.

## How this supports later translation discovery

Later translation discovery will need to know which references are most likely to point to editions, articles, or books that contain translations or substantial discussion of individual inscriptions. The triage layer makes that search tractable by:

- separating raw strings from provisional work candidates;
- grouping obvious recurring families such as OBI-internal references, catalogues, and recurrent publication abbreviations;
- marking likely or possible translation relevance without claiming final certainty.

## How human review should proceed

1. Start with `reference_families.tsv`, sorted by descending occurrence count.
2. Review `reference_family_members.tsv` to see the raw strings behind each family.
3. Adjust or annotate `bibliographic_work_candidates.tsv` conservatively.
4. Use `reference_coverage_by_source.tsv` and `bibliography_triage_report.json` to keep the source-coverage context visible.

The aim at this stage is not to finish authority control. It is to make the reference landscape intelligible enough that later normalization and translation discovery can proceed safely.
