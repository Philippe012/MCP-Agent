from pathlib import Path

ROOT = Path(__file__).resolve().parent

inventory_path = ROOT / "src" / "mcp_rl_env" / "inventory.py"
regression_path = ROOT / "tests" / "test_task_regression.py"

golden_code = '''        results: list[Product] = []
        for product in self.products:
            matched = query in product.name.lower()
            if not matched:
                matched = any(query in tag.lower() for tag in product.tags)
            if matched:
                results.append(product)
        return results
'''

golden_test = '''from mcp_rl_env.inventory import InventoryService, Product


def test_product_matching_multiple_fields_is_returned_once():
    product = Product("X", "Red Sport Shoe", ("sport", "red", "shoe"), 1)
    service = InventoryService([product])

    # "r" matches both the name and multiple tags, but the product is unique.
    assert [p.sku for p in service.search("r")] == ["X"]
'''


def main() -> int:
    text = inventory_path.read_text(encoding="utf-8")

    if golden_code in text:
        print("Golden solution is already applied.")
    else:
        print("Current workspace differs from the original seed.")
        print("Golden solution was not applied automatically.")
        print("Use a fresh seed workspace to apply the golden solution.")
        return 1

    regression_path.write_text(golden_test, encoding="utf-8")
    print("Golden regression test applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())