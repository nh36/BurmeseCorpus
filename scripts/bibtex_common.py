from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path


FIELD_ORDER = [
    "author",
    "editor",
    "title",
    "shorttitle",
    "journal",
    "booktitle",
    "publisher",
    "address",
    "year",
    "volume",
    "number",
    "pages",
    "doi",
    "url",
    "isbn",
    "language",
    "script",
    "reviewstatus",
    "translationrelevance",
    "evidence",
    "sourceofauthority",
    "matchedexternalkey",
    "familyid",
    "note",
]

TEXT_FIELD_NAMES = {
    "author",
    "editor",
    "title",
    "shorttitle",
    "journal",
    "booktitle",
    "publisher",
    "address",
    "doi",
    "url",
    "isbn",
    "language",
    "script",
    "note",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "bibtex"


def normalize_for_match(value: str | None) -> str:
    text = normalize_whitespace(value)
    if not text:
        return ""
    text = text.casefold()
    text = re.sub(r"[“”‘’'\"`]", "", text)
    text = re.sub(r"[^0-9a-z\u1000-\u109f]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_keyword_tokens(value: str | None) -> list[str]:
    text = normalize_for_match(value)
    if not text:
        return []
    tokens = [token for token in text.split() if len(token) > 2 and token not in {"the", "and", "for", "with", "from"}]
    return tokens[:8]


def surname_token(author_value: str | None) -> str:
    text = normalize_whitespace(author_value)
    if not text:
        return ""
    first = re.split(r"\s+(?:and|/)\s+", text, maxsplit=1)[0]
    parts = [part for part in re.split(r"[\s,]+", first) if part]
    return parts[-1].casefold() if parts else ""


def short_title_token(title_value: str | None) -> str:
    for token in title_keyword_tokens(title_value):
        return token
    return "work"


def make_bibtex_key(
    *,
    author: str | None,
    year: str | None,
    title: str | None,
    preferred: str | None = None,
    fallback_prefix: str = "workUnresolved",
    existing_keys: set[str] | None = None,
) -> str:
    existing = existing_keys if existing_keys is not None else set()
    if preferred:
        base = re.sub(r"[^A-Za-z0-9]+", "", preferred)
        if base:
            key = base
            suffix_index = 1
            while key in existing:
                suffix_index += 1
                key = f"{base}{suffix_index}"
            existing.add(key)
            return key
    base_parts = []
    surname = surname_token(author)
    if surname:
        camel = "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", surname) if part)
        if camel:
            base_parts.append(camel[:1].lower() + camel[1:])
    year_token = re.search(r"(1[0-9]{3}|20[0-9]{2})", year or "")
    if year_token:
        base_parts.append(year_token.group(1))
    title_token = short_title_token(title)
    if title_token:
        camel = "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", title_token) if part)
        if camel:
            base_parts.append(camel[:1].lower() + camel[1:])
    base = "".join(base_parts) or fallback_prefix
    if base.startswith("workUnresolved") and base == fallback_prefix:
        base = fallback_prefix
    key = base
    counter = 1
    while key in existing:
        counter += 1
        key = f"{base}{counter:04d}" if base == fallback_prefix else f"{base}{counter}"
    existing.add(key)
    return key


