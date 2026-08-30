
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TASK_ID = "bugfix_inventory"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_file: str
    # Files/dirs (relative to the repo root) copied verbatim into a fresh
    # episode workspace. Each entry must be as specific as possible - the
    # original design copied the *entire* `tasks/` directory, which would
    # have leaked every other task's task.md into every episode workspace
    # the moment a second task existed. Never list a whole shared
    # directory here; list this task's own files.
    seed_include: tuple[str, ...]
    # (workspace-relative destination, repo-root-relative source) pairs.
    # Used twice for the same reason: to seed the initial buggy workspace
    # (harness/workspace.py), and to mutate an otherwise-fixed workspace
    # back to buggy when checking whether a candidate regression test
    # actually proves the fix (verify.py). Keeping one mapping serving
    # both purposes means the "buggy" and "known-buggy-for-mutation-testing"
    # source can never drift apart into two copies.
    buggy_sources: tuple[tuple[str, str], ...]
    # Workspace-relative path the agent is expected to create. Stripped
    # during seeding (pre-task state has no regression test yet) and
    # required, then mutation-tested, during verification.
    regression_test_path: str
    # Python source run via `python -c` against the workspace. Must
    # exercise at least one behavioral property the *visible* test suite
    # (whatever's in seed_include) could not have caught on its own - this
    # is what keeps "passes the tests the agent can see" from ever being
    # sufficient for full reward, at every task, not just this one.
    behavior_check: str


_TASKS: dict[str, TaskSpec] = {}


def register(spec: TaskSpec) -> TaskSpec:
    if spec.task_id in _TASKS:
        raise ValueError(f"task_id {spec.task_id!r} is already registered")
    _TASKS[spec.task_id] = spec
    return spec


def get_task(task_id: str) -> TaskSpec:
    try:
        return _TASKS[task_id]
    except KeyError:
        raise KeyError(
            f"unknown task_id {task_id!r}; registered tasks: {sorted(_TASKS)}"
        ) from None


def all_task_ids() -> tuple[str, ...]:
    return tuple(_TASKS)


register(
    TaskSpec(
        task_id="bugfix_inventory",
        task_file="tasks/bugfix_inventory/task.md",
        seed_include=(
            "src/mcp_rl_env/__init__.py",
            "tests/test_inventory.py",
            "tasks/bugfix_inventory/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(("src/mcp_rl_env/inventory.py", "seed/inventory_buggy.py"),),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
from mcp_rl_env.inventory import InventoryService, Product
p = Product('X', 'Red Shoe', ('sport', 'red', 'shoe'), 1)
q = Product('Y', 'Blue Bag', ('travel', 'blue'), 2)
s = InventoryService([p, q])
assert [x.sku for x in s.search('red')] == ['X']
assert [x.sku for x in s.search('shoe')] == ['X']
assert [x.sku for x in s.search('re')] == ['X']
assert [x.sku for x in s.search('sport')] == ['X']
assert [x.sku for x in s.search('')] == ['X', 'Y']
""",
    )
)

register(
    TaskSpec(
        task_id="bugfix_restock_exact_match",
        task_file="tasks/bugfix_restock_exact_match/task.md",
        seed_include=(
            "src/mcp_rl_env/__init__.py",
            "tests/test_inventory.py",
            "tasks/bugfix_restock_exact_match/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/mcp_rl_env/inventory.py", "tasks/bugfix_restock_exact_match/seed/inventory_restock_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
from mcp_rl_env.inventory import InventoryService, Product
p1 = Product('A1', 'Red Shoe', ('sport', 'red', 'shoe'), 5)
p2 = Product('A10', 'Blue Bag', ('travel', 'blue'), 5)
s = InventoryService([p1, p2])
s.restock('A1', 3)
stocks = {p.sku: p.stock for p in s.products}
assert stocks['A1'] == 8, stocks
assert stocks['A10'] == 5, stocks
assert [x.sku for x in s.search('red')] == ['A1']
""",
    )
)

register(
    TaskSpec(
        task_id="decoy_context_efficiency",
        task_file="tasks/decoy_context_efficiency/task.md",
        seed_include=(
            "src/mcp_rl_env/__init__.py",
            "tests/test_inventory.py",
            "tasks/decoy_context_efficiency/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        # Two overrides: the real buggy source (identical to
        # bugfix_inventory's), plus a decoy file placed alongside it. The
        # decoy is a `buggy_sources` entry rather than a plain
        # seed_include path because its destination (src/mcp_rl_env/) sits
        # under a directory this task doesn't otherwise copy wholesale.
        buggy_sources=(
            ("src/mcp_rl_env/inventory.py", "seed/inventory_buggy.py"),
            ("src/mcp_rl_env/legacy_search.py", "tasks/decoy_context_efficiency/seed/legacy_search.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        # Identical to bugfix_inventory's - the intervention under study
        # here is the decoy file's presence, not a different bug or a
        # different notion of "correct" (see TASK_SUITE_DESIGN.md C2).
        behavior_check="""
from mcp_rl_env.inventory import InventoryService, Product
p = Product('X', 'Red Shoe', ('sport', 'red', 'shoe'), 1)
q = Product('Y', 'Blue Bag', ('travel', 'blue'), 2)
s = InventoryService([p, q])
assert [x.sku for x in s.search('red')] == ['X']
assert [x.sku for x in s.search('shoe')] == ['X']
assert [x.sku for x in s.search('re')] == ['X']
assert [x.sku for x in s.search('sport')] == ['X']
assert [x.sku for x in s.search('')] == ['X', 'Y']
""",
    )
)

register(
    TaskSpec(
        # Fixture for eval/reward_replication.py, not currently run against
        # a live agent (see TASK_SUITE_DESIGN.md C5) - reuses this same
        # registry and mutation-testing mechanism purely so the replication
        # study exercises the real machinery, not a second hand-rolled copy
        # of it.
        task_id="edge_case_coverage",
        task_file="tasks/edge_case_coverage/task.md",
        seed_include=(
            "src/mcp_rl_env/__init__.py",
            "tests/test_inventory.py",
            "tasks/edge_case_coverage/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/mcp_rl_env/inventory.py", "tasks/edge_case_coverage/seed/inventory_emptylist_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
from mcp_rl_env.inventory import InventoryService
assert InventoryService([]).search('anything') == []
assert InventoryService([]).search('') == []
""",
    )
)

register(
    TaskSpec(
        task_id="generalization_contact_index",
        task_file="tasks/generalization_contact_index/task.md",
        seed_include=(
            "src/contact_index/__init__.py",
            "tests/test_contact_index.py",
            "tasks/generalization_contact_index/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            (
                "src/contact_index/directory.py",
                "tasks/generalization_contact_index/seed/directory_buggy.py",
            ),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
from contact_index.directory import Directory, Contact
c1 = Contact('C1', 'Dana Reyes', ('family', 'primary', 'red'), '555-0101')
c2 = Contact('C2', 'Priya Shah', ('work', 'manager'), '555-0202')
d = Directory([c1, c2])
assert [c.contact_id for c in d.find('reyes')] == ['C1']
assert [c.contact_id for c in d.find('red')] == ['C1']
assert [c.contact_id for c in d.find('re')] == ['C1']
assert [c.contact_id for c in d.find('primary')] == ['C1']
assert [c.contact_id for c in d.find('')] == ['C1', 'C2']
""",
    )
)
