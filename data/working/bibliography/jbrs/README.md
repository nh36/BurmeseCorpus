# JBRS working metadata

This directory stores working metadata for the *Journal of the Burma Research Society* (JBRS) reference hunt, local-file matching, OCR planning, and translation-candidate triage. It does **not** store source PDFs, page images, Google Vision JSON, or raw `data_local/` OCR payloads.

## Core workflow
1. Build raw and clean article references: `python3 scripts/build_jbrs_reference_hunt.py`
2. Build or refresh the redacted manifest: `python3 scripts/build_jbrs_local_manifest.py`
3. Write a local runtime path cache when you have live roots available: `python3 scripts/build_jbrs_local_manifest.py --root "/path/to/jbrs/root" --write-runtime-path-cache`
4. Match clean article targets to local files: `python3 scripts/match_jbrs_references_to_local_files.py`
5. Build the OCR plan and status log: `python3 scripts/plan_jbrs_ocr_batches.py`
6. Run OCR preflight before live submission: `python3 scripts/preflight_jbrs_ocr.py --limit 5`
7. Dry-run the Google Vision workflow: `python3 scripts/ocr_jbrs_google_vision.py --dry-run --limit 5`
8. Run live Google Vision OCR only after preflight passes: `python3 scripts/ocr_jbrs_google_vision.py --execute --limit 5`
9. Refresh conservative translation-candidate leads: `python3 scripts/detect_jbrs_translation_candidates.py`
10. Review article-target cleanup in `jbrs_article_reference_targets_review.tsv` before trusting unresolved bibliographic rows.
11. Review candidate outcomes in `jbrs_translation_candidate_review.tsv` before treating any OCR hit as translation-bearing.

## Runtime path cache
- Local runtime cache path: `data_local/ocr/jbrs/manifest/jbrs_runtime_path_map.json`
- The committed TSV keeps redacted path stubs only.
- The runtime cache maps `local_file_id -> absolute local path` and must stay gitignored.

## Local OCR output location
- Preferred local output root: `data_local/ocr/jbrs/`
- Subdirectories used by the live OCR workflow:
  - `manifest/`
  - `google_vision_json/`
  - `page_text/`
  - `article_text/`
  - `logs/`

## Safe to commit
- TSV manifests and match logs in this directory
- JSON summaries
- README and scripts
- short evidence snippets only
- compact OCR-derived published source/translation units when they are clearly marked as OCR-derived extraction output and linked to source metadata

## Must not be committed
- source PDFs or page images
- raw `data_local/` OCR article_text/page_text dumps or Google Vision runtime payloads
- Google Vision JSON payloads
- Nathan's absolute external-drive paths
- Google credentials, API keys, or service-account secrets

## Guardrails
- The Berkeley IOB catalogue record is not a verified local witness.
- The IOB plate portfolios are not the missing companion text witness.
- SIP does not satisfy the separate UEM witness gap.
- Translation candidates are review leads only; do not treat OCR snippets or English prose as verified translation coverage.
