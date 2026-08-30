from pricing.cart import Cart, LineItem


def test_subtotal_sums_line_totals():
    cart = Cart([LineItem("A", 250, 2), LineItem("B", 100, 1)])
    assert cart.line_totals_cents() == [500, 100]
    assert cart.subtotal_cents() == 600


def test_zero_discount_returns_exact_subtotal():
    cart = Cart([LineItem("A", 250, 2)])
    assert cart.total_with_discount_cents(0) == cart.subtotal_cents()


def test_multi_item_discount_rounds_once_on_the_subtotal():
    cart = Cart([LineItem("A", 10, 1), LineItem("B", 10, 1), LineItem("C", 10, 1)])
    assert cart.total_with_discount_cents(15) == 26
