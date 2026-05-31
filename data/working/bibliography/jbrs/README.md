# JBRS working metadata

This directory stores working metadata for the *Journal of the Burma Research Society* (JBRS) reference hunt, local-file matching, OCR planning, and translation-candidate triage. It does **not** store source PDFs, page images, or full OCR text.

## Typical workflow
1. Build the repository reference hunt: `python3 scripts/build_jbrs_reference_hunt.py`
2. Scan one or more external-drive roots without committing absolute paths: `python3 scripts/build_jbrs_local_manifest.py --root "/Volumes/ExternalDrive/JBRS" --root "/Volumes/ExternalDrive/Burmese"`
3. Match references to local files: `python3 scripts/match_jbrs_references_to_local_files.py`
4. Build the OCR batch/status plan: `python3 scripts/plan_jbrs_ocr_batches.py`
5. Dry-run the Google Vision workflow: `python3 scripts/ocr_jbrs_google_vision.py --dry-run --limit 5`
6. Detect translation candidates from existing text or OCR text: `python3 scripts/detect_jbrs_translation_candidates.py`

## Local OCR output location
- Preferred local output root: `data_local/ocr/jbrs/`
- Recommended subdirectories: `manifest/`, `google_vision_json/`, `page_text/`, `article_text/`, `logs/`

## Safe to commit
- TSV manifests and match logs in this directory
- JSON summaries
- README and scripts
- short evidence snippets only

## Must not be committed
- source PDFs or page images
- full OCR text or long extracted passages
- Nathan's absolute external-drive paths
- Google credentials, API keys, or service-account secrets

## Guardrails
- The Berkeley IOB catalogue record is not a verified local witness.
- The IOB plate portfolios are not the missing companion text witness.
- SIP does not satisfy the separate UEM witness gap.
- JBRS translation-candidate rows are only review leads; do not treat OCR snippets or English prose as verified translation coverage.
