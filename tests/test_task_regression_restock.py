from mcp_rl_env.inventory import InventoryService, Product


def test_restock_only_affects_the_exact_sku():
    p1 = Product("A1", "Red Shoe", ("sport", "red", "shoe"), 5)
    p2 = Product("A10", "Blue Bag", ("travel", "blue"), 5)
    service = InventoryService([p1, p2])

    service.restock("A1", 3)

    stocks = {p.sku: p.stock for p in service.products}
    assert stocks["A1"] == 8
    assert stocks["A10"] == 5
