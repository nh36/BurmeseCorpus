from __future__ import annotations

from dataclasses import dataclass
import re

from corpus_common import first_int, normalize_match_text, normalize_whitespace


PAGE_PATTERN = re.compile(r"^\s*([၀-၉]+)\s*$")
ENTRY_PATTERN = re.compile(r"^\s*([၀-၉]+(?:-[က-အ])?)\s*[။၊]\s*(.+?)\s*$")
LINE_PATTERN = re.compile(r"^\s*(?P<number>[၀-၉]+)\s*[။၊.]?\s*(?P<text>.+)$")
FACE_MARKER_PATTERN = re.compile(r"^\((မျက်နှာဘက်|ကျောဘက်|[က-အ]\s*မျက်နှာ)\)\s*$")
MYANMAR_SUFFIXES = {
    "က": "a",
    "ခ": "b",
    "ဂ": "c",
    "ဃ": "d",
}


@dataclass
class PageBlock:
    page_number: int
    lines: list[str]


def strip_trailing_footnote_digits(title: str) -> str:
    return normalize_whitespace(re.sub(r"[0-9]+$", "", title))


def parse_entry_number_token(raw_token: str) -> tuple[int, str]:
    raw_token = normalize_whitespace(raw_token)
    if "-" not in raw_token:
        number = first_int(raw_token)
        if number is None:
            raise ValueError(f"Unable to parse entry token: {raw_token}")
        return number, str(number)

    number_part, suffix_part = raw_token.split("-", 1)
    number = first_int(number_part)
    if number is None:
        raise ValueError(f"Unable to parse entry token: {raw_token}")
    suffix_normalized = MYANMAR_SUFFIXES.get(suffix_part.strip(), suffix_part.strip().casefold())
    return number, f"{number}{suffix_normalized}"


def split_page_blocks(text: str) -> list[PageBlock]:
    blocks: list[PageBlock] = []
    current_page: int | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        page_match = PAGE_PATTERN.match(raw_line.strip())
        if page_match:
            if current_page is not None:
                blocks.append(PageBlock(page_number=current_page, lines=current_lines))
            current_page = first_int(page_match.group(1))
            current_lines = []
            continue
        if current_page is not None:
            current_lines.append(raw_line)

    if current_page is not None:
        blocks.append(PageBlock(page_number=current_page, lines=current_lines))
    return blocks


def heading_from_lines(lines: list[str]) -> tuple[str, int, str] | None:
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        heading = entry_heading_from_line(stripped)
        if not heading:
            return None
        normalized_token, title = heading
        return normalized_token, int(normalized_token[: len(str(first_int(normalized_token)))]), title
    return None


def entry_heading_from_line(stripped: str) -> tuple[str, str] | None:
    match = ENTRY_PATTERN.match(stripped)
    if not match:
        return None
    raw_token = match.group(1)
    _, normalized_token = parse_entry_number_token(raw_token)
    title = strip_trailing_footnote_digits(match.group(2))
    if not title or title[0] in {"။", "၊", ".", ","}:
        return None
    return normalized_token, title


def heading_prefix_start(lines: list[str], heading_index: int) -> int:
    prefix_start = heading_index
    cursor = heading_index - 1
    while cursor >= 0:
        stripped = lines[cursor].strip()
        if not stripped or FACE_MARKER_PATTERN.match(stripped):
            prefix_start = cursor
            cursor -= 1
            continue
        break
    return prefix_start


def entry_page_first_line_number(lines: list[str]) -> int | None:
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or FACE_MARKER_PATTERN.match(stripped):
            continue
        match = LINE_PATTERN.match(stripped)
        if match:
            return first_int(match.group("number"))
    return None


def title_only_page(lines: list[str]) -> str | None:
    non_empty = [normalize_whitespace(line) for line in lines if normalize_whitespace(line)]
    if not non_empty:
        return None
    if any(ENTRY_PATTERN.match(line) or LINE_PATTERN.match(line) or FACE_MARKER_PATTERN.match(line) for line in non_empty):
        return None
    if len(non_empty) > 2:
        return None
    return strip_trailing_footnote_digits(" ".join(non_empty))


