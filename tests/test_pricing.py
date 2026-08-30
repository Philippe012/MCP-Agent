from pricing.cart import Cart, LineItem


def test_subtotal_sums_line_totals():
    cart = Cart([LineItem("A", 250, 2), LineItem("B", 100, 1)])
    assert cart.line_totals_cents() == [500, 100]
    assert cart.subtotal_cents() == 600


def test_zero_discount_returns_exact_subtotal():
    cart = Cart([LineItem("A", 250, 2)])
    assert cart.total_with_discount_cents(0) == cart.subtotal_cents()


def test_multi_item_discount_rounds_once_on_the_subtotal():
    # Three 10-cent items, 15% off.
    # Correct (round once on the 30-cent subtotal): 30*85=2550 -> (2550+50)//100 = 26.
    # Buggy (round each 10-cent line separately): 10*85=850 -> (850+50)//100 = 9 per
    # line, three lines = 27 - one cent too high.
    cart = Cart([LineItem("A", 10, 1), LineItem("B", 10, 1), LineItem("C", 10, 1)])
    assert cart.total_with_discount_cents(15) == 26
