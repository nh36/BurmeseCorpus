# Phase 2 BibTeX authority layer

Phase 2 now has three linked bibliography layers:

1. **triage files** under `data/working/bibliography/`, which cluster raw reference strings conservatively;
2. **source-family authority files** under `data/working/bibliography/bibtex_authority/`, which normalize abbreviations, series, and internal reference systems without pretending they are all ordinary works;
3. **BibTeX authority files** under `data/working/bibliography/bibtex_authority/`, which turn confirmed or plausibly identified works into reusable BibTeX records.

This layer is still provisional, but it is no longer meant to depend mainly on fuzzy matching. The main route to improvement is now **evidence-backed local-source harvesting**, especially Frasch materials and other Burma bibliography folders. The layer is meant to separate **works**, **source abbreviations**, and **locators** so later bibliography authority review and published-translation discovery can proceed on cleaner data.

## Distinctions

- **Raw reference string**: the literal string extracted from a corpus record, such as `OBI 3, p. 2` or `Luce, Myanmar's Debt, JBRS 1932, p. 125`.
- **Locator**: the part of the raw string that points into a work or source family, such as `3, p. 2`, `90`, or `Pl. II 198`.
- **Reference family**: a conservative triage cluster of related raw strings, often based on an abbreviation, author/title pattern, or recurring source label.
- **Source-family authority**: a normalized abbreviation, catalogue family, periodical family, or internal reference system such as `List`, `OBI`, `Pl.`, `RDASB`, or `JBRS`.
- **Work candidate**: a provisional bibliographic candidate inferred from a family.
- **BibTeX authority record**: a reusable BibTeX entry in either `bibliography_authority.bib` or `bibliography_candidates.bib`.

Not every raw string should become its own BibTeX work. `OBI 3, p. 2`, `List 90`, and `Pl. II 198` are usually better treated as a source-family match plus a locator.

The central review tables are now:

- `source_family_authority.tsv`
- `acronym_resolution_status.tsv`
- `remaining_acronym_worklist.tsv`
- `remaining_acronym_evidence.tsv`
- `final_acronym_resolution_sprint.tsv`
- `final_acronym_local_file_hits.tsv`
- `final_acronym_web_searches.tsv`
- `frasch_abbreviation_list_review.tsv`
- `unresolved_acronym_dossier.tsv`
- `source_work_authority.tsv`
- `source_work_locator_systems.tsv`
- `raw_reference_crosswalk_audit.tsv`
- `candidate_stub_review.tsv`
- `raw_reference_to_bibtex.tsv`
- `bibtex_authority.tsv`
- `high_frequency_resolution_plan.tsv`
- `bibtex_authority_report.json`

`raw_reference_to_bibtex.tsv` now keeps `source_family_id`, `source_work_key`, `bibtex_key`, `locator`, `locator_type`, `resolution_status`, and `resolution_level` separate so a raw corpus string can point to a family, a work, both, or neither.

## Acronym resolution

`source_family_resolved` is **not** the same thing as knowing what an acronym expands to. The acronym layer now keeps those questions separate:

- `source_family_authority.tsv` records the stable source-family or series mapping;
- `acronym_resolution_status.tsv` records whether the abbreviation itself is a `confirmed_expansion`, `probable_expansion`, `alias_or_variant_of_PPA`, `probable_locator_system`, `probable_private_luce_locator_system`, `source_family_only`, `contextual_usage_only`, `internal_locator`, `not_an_acronym`, `unresolved_after_targeted_search`, `unresolved_after_exhaustive_search`, or still `unresolved`;
- `remaining_acronym_worklist.tsv` is the focused queue for the last weak source acronyms, including files checked, search terms used, and the recommended conservative action;
- `remaining_acronym_evidence.tsv` records one short targeted-evidence row per remaining acronym, including negative-search rows where nothing documentary was found;
- `acronym_definition_candidates.tsv` records quote-level evidence from corpus documentation, Frasch's *Pagan: Stadt und Staat* materials, and `Bagan Epig Database.doc`.

`source_family_only` is still useful, but it is **not** an expansion. Keep that distinction explicit in both `source_family_authority.tsv` and `acronym_resolution_status.tsv`.

Only strong evidence types such as abbreviation lists, explicit parenthetical definitions, bibliography headings, or source-list entries should count as actual expansions. Contextual usage such as `PPA, p. 55` or `MP 1, p. 81` is still useful for source-family stability, but it should remain visibly weaker than a real definition.

For weak cases, keep the source family visible but keep the expansion visibly unconfirmed unless the evidence is strong enough to classify a **locator system** or **private archival family** conservatively.