def split_top_level(value: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    brace_level = 0
    quote_open = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"' and brace_level == 0:
            quote_open = not quote_open
        elif not quote_open:
            if char == "{":
                brace_level += 1
            elif char == "}":
                brace_level = max(brace_level - 1, 0)
        if char == delimiter and brace_level == 0 and not quote_open:
            segment = "".join(current).strip()
            if segment:
                parts.append(segment)
            current = []
            continue
        current.append(char)
    segment = "".join(current).strip()
    if segment:
        parts.append(segment)
    return parts


def strip_wrapping_delimiters(value: str) -> str:
    text = value.strip()
    changed = True
    while changed and len(text) >= 2:
        changed = False
        if (text.startswith("{") and text.endswith("}")) or (text.startswith('"') and text.endswith('"')):
            inner = text[1:-1].strip()
            if inner:
                text = inner
                changed = True
    return normalize_whitespace(text)


def parse_entry_fields(body: str) -> tuple[str, dict[str, str], list[str]]:
    warnings: list[str] = []
    parts = split_top_level(body)
    if not parts:
        return "", {}, ["empty BibTeX body"]
    bibtex_key = parts[0].strip().strip(",")
    fields: dict[str, str] = {}
    for field_index, part in enumerate(parts[1:], start=1):
        if "=" not in part:
            warnings.append(f"field {field_index} in {bibtex_key or '<unknown>'} is missing '='")
            continue
        field_name, raw_value = part.split("=", 1)
        field_name = field_name.strip().casefold()
        value = strip_wrapping_delimiters(raw_value.strip().rstrip(","))
        fields[field_name] = value
    return bibtex_key, fields, warnings


def _read_balanced_entry(text: str, start_index: int, opening: str, closing: str) -> tuple[str, int, str | None]:
    level = 0
    index = start_index
    while index < len(text):
        char = text[index]
        if char == opening:
            level += 1
        elif char == closing:
            level -= 1
            if level == 0:
                return text[start_index + 1 : index], index + 1, None
        index += 1
    return text[start_index + 1 :], len(text), "unterminated BibTeX entry"


def parse_bibtex_text(text: str, *, source_label: str = "") -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    warnings: list[str] = []
    index = 0
    while index < len(text):
        at_index = text.find("@", index)
        brace_match = re.search(r"(?m)^[ \t]*\{[A-Za-z0-9:_./+-]+\s*,", text[index:])
        brace_index = index + brace_match.start() if brace_match else -1
        if at_index == -1 and brace_index == -1:
            break
        if brace_index != -1 and (at_index == -1 or brace_index < at_index):
            start = brace_index + text[brace_index:].find("{")
            body, next_index, warning = _read_balanced_entry(text, start, "{", "}")
            bibtex_key, fields, field_warnings = parse_entry_fields(body)
            raw_entry = text[brace_index:next_index]
            if warning:
                warnings.append(f"{source_label}: {warning} near malformed entry {bibtex_key or '<unknown>'}")
            warnings.append(f"{source_label}: salvaged malformed entry {bibtex_key or '<unknown>'} without explicit @type")
            warnings.extend(f"{source_label}: {message}" for message in field_warnings)
            entries.append(
                {
                    "entry_type": "unknown",
                    "bibtex_key": bibtex_key,
                    "fields": fields,
                    "raw_entry": raw_entry,
                }
            )
            index = next_index
            continue
        index = at_index + 1
        type_match = re.match(r"([A-Za-z]+)\s*([\{\(])", text[index:])
        if not type_match:
            warnings.append(f"{source_label}: could not parse BibTeX type near offset {at_index}")
            continue
        entry_type = type_match.group(1).casefold()
        opening = type_match.group(2)
        closing = "}" if opening == "{" else ")"
        body_start = index + type_match.end() - 1
        body, next_index, warning = _read_balanced_entry(text, body_start, opening, closing)
        raw_entry = text[at_index:next_index]
        if entry_type in {"comment", "preamble", "string"}:
            index = next_index
            continue
        bibtex_key, fields, field_warnings = parse_entry_fields(body)
        if warning:
            warnings.append(f"{source_label}: {warning} near entry {bibtex_key or '<unknown>'}")
        warnings.extend(f"{source_label}: {message}" for message in field_warnings)
        entries.append(
            {
                "entry_type": entry_type,
                "bibtex_key": bibtex_key,
                "fields": fields,
                "raw_entry": raw_entry,
            }
        )
        index = next_index
    return entries, warnings


def serialize_bibtex_entry(entry: dict) -> str:
    def escape_bibtex_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

    entry_type = entry["entry_type"]
    bibtex_key = entry["bibtex_key"]
    fields: dict[str, str] = entry["fields"]
    ordered_fields = [field for field in FIELD_ORDER if fields.get(field)]
    ordered_fields.extend(sorted(field for field in fields if fields.get(field) and field not in FIELD_ORDER))
    lines = [f"@{entry_type}{{{bibtex_key},"]
    for field in ordered_fields:
        value = escape_bibtex_value(fields[field])
        lines.append(f"  {field} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def write_bibtex(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n\n".join(serialize_bibtex_entry(entry) for entry in entries) + ("\n" if entries else "")
    path.write_text(payload, encoding="utf-8")


def duplicate_keys(entries: list[dict]) -> list[str]:
    counter = Counter(entry["bibtex_key"] for entry in entries if entry.get("bibtex_key"))
    return sorted(key for key, count in counter.items() if count > 1)
