import pytest

from docsearch.query_kinds import identifier_tokens, query_kind


@pytest.mark.parametrize(
    "query",
    [
        "problem in installing apps in karbonn A5i",
        "upgrade to Android 4.4 broke wifi",
        "what does client_max_body_size do",
        "onCreate is called twice",
        "where is /system/app on my phone",
        "how to edit build.prop",
        "adb install -r keeps failing",
        "ERR_4021 at checkout",
    ],
)
def test_queries_with_exact_identifiers(query):
    assert query_kind(query) == "identifier"


@pytest.mark.parametrize(
    "query",
    [
        "phone gets hot when charging",
        "How do I stop apps from running in the background?",
        "USB debugging not working",
        "battery drains fast at night",
        "Can't send SMS after update",
    ],
)
def test_plain_language_queries(query):
    assert query_kind(query) == "natural"


def test_surrounding_punctuation_is_ignored():
    assert identifier_tokens("(build.prop),") == ["(build.prop),"]
    assert query_kind("why?") == "natural"


def test_plain_numbers_are_not_identifiers():
    assert query_kind("2 apps crash after 10 seconds") == "natural"


@pytest.mark.parametrize("query", ["Find my iPhone equivalent", "iOS on Android devices", "WiFi keeps dropping"])
def test_product_names_with_odd_casing_are_natural(query):
    assert query_kind(query) == "natural"


def test_markdown_emphasis_is_not_an_identifier():
    assert query_kind("stale icons in the notification _bar_?") == "natural"


def test_model_numbers_split_by_a_space_are_a_known_miss():
    # Documented limitation: "Nexus 5" is two plain tokens, so it is not detected.
    assert query_kind("custom ringtones on Nexus 5") == "natural"
