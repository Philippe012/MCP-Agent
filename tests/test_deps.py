from deps.resolver import resolve_order


def test_simple_chain_orders_dependency_first():
    order = resolve_order({"app": ["lib"], "lib": []})
    assert order.index("lib") < order.index("app")


def test_diamond_dependency_orders_shared_dependency_first():
    order = resolve_order({"app": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
    assert order.index("d") < order.index("b")
    assert order.index("d") < order.index("c")
    assert order.index("b") < order.index("app")
    assert order.index("c") < order.index("app")
