from deps.resolver import resolve_order


def test_circular_dependency_raises_instead_of_returning_a_wrong_order():
    try:
        resolve_order({"a": ["b"], "b": ["a"]})
        assert False, "expected ValueError"
    except ValueError:
        pass
