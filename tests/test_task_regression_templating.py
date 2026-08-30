from templating.render import render


def test_placeholder_with_surrounding_whitespace_is_substituted():
    assert render("Hello {{ name }}!", {"name": "Ada"}) == "Hello Ada!"
