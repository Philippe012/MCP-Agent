from shipping.quote import quote_cents


def test_odd_weight_is_billed_at_the_next_full_kilogram():
    assert quote_cents("standard", 1500) == 800
