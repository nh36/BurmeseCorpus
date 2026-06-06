#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
LOCAL_PROJECT_DIR = REPO_ROOT / "data" / "local" / "pagan_pinya_ava_ocr"
LOCAL_RUN_SCRIPT = LOCAL_PROJECT_DIR / "run_vision_ocr_pipeline.py"
TRACKED_DIR = Path(__file__).resolve().parent

FILES_TO_COPY = {
    LOCAL_PROJECT_DIR / "output" / "ocr_plain_text_with_page_breaks.txt": TRACKED_DIR / "ocr_plain_text_with_page_breaks.txt",
    LOCAL_PROJECT_DIR / "output" / "ocr_cleaned_text_light.txt": TRACKED_DIR / "ocr_cleaned_text_light.txt",
    LOCAL_PROJECT_DIR / "output" / "ocr_report.md": TRACKED_DIR / "ocr_report.md",
    LOCAL_PROJECT_DIR / "output" / "comparison_report.md": TRACKED_DIR / "comparison_report.md",
    LOCAL_PROJECT_DIR / "output" / "source_selection_report.md": TRACKED_DIR / "source_selection_report.md",
}


def relativize_path(value: str) -> str:
    path = Path(value)
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return path.name


def sync_trackable_outputs() -> None:
    TRACKED_DIR.mkdir(parents=True, exist_ok=True)
    for source_path, destination_path in FILES_TO_COPY.items():
        if not source_path.exists():
            raise FileNotFoundError(f"Missing local OCR output: {source_path}")
        shutil.copyfile(source_path, destination_path)

    metadata_source = LOCAL_PROJECT_DIR / "output" / "ocr_metadata_index.json"
    metadata = json.loads(metadata_source.read_text(encoding="utf-8"))
    manifest = metadata.get("manifest", {})
    tracked_metadata = {
        "generated_at_utc": metadata.get("generated_at_utc", ""),
        "source_pdf": manifest.get("path_stub", "data/local/pagan_pinya_ava_ocr/source/hvd-hxx68w-1780753436.pdf"),
        "ocr_engine": metadata.get("ocr_engine", "Google Cloud Vision DOCUMENT_TEXT_DETECTION"),
        "pdf_rendering": metadata.get("pdf_rendering", "pdftoppm/pdftocairo PNG at 300 dpi"),
        "manifest": {
            "local_file_id": manifest.get("local_file_id", "pagan_pinya_ava_1899_hvd_hxx68w"),
            "source_file_name": manifest.get("source_file_name", "hvd-hxx68w-1780753436.pdf"),
            "path_stub": manifest.get("path_stub", "data/local/pagan_pinya_ava_ocr/source/hvd-hxx68w-1780753436.pdf"),
            "ocr_engine": manifest.get("ocr_engine", "google_vision"),
            "ocr_date": manifest.get("ocr_date", ""),
            "page_count": manifest.get("page_count", metadata.get("page_count_detected", 0)),
            "language_hints": manifest.get("language_hints", ["en", "my"]),
            "image_preprocessing_used": manifest.get("image_preprocessing_used", "pdftoppm-300dpi"),
            "google_vision_batch_id_if_any": manifest.get("google_vision_batch_id_if_any", "pagan-pinya-ava-ocr-0001"),
            "checksum_or_file_fingerprint": manifest.get("checksum_or_file_fingerprint", ""),
            "notes": "Raw per-page Vision JSON is kept under data/local/ and excluded from git.",
        },
        "page_count_detected": int(metadata.get("page_count_detected", 0) or 0),
        "page_json_file_count": int(metadata.get("page_json_file_count", 0) or 0),
        "google_vision_json_path_stub": (
            "data/local/pagan_pinya_ava_ocr/output/vision_run/google_vision_json/"
            "pagan-pinya-ava-1899-hvd-hxx68w/page-XXXX.json"
        ),
    }
    (TRACKED_DIR / "ocr_metadata_index.json").write_text(
        json.dumps(tracked_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    quality_source = LOCAL_PROJECT_DIR / "working" / "pdf_quality_assessment.json"
    quality = json.loads(quality_source.read_text(encoding="utf-8"))
    for file_info in quality.get("files", {}).values():
        if file_info.get("path"):
            file_info["path"] = relativize_path(file_info["path"])
    (TRACKED_DIR / "pdf_quality_assessment.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for markdown_path in [
        TRACKED_DIR / "ocr_report.md",
        TRACKED_DIR / "comparison_report.md",
        TRACKED_DIR / "source_selection_report.md",
    ]:
        markdown_text = markdown_path.read_text(encoding="utf-8")
        root_pattern = r"/(?:" + "|".join(["Users", "Volumes"]) + r")/[^\s`]+"
        markdown_text = re.sub(root_pattern, "<local-path-removed>", markdown_text)
        markdown_path.write_text(markdown_text, encoding="utf-8")


def run_local_ocr_pipeline(skip_ocr: bool) -> None:
    if not LOCAL_RUN_SCRIPT.exists():
        raise FileNotFoundError(f"Missing local OCR pipeline script: {LOCAL_RUN_SCRIPT}")
    command = ["python3", str(LOCAL_RUN_SCRIPT), "--project-dir", str(LOCAL_PROJECT_DIR)]
    if skip_ocr:
        command.append("--skip-ocr")
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run TN 1899 local Vision OCR pipeline and sync trackable outputs to data/working."
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Skip running OCR and only sync/sanitize already-generated local outputs.",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="When running local pipeline, skip OCR and rebuild only derived outputs first.",
    )
    args = parser.parse_args()

    if not args.sync_only:
        run_local_ocr_pipeline(skip_ocr=args.skip_ocr)
    sync_trackable_outputs()
    print(f"Synced trackable outputs to {TRACKED_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
