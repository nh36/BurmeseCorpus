# Phase 2 translation-source discovery

This phase is a planning and discovery pass, not a translation-generation pass.

The immediate purpose is to determine which bibliography/source-work authorities are likely to contain:

- published translations;
- partial translations or translated excerpts;
- full editions or diplomatic/transliterated text without translation;
- plates, images, or other supporting publication apparatus;
- only references or secondary discussion.

## Starting point

The discovery pass should begin from the stabilized authority layer:

- `data/working/bibliography/bibtex_authority/source_work_authority.tsv`
- `data/working/bibliography/bibtex_authority/bibliography_authority.bib`
- `data/working/bibliography/bibtex_authority/raw_reference_to_bibtex.tsv`

Those files already separate source works, locator systems, and emitted publication authorities, which makes it possible to ask better next-phase questions without reopening source-authority QC.

## Working distinctions

- **Inscription catalogues / corpus-style works** may contain editions, transliterations, plates, or sometimes translations.
- **Secondary works** may contain article-level discussion, partial translated quotations, or bibliographic leads rather than full editions.
- **Locator systems** such as collections, shelfmarks, and notebooks should remain structural reference objects unless a published witness is identified separately.
- **Series and periodicals** such as `JBRS`, `JRAS`, `BBHC`, and `ARASI` should be treated as containers for later article discovery, not as proof that a translation has already been identified.

## Discovery questions

For each source work, the next pass should ask:

1. Is this mainly a catalogue, a source edition, a series container, or a secondary discussion work?
2. Does it plausibly include full inscriptions, edited text, translation, commentary, plates, or only references?
3. Is the current authority row strong enough to support targeted local-file or bibliography searches?
4. Should discovery focus first on work-level authorities or on article discovery inside a series/periodical container?

## Conservative operating rule

Do **not** start AI translation generation until published translation coverage has been assessed.

The first job is to identify where published translations or partial translations may already exist, so later translation work can distinguish:

- translation from publication witness;
- translation from edited transliteration only;
- records with no known translation witness yet.

## Initial scaffold

`data/working/bibliography/translation_source_discovery_plan.tsv` is the starter planning table for this phase.

It should remain conservative:

- record likelihoods and priorities, not conclusions;
- distinguish catalogue/edition relevance from translation relevance;
- note when a series or periodical will require later article-level discovery;
- avoid inventing publication metadata or implying that a translation is already confirmed.

## Current discovery workflow

Run the first-pass discovery and validation with:

```bash
python3 scripts/discover_translation_sources.py
python3 scripts/verify_translation_witnesses.py
python3 scripts/validate_translation_source_discovery.py
```

The discovery pass reads:

- `data/working/bibliography/translation_source_discovery_plan.tsv`
- `data/working/bibliography/bibtex_authority/source_work_authority.tsv`
- `data/working/bibliography/bibtex_authority/source_work_locator_systems.tsv`
- `data/working/bibliography/bibtex_authority/bibliography_authority.bib`
- optional local-source manifests under `data/working/bibliography/local_sources/`

and writes:

- `data/working/bibliography/translation_source_discovery/witness_candidates.tsv`
- `data/working/bibliography/translation_source_discovery/witness_classification.tsv`
- `data/working/bibliography/translation_source_discovery/witness_verification.tsv`
- `data/working/bibliography/translation_source_discovery/witness_titlepage_toc_snippets.tsv`
- `data/working/bibliography/translation_source_discovery/missing_direct_witness_search.tsv`
- `data/working/bibliography/translation_source_discovery/source_work_witness_gaps.tsv`
- `data/working/bibliography/translation_source_discovery/sip_witness_inspection.tsv`
- `data/working/bibliography/translation_source_discovery/uem_direct_witness_search.tsv`
- `data/working/bibliography/translation_source_discovery/core_source_direct_witness_search.tsv`
- `data/working/bibliography/translation_source_discovery/inscriptions_of_burma_text_witness_search.tsv`
- `data/working/bibliography/translation_source_discovery/rescue_candidate_review.tsv`
- `data/working/bibliography/translation_source_discovery/epigraphia_birmanica_witness_review.tsv`
- `data/working/bibliography/translation_source_discovery/epigraphia_birmanica_fascicle_coverage.tsv`
- `data/working/bibliography/translation_source_discovery/periodical_article_discovery_plan.tsv`
- `data/working/bibliography/translation_source_discovery/translation_source_discovery_report.json`

## How to read the outputs

`witness_candidates.tsv` is a conservative match layer. It records which local files look plausibly related to each high-priority source work, why they matched, and whether the match still needs human review.

`witness_classification.tsv` is the first interpretation layer. It separates:

- direct source editions from weaker secondary leads;
- plate/image witnesses from text witnesses;
- catalogue-style works from possible translation witnesses;
- series/periodical containers from article-level candidates.

Confirmed translation or edition claims should come only from short inspectable evidence such as OCR snippets or clearly explicit file labels. Filename-only matches should stay provisional.

## Witness verification

Candidate discovery is not the same thing as witness verification.

`witness_candidates.tsv` records leads. `witness_verification.tsv` records the stricter reviewed layer after title-page, contents, OCR-heading, or other short inspectable evidence has been checked.

