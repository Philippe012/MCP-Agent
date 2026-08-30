import pytest

from shipping.quote import quote_cents


def test_exact_kilogram_weight_is_quoted_correctly():
    assert quote_cents("standard", 2000) == 800
    assert quote_cents("express", 1000) == 900


def test_unknown_service_raises():
    with pytest.raises(ValueError):
        quote_cents("overnight", 1000)
