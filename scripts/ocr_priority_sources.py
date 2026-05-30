#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from corpus_common import REPO_ROOT, read_tsv, write_tsv
from extract_bibliography_acronyms import (
    OCR_INDEX_FIELDS,
    OCR_MANIFEST_FIELDS,
    PRIORITY_ACRONYMS,
    compact_text,
    line_has_definition_pattern,
    looks_like_section_heading,
    section_definition_hits,
)
from local_bibliography_common import extract_text_from_path, repo_relative_or_none, source_file_id

LOCAL_TEXT_ROOT = REPO_ROOT / "data/local/ocr_text"
DEFAULT_QUEUE_PATH = REPO_ROOT / "data/working/bibliography/local_sources/ocr_priority_queue.tsv"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "data/working/bibliography/local_sources/local_file_manifest.tsv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/working/bibliography/local_sources/ocr_outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run targeted OCR/text extraction for high-priority bibliography sources.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE_PATH, help="OCR priority queue TSV.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=REPO_ROOT / "data/local/bibliography_sources",
        help="Root directory containing locally cached bibliography sources.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH, help="Local file manifest TSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Tracked OCR output directory.")
    parser.add_argument(
        "--local-text-root",
        type=Path,
        default=LOCAL_TEXT_ROOT,
        help="Gitignored directory for full OCR or extracted text.",
    )
    return parser.parse_args()


def detect_tools() -> dict[str, str]:
    tool_names = ("pdftotext", "pdftoppm", "pdfinfo", "ocrmypdf", "tesseract", "djvutxt", "ddjvu", "gcloud", "curl")
    return {name: path for name in tool_names if (path := shutil.which(name))}


def text_has_usable_content(text: str) -> bool:
    compact = compact_text(text)
    if len(compact) < 240:
        return False
    return len(re.findall(r"[A-Za-z]", compact)) >= 80


def resolve_source_map(manifest_path: Path) -> dict[str, dict[str, str]]:
    if not manifest_path.exists():
        return {}
    rows_by_id: dict[str, dict[str, str]] = {}
    for row in read_tsv(manifest_path):
        copied_path = row.get("copied_path", "")
        if not copied_path:
            continue
        path = REPO_ROOT / copied_path
        rows_by_id[source_file_id(path)] = row
    return rows_by_id


def resolve_source_path(source_file_id_value: str, manifest_row: dict[str, str] | None, source_root: Path) -> Path | None:
    if manifest_row and manifest_row.get("copied_path"):
        candidate = REPO_ROOT / manifest_row["copied_path"]
        if candidate.exists():
            return candidate
    matches = sorted(source_root.glob(f"{source_file_id_value}/*"))
    return matches[0] if matches else None


def run_command(command: list[str], *, text: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=text)


def extract_text_direct(path: Path, tools: dict[str, str]) -> tuple[str, str, str]:
    suffix = path.suffix.casefold()
    if suffix == ".djvu" and "djvutxt" in tools:
        result = run_command([tools["djvutxt"], str(path)])
        return result.stdout, "djvutxt", ""
    text, method, warnings = extract_text_from_path(path)
    return text, method, "; ".join(warnings)


def pdf_page_count(path: Path, tools: dict[str, str]) -> int | None:
    if "pdfinfo" not in tools:
        return None
    result = run_command([tools["pdfinfo"], str(path)])
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def sample_page_numbers(page_count: int | None) -> list[int]:
    if not page_count or page_count <= 0:
        return []
    front_window = min(page_count, 10)
    back_window = min(page_count, 10)
    sampled = list(range(1, front_window + 1))
    sampled.extend(range(max(1, page_count - back_window + 1), page_count + 1))
    return sorted(dict.fromkeys(sampled))


def summarize_page_numbers(page_numbers: list[int]) -> str:
    if not page_numbers:
        return ""
    ranges: list[str] = []
    start = previous = page_numbers[0]
    for page in page_numbers[1:]:
        if page == previous + 1:
            previous = page
            continue
        ranges.append(f"{start}-{previous}" if start != previous else str(start))
        start = previous = page
    ranges.append(f"{start}-{previous}" if start != previous else str(start))
    return ", ".join(ranges)


def append_page_marker(chunks: list[str], page_number: int, text: str) -> None:
    compact = text.strip()
    if not compact:
        return
    chunks.append(f"[[page {page_number}]]")
    chunks.append(compact)