def build_source_entries(text: str) -> list[dict]:
    blocks = split_page_blocks(text)
    explicit_entries: list[dict] = []
    current_entry: dict | None = None

    for block in blocks:
        headings: list[tuple[int, int, str, str]] = []
        active_number = current_entry["source_entry_number"] if current_entry is not None else None
        active_key = current_entry["source_entry_key"] if current_entry is not None else None
        for index, raw_line in enumerate(block.lines):
            stripped = raw_line.strip()
            if not stripped:
                continue
            heading = entry_heading_from_line(stripped)
            if heading is None:
                continue
            normalized_token, title = heading
            candidate_number, _ = parse_entry_number_token(normalized_token)
            if active_number is not None:
                if candidate_number < active_number:
                    continue
                if candidate_number == active_number and normalized_token == active_key:
                    continue
            prefix_start = heading_prefix_start(block.lines, index)
            if prefix_start != 0 and prefix_start == index:
                continue
            headings.append((prefix_start, index, candidate_number, normalized_token, title))
            active_number = candidate_number
            active_key = normalized_token

        if not headings:
            if current_entry is not None:
                current_entry["page_blocks"].append({"page_number": block.page_number, "lines": block.lines})
            continue

        first_prefix_start = headings[0][0]
        if current_entry is not None and first_prefix_start > 0:
            current_entry["page_blocks"].append({"page_number": block.page_number, "lines": block.lines[:first_prefix_start]})

        for heading_offset, (prefix_start, heading_index, candidate_number, normalized_token, title) in enumerate(headings):
            if current_entry is not None:
                explicit_entries.append(current_entry)
            next_prefix_start = headings[heading_offset + 1][0] if heading_offset + 1 < len(headings) else len(block.lines)
            content_lines = block.lines[prefix_start:heading_index] + block.lines[heading_index + 1 : next_prefix_start]
            current_entry = {
                "source_entry_number_original": normalized_token,
                "source_entry_number": candidate_number,
                "source_entry_key": normalized_token,
                "source_title": title,
                "source_title_normalized": normalize_match_text(title),
                "source_page": block.page_number,
                "page_blocks": [{"page_number": block.page_number, "lines": content_lines}],
                "inferred_heading": False,
            }

    if current_entry is not None:
        explicit_entries.append(current_entry)

    split_entries: list[dict] = []
    for index, entry in enumerate(explicit_entries):
        next_entry = explicit_entries[index + 1] if index + 1 < len(explicit_entries) else None
        split_entries.extend(split_implicit_entries(entry, next_entry))

    finalized_entries: list[dict] = []
    for entry in split_entries:
        page_span = [page["page_number"] for page in entry["page_blocks"]]
        content_lines = [line for page in entry["page_blocks"] for line in page["lines"]]
        face_markers = []
        for line in content_lines:
            match = FACE_MARKER_PATTERN.match(line.strip())
            if match:
                face_markers.append(normalize_whitespace(match.group(1)))

        entry["page_span"] = page_span
        entry["page_span_label"] = ",".join(str(page) for page in page_span)
        entry["content_lines"] = content_lines
        entry["face_markers"] = face_markers
        entry["excerpt"] = normalize_whitespace(" ".join(line for line in content_lines[:4] if line.strip())) or None
        finalized_entries.append(entry)

    return finalized_entries


def split_implicit_entries(entry: dict, next_entry: dict | None) -> list[dict]:
    if next_entry is None:
        return [entry]

    gap = next_entry["source_entry_number"] - entry["source_entry_number"]
    if gap <= 1:
        return [entry]

    current_title_key = entry["source_title_normalized"]
    max_line_seen = 0
    candidate_start: int | None = None
    split_title: str | None = None
    split_title_index: int | None = None

    for page_index, page in enumerate(entry["page_blocks"]):
        lines = page["lines"]
        title_only = title_only_page(lines)
        first_line_number = entry_page_first_line_number(lines)

        if (
            candidate_start is not None
            and title_only is not None
            and normalize_match_text(title_only) != current_title_key
        ):
            split_title = title_only
            split_title_index = page_index
            break

        if first_line_number is not None:
            if max_line_seen > 0 and first_line_number <= 2 and candidate_start is None:
                candidate_start = page_index
            max_line_seen = max(max_line_seen, first_line_number)

    if candidate_start is None or split_title is None or split_title_index is None:
        return [entry]

    inferred_number = entry["source_entry_number"] + 1
    implicit_entry = {
        "source_entry_number_original": f"{inferred_number} (inferred)",
        "source_entry_number": inferred_number,
        "source_entry_key": str(inferred_number),
        "source_title": split_title,
        "source_title_normalized": normalize_match_text(split_title),
        "source_page": entry["page_blocks"][candidate_start]["page_number"],
        "page_blocks": entry["page_blocks"][candidate_start : split_title_index + 1],
        "inferred_heading": True,
    }
    truncated_entry = dict(entry)
    truncated_entry["page_blocks"] = entry["page_blocks"][:candidate_start]
    return [truncated_entry, implicit_entry]
