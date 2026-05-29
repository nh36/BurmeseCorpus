from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from corpus_common import REPO_ROOT, normalize_whitespace, read_jsonl, read_tsv, write_tsv


ALLOWED_FAMILY_TYPES = {"source_catalogue", "publication", "article", "book", "internal_reference", "unclear"}
ALLOWED_LIKELY_TRANSLATION = {"yes", "no", "possible", "unknown"}
ALLOWED_REVIEW_STATUS = {"unreviewed", "needs_human_review", "reviewed_provisional", "reviewed_stable"}
ALLOWED_TRANSLATION_RELEVANCE = {"likely_translation", "possible_translation", "unlikely_translation", "unknown"}

ABSOLUTE_PATH_PATTERN = re.compile(r"(^/|^[A-Za-z]:\\\\|/Users/|/home/)")
MYANMAR_PATTERN = re.compile(r"[\u1000-\u109f]")
YEAR_PATTERN = re.compile(r"\b(1[89][0-9]{2}|20[0-9]{2})(?:[-/](?:[0-9]{2}|20[0-9]{2}))?\b")
PAGE_PATTERN = re.compile(r"\b(?:p|pp)\.?\s*[0-9]+(?:[-–][0-9]+)?\b", re.IGNORECASE)
NO_PATTERN = re.compile(r"\bno\.?\s*[0-9]+(?:[-–][0-9]+)?\b", re.IGNORECASE)
VOLUME_PATTERN = re.compile(r"\bvol\.?\s*[ivx0-9]+\b", re.IGNORECASE)


def repo_relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9a-z]+", "-", value.casefold()).strip("-")
    return slug[:80] or "unknown"


def short_text(value: str, *, limit: int = 80) -> str:
    value = normalize_whitespace(value)
    return value if len(value) <= limit else f"{value[: limit - 1].rstrip()}…"


def detect_script(value: str) -> str:
    has_myanmar = bool(MYANMAR_PATTERN.search(value))
    has_latin = bool(re.search(r"[A-Za-z]", value))
    if has_myanmar and has_latin:
        return "mixed"
    if has_myanmar:
        return "myanmar"
    if has_latin:
        return "latin"
    return "unknown"


