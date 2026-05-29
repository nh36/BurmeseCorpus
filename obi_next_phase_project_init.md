# Old Burmese Inscriptions Corpus: next phase project brief

This repository is for the next phase of work on the Old Burmese inscriptions corpus. The aim is to turn the existing structured corpus and the related supplementary inscription collections into a research-grade resource for linguists and historians.

The immediate priority is not the public website. The immediate priority is to make the data coherent, auditable, and extensible: first by bringing the supplementary collections into the same structured format as the existing corpus, and then by adding translations and translation provenance.

## 1. Starting point

The project currently has three relevant Zenodo deposits.

### 1.1 Structured corpus

Zenodo record: `10.5281/zenodo.4321314`  
Title: `A Structured Corpus of Old Burmese Stone Inscriptions`

Local ZIP inspected: `4321314.zip`

Top-level contents:

- `Introduction_ A_Structured_Corpus_of_Burmese_Stone_Inscriptions.pdf`
- `OBI_Translit_System.tsv`
- `OBI_Corpus_Source_Material.zip`
- `OBI_Corpus_Vol1.zip`
- `OBI_Corpus_Vol2.zip`
- `OBI_Corpus_Vol3.zip`
- `OBI_Corpus_Vol4.zip`
- `OBI_Corpus_Vol5.zip`
- `OBI_Corpus_Vol6.zip`
- `OBI_Corpus_Vol7.zip`

The structured corpus contains one `.txt` file per inscription face or text unit. Inventory from the inspected ZIP:

| Volume | Structured `.txt` files | Approx. unique inscription numbers |
|---:|---:|---:|
| 1 | 282 | 225 |
| 2 | 178 | 145 |
| 3 | 271 | 227 |
| 4 | 211 | 152 |
| 5 | 92 | 65 |
| 6 | 38 | 38 |
| 7 | 49 | 38 |
| **Total** | **1,121** | — |

The per-inscription files usually contain the following fields:

- `OBI CORPUS REF:` or, in some volume 6 files, `OBI REF:`
- `INFORMATION SOURCE:`
- `VOLUME:`
- `PART:`
- `INSCRIPTION NUMBER:`
- `PAGE NUMBER:`
- `NUMBER OF FACES:`
- `FACE:`
- `LANGUAGE:`
- `INSCRIPTION SOURCE:`
- `PLACE OF ORIGIN:`
- `CURRENT LOCATION:`
- `REFERENCE NUMBER:`
- `REFERENCES:`
- `TITLE:`
- `DATE:`
- `DONOR:`
- `SUBJECT:`
- `LENGTH:`
- `NOTES:`
- `FOOTNOTES:`
- `INSCRIPTION:`
- `FULL TRANSLITERATION:`

Important observation: no inspected structured file currently contains a `TRANSLATION:` field. Translation must therefore be treated as a new layer, not as a correction of an existing one.

Important observation: `OBI_Corpus_Vol7` appears to be derived from Thein Tun, *Recently Found Inscriptions* / `နှောင်းတွေ့ကျောက်စာများ`. Do not assume it is complete until coverage has been audited against the source deposit.

### 1.2 Thein Tun, Recently Found Inscriptions

Zenodo record: `10.5281/zenodo.1302525`  
Title: `နှောင်းတွေ့ကျောက်စာများ`

Local ZIP inspected: `1302525.zip`

Contents:

- `Recently Found Burmese Inscriptions Original.pdf`
- `Recently Found Burmese Inscriptiosn Open office.odt`
- `Recently Found Burmese Inscriptiosn text.txt`

The `.txt` file is machine-readable but not in the same per-inscription structured format as the main corpus. The inspected text file has approximately 73,000 characters and 1,665 lines.

Because the structured corpus already has a volume 7 apparently based on this source, the first task for this deposit is a coverage audit:

1. identify every inscription in the 2005 source text;
2. identify every corresponding `OBI_Corpus_Vol7` file;
3. mark matches, gaps, duplicates, and face splits;
4. decide whether volume 7 should be completed, corrected, or replaced by a regenerated structure from the source text.

