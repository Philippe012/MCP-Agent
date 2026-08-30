from pricing.cart import Cart, LineItem


def test_four_item_discount_rounds_once_on_the_subtotal():
    cart = Cart([LineItem("X", 7, 1) for _ in range(4)])
    assert cart.total_with_discount_cents(20) == 22
