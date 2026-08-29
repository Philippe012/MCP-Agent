from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    tags: tuple[str, ...]
    stock: int


class InventoryService:
    def __init__(self, products: list[Product]) -> None:
        self.products = products

    def search(self, query: str) -> list[Product]:
        query = query.strip().lower()

        if not query:
            return list(self.products)

        results: list[Product] = []

        for product in self.products:
            if query in product.name.lower():
                results.append(product)
            for tag in product.tags:
                if query in tag.lower():
                    results.append(product)

        return results
