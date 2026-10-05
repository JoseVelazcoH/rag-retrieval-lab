"""Convert the PostgreSQL manual chapters into data/pg-clean/ for the structure experiment.

Source: DocBook SGML files in data/pg-src/doc/src/sgml/ (top level only).
Pre-registered selection rule: files whose first element (ignoring the leading comment)
is <chapter, excluding names starting with release, func, catalogs or appendix-obsolete.

Per file: &name; includes declared in filelist.sgml are inlined (chapters such as
extend.sgml are otherwise empty shells), <indexterm> blocks are removed, known entities
are resolved, then pandoc (docbook -> gfm) converts to markdown. Leftover empty spans
and blank runs are cleaned. Outputs under MIN_WORDS words are skipped, and a file that
pandoc rejects is skipped with a warning.

Prerequisites: pandoc on PATH and the PostgreSQL source in data/pg-src.
Usage: pg_prepare.py
"""
import shutil
import subprocess

from _common import ROOT
from docsearch.md_clean import word_count
from docsearch.sgml_clean import (
    inline_includes,
    is_excluded_name,
    parse_system_entities,
    prepare_markdown,
    remove_indexterms,
    replace_entities,
    starts_with_chapter,
)

SOURCE_DIR = ROOT / "data" / "pg-src" / "doc" / "src" / "sgml"
CLEAN_DIR = ROOT / "data" / "pg-clean"
FILELIST = "filelist.sgml"
MIN_WORDS = 50
PANDOC_COMMAND = ("pandoc", "-f", "docbook", "-t", "gfm", "--wrap=none")


def select_sources() -> list:
    return [
        path
        for path in sorted(SOURCE_DIR.glob("*.sgml"))
        if not is_excluded_name(path.stem)
        and starts_with_chapter(path.read_text(encoding="utf-8"))
    ]


def read_included(file_name: str) -> str | None:
    path = SOURCE_DIR / file_name
    return path.read_text(encoding="utf-8") if path.is_file() else None


def to_markdown(sgml: str, includes: dict[str, str]) -> str:
    sgml = inline_includes(sgml, includes, read_included)
    sgml = replace_entities(remove_indexterms(sgml))
    result = subprocess.run(
        PANDOC_COMMAND, input=sgml, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip().splitlines()[0] if result.stderr else "pandoc failed")
    return prepare_markdown(result.stdout)


def main() -> None:
    if shutil.which(PANDOC_COMMAND[0]) is None:
        raise SystemExit("pandoc is required but was not found on PATH.")
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Missing {SOURCE_DIR}. Place the PostgreSQL sources there first.")
    includes = parse_system_entities((SOURCE_DIR / FILELIST).read_text(encoding="utf-8"))
    sources = select_sources()
    if CLEAN_DIR.exists():
        shutil.rmtree(CLEAN_DIR)
    CLEAN_DIR.mkdir(parents=True)
    written, total_words, short, failed = 0, 0, [], []
    for number, source in enumerate(sources, start=1):
        print(f"\rConverting {number}/{len(sources)}", end="", flush=True)
        try:
            markdown = to_markdown(source.read_text(encoding="utf-8"), includes)
        except (RuntimeError, ValueError) as error:
            failed.append(f"{source.name}: {error}")
            continue
        words = word_count(markdown)
        if words < MIN_WORDS:
            short.append(f"{source.name} ({words} words)")
            continue
        (CLEAN_DIR / f"{source.stem}.md").write_text(markdown, encoding="utf-8")
        written += 1
        total_words += words
    print()
    print(f"Selected: {len(sources)}")
    print(f"Converted: {written} ({total_words} words) -> {CLEAN_DIR}")
    print(f"Skipped (under {MIN_WORDS} words): {len(short)}")
    for entry in short:
        print(f"  {entry}")
    print(f"Skipped (pandoc or format failure): {len(failed)}")
    for entry in failed:
        print(f"  WARNING {entry}")


if __name__ == "__main__":
    main()
