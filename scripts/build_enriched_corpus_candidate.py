from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_common import REPO_ROOT, read_jsonl, read_tsv, write_jsonl, write_tsv

SIP_SOURCE_KEY = "sipSelectionsPagan"
SIP_BIBLIOGRAPHIC_LABEL = "Pe Maung Tin and G. H. Luce, Selections from the Inscriptions of Pagan, 1928"
TN_SOURCE_KEY = "tnInscriptionsPaganPinyaAva"
TN_BIBLIOGRAPHIC_LABEL = "U Tun Nyein, Inscriptions of Pagan, Pinya and Ava: Translation, with Notes, Rangoon, 1899"
PPA_SOURCE_KEY = "ppaCatalogue"
PPA_BIBLIOGRAPHIC_LABEL = "Inscriptions of Pagan, Pinya and Ava, Rangoon, 1892"
IOB_SOURCE_KEY = "lucePeMaungTinInscriptionsOfBurma"
IOB_BIBLIOGRAPHIC_LABEL = "G. H. Luce and U Pe Maung Tin, Inscriptions of Burma"
LIST_SOURCE_KEY = "duroiselle1921list"
LIST_BIBLIOGRAPHIC_LABEL = "Charles Duroiselle, List of Inscriptions Found in Burma"
UB_SOURCE_KEY = "ubSourceFamily"
UB_BIBLIOGRAPHIC_LABEL = "Inscriptions Collected in Upper Burma"
JBRS_SOURCE_KEY = "journalBurmaResearchSociety"
JBRS_BIBLIOGRAPHIC_LABEL = "Journal of the Burma Research Society"

SOURCE_LABELS = {
    SIP_SOURCE_KEY: SIP_BIBLIOGRAPHIC_LABEL,
    TN_SOURCE_KEY: TN_BIBLIOGRAPHIC_LABEL,
    PPA_SOURCE_KEY: PPA_BIBLIOGRAPHIC_LABEL,
    IOB_SOURCE_KEY: IOB_BIBLIOGRAPHIC_LABEL,
    LIST_SOURCE_KEY: LIST_BIBLIOGRAPHIC_LABEL,
    UB_SOURCE_KEY: UB_BIBLIOGRAPHIC_LABEL,
    JBRS_SOURCE_KEY: JBRS_BIBLIOGRAPHIC_LABEL,
}

SOURCE_ROLE_BY_KEY = {
    IOB_SOURCE_KEY: "cross_reference_or_plate_witness",
    LIST_SOURCE_KEY: "catalogue_or_list",
    PPA_SOURCE_KEY: "source_text_or_edition_candidate",
    TN_SOURCE_KEY: "translation_candidate",
    SIP_SOURCE_KEY: "source_text_witness",
    UB_SOURCE_KEY: "catalogue_or_list",
    JBRS_SOURCE_KEY: "commentary_witness",
}

STATUS_BY_KEY = {
    IOB_SOURCE_KEY: "linked",
    LIST_SOURCE_KEY: "cited_or_cross_referenced",
    PPA_SOURCE_KEY: "missing_high_value_source",
    TN_SOURCE_KEY: "missing_high_value_source",
    SIP_SOURCE_KEY: "linked",
    UB_SOURCE_KEY: "cited_or_cross_referenced",
    JBRS_SOURCE_KEY: "cited_or_cross_referenced",
}

WITNESS_STATUS_BY_QC = {
    "clean_for_review": "ocr_clean_for_review",
    "clean_with_unclear_markers": "ocr_with_unclear_markers",
    "contains_possible_page_artifact": "contains_possible_page_artifact",
    "needs_human_text_check": "needs_manual_text_check",
}

ENRICHMENT_STATUSES = {
    "baseline_no_enrichment",
    "enriched_with_bibliographic_crossrefs",
    "enriched_with_bibliographic_crossrefs_and_candidates",
    "enriched_with_sip_witnesses",
    "enriched_with_sip_and_crossrefs",
    "enriched_with_sip_and_candidates",
}

TRANSLATION_STATUSES = {
    "no_translation_known",
    "translation_source_missing",
    "translation_available_unintegrated",
    "translation_integrated",
    "translation_needs_review",
}

WITNESS_STATUSES = {
    "ocr_clean_for_review",
    "ocr_with_unclear_markers",
    "contains_possible_page_artifact",
    "needs_manual_text_check",
}

TRANSLATION_CANDIDATE_STATUSES = {
    "missing_high_value_source",
    "candidate_source_located",
    "candidate_source_review_pending",
}

