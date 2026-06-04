# Inscriptions of Burma extraction notes

- **OCRed witness**: `inscriptions_of_burma-b7c07d9f6d02`
- **Observed structure**: bilingual front matter (English preface, Burmese preface, abbreviation lists), a clean English `INDEX OF PLATES` section on OCR pages 6-10, a Burmese plate index on pages 11-14, dimensions tables, and then mostly facsimile plate/rubbing pages whose OCR is noisy.
- **Contains recognizable inscription numbers**: yes, chiefly through plate numbers plus `List`, `SIP`, `PPA`, `TN`, `UB`, and `JBRS` cross-references in the English/Burmese index pages.
- **Contains Burmese inscription text**: the facsimile plate pages do contain Burmese script, but the OCR quality on the plate images is generally too poor for safe inscription-level extraction from this run.
- **Contains English translations**: no inscription-level English translations were found in the OCRed source text. The only `translation` hits are in the preface, where the editors explain that this facsimile series points readers to other published books containing the inscription text or English translation.
- **Contains plates/rubbings or transcribed text**: overwhelmingly plates/rubbings plus index/catalogue matter; this is not an edited text-and-translation volume.
- **Locator systems present**: Roman-numbered plates in the source itself, plus `List`, `SIP`, `PPA`, `TN`, `UB`, and occasional `JBRS` references in the index entries. The structured corpus cites this witness mostly as `Pl. I ...`, which corresponds to volume-I plate numbers that can be converted to the OCRed Roman plate entries.
- **Segmentation strategy**:
  1. Treat the preface and abbreviation page as commentary/context units.
  2. Treat the English `INDEX OF PLATES` entries as the main extractable units for this source.
  3. Link only exact, single-plate `Pl. I N[a|b]` corpus citations back to the matching Roman-numbered index entries.
  4. Keep range citations, multi-plate citations, and noisy facsimile plate pages as manual-review material.