def google_vision_context(tools: dict[str, str]) -> dict[str, str] | None:
    if "gcloud" not in tools or "curl" not in tools:
        return None
    try:
        token = run_command([tools["gcloud"], "auth", "print-access-token"]).stdout.strip()
        project = run_command([tools["gcloud"], "config", "get-value", "project"]).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    if not token or not project or project == "(unset)":
        return None
    return {"token": token, "project": project}


def render_pdf_page_images(path: Path, *, tools: dict[str, str], temp_dir: Path, page_numbers: list[int]) -> list[tuple[int, Path]]:
    if "pdftoppm" not in tools:
        return []
    rendered: list[tuple[int, Path]] = []
    for page_number in page_numbers:
        image_prefix = temp_dir / f"page-{page_number}"
        run_command(
            [
                tools["pdftoppm"],
                "-png",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(path),
                str(image_prefix),
            ],
            text=False,
        )
        image_paths = sorted(temp_dir.glob(f"{image_prefix.name}-*.png"))
        if image_paths:
            rendered.append((page_number, image_paths[0]))
    return rendered


def render_djvu_page_images(path: Path, *, tools: dict[str, str], temp_dir: Path, page_numbers: list[int]) -> list[tuple[int, Path]]:
    if "ddjvu" not in tools:
        return []
    rendered: list[tuple[int, Path]] = []
    for page_number in page_numbers:
        image_path = temp_dir / f"djvu-page-{page_number}.tiff"
        run_command(
            [
                tools["ddjvu"],
                f"-page={page_number}",
                "-format=tiff",
                str(path),
                str(image_path),
            ],
            text=False,
        )
        if image_path.exists():
            rendered.append((page_number, image_path))
    return rendered


