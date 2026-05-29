from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from bibtex_common import normalize_for_match, sha256_file, slugify
from corpus_common import REPO_ROOT, normalize_whitespace


ROOT_ENV_VARS = ["OBI_LIBRARY_ROOT", "OBI_AUTHOR_ALPHA_ROOT", "OBI_LOCAL_BIB_ROOT"]
RELEVANT_EXTENSIONS = {
    ".doc",
    ".docx",
    ".rtf",
    ".pdf",
    ".txt",
    ".bib",
    ".ris",
    ".enl",
    ".xml",
    ".djvu",
}
HIGH_PRIORITY_TERMS = [
    "luce",
    "gordon luce",
    "u pe maung tin",
    "pe maung tin",
    "duroiselle",
    "blagden",
    "than tun",
    "harvey",
    "ray",
    "u min hswe",
    "frasch",
    "bagan",
    "pagan",
    "burma",
    "myanmar",
    "inscription",
    "inscriptions",
    "jbrs",
    "bbhc",
    "jras",
    "rdasb",
]
FRASCH_TERMS = ["frasch", "frosch", "tilman", "tillman", "bagan epig"]
SOURCE_CACHE_ROOT = REPO_ROOT / "data" / "local" / "bibliography_sources"


@dataclass
class ConfiguredRoot:
    label: str
    path: Path


def configured_roots() -> list[ConfiguredRoot]:
    roots: list[ConfiguredRoot] = []
    for label in ROOT_ENV_VARS:
        value = os.environ.get(label, "").strip()
        if not value:
            continue
        path = Path(value).expanduser()
        if path.exists():
            roots.append(ConfiguredRoot(label=label, path=path))
    return roots


def missing_root_instructions() -> str:
    return (
        'Set one or more of OBI_LIBRARY_ROOT, OBI_AUTHOR_ALPHA_ROOT, or OBI_LOCAL_BIB_ROOT, '
        'for example:\n'
        'export OBI_AUTHOR_ALPHA_ROOT="/Volumes/ExternalDrive/Authors alphabetical"\n'
        'export OBI_LOCAL_BIB_ROOT="$HOME/Downloads"'
    )


def is_hidden_or_sidecar(path: Path) -> bool:
    return path.name.startswith(".") or path.name.startswith("._")


def safe_source_path(path: Path, root: ConfiguredRoot) -> str:
    return f"{root.label}:{path.relative_to(root.path).as_posix()}"


def repo_relative_or_none(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def is_relevant_file(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in RELEVANT_EXTENSIONS and not is_hidden_or_sidecar(path)


def normalized_name(path: Path) -> str:
    return normalize_for_match(path.name + " " + path.parent.name)


def path_matches_terms(path: Path, search_terms: Iterable[str]) -> bool:
    haystack = normalized_name(path)
    return any(normalize_for_match(term) in haystack for term in search_terms)


def probable_relevance(path: Path, search_terms: Iterable[str]) -> str:
    haystack = normalized_name(path)
    score = sum(1 for term in search_terms if normalize_for_match(term) in haystack)
    if path.suffix.casefold() in {".bib", ".ris", ".enl"} or "bibliography" in haystack or "database" in haystack:
        score += 2
    if path.suffix.casefold() in {".doc", ".docx", ".rtf"}:
        score += 1
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def discover_candidate_files(roots: list[ConfiguredRoot], search_terms: Iterable[str]) -> list[tuple[ConfiguredRoot, Path, str]]:
    candidates: list[tuple[ConfiguredRoot, Path, str]] = []
    escaped_terms = [re.escape(term) for term in search_terms if term]
    search_pattern = "|".join(escaped_terms)
    extension_terms = " -o ".join(f"-iname '*{suffix}'" for suffix in sorted(RELEVANT_EXTENSIONS))
    for root in roots:
        command = (
            f"find {shlex.quote(str(root.path))} -type f \\( {extension_terms} \\) 2>/dev/null "
            f"| grep -iE {shlex.quote(search_pattern)} || true"
        )
        result = subprocess.run(
            ["bash", "-lc", command],
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            path = Path(line.strip())
            if not is_relevant_file(path):
                continue
            match_type = "file_name" if path_matches_terms(path, search_terms) else "directory_name"
            candidates.append((root, path, match_type))
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[ConfiguredRoot, Path, str]] = []
    for root, path, match_type in candidates:
        key = (root.label, str(path))
        if key in seen:
            continue
        seen.add(key)
        unique.append((root, path, match_type))
    return unique


def filename_metadata(path: Path) -> dict[str, str]:
    base = path.stem.replace("_", " ").replace("&", " and ")
    base = normalize_whitespace(base)
    year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})(?:-[0-9]{2,4})?\b", base)
    year = year_match.group(1) if year_match else ""
    author = ""
    title = base
    if year_match:
        before = base[: year_match.start()].strip(" -_,()")
        after = base[year_match.end() :].strip(" -_,()")
        author = before
        title = after or base
    title = re.sub(r"\s+", " ", title).strip(" -_,()")
    return {
        "probable_author": author,
        "probable_year": year,
        "probable_work_label": title or base,
    }


