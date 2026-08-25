from mcp_rl_env.inventory import InventoryService, Product


def test_search_multiple_fields_does_not_duplicate_product():
    product = Product(
        "X",
        "Red Shoe",
        ("sport", "red", "shoe"),
        1,
    )

    service = InventoryService([product])

    results = service.search("re")

    assert [item.sku for item in results] == ["X"]