### 1.3 Sagaing Region newly found inscriptions

Zenodo record: `10.5281/zenodo.1203709`  
Title: `စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ`

Local ZIP inspected: `1203709.zip`

Contents:

- `စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ-.pdf`
- `စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.odt`
- `စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ.txt`

The `.txt` file is machine-readable but not in the same per-inscription structured format as the main corpus. The inspected text file has approximately 95,000 characters and 1,142 lines. It contains repeated metadata blocks, including fields such as:

- `ကျောက်စာအမည်`
- `မူလ/ဆင့်ထိုး/စပ်ထိုး`
- `မူလတည်ရာဌာန`
- `ယခုတည်ရာဌာန`
- `ကျောက်တိုင်အမှတ်` / variant spellings in the source
- `ကျောက်စာမျက်နှာ`
- `ကောဇာသက္ကရာဇ်`
- `လှူဒါန်းသူ`
- `အလှူပစ္စည်း`
- line-numbered inscription text
- continuous inscription text
- `မှတ်ချက်`

This deposit is probably the clearest first target for conversion into the structured corpus format.

## 2. Project goals

### 2.1 Data integration

Bring all three deposits into a coherent corpus structure, while preserving the raw source files and the exact original strings.

Minimum output:

- one stable record ID per inscription or inscription face;
- one parsed metadata record per text unit;
- line-level transcription;
- full transliteration;
- source citation and page reference;
- source provenance for every field;
- clear distinction between diplomatic source text, normalised forms, transliteration, translation, and editorial notes.

### 2.2 Translation layer

Add English translations in two stages.

Stage A: published translations.

- Extract all bibliography and reference strings from the structured corpus.
- Normalize them into a bibliography table, preserving the exact original `REFERENCES:` strings.
- Locate the cited works in Nathan’s external hard drive library.
- Copy the relevant files into a local project source directory.
- OCR or re-OCR them where necessary.
- Identify and extract published translations of inscriptions.
- Link every translation to the exact source, page, inscription number, and confidence level.

Stage B: AI-assisted translations where no published translation exists.

- Use AI only after the published-translation audit has been performed.
- Use a controlled vocabulary and translation memory.
- Keep each AI translation explicitly marked as AI-assisted.
- Store prompts, model names, dates, inputs, outputs, and human-review status.
- Never allow an AI translation to overwrite a published translation or the diplomatic transcription.

### 2.3 Research usability

Make the corpus usable for historical linguists, philologists, historians, and epigraphists.

Required capabilities:

- search by inscription, source volume, page, place, date, donor, subject, and referenced bibliography;
- search by word form in Burmese script and transliteration;
- retrieve first attestations of words or forms;
- display attestations by chronology and geography;
- distinguish Old Burmese, later Burmese, Pali, Sanskrit, Mon, Pyu, and uncertain language material where possible;
- show line-level context for every attestation;
- link to scans where available;
- show translation and translation provenance next to the source text.

The eventual public site should come later. The near-term work should make a reliable dataset that a site can consume.

## 3. Proposed repository layout

Create a repository with this structure:

```text
.
├── README.md
├── data/
│   ├── raw/
│   │   ├── zenodo_4321314/
│   │   ├── zenodo_1302525/
│   │   └── zenodo_1203709/
│   ├── extracted/
│   │   ├── structured_corpus_current/
│   │   ├── supplementary_1302525/
│   │   └── supplementary_1203709/
│   ├── working/
│   │   ├── inventory/
│   │   ├── bibliography/
│   │   ├── ocr/
│   │   ├── translations/
│   │   └── qa/
│   └── release/
├── docs/
│   ├── data_model.md
│   ├── transliteration.md
│   ├── bibliography_workflow.md
│   ├── translation_guidelines.md
│   └── website_future.md
├── scripts/
│   ├── audit_inventory.py
│   ├── extract_structured_corpus.py
│   ├── parse_sagaing.py
│   ├── parse_recently_found.py
│   ├── extract_references.py
│   ├── match_library_sources.py
│   ├── run_google_vision_ocr.py
│   ├── ingest_published_translations.py
│   └── validate_corpus.py
├── schemas/
│   ├── inscription.schema.json
│   ├── line.schema.json
│   ├── bibliography.schema.json
│   ├── translation.schema.json
│   └── place.schema.json
└── tests/
    ├── fixtures/
    └── test_parsers.py
```