Use the verification pass to keep these distinctions explicit:

- filename matches are leads, not proof;
- title page, contents, preface, or OCR-heading evidence is needed before confirming a translation or edition witness;
- periodical containers and secondary articles must remain distinct from direct source witnesses;
- weak false positives should stay in the data as reviewed outcomes rather than being silently deleted.

`witness_titlepage_toc_snippets.tsv` stores only short snippets that justify the verification status. Do not commit full OCR text, scans, or page images.

`missing_direct_witness_search.tsv` documents targeted direct-witness searches for high-priority works that still need a better local witness.

## Direct witness gaps and witness inspection

Witness verification identifies reviewed leads. It does **not** by itself prove translation coverage.

Use the new gap and inspection tables to keep that distinction explicit:

- `source_work_witness_gaps.tsv` tracks which high-priority works still need a direct witness, a title-page review, or a translation-specific inspection pass.
- `sip_witness_inspection.tsv` records the short inspected evidence for the verified SIP witness. SIP now has a verified direct witness, but translation coverage must still come from explicit inspected evidence rather than title-family inheritance.
- `uem_direct_witness_search.tsv` keeps UEM separate from SIP. A shared `Selections ...` title family is not enough: the Luce/Pe Maung Tin SIP witness must remain excluded from UEM unless author/editor evidence supports UEM directly.
- `core_source_direct_witness_search.tsv` records targeted local-file search results for TN, PPA, and UB.
- `inscriptions_of_burma_text_witness_search.tsv` keeps the Inscriptions of Burma text-volume search separate from already verified plate/facsimile witnesses.
- `rescue_candidate_review.tsv` and `epigraphia_birmanica_witness_review.tsv` keep ambiguous rescue files and numbered PDFs visible as reviewed evidence instead of auto-mapping them.

In practice:

- SIP can be a verified direct witness and still remain translation-unknown.
- works without a verified direct witness should stay in the gap table rather than being silently inferred from related filenames;
- rescue candidates such as numbered PDFs or broad title-family matches must be reviewed before they count toward any direct-witness totals.

## Promoting direct witnesses

Promotion should stay conservative, but strong local evidence can justify a provisional verified layer when the file/path identity is already explicit.

- direct-looking file/path evidence can justify promotion to `verified_direct_witness` when the witness still carries `needs_human_review = true`;
- title-page or contents snippets are preferred and should be added whenever short extractable evidence is available;
- `Epigraphia Birmanica` fascicles should be handled as source-edition witnesses, not translation witnesses, unless explicit translation evidence appears in the fascicle itself;
- SIP now has a verified edition witness with extended inspection rows, but it still needs deeper sample-entry/content review before any translation claim can be made;
- `Inscriptions of Burma` plate volumes remain plate witnesses only and do not replace the missing text witness.

## Content profiles and failed OCR

Identity evidence is not content evidence.

- a title page can verify that a file is the right witness without proving that it contains translation;
- failed OCR should be recorded as `attempted_no_recoverable_text`, which means the content status remains `unknown` or `unconfirmed`, not `false` or `not_present`;
- edition status, translation status, notes/commentary status, and plate/image status should be tracked separately in `source_witness_content_profile.tsv` and the supporting inspection tables;
- `sip_witness_inspection.tsv` can show that SIP sample-entry OCR was attempted while `sip_sample_entry_inspected = false` remains the correct report value if no recoverable entry text was isolated;
- `eb_fascicle_content_inspection.tsv` should capture short title-page, contents, or sample-entry snippets for promoted `Epigraphia Birmanica` fascicles, but those fascicles stay non-translation witnesses unless explicit translation evidence appears;
- `inscriptions_of_burma_text_witness_search.tsv` and `inscriptions_of_burma_text_volume_hunt.tsv` should keep plate/facsimile files visible as evidence while marking them as false positives for the missing text-witness gap;
- direct-witness gaps therefore remain open for UEM, TN, PPA, UB, and the missing `Inscriptions of Burma` text volume even when plate witnesses or title-page-only identity evidence exist.

## Periodicals and series

`JBRS`, `JRAS`, `BBHC`, and `ARASI` should remain containers unless article-level evidence is identified. `EB` needs direct fascicle review; do not treat unrelated numbered PDFs or periodical-style matches as EB witnesses automatically.

Use `periodical_article_discovery_plan.tsv` to queue that next step:

1. start from normalized raw reference examples;
2. map those examples to local issue/article files where possible;
3. inspect the article-level witness before promoting any translation or edition claim.

Do not treat a periodical container row as proof that the whole series is a translation source.

## Editions, translations, plates, and references

Keep the distinctions explicit:

- a file with `Plates` in the title may be a plate witness without being a translation witness;
- a catalogue may provide stable metadata and locators without giving a translation;
- an article that mentions inscriptions may still be only secondary discussion;
- a work titled `Inscriptions ...` is only a **possible** edition witness until the contents are inspected.

## Out of scope

AI translation generation is still out of scope for this phase.

The point of this pass is to identify existing published witnesses first, so later translation work can distinguish between:

- inscriptions that already have a published translation witness;
- inscriptions that only have edition/transliteration witnesses;
- inscriptions for which no translation witness has yet been found.