`unresolved_after_targeted_search` is useful for the first focused pass, but the final-six sprint now prefers more specific outcomes:

- `probable_expansion` when the publication title is well supported but the exact abbreviation line is still inferred, as with `RDASB`;
- `probable_locator_system` for references such as `MP` or `OR` that behave like collection or shelfmark systems;
- `probable_private_luce_locator_system` for numbered Luce notebook references such as `Luce D 825` or `Luce J 2507`;
- `unresolved_after_exhaustive_search` only when local and targeted web searches plus occurrence-level review still fail to recover a distinct definition.

Treat parenthetical remarks, note labels, and ordinary English words as false-positive territory, not as expansions. `spelling of inscription (OBI)`, `Date ... (List)`, or lowercase `or:` are usage/noise patterns; they belong in the false-positive audit, not in `acronym_resolution_status.tsv`.

Keep acronym evidence quotes short and documentary. Long catalogue prose should stay in the extraction context tables, while `best_evidence_quote` should remain a concise abbreviation-list row, heading, or source-list phrase.

Manual acronym seeds now live in `manual_acronym_seeds.tsv`. They record expert identifications such as `EB`, `JBRS`, `JRAS`, and `OBI` without pretending that a documentary source has already been found. In `acronym_resolution_status.tsv`, these appear as high-confidence `manual_seed` evidence and should keep a note that documentary corroboration is still desirable.

The manual seed table and the documentary evidence tables are intentionally separate:

- `manual_acronym_seeds.tsv` records Nathan's expert identifications directly;
- `acronym_resolution_status.tsv` carries the currently chosen expansion and the best available evidence source;
- `remaining_acronym_evidence.tsv` and `acronym_definition_candidates.tsv` record documentary confirmation or the lack of it.

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

## Resolution semantics

The authority layer now uses explicit resolution language:

- `resolution_status`: `unresolved`, `alias_resolved`, `source_family_resolved`, `series_level_resolved`, `work_level_resolved`, `confirmed_work`, `provisional_work`, `needs_human_review`
- `resolution_level`: `raw_locator`, `abbreviation`, `source_family`, `series`, `work`, `article`, `book`, `internal_reference`, `unknown`

This prevents source-family placeholders from being counted as fully confirmed works. For example:

- `RDASB 1971` is a **series-level** resolution with a year locator;
- `Pl. II 198` is an **internal-reference** resolution with a plate locator;
- `List 90` is a **confirmed work** plus a catalogue-number locator;
- `PPA, p. 55` or `UB 1, p. 297` can be **source-family-resolved** without being fully confirmed publications.

## Source works versus locator systems

The current pass makes the locator/work split explicit for high-frequency source references:

- `Pl.` is a **plate locator system**, not a bibliographic title;
- `IOB` is treated as a **locator-style reference into the same underlying work** as `Pl.`;
- `List`, `PPA`, and `UB` are source works with stable locator patterns rather than standalone expansions of every raw string;
- `MP` is treated as a Mandalay Palace stone-collection locator system, not a stand-alone publication;
- `OR` is treated as a British Library Oriental manuscript shelfmark system;
- `Luce D` and `Luce J` are treated as unpublished Luce notebook locator families unless later publication evidence appears.

Use these files together:

- `source_work_authority.tsv` for the stable source-work layer that downstream normalization should target;
- `source_family_authority.tsv` for the source-family row and its `source_work_key` / `related_source_work_key`;
- `source_work_locator_systems.tsv` for the consolidated locator-system summary;
- `raw_reference_to_bibtex.tsv` for per-reference locator parsing and raw-string preservation;
- `raw_reference_crosswalk_audit.tsv` for high-occurrence crosswalk gaps or semantic mismatches.

The key practical reading rules are now:

- `Pl. II 198` = a **plate locator** into *Inscriptions of Burma*;
- `IOB--278` = an **IOB catalogue-style locator** into the same underlying Luce and Pe Maung Tin work;
- `List 90` = a **catalogue-number locator** into Duroiselle's *List*;
- `PPA, p. 55` = a **page locator** into *Inscriptions of Pagan, Pinya and Ava*;
- `UB 1, p. 297` = a **volume/page locator** into *Inscriptions Collected in Upper Burma*;
- `MP 1, p. 21` or `MP stone 507` = a **Mandalay Palace stone collection locator**, not a bibliographic title;
- `OR 3434, fol. gha verso` = a **British Library Oriental manuscript shelfmark plus folio locator**.

## Final acronym resolution sprint