Rules:

- `data/raw/` is immutable.
- `data/extracted/` contains direct extractions from ZIPs, PDFs, ODTs, and TXT files.
- `data/working/` contains intermediate derived files.
- `data/release/` contains only validated release candidates.
- No script should silently modify `data/raw/`.
- Every derived file should be reproducible from raw data and scripts.

## 4. Suggested core data model

Use simple tabular/JSONL outputs first. TEI XML can be added later if it becomes useful, but the first version should be easy to validate and easy to query.

### 4.1 `inscriptions.jsonl`

One record per inscription text unit or face.

Suggested fields:

```json
{
  "record_id": "obi-v01-n0100-ob-p0167",
  "source_deposit": "zenodo_4321314",
  "source_volume": "1",
  "source_part": "A",
  "source_inscription_number": "100",
  "source_page": "167",
  "face": "obverse",
  "number_of_faces": "2",
  "title_original": "သင်ကြီး အို့သီသင် ကျောက်စာ",
  "title_transliteration": "saṅʻkrīḥ ʔuiɂsīsaṅʻ inscription",
  "date_original": "CS 586 = CE 1224",
  "date_normalized": {
    "calendar": "CS/CE",
    "cs_year": 586,
    "ce_year": 1224,
    "confidence": "high"
  },
  "place_of_origin_original": "...",
  "place_id": null,
  "current_location_original": "...",
  "donor_original": "...",
  "subject_original": "...",
  "language_original": "",
  "references_original": "...",
  "notes_original": "...",
  "source_file": "OBI_Corpus_Vol1/OBI_Vol1_No100__ob_p167.txt",
  "provenance": {
    "created_from": "structured corpus txt",
    "created_by_script": "extract_structured_corpus.py",
    "created_date": "YYYY-MM-DD"
  }
}
```

### 4.2 `lines.jsonl`

One record per inscription line.

```json
{
  "record_id": "obi-v01-n0100-ob-p0167",
  "line_id": "obi-v01-n0100-ob-p0167-l001",
  "line_number_original": "၁",
  "line_number_arabic": 1,
  "text_original": "။ သကရစ် ၅၈၆ ခူဆုန်",
  "transliteration": "|| sakaracʻ 586 khūchunʻ",
  "page_break_before": null,
  "footnote_refs": [],
  "uncertain": false
}
```

### 4.3 `translations.jsonl`

One record per translation segment. A translation may apply to a whole inscription, a face, a line, or a range of lines.

```json
{
  "translation_id": "tr-obi-v01-n0100-ob-p0167-published-001",
  "record_id": "obi-v01-n0100-ob-p0167",
  "line_start": 1,
  "line_end": 16,
  "translation_text": "...",
  "translation_type": "published",
  "source_bibliography_id": "bib-luce-1959-example",
  "source_page": "...",
  "source_note": "translation checked against scan",
  "confidence": "medium",
  "review_status": "needs_human_review"
}
```

For AI-assisted translations, add:

```json
{
  "translation_type": "ai_assisted",
  "model": "MODEL_NAME",
  "prompt_id": "prompt-YYYYMMDD-001",
  "controlled_vocabulary_version": "v0.1",
  "human_reviewer": null,
  "review_status": "unreviewed"
}
```

### 4.4 `bibliography.jsonl`

One record per normalized bibliographic item.

