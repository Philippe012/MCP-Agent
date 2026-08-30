def resolve_order(dependencies: dict[str, list[str]]) -> list[str]:
    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ValueError(f"circular dependency detected involving {node!r}")
        visiting.add(node)
        for dep in dependencies.get(node, []):
            visit(dep)
        visiting.discard(node)
        visited.add(node)
        order.append(node)

    for node in dependencies:
        visit(node)
    return order