def ocr_images_with_google_vision(
    image_pages: list[tuple[int, Path]],
    *,
    tools: dict[str, str],
    vision_context: dict[str, str] | None,
) -> tuple[dict[int, str], str]:
    if not vision_context:
        return {}, "Google Vision not configured"
    responses_by_page: dict[int, str] = {}
    try:
        for offset in range(0, len(image_pages), 5):
            batch = image_pages[offset : offset + 5]
            payload = {
                "requests": [
                    {
                        "image": {"content": base64.b64encode(image_path.read_bytes()).decode("ascii")},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    }
                    for _, image_path in batch
                ]
            }
            result = subprocess.run(
                [
                    tools["curl"],
                    "-sS",
                    "-X",
                    "POST",
                    "-H",
                    f"Authorization: Bearer {vision_context['token']}",
                    "-H",
                    f"x-goog-user-project: {vision_context['project']}",
                    "-H",
                    "Content-Type: application/json; charset=utf-8",
                    "https://vision.googleapis.com/v1/images:annotate",
                    "-d",
                    json.dumps(payload, ensure_ascii=False),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            response = json.loads(result.stdout)
            for (page_number, _), item in zip(batch, response.get("responses", [])):
                if item.get("error"):
                    raise RuntimeError(item["error"].get("message", "Google Vision request failed"))
                text = item.get("fullTextAnnotation", {}).get("text", "")
                if text:
                    responses_by_page[page_number] = text
    except Exception as exc:
        return {}, f"Google Vision failed: {exc}"
    return responses_by_page, ""


def ocr_image_pages_locally(image_pages: list[tuple[int, Path]], *, tools: dict[str, str]) -> tuple[dict[int, str], str]:
    if "tesseract" not in tools:
        return {}, "tesseract not available"
    responses_by_page: dict[int, str] = {}
    for page_number, image_path in image_pages:
        result = run_command(
            [
                tools["tesseract"],
                str(image_path),
                "stdout",
                "-l",
                "eng",
                "--psm",
                "6",
            ]
        )
        if result.stdout.strip():
            responses_by_page[page_number] = result.stdout
    if not responses_by_page:
        return {}, "sampled OCR produced no readable text"
    return responses_by_page, ""


def extract_pdf_text_pages(path: Path, *, tools: dict[str, str], page_numbers: list[int]) -> tuple[str, str]:
    if "pdftotext" not in tools or not page_numbers:
        return "", ""
    chunks: list[str] = []
    for page_number in page_numbers:
        result = run_command(
            [
                tools["pdftotext"],
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(path),
                "-",
            ]
        )
        append_page_marker(chunks, page_number, result.stdout)
    return "\n".join(chunks).strip(), summarize_page_numbers(page_numbers)


def ocr_pdf_sampled_pages(
    path: Path,
    *,
    tools: dict[str, str],
    temp_dir: Path,
    page_numbers: list[int],
    vision_context: dict[str, str] | None,
) -> tuple[str, str, str, str]:
    image_pages = render_pdf_page_images(path, tools=tools, temp_dir=temp_dir, page_numbers=page_numbers)
    if not image_pages:
        return "", "", "", "pdftoppm not available or produced no page images"
    vision_rows, vision_note = ocr_images_with_google_vision(image_pages, tools=tools, vision_context=vision_context)
    method = "pdftoppm+google-vision" if vision_rows else ""
    text_rows = vision_rows
    local_note = ""
    if not text_rows:
        text_rows, local_note = ocr_image_pages_locally(image_pages, tools=tools)
        method = "pdftoppm+tesseract" if text_rows else ""
    chunks: list[str] = []
    for page_number in page_numbers:
        append_page_marker(chunks, page_number, text_rows.get(page_number, ""))
    page_scope = summarize_page_numbers(page_numbers)
    if not chunks:
        note = "; ".join(part for part in (vision_note, local_note) if part)
        return "", "", page_scope, note or "sampled OCR produced no readable text"
    note = "; ".join(part for part in (vision_note if vision_rows else "", local_note if not vision_rows else "") if part)
    return "\n".join(chunks).strip(), method, page_scope, note


def ocr_djvu_sampled_pages(
    path: Path,
    *,
    tools: dict[str, str],
    temp_dir: Path,
    page_numbers: list[int],
    vision_context: dict[str, str] | None,
) -> tuple[str, str, str, str]:
    image_pages = render_djvu_page_images(path, tools=tools, temp_dir=temp_dir, page_numbers=page_numbers)
    if not image_pages:
        return "", "", "", "ddjvu not available or produced no page images"
    vision_rows, vision_note = ocr_images_with_google_vision(image_pages, tools=tools, vision_context=vision_context)
    method = "ddjvu+google-vision" if vision_rows else ""
    text_rows = vision_rows
    local_note = ""
    if not text_rows:
        text_rows, local_note = ocr_image_pages_locally(image_pages, tools=tools)
        method = "ddjvu+tesseract" if text_rows else ""
    chunks: list[str] = []
    for page_number in page_numbers:
        append_page_marker(chunks, page_number, text_rows.get(page_number, ""))
    page_scope = summarize_page_numbers(page_numbers)
    if not chunks:
        note = "; ".join(part for part in (vision_note, local_note) if part)
        return "", "", page_scope, note or "sampled DJVU OCR produced no readable text"
    note = "; ".join(part for part in (vision_note if vision_rows else "", local_note if not vision_rows else "") if part)
    return "\n".join(chunks).strip(), method, page_scope, note or ""


def extract_priority_text(path: Path, *, tools: dict[str, str], vision_context: dict[str, str] | None) -> tuple[str, str, str, str]:
    direct_text, direct_method, direct_note = extract_text_direct(path, tools)
    if text_has_usable_content(direct_text):
        return direct_text, direct_method or "direct", "full document", direct_note
    suffix = path.suffix.casefold()
    page_count = None
    page_numbers: list[int] = []
    page_scope = "full document"
    if suffix == ".pdf":
        page_count = pdf_page_count(path, tools)
        page_numbers = sample_page_numbers(page_count)
        if page_numbers:
            sampled_text, sampled_scope = extract_pdf_text_pages(path, tools=tools, page_numbers=page_numbers)
            if text_has_usable_content(sampled_text):
                note = "; ".join(value for value in (direct_note, "sampled front/back pages with pdftotext") if value)
                return sampled_text, "pdftotext(sampled)", sampled_scope, note
        page_scope = summarize_page_numbers(page_numbers) or page_scope
    elif suffix == ".djvu":
        direct_scope = "full document"
        if text_has_usable_content(direct_text):
            return direct_text, direct_method or "djvutxt", direct_scope, direct_note
    with tempfile.TemporaryDirectory(prefix="ocr-priority-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        if suffix == ".pdf":
            ocr_text, ocr_method, page_scope, ocr_note = ocr_pdf_sampled_pages(
                path,
                tools=tools,
                temp_dir=temp_dir,
                page_numbers=page_numbers,
                vision_context=vision_context,
            )
        elif suffix == ".djvu":
            if not page_numbers:
                page_numbers = list(range(1, 11))
                page_scope = summarize_page_numbers(page_numbers)
            ocr_text, ocr_method, page_scope, ocr_note = ocr_djvu_sampled_pages(
                path,
                tools=tools,
                temp_dir=temp_dir,
                page_numbers=page_numbers,
                vision_context=vision_context,
            )
        else:
            ocr_text, ocr_method, ocr_note = "", "", f"unsupported OCR source type {suffix}"
    if text_has_usable_content(ocr_text):
        note = "; ".join(value for value in (direct_note, ocr_note) if value)
        return ocr_text, ocr_method, page_scope, note
    if text_has_usable_content(direct_text):
        return direct_text, direct_method or "direct", "full document", direct_note
    combined_note = "; ".join(value for value in (direct_note, ocr_note) if value)
    return "", "", page_scope, combined_note or "no usable text extracted"


def small_excerpt(lines: list[str], start_index: int) -> tuple[str, str, str]:
    excerpt_lines = [compact_text(lines[start_index])]
    end_index = start_index
    for next_index in range(start_index + 1, len(lines)):
        next_heading = looks_like_section_heading(lines[next_index])
        if next_heading:
            break
        next_line = compact_text(lines[next_index])
        if not next_line:
            if len(excerpt_lines) > 1:
                break
            continue
        excerpt_lines.append(next_line)
        end_index = next_index
        if len(" ".join(excerpt_lines)) >= 700 or len(excerpt_lines) >= 16:
            break
    return compact_text(" ".join(excerpt_lines))[:700], f"line {start_index + 1}", f"line {end_index + 1}"


def build_ocr_index_rows(
    *,
    source_file_id_value: str,
    source_file_label: str,
    text: str,
    ocr_source: str,
    target_acronyms: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = text.splitlines()
    seen: set[tuple[str, str]] = set()
    current_page = ""
    for index, line in enumerate(lines):
        page_match = re.fullmatch(r"\[\[page (\d+)\]\]", compact_text(line))
        if page_match:
            current_page = page_match.group(1)
            continue
        heading = looks_like_section_heading(line)
        if heading:
            snippet_text, start_hint, end_hint = small_excerpt(lines, index)
            acronyms_found = ", ".join(section_definition_hits("\n".join([heading, snippet_text])))
            key = (heading.casefold(), snippet_text)
            if key not in seen:
                seen.add(key)
                rows.append(
                    {
                        "source_file_id": source_file_id_value,
                        "source_file_label": source_file_label,
                        "ocr_source": ocr_source,
                        "page_hint": current_page,
                        "section_start_hint": start_hint,
                        "section_end_hint": end_hint,
                        "matched_heading": heading,
                        "snippet_text": snippet_text,
                        "acronyms_found": acronyms_found,
                        "extraction_confidence": "high",
                        "notes": "",
                    }
                )
        compact_line = compact_text(line)
        if not compact_line:
            continue
        matching_targets = [acronym for acronym in target_acronyms if line_has_definition_pattern(compact_line, acronym)]
        if not matching_targets:
            continue
        snippet = compact_text(" ".join(compact_text(lines[offset]) for offset in range(index, min(len(lines), index + 3)) if compact_text(lines[offset])))
        key = ("explicit definition context", snippet)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "source_file_id": source_file_id_value,
                "source_file_label": source_file_label,
                "ocr_source": ocr_source,
                "page_hint": current_page,
                "section_start_hint": f"line {index + 1}",
                "section_end_hint": f"line {min(len(lines), index + 3)}",
                "matched_heading": "explicit definition context",
                "snippet_text": snippet[:700],
                "acronyms_found": ", ".join(sorted(dict.fromkeys(matching_targets), key=lambda value: value.casefold())),
                "extraction_confidence": "medium",
                "notes": "definition-like row outside a recognized heading",
            }
        )
    return rows


def queue_target_acronyms(value: str) -> list[str]:
    acronyms = [item.strip() for item in value.split(",") if item.strip()]
    return [acronym for acronym in acronyms if acronym in PRIORITY_ACRONYMS]


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.local_text_root.mkdir(parents=True, exist_ok=True)
    tools = detect_tools()
    vision_context = google_vision_context(tools)
    source_map = resolve_source_map(args.manifest)

    manifest_rows: list[dict[str, str]] = []
    index_rows: list[dict[str, str]] = []
    failed_sources: list[str] = []

    queue_rows = [row for row in read_tsv(args.queue) if row.get("priority") == "high"]
    for queue_row in queue_rows:
        if queue_row.get("priority") != "high":
            continue
        source_id_value = queue_row["source_file_id"]
        manifest_source_row = source_map.get(source_id_value)
        source_path = resolve_source_path(source_id_value, manifest_source_row, args.source_root)
        if not source_path or not source_path.exists():
            manifest_rows.append(
                {
                    "source_file_id": source_id_value,
                    "source_file_label": queue_row.get("source_file_label", ""),
                    "source_path": "",
                    "local_text_path": "",
                    "file_type": "",
                    "extraction_method": "",
                    "tool_used": "",
                    "extraction_status": "missing_source",
                    "text_sha256": "",
                    "text_length": "0",
                    "page_scope": "",
                    "notes": "source file missing from local cache manifest",
                }
            )
            failed_sources.append(source_id_value)
            continue

        try:
            text, method, page_scope, note = extract_priority_text(source_path, tools=tools, vision_context=vision_context)
        except Exception as exc:
            manifest_rows.append(
                {
                    "source_file_id": source_id_value,
                    "source_file_label": queue_row.get("source_file_label", source_path.name),
                    "source_path": repo_relative_or_none(source_path) or str(source_path),
                    "local_text_path": "",
                    "file_type": source_path.suffix.casefold().lstrip("."),
                    "extraction_method": "",
                    "tool_used": "",
                    "extraction_status": "failed",
                    "text_sha256": "",
                    "text_length": "0",
                    "page_scope": "",
                    "notes": f"{exc.__class__.__name__}: {exc}",
                }
            )
            failed_sources.append(source_id_value)
            continue
        local_text_path = args.local_text_root / f"{source_id_value}.txt"
        extraction_status = "failed"
        if text_has_usable_content(text):
            local_text_path.write_text(text, encoding="utf-8")
            extraction_status = "success"
            index_rows.extend(
                build_ocr_index_rows(
                    source_file_id_value=source_id_value,
                    source_file_label=queue_row.get("source_file_label", source_path.name),
                    text=text,
                    ocr_source=method,
                    target_acronyms=queue_target_acronyms(queue_row.get("target_acronyms", "")),
                )
            )
        else:
            failed_sources.append(source_id_value)

        manifest_rows.append(
            {
                "source_file_id": source_id_value,
                "source_file_label": queue_row.get("source_file_label", source_path.name),
                "source_path": repo_relative_or_none(source_path) or str(source_path),
                "local_text_path": repo_relative_or_none(local_text_path) or str(local_text_path) if local_text_path.exists() else "",
                "file_type": source_path.suffix.casefold().lstrip("."),
                "extraction_method": method,
                "tool_used": method,
                "extraction_status": extraction_status,
                "text_sha256": "",
                "text_length": str(len(text)),
                "page_scope": page_scope,
                "notes": note,
            }
        )

    for row in manifest_rows:
        if row["local_text_path"]:
            local_text_path = REPO_ROOT / row["local_text_path"]
            row["text_sha256"] = hashlib.sha256(local_text_path.read_bytes()).hexdigest()

    manifest_rows.sort(key=lambda row: row["source_file_label"].casefold())
    index_rows.sort(key=lambda row: (row["source_file_label"].casefold(), row["matched_heading"].casefold(), row["section_start_hint"]))
    write_tsv(args.output_dir / "ocr_manifest.tsv", manifest_rows, OCR_MANIFEST_FIELDS)
    write_tsv(args.output_dir / "ocr_text_index.tsv", index_rows, OCR_INDEX_FIELDS)

    report = {
        "available_tools": sorted(tools),
        "google_vision_configured": bool(vision_context),
        "queue_rows": len(queue_rows),
        "files_attempted": len(manifest_rows),
        "files_successful": sum(1 for row in manifest_rows if row["extraction_status"] == "success"),
        "files_failed": sum(1 for row in manifest_rows if row["extraction_status"] != "success"),
        "failed_source_ids": failed_sources,
        "abbreviation_section_hits": len(index_rows),
    }
    (args.output_dir / "ocr_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
