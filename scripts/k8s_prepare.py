"""Clean the Kubernetes concept docs into data/k8s-clean/ for the structure experiment.

Each Hugo markdown file becomes "# <title>" plus its cleaned body (front matter,
shortcodes, HTML comments and link targets removed; headings, lists, code and tables
kept). Files whose cleaned body has under MIN_BODY_WORDS words (section index stubs)
are skipped.

Usage: k8s_prepare.py
"""
import shutil

from _common import ROOT
from docsearch.md_clean import clean_document

SOURCE_DIR = ROOT / "data" / "k8s-website" / "content" / "en" / "docs" / "concepts"
CLEAN_DIR = ROOT / "data" / "k8s-clean"
MIN_BODY_WORDS = 50


def main() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Missing {SOURCE_DIR}. Clone kubernetes/website first.")
    if CLEAN_DIR.exists():
        shutil.rmtree(CLEAN_DIR)
    sources = sorted(SOURCE_DIR.rglob("*.md"))
    written, skipped, total_words = 0, [], 0
    for source in sources:
        relative = source.relative_to(SOURCE_DIR)
        text, words = clean_document(source.read_text(encoding="utf-8"), source.stem)
        if words < MIN_BODY_WORDS:
            skipped.append(f"{relative} ({words} words)")
            continue
        target = CLEAN_DIR / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written += 1
        total_words += words
        print(f"\rCleaning {written + len(skipped)}/{len(sources)}", end="", flush=True)
    print()
    print(f"Source files: {len(sources)}")
    print(f"Written: {written} ({total_words} body words) -> {CLEAN_DIR}")
    print(f"Skipped (under {MIN_BODY_WORDS} words): {len(skipped)}")
    for entry in skipped:
        print(f"  {entry}")


if __name__ == "__main__":
    main()
