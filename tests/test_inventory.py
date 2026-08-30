from mcp_agent_benchmark.inventory import InventoryService, Product


PRODUCTS = [
    Product("A1", "Red Running Shoe", ("sport", "red", "shoe"), 10),
    Product("B2", "Blue Backpack", ("travel", "blue", "bag"), 4),
    Product("C3", "Green Water Bottle", ("sport", "green", "bottle"), 8),
]


def test_search_by_name():
    service = InventoryService(PRODUCTS)
    assert [p.sku for p in service.search("backpack")] == ["B2"]


def test_empty_query_returns_all():
    service = InventoryService(PRODUCTS)
    assert [p.sku for p in service.search("")] == ["A1", "B2", "C3"]
