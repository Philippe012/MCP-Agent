from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent

inventory_path = ROOT / "src" / "mcp_agent_benchmark" / "inventory.py"
regression_path = ROOT / "tests" / "test_task_regression.py"

golden_test = '''from mcp_agent_benchmark.inventory import InventoryService, Product


def test_search_multiple_fields_does_not_duplicate_product():
    product = Product(
        "X",
        "Red Shoe",
        ("sport", "red", "shoe"),
        1,
    )

    service = InventoryService([product])

    results = service.search("re")

    assert [item.sku for item in results] == ["X"]'''


def _search_is_already_fixed() -> bool:
    spec = importlib.util.spec_from_file_location("mcp_agent_benchmark_inventory_check", inventory_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    product = module.Product("X", "Red Sport Shoe", ("sport", "red", "shoe"), 1)
    service = module.InventoryService([product])
    return [p.sku for p in service.search("r")] == ["X"]


def main() -> int:
    if not _search_is_already_fixed():
        print("Current workspace differs from the original seed.")
        print("Golden solution was not applied automatically.")
        print("Use a fresh seed workspace to apply the golden solution.")
        return 1

    print("Golden solution is already applied.")

    if regression_path.exists():
        print("Golden regression test already present (left unmodified).")
    else:
        regression_path.write_text(golden_test, encoding="utf-8")
        print("Golden regression test applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