The last six hard cases (`IPPA`, `Luce D`, `Luce J`, `MP`, `OR`, `RDASB`) received one more targeted pass before the acronym phase closed.

That sprint now records:

- `final_acronym_resolution_sprint.tsv` for the hypothesis, search strategy, and recommended status per acronym;
- `final_acronym_local_file_hits.tsv` for cache/manifest hits and negative local searches;
- `final_acronym_web_searches.tsv` for targeted web searches kept separate from local primary evidence;
- `frasch_abbreviation_list_review.tsv` for the explicit re-check of the key Frasch abbreviation-list slices;
- `unresolved_acronym_dossier.tsv` for the residue that stayed unresolved even after the final sprint.

The operating rule is conservative:

- use a **probable expansion** only when the publication title is well supported, even if the exact abbreviation line is still missing;
- use **locator-system** statuses for holding, collection, or archival numbering systems;
- do **not** turn private or local locator systems into ordinary BibTeX works;
- keep the irreducible residue explicit instead of hiding it behind source-family placeholders.

## IPPA resolution

`IPPA` was the final priority acronym kept open after the sprint, so it received an occurrence-level review rather than another acronym-only search.

That review now writes:

- `ippa_occurrence_contexts.tsv`
- `ippa_ppa_comparison.tsv`
- `ippa_local_context_search.tsv`
- `ippa_frasch_abbrev_neighbourhood.tsv`
- `ippa_record_review.tsv`
- `ippa_targeted_ocr_notes.tsv`
- `ippa_resolution_decision.tsv`

The current classification is **alias_or_variant_of_PPA**: the raw structured OBI source preserves `IPPA` strings, but the occurrence pattern and Frasch abbreviation evidence tie that family to the same underlying work as `PPA`, *Inscriptions of Pagan, Pinya and Ava*. The builder therefore preserves raw `IPPA` strings in `raw_reference_to_bibtex.tsv`, links `sf-ippa` to `sf-ppa`, and routes both families to the same underlying `ppaCatalogue` work without inventing a separate BibTeX publication.

## Acronym and source-family resolution status

The acronym-resolution phase is now closed for the priority set. No priority acronym remains unresolved.

- `IPPA` is treated as an **alias/variant locator family** into `PPA`, not as a separate bibliographic work.
- Raw `IPPA` strings are preserved in `raw_reference_to_bibtex.tsv` even when they map to the shared `ppaCatalogue` source work.
- `MP`, `OR`, `Luce D`, `Luce J`, `IOB`, and `Pl.` are treated as locator systems or private locator systems, not ordinary bibliography items.
- `source_work_authority.tsv` is now the stable source-work layer, while `source_work_locator_systems.tsv` records how families such as `Pl.`, `IOB`, `PPA`/`IPPA`, `UB`, `SIP`, `UEM`, `TN`, `MP`, and `OR` point into those works or collections.
- `candidate_stub_review.tsv` and `raw_reference_crosswalk_audit.tsv` are now the closing cleanup layer for suppressing non-work residue and surfacing remaining crosswalk issues without reopening the acronym hunt.

The next phase should build on this consolidation for **bibliography/source-work normalization** and **translation-source discovery**, not by reopening broad acronym chasing.

## Source-work authority and BibTeX emission

`source_work_authority.tsv` is intentionally broader than `bibliography_authority.bib`.

- It includes publication-like source works, periodicals, series, corpus/source authorities, locator collections, manuscript collections, and private notebook authorities.
- Not every authority object should become an ordinary BibTeX publication.
- Locator systems and alias families remain authority objects even when they should not emit standalone `@book`-style records.

The current QC layer makes that distinction explicit:

- `source_work_authority.tsv` carries the canonical `source_work_key`, `authority_level`, and evidence-backed source-work metadata.
- `source_work_locator_systems.tsv` records how families such as `Pl.`, `IOB`, `IPPA`, `MP`, `OR`, `Luce D`, and `Luce J` point into works or collections without turning those locator systems into ordinary publications.
- `source_work_to_bibtex_reconciliation.tsv` records whether a source-work authority should emit a BibTeX row, remain candidate-only, or be intentionally suppressed from publication-style emission.

This means:

- series- and periodical-level authorities such as `JBRS`, `JRAS`, `BBHC`, `ARASI`, and `Epigraphia Birmanica` can remain publication-like authorities without pretending to be article-level records;
- source-work authorities such as `PPA`, `UB`, `SIP`, `UEM`, `TN`, `List`, and *Inscriptions of Burma* can emit BibTeX rows when the bibliographic witness is strong enough;
- locator collections, manuscript collections, and private Luce notebook systems should remain structural authorities unless there is explicit reason to emit them as `@misc` or `@unpublished`.