def normalize_core(raw_reference: str) -> str:
    normalized = unicodedata.normalize("NFKC", normalize_whitespace(raw_reference))
    normalized = PAGE_PATTERN.sub(" ", normalized)
    normalized = NO_PATTERN.sub(" ", normalized)
    normalized = VOLUME_PATTERN.sub(" ", normalized)
    normalized = re.sub(r"\b(?:repr\.?|copy)\b", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[\[\](){},;]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .,-")
    lowered = normalized.casefold()
    lowered = re.sub(r"[^0-9a-z\u1000-\u109f]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def classify_reference(raw_reference: str) -> dict:
    cleaned = normalize_whitespace(raw_reference)
    lowered = unicodedata.normalize("NFKC", cleaned).casefold()
    normalized_core = normalize_core(cleaned)

    prefix_rules = [
        (r"^\s*obi(?:\b|\d)", "obi-internal", "OBI internal references", "internal_reference", "no"),
        (r"^\s*list\b", "list-catalogue", "List references", "source_catalogue", "no"),
        (r"^\s*ippa\b", "ippa-catalogue", "IPPA references", "source_catalogue", "no"),
        (r"^\s*iob\b", "iob-catalogue", "IOB references", "source_catalogue", "no"),
        (r"^\s*bed\s*b\b", "bed-b-catalogue", "BED B references", "source_catalogue", "no"),
        (r"^\s*pl\.?\b", "plate-references", "Plate references", "internal_reference", "no"),
        (r"^\s*uem\b", "uem-catalogue", "UEM references", "source_catalogue", "no"),
        (r"^\s*ppa\b", "ppa-catalogue", "PPA references", "source_catalogue", "no"),
        (r"^\s*tn\b", "tn-catalogue", "TN references", "source_catalogue", "no"),
        (r"^\s*u min hswe\b", "u-min-hswe-catalogue", "U Min Hswe references", "source_catalogue", "possible"),
        (r"^\s*sip\b", "sip-catalogue", "SIP references", "source_catalogue", "no"),
        (r"^\s*or\b", "or-catalogue", "OR references", "source_catalogue", "no"),
        (r"^\s*mm\b", "mm-catalogue", "MM references", "source_catalogue", "no"),
        (r"^\s*eb\b", "eb-publication", "EB references", "publication", "unknown"),
    ]
    for pattern, family_slug, family_label, family_type, translation_flag in prefix_rules:
        if re.search(pattern, lowered):
            return {
                "family_id": f"fam-{family_slug}",
                "family_label": family_label,
                "family_type": family_type,
                "likely_contains_translation": translation_flag,
                "notes": "Grouped by recurring leading label.",
            }

    contains_rules = [
        ("rdasb", "rdasb-publication", "RDASB references", "publication", "unknown"),
        ("jras", "jras-publication", "JRAS references", "publication", "possible"),
        ("jbrs", "jbrs-publication", "JBRS references", "publication", "possible"),
        ("bbhc", "bbhc-publication", "BBHC references", "publication", "possible"),
    ]
    for token, family_slug, family_label, family_type, translation_flag in contains_rules:
        if token in lowered:
            return {
                "family_id": f"fam-{family_slug}",
                "family_label": family_label,
                "family_type": family_type,
                "likely_contains_translation": translation_flag,
                "notes": "Grouped by recurring publication abbreviation.",
            }

    if "harvey" in lowered and "history" in lowered:
        return {
            "family_id": "fam-harvey-history",
            "family_label": "Harvey, History references",
            "family_type": "book",
            "likely_contains_translation": "possible",
            "notes": "Grouped by recurring author/title pair.",
        }
    if "ray" in lowered and "theravada" in lowered:
        return {
            "family_id": "fam-ray-theravada-buddhism",
            "family_label": "Ray, Theravada Buddhism",
            "family_type": "book",
            "likely_contains_translation": "no",
            "notes": "Grouped by recurring author/title pair.",
        }
    if "anthology" in lowered:
        return {
            "family_id": "fam-anthology",
            "family_label": "Anthology references",
            "family_type": "book",
            "likely_contains_translation": "possible",
            "notes": "Grouped by recurring title keyword.",
        }

    if "translation" in lowered or "version" in lowered or "four languages" in lowered or "in pali" in lowered:
        family_id = f"fam-raw-{slugify(normalized_core or lowered)}"
        return {
            "family_id": family_id,
            "family_label": short_text(cleaned),
            "family_type": "article" if "," in cleaned else "book",
            "likely_contains_translation": "yes",
            "notes": "Kept as a narrow title-specific family because the reference may represent a translation-related work.",
        }

    fallback_core = normalized_core or lowered or cleaned.casefold()
    family_label = short_text(cleaned if len(fallback_core.split()) <= 5 else fallback_core)
    return {
        "family_id": f"fam-raw-{slugify(fallback_core)}",
        "family_label": family_label,
        "family_type": "unclear",
        "likely_contains_translation": "unknown",
        "notes": "No stronger conservative family signal was detected.",
    }


def looks_like_author(value: str) -> bool:
    stripped = value.strip()
    if not stripped or re.search(r"\d", stripped):
        return False
    if re.match(r"^(the|a|an)\b", stripped, flags=re.IGNORECASE):
        return False
    if re.fullmatch(r"[A-Z ./'()&+-]+", stripped) and stripped.upper() == stripped:
        return False
    return bool(re.search(r"[a-z\u1000-\u109f]", stripped))


def infer_author_title_year(sample_references: list[str], family_label: str, family_type: str) -> tuple[str, str, str, str]:
    sample = sample_references[0] if sample_references else family_label
    author_original = ""
    title_original = ""
    publication_details = ""
    year = ""
    year_match = YEAR_PATTERN.search(sample)
    if year_match:
        year = year_match.group(1)
    if family_type not in {"source_catalogue", "internal_reference"} and "," in sample:
        first, remainder = sample.split(",", 1)
        if looks_like_author(first) and len(first.strip().split()) <= 6:
            author_original = first.strip()
            title_candidate = re.sub(r"\b(?:in|p|pp)\b.*$", "", remainder, flags=re.IGNORECASE).strip(" ,")
            if title_candidate and title_candidate != remainder.strip():
                title_original = title_candidate
            elif remainder.strip():
                publication_details = short_text(remainder.strip(), limit=120)
    return author_original, title_original, publication_details, year


def build_work_candidate(family: dict, member_rows: list[dict]) -> dict:
    sample_references = [row["raw_reference_string"] for row in member_rows[:3]]
    explicit_overrides = {
        "fam-anthology": ("", "Anthology", "", ""),
        "fam-harvey-history": ("Harvey", "History of Myanmar", "", ""),
        "fam-ray-theravada-buddhism": ("Ray", "Theravada Buddhism", "", ""),
    }
    author_original, title_original, publication_details, year = explicit_overrides.get(
        family["family_id"],
        infer_author_title_year(sample_references, family["family_label"], family["family_type"]),
    )
    author_normalized = author_original.casefold() if author_original else ""
    title_normalized = normalize_core(title_original) if title_original else ""
    script = detect_script(" ".join(sample_references) or family["family_label"])
    translation_map = {
        "yes": "likely_translation",
        "possible": "possible_translation",
        "no": "unlikely_translation",
        "unknown": "unknown",
    }
    return {
        "work_candidate_id": family["family_id"].replace("fam-", "work-", 1),
        "family_id": family["family_id"],
        "provisional_short_label": family["family_label"],
        "author_original": author_original,
        "author_normalized": author_normalized,
        "year": year,
        "title_original": title_original,
        "title_normalized": title_normalized,
        "publication_details": publication_details,
        "language": "",
        "script": script,
        "translation_relevance": translation_map[family["likely_contains_translation"]],
        "evidence_raw_references": " | ".join(short_text(reference, limit=60) for reference in sample_references),
        "review_status": "unreviewed",
        "notes": family["notes"],
    }


def build_bibliography_triage(
    raw_reference_rows: list[dict],
    occurrence_rows: list[dict],
    inscription_rows: list[dict],
) -> tuple[list[dict], list[dict], list[dict], dict]:
    occurrence_counts: Counter[str] = Counter()
    example_record_ids: dict[str, list[str]] = defaultdict(list)
    for row in occurrence_rows:
        raw_reference = normalize_whitespace(row["raw_reference_string"])
        occurrence_counts[raw_reference] += 1
        if row["record_id"] not in example_record_ids[raw_reference] and len(example_record_ids[raw_reference]) < 5:
            example_record_ids[raw_reference].append(row["record_id"])

    family_members: dict[str, list[dict]] = defaultdict(list)
    for raw_reference in sorted(occurrence_counts):
        classification = classify_reference(raw_reference)
        family_members[classification["family_id"]].append(
            {
                "family_id": classification["family_id"],
                "raw_reference_string": raw_reference,
                "occurrence_count": occurrence_counts[raw_reference],
                "example_record_ids": " | ".join(example_record_ids[raw_reference]),
                "notes": classification["notes"],
                "_family_label": classification["family_label"],
                "_family_type": classification["family_type"],
                "_likely_contains_translation": classification["likely_contains_translation"],
            }
        )

    family_rows: list[dict] = []
    member_rows: list[dict] = []
    work_candidates: list[dict] = []
    families_by_type: Counter[str] = Counter()
    translation_relevance_counts: Counter[str] = Counter()

    for family_id, members in family_members.items():
        members.sort(key=lambda row: (-row["occurrence_count"], row["raw_reference_string"]))
        family_label = members[0]["_family_label"]
        family_type = members[0]["_family_type"]
        likely_contains_translation = members[0]["_likely_contains_translation"]
        occurrence_count = sum(row["occurrence_count"] for row in members)
        family_row = {
            "family_id": family_id,
            "family_label": family_label,
            "family_type": family_type,
            "member_count": len(members),
            "occurrence_count": occurrence_count,
            "sample_raw_references": " | ".join(short_text(row["raw_reference_string"], limit=50) for row in members[:3]),
            "likely_contains_translation": likely_contains_translation,
            "review_status": "unreviewed",
            "notes": members[0]["notes"],
        }
        family_rows.append(family_row)
        families_by_type[family_type] += 1

        for row in members:
            member_rows.append(
                {
                    "family_id": family_id,
                    "raw_reference_string": row["raw_reference_string"],
                    "occurrence_count": row["occurrence_count"],
                    "example_record_ids": row["example_record_ids"],
                    "notes": row["notes"],
                }
            )

        work_candidate = build_work_candidate(family_row, members)
        work_candidates.append(work_candidate)
        translation_relevance_counts[work_candidate["translation_relevance"]] += 1

    family_rows.sort(key=lambda row: (-row["occurrence_count"], row["family_id"]))
    member_rows.sort(key=lambda row: (row["family_id"], -row["occurrence_count"], row["raw_reference_string"]))
    work_candidates.sort(key=lambda row: row["work_candidate_id"])

    records_with_references = sum(1 for record in inscription_rows if record.get("references_original"))
    records_without_references = len(inscription_rows) - records_with_references
    report = {
        "input_files": {
            "raw_references": "data/working/bibliography/raw_references.tsv",
            "reference_occurrences": "data/working/bibliography/reference_occurrences.tsv",
            "inscriptions_jsonl": "data/release/corpus_release_v0_3/inscriptions.jsonl",
        },
        "raw_reference_count": len(raw_reference_rows),
        "reference_occurrence_count": len(occurrence_rows),
        "family_count": len(family_rows),
        "work_candidate_count": len(work_candidates),
        "unclustered_reference_count": sum(1 for row in family_rows if row["member_count"] == 1),
        "families_by_type": dict(sorted(families_by_type.items())),
        "translation_relevance_counts": dict(sorted(translation_relevance_counts.items())),
        "records_with_references": records_with_references,
        "records_without_references": records_without_references,
        "notes": [
            "This is a conservative bibliography/source authority triage layer, not final bibliography normalization.",
            "Structured OBI records provide the raw reference landscape in corpus_release_v0_3.",
            "Sagaing records currently have no raw references in the release input.",
            "Recently Found contributes editorial relations rather than independent inscription rows in corpus_release_v0_3, so it contributes no direct raw-reference occurrences here.",
        ],
    }
    return family_rows, member_rows, work_candidates, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-references",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "raw_references.tsv",
    )
    parser.add_argument(
        "--reference-occurrences",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography" / "reference_occurrences.tsv",
    )
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=REPO_ROOT / "data" / "release" / "corpus_release_v0_3" / "inscriptions.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "working" / "bibliography",
    )
    args = parser.parse_args()

    raw_reference_rows = read_tsv(args.raw_references)
    occurrence_rows = read_tsv(args.reference_occurrences)
    inscription_rows = read_jsonl(args.input_jsonl)
    family_rows, member_rows, work_candidates, report = build_bibliography_triage(
        raw_reference_rows,
        occurrence_rows,
        inscription_rows,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        args.output_dir / "reference_families.tsv",
        family_rows,
        [
            "family_id",
            "family_label",
            "family_type",
            "member_count",
            "occurrence_count",
            "sample_raw_references",
            "likely_contains_translation",
            "review_status",
            "notes",
        ],
    )
    write_tsv(
        args.output_dir / "reference_family_members.tsv",
        member_rows,
        [
            "family_id",
            "raw_reference_string",
            "occurrence_count",
            "example_record_ids",
            "notes",
        ],
    )
    write_tsv(
        args.output_dir / "bibliographic_work_candidates.tsv",
        work_candidates,
        [
            "work_candidate_id",
            "family_id",
            "provisional_short_label",
            "author_original",
            "author_normalized",
            "year",
            "title_original",
            "title_normalized",
            "publication_details",
            "language",
            "script",
            "translation_relevance",
            "evidence_raw_references",
            "review_status",
            "notes",
        ],
    )
    (args.output_dir / "bibliography_triage_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "family_count": len(family_rows),
                "work_candidate_count": len(work_candidates),
                "report": repo_relative_path(args.output_dir / "bibliography_triage_report.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
