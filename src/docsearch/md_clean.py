"""Clean Hugo markdown (front matter, shortcodes, comments, links) into plain markdown."""
import re

FRONT_MATTER_PATTERN = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
TITLE_PATTERN = re.compile(r"^title:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
FENCE_PATTERN = re.compile(r"^[ \t]*(`{3,}|~{3,})")
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
SHORTCODE_PATTERN = re.compile(r"\{\{[<%]-?\s*(/?)([\w-]+)(.*?)-?/?[>%]\}\}", re.DOTALL)
ATTRIBUTE_PATTERN = r"""{name}=(["'])(.*?)\1"""
LINK_URL = r"""\(\s*[^()\s]*(?:\([^()]*\)[^()\s]*)*(?:\s+"[^"]*")?\s*\)"""
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]" + LINK_URL)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]" + LINK_URL)
BLANK_RUN_PATTERN = re.compile(r"\n{4,}")
TRAILING_SPACE_PATTERN = re.compile(r"[ \t]+$", re.MULTILINE)
COMMENT_SHORTCODE = "comment"
TOOLTIP_SHORTCODE = "glossary_tooltip"


def split_fences(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_code, block) pieces; fence lines belong to the code block."""
    blocks: list[tuple[bool, str]] = []
    current: list[str] = []
    in_code = False
    marker = ""
    for line in text.splitlines(keepends=True):
        match = FENCE_PATTERN.match(line)
        if not in_code and match:
            if current:
                blocks.append((False, "".join(current)))
            current, in_code, marker = [line], True, match.group(1)
        elif in_code and match and _closes(match.group(1), marker, line):
            current.append(line)
            blocks.append((True, "".join(current)))
            current, in_code = [], False
        else:
            current.append(line)
    if current:
        blocks.append((in_code, "".join(current)))
    return blocks


def _closes(fence: str, marker: str, line: str) -> bool:
    return fence[0] == marker[0] and len(fence) >= len(marker) and line.strip() == fence


def split_front_matter(raw: str) -> tuple[str, str]:
    """Return (front matter, body). Front matter is empty when the file has none."""
    match = FRONT_MATTER_PATTERN.match(raw)
    if not match:
        return "", raw
    return match.group(1), raw[match.end():]


def extract_title(front_matter: str) -> str | None:
    match = TITLE_PATTERN.search(front_matter)
    if not match:
        return None
    title = match.group(1).strip()
    if len(title) >= 2 and title[0] == title[-1] and title[0] in "\"'":
        title = title[1:-1]
    return title or None


def remove_html_comments(text: str) -> str:
    return COMMENT_PATTERN.sub("", text)


def _attribute(args: str, name: str) -> str | None:
    match = re.search(ATTRIBUTE_PATTERN.format(name=name), args)
    return match.group(2) if match else None


def _replace_shortcode(match: re.Match) -> str:
    name, args = match.group(2), match.group(3)
    if name == TOOLTIP_SHORTCODE and not match.group(1):
        return _attribute(args, "text") or _attribute(args, "term_id") or ""
    return ""


def _drop_comment_blocks(text: str) -> str:
    """Hugo {{< comment >}}...{{< /comment >}} holds authoring notes, not content."""
    pattern = re.compile(
        r"\{\{[<%]-?\s*comment\s*-?[>%]\}\}.*?\{\{[<%]-?\s*/comment\s*-?[>%]\}\}",
        re.DOTALL,
    )
    return pattern.sub("", text)


def replace_shortcodes(text: str) -> str:
    """glossary_tooltip becomes its text (or term_id); every other tag is dropped.

    Paired shortcodes keep their inner content because only the tags are removed.
    """
    return SHORTCODE_PATTERN.sub(_replace_shortcode, _drop_comment_blocks(text))


def strip_links(text: str) -> str:
    """[text](url) becomes text and ![alt](url) becomes alt."""
    return LINK_PATTERN.sub(r"\1", IMAGE_PATTERN.sub(r"\1", text))


def collapse_blank_lines(text: str) -> str:
    """Three or more blank lines become two."""
    return BLANK_RUN_PATTERN.sub("\n\n\n", text)


def _clean_prose(block: str) -> str:
    block = remove_html_comments(block)
    block = replace_shortcodes(block)
    block = strip_links(block)
    return TRAILING_SPACE_PATTERN.sub("", block)


def clean_body(body: str) -> str:
    """Clean prose outside code fences; fenced code is kept untouched."""
    pieces = [block if is_code else _clean_prose(block) for is_code, block in split_fences(body)]
    return collapse_blank_lines("".join(pieces)).strip()


def word_count(text: str) -> int:
    return len(text.split())


def clean_document(raw: str, fallback_title: str) -> tuple[str, int]:
    """Return the cleaned markdown ("# title" + body) and the body word count."""
    front, body = split_front_matter(raw)
    title = extract_title(front) or fallback_title
    cleaned = clean_body(body)
    return f"# {title}\n\n{cleaned}\n", word_count(cleaned)