```json
{
  "bibliography_id": "bib-rdasb-1947",
  "short_label": "RDASB 1947",
  "raw_reference_strings": [
    "BED B 586-4; Pl. II 124a; OBI 1, p. 167; RDASB 1947"
  ],
  "author": null,
  "year": "1947",
  "title": null,
  "publication": "Report of the Director, Archaeological Survey of Burma",
  "local_library_candidates": [],
  "local_file_path": null,
  "ocr_status": "not_started",
  "translation_relevance": "unknown",
  "notes": "Created from REFERENCES field; needs bibliographic normalization."
}
```

### 4.5 `attestations.jsonl`

This comes later, after tokenization rules are stable.

```json
{
  "attestation_id": "att-00000001",
  "record_id": "obi-v01-n0100-ob-p0167",
  "line_id": "obi-v01-n0100-ob-p0167-l001",
  "form_original": "သကရစ်",
  "form_transliteration": "sakaracʻ",
  "lemma_id": null,
  "pos": null,
  "date_normalized": 1224,
  "place_id": null,
  "context_original": "။ သကရစ် ၅၈၆ ခူဆုန်",
  "context_translation": null
}
```

## 5. Immediate agent task: bibliography extraction

The first practical task is to extract, normalize, and audit the bibliography/reference layer in the existing structured corpus.

### 5.1 Inputs

- all structured `.txt` files from `OBI_Corpus_Vol1.zip` through `OBI_Corpus_Vol7.zip`;
- `OBI_Translit_System.tsv` for later use;
- `Introduction_ A_Structured_Corpus_of_Burmese_Stone_Inscriptions.pdf` for documentation context.

### 5.2 Outputs

Create:

```text
data/working/bibliography/raw_references.tsv
data/working/bibliography/reference_occurrences.tsv
data/working/bibliography/bibliography_candidates.tsv
data/working/bibliography/bibliography_normalization_notes.md
```

#### `raw_references.tsv`

One row per distinct raw `REFERENCES:` string.

Columns:

- `raw_reference_id`
- `raw_references_string`
- `occurrence_count`
- `example_record_id`
- `example_source_file`
- `notes`

#### `reference_occurrences.tsv`

One row per inscription file with a non-empty `REFERENCES:` field.

Columns:

- `record_id`
- `source_file`
- `volume`
- `inscription_number`
- `page_number`
- `title_original`
- `date_original`
- `raw_references_string`

#### `bibliography_candidates.tsv`

One row per parsed candidate reference token.

Columns:

- `candidate_id`
- `raw_reference_id`
- `candidate_label`
- `candidate_type`
- `candidate_year`
- `candidate_page_or_plate`
- `confidence`
- `needs_human_review`
- `notes`

Candidate types may include:

- `OBI`
- `IOB`
- `BED`
- `RDASB`
- `List`
- `Plate`
- `PPA`
- `TN`
- `U_Min_Hswe`
- `Luce`
- `Frasch`
- `Other`
- `Unknown`

Do not try to solve the whole bibliography in one pass. Preserve exact strings first. Normalize conservatively.

### 5.3 Known facts from first inspection

From the inspected structured corpus:

- total structured `.txt` files: `1121`;
- files with non-empty `REFERENCES:` field: approximately `920`;
- files with blank or missing reference content: approximately `201`;
- distinct raw `REFERENCES:` strings: approximately `874`.

These figures should be regenerated by the repository scripts and treated as testable outputs, not as hard-coded facts.

### 5.4 Acceptance criteria for first commit

The first successful commit should:

1. unpack the three Zenodo ZIPs into `data/raw/` or document their required placement;
2. extract the structured corpus into `data/extracted/structured_corpus_current/`;
3. run an inventory script that reports counts by volume;
4. extract all `REFERENCES:` fields;
5. produce the four bibliography output files listed above;
6. include tests for at least five representative reference strings;
7. include a short `bibliography_normalization_notes.md` explaining ambiguous abbreviations and unresolved items.

## 6. Local library collection workflow

The next task after bibliography extraction is to locate cited sources on Nathan’s external hard drive.

The agent should not assume a fixed path. Use an environment variable:

```bash
export OBI_LIBRARY_ROOT="/path/to/external/hard/drive/library"
```

The likely organization is author-alphabetical. For example, material by Gordon Luce may be under an author folder such as `Luce`, `Gordon Luce`, or a similar alphabetical directory.

### 6.1 Matching strategy

1. Create a list of target bibliography candidates.
2. Search filenames and directory names under `$OBI_LIBRARY_ROOT`.
3. Use conservative fuzzy matching for author, year, title, and abbreviations.
4. Copy likely source PDFs/images into:

```text
data/working/bibliography/source_library_copies/
```

5. Record every copied file in:

```text
data/working/bibliography/source_library_manifest.tsv
```

Columns:

- `bibliography_id`
- `candidate_label`
- `original_path`
- `copied_path`
- `file_name`
- `file_size`
- `sha256`
- `match_confidence`
- `match_reason`
- `needs_human_review`
- `notes`

Rules:

- Never modify the external hard drive files.
- Never delete local copies automatically.
- Always compute checksums.
- Record uncertain matches rather than pretending they are certain.

## 7. OCR workflow for bibliography sources

Some bibliography sources will be scans. Use Google Cloud Vision or another OCR provider only through reproducible scripts.

### 7.1 OCR storage

Store OCR results by source file and page:

```text
data/working/ocr/
├── source_id/
│   ├── pages/
│   │   ├── page_0001.json
│   │   ├── page_0001.txt
│   │   └── page_0001.hocr
│   └── manifest.tsv
```

The OCR manifest should include:

- `source_id`
- `page_number`
- `input_file`
- `input_sha256`
- `ocr_engine`
- `ocr_engine_version`
- `ocr_date`
- `language_hints`
- `output_json`
- `output_txt`
- `quality_notes`

### 7.2 OCR rules

- Keep page-level OCR output.
- Keep raw JSON where possible.
- Do not collapse all pages into one text file without retaining page links.
- Preserve page numbers because translations must be citeable.
- Expect OCR problems with Burmese, old typography, diacritics, and mixed Roman/Burmese text.

## 8. Published translation ingestion

Published translations should be treated as a separate evidential layer.

### 8.1 Search targets

For each bibliography source, search OCR text for:

- inscription number;
- title in Burmese script;
- title in transliteration;
- OBI reference;
- IOB reference;
- BED reference;
- page number;
- date or donor names;
- phrases such as `translation`, `translates`, `rendered`, `inscription reads`, `text`, `obverse`, `reverse`.

### 8.2 Extraction output

Create:

```text
data/working/translations/published_translation_candidates.tsv
```

Columns:

- `translation_candidate_id`
- `record_id`
- `bibliography_id`
- `source_file`
- `source_page`
- `matched_by`
- `candidate_translation_text`
- `line_alignment_status`
- `confidence`
- `needs_human_review`
- `notes`

Do not ingest a published translation directly into the release data until a human has checked the match.

## 9. AI-assisted translation pipeline

AI translation is useful, but it must be controlled and auditable.

### 9.1 Principles

- Published translations take priority.
- AI translations must be marked as AI-assisted.
- AI output must never overwrite the diplomatic text, transliteration, or published translations.
- Store prompts and model metadata.
- Use a project glossary and controlled vocabulary.
- Encourage literalness and line-by-line alignment before producing a readable translation.

### 9.2 Suggested translation stages

For each inscription without a published translation:

1. **Preparation**: collect diplomatic text, transliteration, metadata, date, subject, donor, and notes.
2. **Glossary pass**: identify known formulaic terms, units, offices, religious vocabulary, kinship terms, land terms, and donor formulae.
3. **Line-by-line literal draft**: produce a conservative translation aligned to line numbers.
4. **Commentary pass**: flag uncertain words, formulae, broken passages, and possible proper names.
5. **Readable translation**: produce a smoother translation only after the line-by-line version exists.
6. **Human review**: mark as reviewed, revised, rejected, or accepted.

### 9.3 Controlled vocabulary files

