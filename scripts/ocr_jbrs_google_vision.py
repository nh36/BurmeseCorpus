from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from corpus_common import ensure_parent, read_tsv, write_tsv
from jbrs_workflow_common import (
    DEFAULT_LOCAL_OUTPUT_ROOT,
    DEFAULT_PREFLIGHT_REPORT_PATH,
    DEFAULT_RUNTIME_PATH_CACHE,
    GITIGNORE_PATH,
    IMAGE_EXTENSIONS,
    JBRS_OCR_BATCH_PLAN_PATH,
    JBRS_OCR_STATUS_LOG_PATH,
    OCR_STATUS_LOG_FIELDS,
    now_iso,
)

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or dry-run the JBRS Google Vision OCR workflow.")
    parser.add_argument("--batch-plan", type=Path, default=JBRS_OCR_BATCH_PLAN_PATH)
    parser.add_argument("--status-log", type=Path, default=JBRS_OCR_STATUS_LOG_PATH)
    parser.add_argument("--runtime-path-cache", type=Path, default=DEFAULT_RUNTIME_PATH_CACHE)
    parser.add_argument("--local-output-root", type=Path, default=DEFAULT_LOCAL_OUTPUT_ROOT)
    parser.add_argument("--preflight-report", type=Path, default=DEFAULT_PREFLIGHT_REPORT_PATH)
    parser.add_argument("--batch-id", action="append", default=[], help="Optional batch_id filter.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Validate staged OCR work without submitting anything.")
    parser.add_argument("--execute", action="store_true", help="Run live Google Vision OCR for selected ready_for_ocr rows.")
    return parser.parse_args()


def select_batch_rows(batch_rows: list[dict[str, str]], batch_ids: list[str], limit: int) -> list[dict[str, str]]:
    selected = [
        row
        for row in batch_rows
        if row.get("status") == "ready_for_ocr" and (not batch_ids or row.get("batch_id") in set(batch_ids))
    ]
    if limit > 0:
        selected = selected[:limit]
    return selected


def gitignored_data_local() -> bool:
    if not GITIGNORE_PATH.exists():
        return False
    text = GITIGNORE_PATH.read_text(encoding="utf-8")
    return "data_local/" in text or "data_local/ocr/jbrs" in text


