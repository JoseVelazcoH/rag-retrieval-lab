"""Classify queries by whether they contain an exact identifier.

The rule is fixed before looking at any retrieval result, so the split cannot be
tuned to favor a search mode. A token counts as an identifier when it looks like
something a person would copy and paste rather than paraphrase.

Known limitation: a model number split by a space ("Nexus 5") is two plain
tokens and is not detected.
"""
import re

_EDGE_PUNCTUATION = "\"'`.,;:!?()[]{}<>"

_RULES = {
    "letters_and_digits": re.compile(r"(?=.*[A-Za-z])(?=.*\d)"),  # A5i, S4, ERR_4021
    "version_number": re.compile(r"^\d+(\.\d+)+$"),  # 4.4, 2.3.6
    "underscore": re.compile(r"[A-Za-z0-9]_[A-Za-z0-9]"),  # client_max_body_size
    "camel_case": re.compile(r"[a-z]{2}[A-Z]"),  # onCreate, getString
    "path": re.compile(r"[/\\]"),  # /system/app
    "file_name": re.compile(r"^\w+\.[A-Za-z]{2,5}$"),  # build.prop, app.apk
    "flag": re.compile(r"^--?[A-Za-z]"),  # -r, --force
}


def identifier_rules(token: str) -> list[str]:
    """Names of the rules a single token matches, empty when it is a plain word."""
    cleaned = token.strip(_EDGE_PUNCTUATION) if not token.startswith("-") else token.rstrip(_EDGE_PUNCTUATION)
    if not cleaned:
        return []
    return [name for name, pattern in _RULES.items() if pattern.search(cleaned)]


def identifier_tokens(query: str) -> list[str]:
    return [token for token in query.split() if identifier_rules(token)]


def query_kind(query: str) -> str:
    """'identifier' when any token matches a rule, otherwise 'natural'."""
    return "identifier" if identifier_tokens(query) else "natural"
