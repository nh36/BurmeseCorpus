# Translation source discovery

This directory contains working-state artifacts for translation-source discovery, witness verification, acquisition tracking, and human review routing. It is a working layer, not release data.

## Authoritative current-state files
- `translation_source_discovery_phase_summary.md`
- `direct_witness_acquisition_status.tsv`
- `human_acquisition_checklist.tsv`
- `acquisition_action_queue.tsv`
- `source_work_witness_gaps.tsv`
- `next_actions_index.tsv`

## Evidence and log layers
- `external_catalogue_search_log.tsv`
- `external_catalogue_candidate_triage.tsv`
- `witness_hunt_candidate_triage.tsv`
- `ruled_out_witness_candidates.tsv`

## Guardrails
- The Berkeley IOB catalogue record is not a verified local witness.
- The IOB plate portfolios are not the missing companion text witness.
- SIP does not satisfy the separate UEM witness gap.
- Do not infer translation coverage from OCR fragments or generic English prose.
