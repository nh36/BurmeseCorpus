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
