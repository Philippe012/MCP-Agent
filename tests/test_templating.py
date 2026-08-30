from templating.render import render


def test_unspaced_placeholder_is_substituted():
    assert render("Hi {{name}}", {"name": "Bo"}) == "Hi Bo"


def test_unknown_key_placeholder_is_left_untouched():
    assert render("{{missing}}", {}) == "{{missing}}"