Create:

```text
data/working/translations/glossary_terms.tsv
data/working/translations/formulae.tsv
data/working/translations/names_places.tsv
data/working/translations/units_measures.tsv
data/working/translations/translation_memory.tsv
```

Each row should include:

- source form;
- transliteration;
- normalized lemma if known;
- preferred English rendering;
- alternative renderings;
- notes;
- source evidence;
- review status.

## 10. Supplementary corpus conversion

### 10.1 Sagaing parser

The Sagaing text has repeated metadata blocks and line-numbered texts. Build `parse_sagaing.py` to produce structured records that match the main corpus format.

Expected parser tasks:

- split entries at section markers and metadata headers;
- extract title, origin, current location, stone number, face count, date, donor, subject/donation, notes;
- extract line-numbered inscription text;
- extract continuous text where present;
- create stable IDs, probably with prefix `sagaing-` until integrated;
- record page/section markers from the source;
- flag malformed or uncertain entries for human review.

### 10.2 Recently Found parser and volume 7 audit

Build `parse_recently_found.py` only after auditing `OBI_Corpus_Vol7`.

Expected audit outputs:

```text
data/working/inventory/recently_found_source_entries.tsv
data/working/inventory/vol7_structured_entries.tsv
data/working/inventory/recently_found_to_vol7_crosswalk.tsv
```

Crosswalk columns:

- `source_entry_number`
- `source_title`
- `source_page`
- `vol7_record_id`
- `vol7_inscription_number`
- `vol7_title`
- `match_status`
- `match_confidence`
- `notes`

Match statuses:

- `matched`
- `matched_split_face`
- `possible_match`
- `missing_from_vol7`
- `extra_in_vol7`
- `duplicate`
- `needs_human_review`

## 11. Validation and quality control

Create validation scripts early.

Minimum checks:

- every record has a stable `record_id`;
- every record has source provenance;
- no derived record lacks a source file;
- line numbers are sequential where they are expected to be sequential;
- page breaks are preserved where present;
- raw strings are preserved before normalization;
- every translation has provenance;
- AI translations are clearly marked;
- no `data/raw/` file has been modified;
- all copied bibliography files have checksums.

## 12. Future website

The website should be built only after the data model is stable.

Likely future features:

- inscription browser;
- faceted search by date, place, donor, subject, source, language, and bibliography;
- word-form search in Burmese script and transliteration;
- first-attestation search;
- timeline view;
- map view;
- side-by-side source text, transliteration, translation, and scan;
- export citations and corpus slices.

Potential backend formats:

- JSONL release files for static publication;
- SQLite or DuckDB for local querying;
- PostgreSQL/PostGIS if the website needs spatial querying;
- static site search index for early prototypes.

Do not start with the website. Start with reliable data.

## 13. First sprint checklist

The first sprint should produce a small but real improvement to the corpus infrastructure.

- [ ] Create repository with the layout above.
- [ ] Place the three Zenodo ZIPs under `data/raw/`.
- [ ] Add a script to unpack and inventory the ZIPs.
- [ ] Extract all structured corpus `.txt` files.
- [ ] Generate count reports by volume.
- [ ] Extract all `REFERENCES:` fields.
- [ ] Produce `raw_references.tsv`, `reference_occurrences.tsv`, and `bibliography_candidates.tsv`.
- [ ] Write `bibliography_normalization_notes.md`.
- [ ] Add parser tests for five structured corpus files.
- [ ] Add parser tests for two Sagaing entries.
- [ ] Add parser tests for two Recently Found entries or volume 7 crosswalk examples.
- [ ] Decide whether the next sprint should focus on Sagaing conversion or bibliography-source matching.

Recommended order:

1. bibliography extraction from the existing structured corpus;
2. Sagaing parser prototype;
3. Thein Tun / volume 7 coverage audit;
4. local library source matching;
5. OCR pipeline;
6. published translation ingestion;
7. controlled AI translation pipeline;
8. release data model;
9. website prototype.
