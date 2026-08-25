from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / "src/mcp_rl_env/inventory.py"
text = path.read_text(encoding="utf-8")
old = '''        results: list[Product] = []\n        for product in self.products:\n            if query in product.name.lower():\n                results.append(product)\n            for tag in product.tags:\n                if query in tag.lower():\n                    results.append(product)\n        return results\n'''
new = '''        results: list[Product] = []\n        for product in self.products:\n            matched = query in product.name.lower()\n            if not matched:\n                matched = any(query in tag.lower() for tag in product.tags)\n            if matched:\n                results.append(product)\n        return results\n'''
if old not in text:
    raise SystemExit("Seed file does not match expected task version")
path.write_text(text.replace(old, new), encoding="utf-8")

regression = ROOT / "tests/test_task_regression.py"
regression.write_text('''from mcp_rl_env.inventory import InventoryService, Product\n\n\ndef test_product_matching_multiple_fields_is_returned_once():\n    product = Product("X", "Red Sport Shoe", ("sport", "red", "shoe"), 1)\n    service = InventoryService([product])\n\n    # "r" matches both the name and multiple tags, but the product is unique.\n    assert [p.sku for p in service.search("r")] == ["X"]\n''', encoding="utf-8")
print("Applied golden reference solution.")
