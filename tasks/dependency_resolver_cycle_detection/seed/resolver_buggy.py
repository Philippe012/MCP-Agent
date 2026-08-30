def resolve_order(dependencies: dict[str, list[str]]) -> list[str]:
    order: list[str] = []
    # BUG: a single `visited` set can't distinguish "currently being
    # explored" from "fully resolved" - a node that's part of a cycle
    # looks "visited" the moment it's first entered, so the cycle back to
    # it is silently ignored instead of raising, and a wrong order is
    # returned with no error.
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        visited.add(node)
        for dep in dependencies.get(node, []):
            visit(dep)
        order.append(node)

    for node in dependencies:
        visit(node)
    return order
