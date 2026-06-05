# SIP extraction notes

- **Confirmed witness**: `luce_pemaungtin_1928_inscriptions_of_pag-da9f6d6d89b3`
- **Bibliographic identity**: the OCRed title page confirms *Selections from the Inscriptions of Pagan*, by Pe Maung Tin and G. H. Luce, University of Rangoon Department of Oriental Studies Publication No. 1, 1928.
- **Contains edited Burmese / Old Burmese source text**: yes. The body pages contain edited Burmese inscription text arranged by numbered inscription entries.
- **Contains English translation**: no inscription-level English translation was identified in the OCRed volume.
- **Contains transliteration/transcription**: the book appears to present edited Burmese inscription text rather than a separate Roman transliteration layer.
- **Contains commentary**: yes. There is Burmese front matter/preface and brief editorial/contextual matter around the text and contents.
- **Locator system**: SIP page numbers are the useful extraction locator, and the IOB concordance links those SIP page references back to IOB plates plus List/PPA/TN references. The OCRed PDF includes about 10 prefatory pages before SIP printed page 1, so SIP printed page `N` maps approximately to OCR page `N + 10`.
- **Segmentation strategy**:
  1. Keep the title page, preface, and contents as commentary/catalogue context.
  2. Use the IOB-derived `sip_cross_reference_targets.tsv` rows as the extraction spine.
  3. Extract one SIP unit per cited SIP page range, linking only the rows that already have high-confidence corpus links through the IOB concordance.
  4. Leave uncertain SIP references and noisy/end-matter artifacts marked for manual review.
