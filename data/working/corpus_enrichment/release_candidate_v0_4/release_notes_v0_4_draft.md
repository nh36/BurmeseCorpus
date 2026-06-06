# v0.4 candidate release notes (draft)

## Candidate summary

- total records: 1152
- records with any enrichment: 67
- records with integrated translations: 25
- integrated translation-unit count: 28
- SIP source-text witness count (record-level): 5
- cross-reference enrichment counts: IOB=63, List=43, PPA=21, TN-candidate=21

## Sources integrated

- U Pe Maung Tin and G. H. Luce, The Shwegugyi Pagoda Inscription, Pagan, 1141 A.D. (JBRS 10(2), 1920, pp. 67-74)
- U Tun Nyein / Taw Sein Ko / Forchhammer, Inscriptions of Pagan, Pinya and Ava: Translation, with Notes. Rangoon: Government Press, 1899.
- Tun Aung Chain, The Rajakumar Inscription, Cultural Classics, Yangon Universities Press, 2001, pp. 25-37

## Sources excluded or blocked

- jbrsAnanda1976: out_of_scope_late_ink_wall_inscription
- fraschPaganMachineTranslation2004: wrong_source_rejected
- peMaungTinMyazedi1974: wrong_source_rejected
- ppaCatalogue: source_missing_acquire_manually
- sipSelectionsPagan: no_translation_present
- lucePeMaungTinInscriptionsOfBurma: no_translation_present

## Residual unresolved TN items

- TN 6 — translation_fragment_without_secure_locator: translation_fragment_without_secure_locator
- TN 70-71 — probable_overlap_but_no_record_link: probable_overlap_but_no_record_link

## Known limitations

- TN residual unresolved cases remain and are preserved as review material only.
- Rajakumar Mon and Pyu units remain candidate-only until secure corpus-record links are found.
- Ananda remains out of scope for this release-candidate workflow.
- This is a draft release candidate and not yet a Zenodo package.

## Pre-release review for Nathan

- Review `tn_unresolved_review_v0_4.tsv` and decide whether any residual TN item should be closed, deferred, or escalated.
- Spot-check manual hard-case integrations in `tn_manual_resolution_log.tsv` against cited boundaries.
- Confirm source exclusions (especially Ananda/out-of-scope items) are still desired for this release.
- Approve record-level and translation-unit counts before any external publication step.
