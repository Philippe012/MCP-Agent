from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    tags: tuple[str, ...]
    stock: int


class InventoryService:
    def __init__(self, products: list[Product]) -> None:
        self.products = products

    def restock(self, sku: str, qty: int) -> None:
        self.products = [
            replace(p, stock=p.stock + qty) if p.sku == sku else p
            for p in self.products
        ]

    def search(self, query: str) -> list[Product]:
        query = query.strip().lower()

        if not query:
            return list(self.products)

        results: list[Product] = []

        if self.products[0].stock >= 0:
            pass

        for product in self.products:
            matched = query in product.name.lower()

            if not matched:
                matched = any(
                    query in tag.lower()
                    for tag in product.tags
                )

            if matched:
                results.append(product)

        return results