def staged_forbidden_paths() -> list[str]:
    result = subprocess.run(
        ["git", "--no-pager", "diff", "--cached", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    forbidden: list[str] = []
    for line in result.stdout.splitlines():
        lowered = line.casefold()
        if lowered.startswith("data_local/ocr/jbrs/") or lowered.startswith("data/local/ocr_text/"):
            forbidden.append(line)
        elif Path(line).suffix.casefold() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            forbidden.append(line)
    return forbidden


def ensure_output_directories(local_output_root: Path) -> dict[str, Path]:
    paths = {
        "manifest": local_output_root / "manifest",
        "google_json": local_output_root / "google_vision_json",
        "page_text": local_output_root / "page_text",
        "article_text": local_output_root / "article_text",
        "logs": local_output_root / "logs",
        "rendered_pages": local_output_root / "logs/rendered_pages",
    }
    for path in paths.values():
        ensure_parent(path / ".keep")
        path.mkdir(parents=True, exist_ok=True)
    return paths


def load_runtime_path_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def lookup_access_token() -> tuple[str, str]:
    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token, "GOOGLE_OAUTH_ACCESS_TOKEN"
    commands = [
        ["gcloud", "auth", "application-default", "print-access-token"],
        ["gcloud", "auth", "print-access-token"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        token = result.stdout.strip()
        if token:
            return token, " ".join(command)
    raise RuntimeError("Unable to obtain a Google access token. Configure ADC or gcloud auth first.")


def preflight_report(
    *,
    selected_rows: list[dict[str, str]],
    runtime_path_cache: dict[str, str],
    local_output_root: Path,
    live_mode: bool,
) -> dict[str, object]:
    report: dict[str, object] = {"selected_batch_ids": [row.get("batch_id", "") for row in selected_rows], "errors": [], "warnings": []}
    errors: list[str] = report["errors"]  # type: ignore[assignment]
    warnings: list[str] = report["warnings"]  # type: ignore[assignment]

    if not selected_rows:
        errors.append("No ready_for_ocr rows were selected.")

    if not runtime_path_cache:
        errors.append("Runtime path cache is missing or empty.")

    if not gitignored_data_local():
        errors.append("data_local/ is not gitignored.")

    forbidden = staged_forbidden_paths()
    if forbidden:
        errors.append("Forbidden staged files detected: " + ", ".join(forbidden[:5]))

    output_paths = ensure_output_directories(local_output_root)
    for name, path in output_paths.items():
        if not os.access(path, os.W_OK):
            errors.append(f"Output directory is not writable: {name} -> {path}")

    resolved = 0
    for row in selected_rows:
        if row.get("status") != "ready_for_ocr":
            errors.append(f"Selected row is not ready_for_ocr: {row.get('batch_id', '')}")
        runtime_path = runtime_path_cache.get(row.get("local_file_id", ""), "")
        if not runtime_path:
            errors.append(f"Missing runtime path for {row.get('local_file_id', '')}")
            continue
        if not Path(runtime_path).exists():
            errors.append(f"Runtime path does not exist for {row.get('local_file_id', '')}")
            continue
        resolved += 1
    report["resolved_runtime_path_count"] = resolved

    if live_mode:
        try:
            _token, provider = lookup_access_token()
            report["credential_source"] = provider
        except RuntimeError as exc:
            errors.append(str(exc))
    else:
        warnings.append("Dry run does not require Google credentials.")

    return report


def write_preflight_report(path: Path, report: dict[str, object]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_pdf_pages(source_path: Path, rendered_dir: Path) -> list[Path]:
    rendered_dir.mkdir(parents=True, exist_ok=True)
    prefix = rendered_dir / "page"
    commands = []
    if shutil.which("pdftoppm"):
        commands.append(["pdftoppm", "-png", "-r", "300", str(source_path), str(prefix)])
    if shutil.which("pdftocairo"):
        commands.append(["pdftocairo", "-png", "-r", "300", str(source_path), str(prefix)])
    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True)
            pages = sorted(rendered_dir.glob("page-*.png"))
            if not pages:
                pages = sorted(rendered_dir.glob("page*.png"))
            if pages:
                return pages
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError("Unable to render PDF pages; pdftoppm/pdftocairo conversion failed.")


def source_to_images(source_path: Path, rendered_root: Path, output_basename: str) -> list[Path]:
    suffix = source_path.suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return [source_path]
    if suffix == ".pdf":
        return render_pdf_pages(source_path, rendered_root / output_basename)
    raise RuntimeError(f"Unsupported OCR source type: {source_path.suffix}")


def vision_ocr_image(image_path: Path, access_token: str) -> dict[str, object]:
    content = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = json.dumps(
        {
            "requests": [
                {
                    "image": {"content": content},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    "imageContext": {"languageHints": ["en", "my"]},
                }
            ]
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        VISION_ENDPOINT,
        data=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - integration behavior
        raise RuntimeError(exc.read().decode("utf-8", errors="ignore") or str(exc)) from exc


def extract_vision_text(response: dict[str, object]) -> str:
    responses = response.get("responses", [])
    if not isinstance(responses, list) or not responses:
        return ""
    first = responses[0]
    if not isinstance(first, dict):
        return ""
    if "error" in first:
        raise RuntimeError(str(first["error"]))
    full_text = first.get("fullTextAnnotation", {})
    if isinstance(full_text, dict) and full_text.get("text"):
        return str(full_text["text"])
    text_annotations = first.get("textAnnotations", [])
    if isinstance(text_annotations, list) and text_annotations:
        top = text_annotations[0]
        if isinstance(top, dict) and top.get("description"):
            return str(top["description"])
    return ""


def relative_stub(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_status_log_row(
    existing_row: dict[str, str] | None,
    batch_row: dict[str, str],
    *,
    status: str,
    notes: str,
    output_path: Path | None = None,
    metadata_sidecar: Path | None = None,
    pages_submitted: int | None = None,
    pages_completed: int | None = None,
    error_type: str = "",
    error_message_short: str = "",
) -> dict[str, str]:
    row = dict(existing_row or {})
    row.update(
        {
            "ocr_job_id": row.get("ocr_job_id", f"{batch_row['batch_id']}-run"),
            "batch_id": batch_row["batch_id"],
            "local_file_id": batch_row["local_file_id"],
            "file_name": batch_row["file_name"],
            "ocr_engine": batch_row["ocr_engine"],
            "ocr_scope": batch_row["ocr_scope"],
            "status": status,
            "pages_submitted": row.get("pages_submitted", "") if pages_submitted is None else (str(pages_submitted) if pages_submitted else ""),
            "pages_completed": row.get("pages_completed", "") if pages_completed is None else (str(pages_completed) if pages_completed else ""),
            "output_path_stub": relative_stub(output_path) if output_path else row.get("output_path_stub", ""),
            "metadata_sidecar_stub": relative_stub(metadata_sidecar) if metadata_sidecar else row.get("metadata_sidecar_stub", ""),
            "error_type": error_type,
            "error_message_short": error_message_short,
            "created_at": row.get("created_at", now_iso()),
            "updated_at": now_iso(),
            "notes": notes,
        }
    )
    return row


def run_selected_batches(args: argparse.Namespace) -> int:
    batch_rows = read_tsv(args.batch_plan)
    status_rows = {row.get("batch_id", ""): row for row in read_tsv(args.status_log)} if args.status_log.exists() else {}
    runtime_path_cache = load_runtime_path_cache(args.runtime_path_cache)
    selected_rows = select_batch_rows(batch_rows, args.batch_id, args.limit)
    live_mode = args.execute and not args.dry_run
    report = preflight_report(
        selected_rows=selected_rows,
        runtime_path_cache=runtime_path_cache,
        local_output_root=args.local_output_root,
        live_mode=live_mode,
    )
    write_preflight_report(args.preflight_report, report)
    if report["errors"]:
        if selected_rows:
            for batch_row in selected_rows:
                status_rows[batch_row["batch_id"]] = update_status_log_row(
                    status_rows.get(batch_row["batch_id"]),
                    batch_row,
                    status="failed",
                    notes="OCR preflight failed before submission.",
                    error_type="preflight_failed",
                    error_message_short=truncate_error("; ".join(report["errors"])),  # type: ignore[arg-type]
                )
            write_tsv(args.status_log, [status_rows[key] for key in sorted(status_rows)], OCR_STATUS_LOG_FIELDS)
        return 1

    if args.dry_run or not args.execute:
        for batch_row in selected_rows:
            metadata_path = args.local_output_root / "manifest" / f"{batch_row['output_basename']}.json"
            status_rows[batch_row["batch_id"]] = update_status_log_row(
                status_rows.get(batch_row["batch_id"]),
                batch_row,
                status="dry_run_ok",
                notes="Dry run passed preflight; live OCR can be attempted with --execute.",
                metadata_sidecar=metadata_path,
            )
        write_tsv(args.status_log, [status_rows[key] for key in sorted(status_rows)], OCR_STATUS_LOG_FIELDS)
        return 0

    access_token, credential_source = lookup_access_token()
    paths = ensure_output_directories(args.local_output_root)
    for batch_row in selected_rows:
        source_path = Path(runtime_path_cache[batch_row["local_file_id"]])
        article_text_path = paths["article_text"] / f"{batch_row['output_basename']}.txt"
        metadata_path = paths["manifest"] / f"{batch_row['output_basename']}.json"
        json_dir = paths["google_json"] / batch_row["output_basename"]
        page_text_dir = paths["page_text"] / batch_row["output_basename"]
        json_dir.mkdir(parents=True, exist_ok=True)
        page_text_dir.mkdir(parents=True, exist_ok=True)
        submitted_page_count = 0
        completed_page_count = 0
        try:
            images = source_to_images(source_path, paths["rendered_pages"], batch_row["output_basename"])
            submitted_page_count = len(images)
            status_rows[batch_row["batch_id"]] = update_status_log_row(
                status_rows.get(batch_row["batch_id"]),
                batch_row,
                status="submitted",
                notes=f"Submitting {submitted_page_count} image page(s) to Google Vision via {credential_source}.",
                output_path=article_text_path,
                metadata_sidecar=metadata_path,
                pages_submitted=submitted_page_count,
            )
            write_tsv(args.status_log, [status_rows[key] for key in sorted(status_rows)], OCR_STATUS_LOG_FIELDS)

            page_texts: list[str] = []
            for index, image_path in enumerate(images, start=1):
                response = vision_ocr_image(image_path, access_token)
                (json_dir / f"page-{index:04d}.json").write_text(
                    json.dumps(response, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                page_text = extract_vision_text(response)
                (page_text_dir / f"page-{index:04d}.txt").write_text(page_text, encoding="utf-8")
                page_texts.append(f"[[page {index}]]\n{page_text}".rstrip() + "\n")
                completed_page_count = index

            article_text_path.write_text("\n".join(page_texts).rstrip() + "\n", encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "local_file_id": batch_row["local_file_id"],
                        "source_file_name": batch_row["file_name"],
                        "path_stub": batch_row["path_stub"],
                        "journal": "Journal of the Burma Research Society",
                        "volume": batch_row.get("volume", ""),
                        "issue": batch_row.get("issue", ""),
                        "year": batch_row.get("year", ""),
                        "ocr_engine": batch_row["ocr_engine"],
                        "ocr_date": now_iso(),
                        "page_count": len(images),
                        "language_hints": ["en", "my"],
                        "image_preprocessing_used": "pdftoppm-300dpi" if source_path.suffix.casefold() == ".pdf" else "",
                        "google_vision_batch_id_if_any": batch_row["batch_id"],
                        "checksum_or_file_fingerprint": sha256_for_file(source_path),
                        "notes": "Live Google Vision OCR output stored under data_local/ocr/jbrs/ and kept out of git.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            status_rows[batch_row["batch_id"]] = update_status_log_row(
                status_rows.get(batch_row["batch_id"]),
                batch_row,
                status="completed",
                notes=f"Live Google Vision OCR completed via {credential_source}.",
                output_path=article_text_path,
                metadata_sidecar=metadata_path,
                pages_submitted=submitted_page_count,
                pages_completed=completed_page_count,
            )
        except Exception as exc:  # pragma: no cover - integration behavior
            status_rows[batch_row["batch_id"]] = update_status_log_row(
                status_rows.get(batch_row["batch_id"]),
                batch_row,
                status="failed",
                notes="Live Google Vision OCR failed.",
                output_path=article_text_path,
                metadata_sidecar=metadata_path,
                pages_submitted=submitted_page_count if submitted_page_count else None,
                pages_completed=completed_page_count if completed_page_count else None,
                error_type=exc.__class__.__name__,
                error_message_short=truncate_error(str(exc)),
            )
    write_tsv(args.status_log, [status_rows[key] for key in sorted(status_rows)], OCR_STATUS_LOG_FIELDS)
    return 0


def truncate_error(value: str, limit: int = 140) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def main() -> None:
    args = parse_args()
    if not args.dry_run and not args.execute:
        args.dry_run = True
    raise SystemExit(run_selected_batches(args))


if __name__ == "__main__":
    main()