PREVIEW_FIELDS = [
    "linked_corpus_record_id",
    "linked_inscription_id",
    "title_or_label",
    "language",
    "has_existing_transcription",
    "has_source_text_witness",
    "source_text_witness_count",
    "has_bibliographic_crossrefs",
    "crossref_sources",
    "has_translation",
    "translation_status",
    "translation_candidate_sources",
    "translation_candidate_locators",
    "sip_ref",
    "iob_plate",
    "list_ref",
    "ppa_ref",
    "tn_ref",
    "comparison_status",
    "preview_note",
]

SUMMARY_FIELDS = [
    "total_records",
    "records_with_any_enrichment",
    "records_with_sip_source_text_witness",
    "records_with_iob_crossref",
    "records_with_list_crossref",
    "records_with_ppa_candidate",
    "records_with_tn_translation_candidate",
    "records_with_translation_status_no_translation_known",
    "records_with_translation_status_translation_source_missing",
    "records_with_translation_integrated",
    "records_with_existing_full_transliteration",
]


def join_unique(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return "; ".join(seen)


def source_label(source_key: str) -> str:
    return SOURCE_LABELS.get(source_key, source_key)


def build_crossref_entry(source_key: str, source_locator: str, basis: str) -> dict:
    return {
        "source_key": source_key,
        "source_label": source_label(source_key),
        "source_locator": source_locator,
        "source_role": SOURCE_ROLE_BY_KEY[source_key],
        "status": STATUS_BY_KEY[source_key],
        "basis": basis,
    }


def build_crossrefs_from_iob_row(row: dict) -> tuple[list[dict], dict]:
    crossrefs: list[dict] = []
    candidate_summary = {
        "has_sip": False,
        "has_tn_candidate": False,
        "has_list": False,
        "has_ppa_candidate": False,
        "has_iob": False,
        "has_ub": False,
        "has_jbrs": False,
    }

    plate = (row.get("iob_plate") or "").strip()
    linked_record_id = (row.get("linked_corpus_record_id") or "").strip()
    if linked_record_id and plate:
        crossrefs.append(
            build_crossref_entry(
                IOB_SOURCE_KEY,
                plate,
                "IOB cross-reference index linked to structured corpus record.",
            )
        )
        candidate_summary["has_iob"] = True

    field_specs = [
        (LIST_SOURCE_KEY, "list_ref", "IOB cross-reference index gives List reference."),
        (PPA_SOURCE_KEY, "ppa_ref", "IOB cross-reference index gives PPA reference."),
        (TN_SOURCE_KEY, "tn_ref", "IOB cross-reference index gives TN reference."),
        (SIP_SOURCE_KEY, "sip_ref", "IOB cross-reference index gives SIP reference."),
        (UB_SOURCE_KEY, "ub_ref", "IOB cross-reference index gives UB reference."),
        (JBRS_SOURCE_KEY, "jbrs_ref", "IOB cross-reference index gives JBRS reference."),
    ]
    for source_key, field_name, basis in field_specs:
        value = (row.get(field_name) or "").strip()
        if not value:
            continue
        crossrefs.append(build_crossref_entry(source_key, value, basis))
        if source_key == LIST_SOURCE_KEY:
            candidate_summary["has_list"] = True
        elif source_key == PPA_SOURCE_KEY:
            candidate_summary["has_ppa_candidate"] = True
        elif source_key == TN_SOURCE_KEY:
            candidate_summary["has_tn_candidate"] = True
        elif source_key == SIP_SOURCE_KEY:
            candidate_summary["has_sip"] = True
        elif source_key == UB_SOURCE_KEY:
            candidate_summary["has_ub"] = True
        elif source_key == JBRS_SOURCE_KEY:
            candidate_summary["has_jbrs"] = True

    return crossrefs, candidate_summary


def build_sip_witness(row: dict) -> dict:
    qc_status = row.get("accepted_export_qc_status", "")
    witness_status = WITNESS_STATUS_BY_QC.get(qc_status, "needs_manual_text_check")
    notes = " | ".join(
        part
        for part in [row.get("accepted_export_qc_notes", "").strip(), row.get("notes", "").strip()]
        if part
    )
    return {
        "sip_inscription_unit_id": row.get("sip_inscription_unit_id", ""),
        "source_key": SIP_SOURCE_KEY,
        "source_bibliographic_label": SIP_BIBLIOGRAPHIC_LABEL,
        "source_locator": " | ".join(
            part
            for part in [row.get("sip_ref", "").strip(), row.get("iob_plate", "").strip(), row.get("list_ref", "").strip()]
            if part
        ),
        "witness_text_raw": row.get("raw_ocr_text", ""),
        "witness_text_cleaned": row.get("cleaned_witness_text", ""),
        "witness_status": witness_status,
        "comparison_status": row.get("comparison_status", ""),
        "notes": notes,
        "provenance": {
            "source_file": "data/working/bibliography/sip_accepted_witness_units.tsv",
            "sip_inscription_unit_id": row.get("sip_inscription_unit_id", ""),
            "accepted_export_qc_status": qc_status,
            "accepted_export_qc_notes": row.get("accepted_export_qc_notes", ""),
        },
    }


def build_translation_candidates(crossrefs: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for entry in crossrefs:
        if entry["source_key"] != TN_SOURCE_KEY:
            continue
        candidates.append(
            {
                "source_key": TN_SOURCE_KEY,
                "source_bibliographic_label": TN_BIBLIOGRAPHIC_LABEL,
                "source_locator_hint": entry["source_locator"],
                "status": "missing_high_value_source",
                "basis": "IOB cross-reference index gives a TN reference, but no local TN file is currently available.",
            }
        )
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for candidate in candidates:
        key = (
            candidate["source_key"],
            candidate["source_locator_hint"],
            candidate["status"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def choose_enrichment_status(has_sip: bool, has_crossrefs: bool, has_tn_candidates: bool) -> str:
    if has_sip and has_tn_candidates:
        return "enriched_with_sip_and_candidates"
    if has_sip and has_crossrefs:
        return "enriched_with_sip_and_crossrefs"
    if has_sip:
        return "enriched_with_sip_witnesses"
    if has_crossrefs and has_tn_candidates:
        return "enriched_with_bibliographic_crossrefs_and_candidates"
    if has_crossrefs:
        return "enriched_with_bibliographic_crossrefs"
    return "baseline_no_enrichment"


def build_preview_row(record: dict, sip_rows: list[dict], crossrefs: list[dict], translation_candidates: list[dict]) -> dict:
    source_text_witnesses = sip_rows
    crossref_labels = [entry["source_label"] for entry in crossrefs]
    candidate_labels = [candidate["source_bibliographic_label"] for candidate in translation_candidates]
    candidate_locators = [candidate["source_locator_hint"] for candidate in translation_candidates]
    record_sip_refs = [row.get("sip_ref", "") for row in sip_rows]
    record_iob_plates = [row.get("iob_plate", "") for row in sip_rows]
    record_list_refs = [row.get("list_ref", "") for row in sip_rows]
    record_ppa_refs = [row.get("ppa_ref", "") for row in sip_rows]
    record_tn_refs = [row.get("tn_ref", "") for row in sip_rows]

    if sip_rows and crossrefs:
        preview_note = "SIP source-text witness and IOB cross-reference enrichment."
    elif sip_rows:
        preview_note = "SIP source-text witness integrated."
    elif crossrefs and translation_candidates:
        preview_note = "IOB cross-reference enrichment with TN translation candidate."
    else:
        preview_note = "IOB cross-reference enrichment."

    translation_status = "translation_source_missing" if translation_candidates else "no_translation_known"

    return {
        "linked_corpus_record_id": record["record_id"],
        "linked_inscription_id": (sip_rows[0].get("linked_inscription_id", "") if sip_rows else record["record_id"]),
        "title_or_label": record.get("title_original", "") or record.get("title_transliteration", ""),
        "language": record.get("language_original", ""),
        "has_existing_transcription": "true" if record.get("full_transliteration") else "false",
        "has_source_text_witness": "true" if sip_rows else "false",
        "source_text_witness_count": str(len(sip_rows)),
        "has_bibliographic_crossrefs": "true" if crossrefs else "false",
        "crossref_sources": join_unique(crossref_labels),
        "has_translation": "true" if record.get("translations") else "false",
        "translation_status": translation_status,
        "translation_candidate_sources": join_unique(candidate_labels),
        "translation_candidate_locators": join_unique(candidate_locators),
        "sip_ref": join_unique(record_sip_refs),
        "iob_plate": join_unique(record_iob_plates),
        "list_ref": join_unique(record_list_refs),
        "ppa_ref": join_unique(record_ppa_refs),
        "tn_ref": join_unique(record_tn_refs),
        "comparison_status": join_unique([row.get("comparison_status", "") for row in sip_rows]),
        "preview_note": preview_note,
    }


def build_enriched_records(
    inscriptions: list[dict],
    sip_rows: list[dict],
    crossref_rows: list[dict],
) -> tuple[list[dict], list[dict], dict[str, int]]:
    sip_by_record: dict[str, list[dict]] = {}
    for row in sip_rows:
        record_id = (row.get("linked_corpus_record_id") or "").strip()
        if record_id:
            sip_by_record.setdefault(record_id, []).append(row)

    crossref_by_record: dict[str, list[dict]] = {}
    iob_rows_by_record: dict[str, list[dict]] = {}
    for row in crossref_rows:
        record_id = (row.get("linked_corpus_record_id") or "").strip()
        if not record_id:
            continue
        iob_rows_by_record.setdefault(record_id, []).append(row)

    enriched_records: list[dict] = []
    preview_rows: list[dict] = []
    for record in inscriptions:
        record_id = record.get("record_id", "")
        record_iob_rows = iob_rows_by_record.get(record_id, [])
        record_sip_rows = sip_by_record.get(record_id, [])

        crossrefs: list[dict] = []
        candidate_summary = {
            "has_sip": bool(record_sip_rows),
            "has_tn_candidate": False,
            "has_list": False,
            "has_ppa_candidate": False,
            "has_iob": False,
            "has_ub": False,
            "has_jbrs": False,
        }
        for row in record_iob_rows:
            row_crossrefs, row_summary = build_crossrefs_from_iob_row(row)
            crossrefs.extend(row_crossrefs)
            for key, value in row_summary.items():
                candidate_summary[key] = candidate_summary[key] or value

        if not crossrefs and not record_sip_rows:
            enriched_records.append(record)
            continue

        enriched = dict(record)
        translation_candidates = build_translation_candidates(crossrefs)

        if record_sip_rows:
            sip_witnesses = [build_sip_witness(row) for row in record_sip_rows]
            enriched["source_text_witnesses"] = sip_witnesses
        else:
            sip_witnesses = []

        if crossrefs:
            enriched["bibliographic_crossrefs"] = crossrefs

        if translation_candidates:
            enriched["translation_source_candidates"] = translation_candidates

        enriched["translations"] = []
        enriched["translation_status"] = (
            "translation_source_missing"
            if translation_candidates
            else "no_translation_known"
        )
        enriched["enrichment_status"] = choose_enrichment_status(
            has_sip=bool(sip_witnesses),
            has_crossrefs=bool(crossrefs),
            has_tn_candidates=bool(translation_candidates),
        )
        enriched["enrichment_notes"] = (
            "SIP witness provenance integrated; "
            if sip_witnesses
            else ""
        ) + (
            "Bibliographic cross-reference evidence integrated from the IOB index."
            if crossrefs
            else "No bibliographic cross-reference evidence added."
        )
        if translation_candidates:
            enriched["enrichment_notes"] += " TN translation candidate preserved without adding translation text."

        enriched_records.append(enriched)
        preview_rows.append(
            build_preview_row(record, record_sip_rows, crossrefs, translation_candidates)
        )

    summary = {
        "total_records": len(enriched_records),
        "records_with_any_enrichment": sum(
            1
            for row in enriched_records
            if row.get("source_text_witnesses")
            or row.get("bibliographic_crossrefs")
            or row.get("translation_source_candidates")
            or row.get("translations")
            or row.get("translation_status")
        ),
        "records_with_sip_source_text_witness": sum(1 for row in enriched_records if row.get("source_text_witnesses")),
        "records_with_iob_crossref": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == IOB_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_list_crossref": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == LIST_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_ppa_candidate": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == PPA_SOURCE_KEY for entry in row.get("bibliographic_crossrefs", []))
        ),
        "records_with_tn_translation_candidate": sum(
            1
            for row in enriched_records
            if any(entry.get("source_key") == TN_SOURCE_KEY for entry in row.get("translation_source_candidates", []))
        ),
        "records_with_translation_status_no_translation_known": sum(
            1 for row in enriched_records if row.get("translation_status") == "no_translation_known"
        ),
        "records_with_translation_status_translation_source_missing": sum(
            1 for row in enriched_records if row.get("translation_status") == "translation_source_missing"
        ),
        "records_with_translation_integrated": sum(
            1 for row in enriched_records if row.get("translation_status") == "translation_integrated"
        ),
        "records_with_existing_full_transliteration": sum(1 for row in enriched_records if row.get("full_transliteration")),
    }
    return enriched_records, preview_rows, summary


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
        "--iob-crossref-path",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "inscriptions_of_burma_cross_reference_index.tsv",
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
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "corpus_enrichment" / "enriched_candidate_summary.json",
    )
    args = parser.parse_args()

    inscriptions = read_jsonl(args.input_inscriptions)
    sip_rows = read_tsv(args.sip_accepted_path)
    crossref_rows = read_tsv(args.iob_crossref_path)

    enriched_records, preview_rows, summary = build_enriched_records(inscriptions, sip_rows, crossref_rows)
    write_jsonl(args.output_jsonl, enriched_records)
    write_tsv(args.output_preview_tsv, preview_rows, PREVIEW_FIELDS)
    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(enriched_records)} enriched records, {len(preview_rows)} preview rows, "
        f"and {len(summary)} summary fields."
    )


if __name__ == "__main__":
    main()
