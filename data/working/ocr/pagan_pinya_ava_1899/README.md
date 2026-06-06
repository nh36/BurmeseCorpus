# TN 1899 OCR (tracked outputs)

This directory tracks reusable OCR derivatives for:

**U Tun Nyein / Taw Sein Ko / Forchhammer, _Inscriptions of Pagan, Pinya and Ava: Translation, with Notes_ (Rangoon: Government Press, 1899).**

Selected source PDF:

- `hvd-hxx68w-1780753436.pdf` (stored in local, gitignored workspace under `data/local/pagan_pinya_ava_ocr/source/`)

## Tracked files in this directory

- `ocr_plain_text_with_page_breaks.txt`
- `ocr_cleaned_text_light.txt`
- `ocr_report.md`
- `comparison_report.md`
- `source_selection_report.md`
- `ocr_metadata_index.json`
- `pdf_quality_assessment.json`
- `run_vision_ocr_pipeline.py`

## Rerun workflow

From repository root:

```bash
python3 data/working/ocr/pagan_pinya_ava_1899/run_vision_ocr_pipeline.py
```

If local OCR outputs already exist and you only want to resync/sanitize tracked files:

```bash
python3 data/working/ocr/pagan_pinya_ava_1899/run_vision_ocr_pipeline.py --sync-only
```

## Deliberately untracked artifacts

These remain in `data/local/pagan_pinya_ava_ocr/` and are not committed:

- source PDFs and ZIP files
- rendered page images
- raw per-page Google Vision JSON
- runtime caches and temporary OCR batch logs
- credentials, API keys, and machine-local absolute paths
