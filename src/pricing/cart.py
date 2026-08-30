from dataclasses import dataclass


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price_cents: int
    quantity: int


class Cart:
    def __init__(self, items: list[LineItem]) -> None:
        self.items = items

    def line_totals_cents(self) -> list[int]:
        return [item.unit_price_cents * item.quantity for item in self.items]

    def subtotal_cents(self) -> int:
        return sum(self.line_totals_cents())

    def total_with_discount_cents(self, discount_percent: int) -> int:
        """Apply a percentage discount to the subtotal and round to the
        nearest cent exactly once, on the subtotal - never once per line
        item, which compounds rounding error across a multi-line basket."""
        subtotal = self.subtotal_cents()
        discounted = subtotal * (100 - discount_percent)
        return (discounted + 50) // 100