Messy OCR evidence is still preserved, but it no longer belongs in clean BibTeX fields. The QC pass keeps raw or noisy evidence in TSV audit/evidence tables, while emitted BibTeX rows use short, citation-like summaries and normalized script values.

## Source-authority QC closeout

The source-authority QC pass closes with `source_work_authority.tsv` as the central source-work table.

- `source_work_authority.tsv` is the authority layer for source works, series, periodicals, corpus sources, locator collections, manuscript collections, and notebook-style authorities.
- `bibliography_authority.bib` is generated only for publication-like authority objects that the reconciliation layer says should emit BibTeX.
- `source_work_locator_systems.tsv` carries locator semantics for systems such as `IOB`, `Pl.`, `IPPA`, `MP`, `OR`, `Luce D`, and `Luce J` instead of treating those systems as ordinary publications.
- `bibliography_candidates.bib` remains separate for retained candidate stubs such as *Anthology* and *Rajakumar's Inscription*.
- `raw_reference_crosswalk_audit.tsv` is intentionally conservative: any remaining residues are documented explicitly instead of being hidden.

At this point the authority model is ready for the next phase. The follow-on work should be **bibliography normalization** and **translation-source discovery**, not another redesign of the source-authority layer.

## Authority vs candidate BibTeX

- `bibliography_authority.bib` holds conservative authority entries supported by imported external BibTeX, Frasch/local-source evidence, repository-backed source identification, or strong manual/source-family seeds.
- `bibliography_candidates.bib` holds provisional stubs only for plausible standalone works, articles, or books.

Every provisional or machine-generated candidate should carry an explicit note that it still requires human review.

Locator-only families should not generate separate machine-stub works. The builder now suppresses those rows and records the drop in `suppressed_locator_stub_count`.

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

`data/working/bibliography/bibtex_authority/source_abbreviation_seeds.tsv` remains the seed worksheet, but the main review target is now `source_family_authority.tsv`.

Important review columns:

- `evidence_source_file`
- `evidence_ref_id`
- `evidence_quote_short`
- `confidence`
- `needs_human_review`

Use these rows to confirm or keep provisional expansions for abbreviations such as `A`, `B`, `MP`, `UB`, `PPA`, `TN`, `IPPA`, `UEM`, `SIP`, `MM`, `OR`, `Pl.`, `ARASI`, `Luce D`, `Luce J`, `JBRS`, and `JRAS`.

If an expansion is still uncertain, keep the seed row but leave `needs_human_review = true`.

The current best documentary targets for acronym review are the original corpus bibliographic-information files, Frasch's *Pagan: Stadt und Staat* witnesses and translations, `Bagan Epig Database.doc`, and nearby Luce/Frasch local files. If those files do not yield an explicit definition, keep the acronym visibly weak rather than hiding it behind a family placeholder.

Targeted OCR is now part of that review loop:

- use `ocr_priority_queue.tsv` to decide which files justify OCR;
- run `python3 scripts/ocr_priority_sources.py`;
- keep full OCR text only under gitignored `data/local/ocr_text/`;
- commit only `ocr_manifest.tsv`, `ocr_text_index.tsv`, and `ocr_report.json`;
- review `acronym_manual_review_packet.tsv` after rebuilding to see which priority acronyms moved to confirmed/probable, which are still unresolved after targeted search, and which still need human work;
- use `remaining_acronym_worklist.tsv` and `remaining_acronym_evidence.tsv` as the explicit handoff packet for the few weak acronyms that still need human judgment.

## Reviewing high-frequency families first

Two files now work together:

- `high_frequency_unresolved.tsv`
- `high_frequency_resolution_plan.tsv`

The first is the remaining unresolved queue, sorted by descending `occurrence_count`.

The second is the explicit review sheet for the top families first. It records:

- the current `resolution_status` and `resolution_level`;
- the shared source-family or BibTeX authority key;
- the evidence source and confidence;
- the next action required before final confirmation.

This is the main mechanism for improving the authority layer without creating more machine stubs for low-value tail cases. The goal is not to maximize BibTeX entries. The goal is to produce a correct crosswalk from raw corpus references to source families, works, and locators.

## Why this matters for translation discovery

Published translations are often tied to identifiable works, not to raw locator strings. By separating:

- journal or catalogue families,
- specific identified works,
- and locators within those works,

the BibTeX authority layer makes it easier to ask later questions like:

- which references plausibly point to editions with translations;
- which references are just source catalogues or inscription lists;
- which journal/article families need detailed human disambiguation before translation discovery can proceed.
