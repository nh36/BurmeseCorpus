from __future__ import annotations

import argparse
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl, read_tsv, write_jsonl, write_tsv

SIP_SOURCE_KEY = "sipSelectionsPagan"
SIP_BIBLIOGRAPHIC_LABEL = "Pe Maung Tin and G. H. Luce, Selections from the Inscriptions of Pagan, 1928"

TN_SOURCE_KEY = "tnInscriptionsPaganPinyaAva"
TN_BIBLIOGRAPHIC_LABEL = (
    "U Tun Nyein, Inscriptions of Pagan, Pinya and Ava. Translation, with Notes, Rangoon, 1899"
)

SIP_QC_TO_WITNESS_STATUS = {
    "clean_for_review": "ocr_clean_for_review",
    "clean_with_unclear_markers": "ocr_with_unclear_markers",
    "contains_possible_page_artifact": "contains_possible_page_artifact",
    "needs_human_text_check": "needs_manual_text_check",
}

PREVIEW_FIELDS = [
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "language",
    "has_existing_transcription",
    "has_source_text_witness",
    "source_text_witness_count",
    "has_translation",
    "translation_status",
    "translation_candidate_sources",
    "sip_ref",
    "iob_plate",
    "comparison_status",
    "preview_note",
]


def join_nonempty(parts: list[str]) -> str:
    return " | ".join(part for part in parts if part)


def build_source_locator(row: dict) -> str:
    return join_nonempty(
        [
            row.get("sip_ref", "").strip(),
            row.get("iob_plate", "").strip(),
            row.get("list_ref", "").strip(),
        ]
    )


def maybe_tn_candidate(row: dict, base_record: dict) -> list[dict]:
    references_original = (base_record.get("references_original") or "").casefold()
    tn_ref = (row.get("tn_ref") or "").strip()
    has_tn_evidence = bool(tn_ref) or "tn" in references_original
    if not has_tn_evidence:
        return []
    locator_hint = tn_ref if tn_ref else "TN locator present in references_original; see source citation inventory."
    return [
        {
            "source_key": TN_SOURCE_KEY,
            "source_bibliographic_label": TN_BIBLIOGRAPHIC_LABEL,
            "source_locator_hint": locator_hint,
            "status": "missing_high_value_source",
            "basis": "Existing corpus/SIP citation evidence points to TN, but no local TN file is currently available.",
        }
    ]


def witness_from_row(row: dict) -> dict:
    qc_status = row.get("accepted_export_qc_status", "")
    witness_status = SIP_QC_TO_WITNESS_STATUS.get(qc_status, "needs_manual_text_check")
    notes_parts = [row.get("accepted_export_qc_notes", "").strip(), row.get("notes", "").strip()]
    notes = " | ".join(part for part in notes_parts if part)
    return {
        "sip_inscription_unit_id": row.get("sip_inscription_unit_id", ""),
        "source_key": SIP_SOURCE_KEY,
        "source_bibliographic_label": SIP_BIBLIOGRAPHIC_LABEL,
        "source_locator": build_source_locator(row),
        "witness_text_raw": row.get("raw_ocr_text", ""),
        "witness_text_cleaned": row.get("cleaned_witness_text", ""),
        "witness_status": witness_status,
        "comparison_status": row.get("comparison_status", ""),
        "notes": notes,
    }


def build_enriched_records(inscriptions: list[dict], sip_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    sip_by_record: dict[str, list[dict]] = {}
    for row in sip_rows:
        record_id = row.get("linked_corpus_record_id", "").strip()
        if not record_id:
            continue
        sip_by_record.setdefault(record_id, []).append(row)

    enriched_records: list[dict] = []
    preview_rows: list[dict] = []
    for record in inscriptions:
        record_id = record.get("record_id", "")
        sip_record_rows = sip_by_record.get(record_id, [])
        if not sip_record_rows:
            enriched_records.append(record)
            continue

        enriched = dict(record)
        witnesses = [witness_from_row(row) for row in sip_record_rows]
        has_tn_candidate = any(maybe_tn_candidate(row, record) for row in sip_record_rows)
        translation_candidates: list[dict] = []
        for row in sip_record_rows:
            translation_candidates.extend(maybe_tn_candidate(row, record))

        if has_tn_candidate:
            translation_status = "translation_source_missing"
            enrichment_status = "enriched_with_sip_and_candidates"
        else:
            translation_status = "no_translation_known"
            enrichment_status = "enriched_with_sip_witnesses"

        enriched["source_text_witnesses"] = witnesses
        enriched["translations"] = []
        enriched["translation_status"] = translation_status
        if translation_candidates:
            # Keep order stable but avoid duplicate candidate objects.
            seen = set()
            deduped: list[dict] = []
            for candidate in translation_candidates:
                key = (
                    candidate.get("source_key", ""),
                    candidate.get("source_locator_hint", ""),
                    candidate.get("status", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(candidate)
            enriched["translation_source_candidates"] = deduped
        enriched["enrichment_status"] = enrichment_status
        enriched["enrichment_notes"] = (
            f"Enriched from accepted SIP witness units ({len(witnesses)} unit(s)); "
            f"existing corpus fields preserved without overwriting transcription."
        )

        enriched_records.append(enriched)

        preview_rows.append(
            {
                "linked_corpus_record_id": record_id,
                "linked_inscription_id": sip_record_rows[0].get("linked_inscription_id", ""),
                "title_or_label": record.get("title_original", "") or record.get("title_transliteration", ""),
                "language": record.get("language_original", ""),
                "has_existing_transcription": "true" if record.get("full_transliteration") else "false",
                "has_source_text_witness": "true",
                "source_text_witness_count": str(len(witnesses)),
                "has_translation": "true" if enriched.get("translations") else "false",
                "translation_status": translation_status,
                "translation_candidate_sources": "; ".join(
                    candidate.get("source_key", "") for candidate in enriched.get("translation_source_candidates", [])
                ),
                "sip_ref": "; ".join(
                    sorted({row.get("sip_ref", "").strip() for row in sip_record_rows if row.get("sip_ref", "").strip()})
                ),
                "iob_plate": "; ".join(
                    sorted(
                        {
                            row.get("iob_plate", "").strip()
                            for row in sip_record_rows
                            if row.get("iob_plate", "").strip()
                        }
                    )
                ),
                "comparison_status": "; ".join(
                    sorted(
                        {
                            row.get("comparison_status", "").strip()
                            for row in sip_record_rows
                            if row.get("comparison_status", "").strip()
                        }
                    )
                ),
                "preview_note": "SIP source-text witness integrated; translation metadata explicit.",
            }
        )
    return enriched_records, preview_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-inscriptions",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "corpus_release_v0_3" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--sip-accepted-path",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "sip_accepted_witness_units.tsv",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "inscriptions_enriched_candidate.jsonl",
    )
    parser.add_argument(
        "--output-preview-tsv",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "enriched_candidate_preview.tsv",
    )
    args = parser.parse_args()

    inscriptions = read_jsonl(args.input_inscriptions)
    sip_rows = read_tsv(args.sip_accepted_path)

    enriched_records, preview_rows = build_enriched_records(inscriptions, sip_rows)
    write_jsonl(args.output_jsonl, enriched_records)
    write_tsv(args.output_preview_tsv, preview_rows, PREVIEW_FIELDS)
    print(
        f"Wrote {len(enriched_records)} enriched records and {len(preview_rows)} preview rows "
        f"from {len(sip_rows)} accepted SIP units."
    )


if __name__ == "__main__":
    main()
