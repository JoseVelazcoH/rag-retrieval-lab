import re
from collections.abc import Callable

from docsearch.md_clean import collapse_blank_lines

LEADING_COMMENT_PATTERN = re.compile(r"\A(?:\s*<!--.*?-->)*\s*", re.DOTALL)
INDEXTERM_PATTERN = re.compile(r"<indexterm\b[^>]*/>|<indexterm\b.*?</indexterm>", re.DOTALL)
SYSTEM_ENTITY_PATTERN = re.compile(r"<!ENTITY\s+([\w.-]+)\s+SYSTEM\s+\"([^\"]+)\"\s*>")
ENTITY_REFERENCE_PATTERN = re.compile(r"&([A-Za-z][\w.-]*);")
EMPTY_SPAN_PATTERN = re.compile(r"<span\b[^>]*>\s*</span>")
XML_ENTITIES = frozenset({"amp", "lt", "gt", "quot", "apos"})
CHAPTER_START = "<chapter"
EXCLUDED_PREFIXES = ("release", "func", "catalogs", "appendix-obsolete")
MAX_INCLUDE_DEPTH = 5
VERSION_TEXT = "current"
# Named entities declared by the PostgreSQL build, as numeric references or plain text.
NAMED_ENTITY_TEXT = {
    "version": VERSION_TEXT,
    "majorversion": VERSION_TEXT,
    "mdash": "&#8212;",
    "ndash": "&#8211;",
    "bull": "&#8226;",
    "nbsp": "&#160;",
    "zwsp": "",
    "ocirc": "&#244;",
    "rarr": "&#8594;",
    "aacute": "&#225;",
    "oacute": "&#243;",
    "copy": "&#169;",
    "AElig": "&#198;",
}


def starts_with_chapter(text: str) -> bool:
    """True when the first element, ignoring leading comments, is <chapter."""
    body = LEADING_COMMENT_PATTERN.sub("", text, count=1)
    return body.startswith(CHAPTER_START)


def is_excluded_name(name: str) -> bool:
    return name.startswith(EXCLUDED_PREFIXES)


def remove_indexterms(text: str) -> str:
    """Drop every <indexterm> block, multiline or self-closed."""
    return INDEXTERM_PATTERN.sub("", text)


def parse_system_entities(declarations: str) -> dict[str, str]:
    """Map entity name to file name for each <!ENTITY name SYSTEM "file"> declaration."""
    return dict(SYSTEM_ENTITY_PATTERN.findall(declarations))


def inline_includes(
    text: str,
    includes: dict[str, str],
    read: Callable[[str], str | None],
    depth: int = 0,
) -> str:
    """Replace &name; with the content of the file it includes (recursively, depth-capped).

    Unreadable files, unknown names and references past the depth cap are left untouched.
    """

    def replace(match: re.Match) -> str:
        file_name = includes.get(match.group(1))
        if file_name is None or depth >= MAX_INCLUDE_DEPTH:
            return match.group(0)
        included = read(file_name)
        if included is None:
            return match.group(0)
        return inline_includes(included, includes, read, depth + 1)

    return ENTITY_REFERENCE_PATTERN.sub(replace, text)


def replace_entities(text: str) -> str:
    """Resolve known named entities and drop unknown ones; XML built-ins stay as they are."""

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name in XML_ENTITIES:
            return match.group(0)
        return NAMED_ENTITY_TEXT.get(name, "")

    return ENTITY_REFERENCE_PATTERN.sub(replace, text)


def remove_empty_spans(markdown: str) -> str:
    return EMPTY_SPAN_PATTERN.sub("", markdown)


def prepare_markdown(markdown: str) -> str:
    """Final pass over pandoc output: no empty spans, no blank runs, starts with '# '."""
    cleaned = collapse_blank_lines(remove_empty_spans(markdown)).strip()
    if not cleaned.startswith("# "):
        raise ValueError("converted document does not start with a '# ' heading")
    return cleaned + "\n"
