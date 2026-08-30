from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent

inventory_path = ROOT / "src" / "mcp_rl_env" / "inventory.py"
regression_path = ROOT / "tests" / "test_task_regression.py"

golden_test = '''from mcp_rl_env.inventory import InventoryService, Product


def test_product_matching_multiple_fields_is_returned_once():
    product = Product("X", "Red Sport Shoe", ("sport", "red", "shoe"), 1)
    service = InventoryService([product])

    # "r" matches both the name and multiple tags, but the product is unique.
    assert [p.sku for p in service.search("r")] == ["X"]
'''


def _search_is_already_fixed() -> bool:
    spec = importlib.util.spec_from_file_location("mcp_rl_env_inventory_check", inventory_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    product = module.Product("X", "Red Sport Shoe", ("sport", "red", "shoe"), 1)
    service = module.InventoryService([product])
    return [p.sku for p in service.search("r")] == ["X"]


def main() -> int:
    if _search_is_already_fixed():
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
