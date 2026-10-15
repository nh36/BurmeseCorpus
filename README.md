# Old Burmese Inscriptions Corpus

A structured, provenance-aware corpus of Old Burmese stone inscriptions for research in historical linguistics, philology, epigraphy, and the history of Myanmar.

This repository develops **[A Structured Corpus of Old Burmese Stone Inscriptions](https://doi.org/10.5281/zenodo.4321314)** alongside two supplementary inscription collections. It provides machine-readable inscription metadata and texts, line-level data, source cross-references, validation tools, and ongoing work on bibliographic authorities and published translations. The aim is to make evidence inspectable and reusable without obscuring the distinction between a source reading and a later editorial decision.

## Start here

The current **validated, whole-corpus baseline** is [`data/release/corpus_release_v0_3/`](data/release/corpus_release_v0_3/). You can work with the files in that directory without rebuilding the corpus.

| Measure | Release v0.3 |
| --- | ---: |
| Inscription-level records | **1,152** |
| Line-level records | **24,299** |
| Structured OBI records | 1,121 |
| Supplementary Sagaing records | 31 |
| Editorial relations with *Recently Found Inscriptions* | 3 |

These are **data-record counts**, not a count of unique stones or archaeological monuments: a record can represent an inscription face or text unit. The figures are taken from the [release manifest](data/release/corpus_release_v0_3/release_manifest.json) and [validation report](data/release/corpus_release_v0_3/validation_report.json).

**The canonical release data are `inscriptions.jsonl` and `lines.jsonl`.** The SQLite database is a derived convenience export. Later enrichment and translation files in `data/working/` are research candidates, not replacements for the validated baseline.

### Explore the data

Clone the repository:

```bash
git clone https://github.com/nh36/BurmeseCorpus.git
cd BurmeseCorpus
```

The release is already included. You can inspect inscription metadata using Python's standard-library SQLite module:

```python
import sqlite3

db = "data/release/corpus_release_v0_3/corpus_release.sqlite"
with sqlite3.connect(db) as connection:
    rows = connection.execute(
        """
        SELECT record_id, title_original, date_original
        FROM inscriptions
        ORDER BY record_id
        LIMIT 10
        """
    )
    for record in rows:
        print(record)
```

Or read the authoritative JSONL directly:

```python
import json

path = "data/release/corpus_release_v0_3/inscriptions.jsonl"
with open(path, encoding="utf-8") as source:
    for line in source:
        record = json.loads(line)
        print(record["record_id"], record.get("title_original"))
        break
```

Join `lines.jsonl` to `inscriptions.jsonl` on `record_id`; individual lines have their own `line_id`. Field definitions and identifier conventions are documented in [the field dictionary](docs/field_dictionary.md) and [data model](docs/data_model.md).

## Sources and provenance

The corpus draws on three Zenodo deposits. Their different relationships to the release matter:

| Source | Identifier | Role in v0.3 |
| --- | --- | --- |
| *A Structured Corpus of Old Burmese Stone Inscriptions* (OBI) | [10.5281/zenodo.4321314](https://doi.org/10.5281/zenodo.4321314) | Canonical structured base: 1,121 records and 23,696 lines |
| Thein Tun, *Recently Found Burmese Inscriptions* (`နှောင်းတွေ့ကျောက်စာများ`) | [10.5281/zenodo.1302525](https://doi.org/10.5281/zenodo.1302525) | Supplementary source checked against OBI volume 7; three editorial relations, with no duplicated canonical records added |
| *Newly Found Inscriptions in the Sagaing Region* (`စစ်ကိုင်းတိုင်းဒေသကြီးအတွင်းရှိအသစ်တွေ့ကျောက်စာများ`) | [10.5281/zenodo.1203709](https://doi.org/10.5281/zenodo.1203709) | Supplementary structured data: 31 records and 603 lines |

The original structured OBI dataset credits **U Nyein Maung, Jennifer Lewis-Wong, Khin Khin Zaw, Patrick McCormick, and Nathan W. Hill**. Consult the DOI records for the full source metadata and preferred citations. The OBI corpus is itself substantially based on the published *Ancient Burmese Inscriptions* collection; this repository does not replace the underlying editions.

The [source registry](data/release/corpus_release_v0_3/sources.jsonl) records each deposit's role, contributions and processing scripts.

### Editorial treatment

- OBI records preserve their `obi-...` identifiers, original text and transliteration, original metadata, and source-file provenance.
- Sagaing records retain `sagaing-...` identifiers. Their correspondence to the OBI numbering and external catalogues has **not** been fully reconciled.
- Thein Tun's *Recently Found* collection overlaps with OBI volume 7. Entries **12** and **37** are treated as embedded-in-earlier-record cases rather than silently emitted as additional inscriptions; entry **21** is retained as a title-variant relationship. These decisions are documented in [`editorial_relations.jsonl`](data/release/corpus_release_v0_3/editorial_relations.jsonl).
- Diplomatic source text, transliteration, normalisation, bibliography, and translation are distinct evidential layers. A proposed cross-reference or translation should not overwrite the source text.

For detailed editorial choices, see the [release notes](data/release/corpus_release_v0_3/release_notes.md) and [Phase 1 closeout](docs/phase1_closeout.md).

## Repository layout

```text
4321314/              Original structured OBI deposit material
1302525/              Recently Found source text
1203709/              Sagaing source text
data/
  raw/                Intended immutable raw-source staging area
  extracted/          Parsed source data and inventories
  release/            Validated corpus releases (v0.3 is the baseline)
  working/            Bibliography, witness, OCR, translation and QA work
docs/                 Data model, field dictionary and research workflows
schemas/              JSON schemas for corpus and downstream data
scripts/              Parsers, builders, audits, enrichment and validation
tests/                Parser and workflow tests
```

The original Zenodo materials are currently organised under directories named for their deposit IDs. `data/raw/` is a target staging area, not a sign that those source directories have been moved. The OBI transliteration table is [`4321314/OBI_Translit_System.tsv`](4321314/OBI_Translit_System.tsv).

### Main v0.3 release files

| File | Purpose |
| --- | --- |
| [`inscriptions.jsonl`](data/release/corpus_release_v0_3/inscriptions.jsonl) | Inscription-level metadata, source text fields, identifiers and provenance |
| [`lines.jsonl`](data/release/corpus_release_v0_3/lines.jsonl) | Numbered lines, Burmese text and transliteration |
| [`editorial_relations.jsonl`](data/release/corpus_release_v0_3/editorial_relations.jsonl) | Explicit decisions about overlapping or variant source records |
| [`sources.jsonl`](data/release/corpus_release_v0_3/sources.jsonl) | Deposit-level source registry |
| [`release_manifest.json`](data/release/corpus_release_v0_3/release_manifest.json) | Release inputs, counts, status and limitations |
| [`corpus_release.sqlite`](data/release/corpus_release_v0_3/corpus_release.sqlite) | Regenerable SQLite export with `inscriptions`, `lines`, `editorial_relations` and `sources` tables |

## Rebuilding and validation

Most core parsing and release tools use Python's standard library. Run scripts from the repository root. The checked-in release is available immediately, but **re-extracting the structured OBI base requires the seven `OBI_Corpus_Vol1.zip` through `OBI_Corpus_Vol7.zip` archives** from [Zenodo 4321314](https://doi.org/10.5281/zenodo.4321314). Place them in `4321314/`. ZIP files are excluded by `.gitignore` and are not included in a fresh clone.

Once these archives are present, the principal release-generation sequence is:

```bash
python3 scripts/extract_structured_corpus.py
python3 scripts/parse_recently_found.py
python3 scripts/parse_recently_found_records.py
python3 scripts/audit_inventory.py
python3 scripts/parse_sagaing.py
python3 scripts/merge_unified_release.py
python3 scripts/build_corpus_release.py
python3 scripts/validate_corpus.py --dataset data/release/corpus_release_v0_3
```

This uses the checked-in editorial override and release-policy files. To validate **only the existing release**, without re-extracting the sources, run:

```bash
python3 scripts/validate_corpus.py --dataset data/release/corpus_release_v0_3
```

The Python test suite can be run with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

For the complete dependency order, optional review stages, expected outputs and post-release bibliography steps, consult [`docs/release_workflow.md`](docs/release_workflow.md). Some specialised OCR and local-source discovery workflows additionally require external source files, services or machine-specific configuration.

## Work in progress

The repository also contains substantial **Phase 2 research work**. It should be interpreted according to its evidence and review status:

- **Bibliography and source authority:** parsing original reference strings, resolving source families and abbreviations, assembling BibTeX authorities, and retaining uncertain matches for human review. See [BibTeX authority documentation](docs/phase2_bibtex_authority.md).
- **Published source and translation discovery:** distinguishing actual editions, plates, cross-references, partial translations, and mere bibliographic leads. See [translation-source discovery](docs/phase2_translation_source_discovery.md).
- **OCR and witness verification:** storing auditable, source-linked evidence rather than equating a matching filename or unsuccessful OCR attempt with confirmation.
- **Corpus enrichment:** a [draft v0.4 candidate](data/working/corpus_enrichment/release_candidate_v0_4/release_notes_v0_4_draft.md) incorporates reviewed cross-references and some published translations. Its current draft notes report 69 enriched records, including 27 with integrated translations. **It has not superseded v0.3 as the validated release.**

The project does not yet claim comprehensive translations, definitive bibliography/place/date/name authorities, a completed Sagaing crosswalk, or a public search interface. In particular, a missing translation in the release must not be mistaken for evidence that no translation has ever been published.

## Research use, citation and rights

For reproducible research, identify **the repository commit and corpus release (`corpus_release_v0_3`)**, and cite the **underlying Zenodo deposit or publication** relevant to the inscriptions used. Bibliographical and source details can be traced through `sources.jsonl`, the per-record provenance fields, and the original source references.

This repository currently has **no top-level `LICENSE` file**. Its availability on GitHub does not itself establish uniform reuse rights over code, transcriptions, scanned sources, editions or third-party translations. Before redistribution, consult the rights statements of the relevant source deposits and underlying publications. Please preserve attribution, original reference strings, source identifiers and explicit uncertainty when deriving new datasets.

## Contributing

Corrections to transcriptions, uncertain alignments, bibliographic attributions and translation evidence are welcome through [GitHub issues](https://github.com/nh36/BurmeseCorpus/issues) or pull requests. Useful reports identify the `record_id` or `line_id`, the relevant source and page, and the precise proposed change with supporting evidence. Source readings and editorial interpretation should be recorded separately.

See [the project brief](obi_next_phase_project_init.md) for the longer-term research programme.
