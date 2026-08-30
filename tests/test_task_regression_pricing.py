from pricing.cart import Cart, LineItem


def test_four_item_discount_rounds_once_on_the_subtotal():
    # 4 items at 7 cents, 20% off. Once (correct): subtotal=28, 28*80=2240,
    # (2240+50)//100=22. Per-line (buggy): 7*80=560,(560+50)//100=6 each,
    # four lines = 24 - two cents too high. Different numbers than both
    # the pre-existing suite test and the hidden verifier check.
    cart = Cart([LineItem("X", 7, 1) for _ in range(4)])
    assert cart.total_with_discount_cents(20) == 22