def source_file_id(path: Path, root: ConfiguredRoot) -> str:
    safe = slugify(path.stem)[:40]
    digest = sha256_file(path)[:12]
    return f"{safe}-{digest}"


def copy_to_local_cache(path: Path, root: ConfiguredRoot, *, source_folder_hint: str = "") -> dict[str, str]:
    SOURCE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    file_id = source_file_id(path, root)
    destination_dir = SOURCE_CACHE_ROOT / file_id
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / path.name
    if destination.exists():
        destination.unlink()
    shutil.copyfile(path, destination)
    source_stat = path.stat()
    os.utime(destination, (source_stat.st_atime, source_stat.st_mtime))
    return {
        "source_file_id": file_id,
        "original_path": safe_source_path(path, root),
        "copied_path": repo_relative_or_none(destination) or destination.name,
        "file_name": path.name,
        "file_type": path.suffix.casefold().lstrip("."),
        "file_size": str(path.stat().st_size),
        "sha256": sha256_file(path),
        "source_folder_hint": source_folder_hint or path.parent.name,
        "copy_date": datetime.now(timezone.utc).isoformat(),
        "copy_status": "copied",
        "notes": "",
    }


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_with_textutil(path: Path) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "converted.txt"
        subprocess.run(
            ["textutil", "-convert", "txt", "-output", str(output_path), str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return output_path.read_text(encoding="utf-8", errors="replace"), "textutil"


def _extract_docx(path: Path) -> tuple[str, str]:
    try:
        from docx import Document

        document = Document(path)
        lines = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(lines), "python-docx"
    except Exception:
        return _extract_with_textutil(path)


def _extract_doc(path: Path) -> tuple[str, str]:
    try:
        return _extract_with_textutil(path)
    except Exception:
        result = subprocess.run(
            ["antiword", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout, "antiword"


def _extract_pdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if normalize_whitespace(text):
            return text, "pypdf"
    except Exception:
        pass
    result = subprocess.run(
        ["pdftotext", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout, "pdftotext"


def extract_text_from_path(path: Path) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    suffix = path.suffix.casefold()
    try:
        if suffix in {".txt", ".bib", ".ris", ".enl", ".xml"}:
            return read_text_file(path), "text", warnings
        if suffix == ".docx":
            text, method = _extract_docx(path)
            return text, method, warnings
        if suffix in {".doc", ".rtf"}:
            text, method = _extract_doc(path if suffix == ".doc" else path)
            return text, method, warnings
        if suffix == ".pdf":
            text, method = _extract_pdf(path)
            return text, method, warnings
    except Exception as exc:
        warnings.append(f"{path.name}: extraction failed with {exc.__class__.__name__}")
        return "", "failed", warnings
    warnings.append(f"{path.name}: no extractor configured for {suffix}")
    return "", "unsupported", warnings
