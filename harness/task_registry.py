
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TASK_ID = "bugfix_inventory"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_file: str
    seed_include: tuple[str, ...]
    buggy_sources: tuple[tuple[str, str], ...]
    regression_test_path: str
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
            "src/mcp_agent_benchmark/__init__.py",
            "tests/test_inventory.py",
            "tasks/bugfix_inventory/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(("src/mcp_agent_benchmark/inventory.py", "seed/inventory_buggy.py"),),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from mcp_agent_benchmark.inventory import InventoryService, Product
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
            "src/mcp_agent_benchmark/__init__.py",
            "tests/test_inventory.py",
            "tasks/bugfix_restock_exact_match/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/mcp_agent_benchmark/inventory.py", "tasks/bugfix_restock_exact_match/seed/inventory_restock_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from mcp_agent_benchmark.inventory import InventoryService, Product
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
            "src/mcp_agent_benchmark/__init__.py",
            "tests/test_inventory.py",
            "tasks/decoy_context_efficiency/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/mcp_agent_benchmark/inventory.py", "seed/inventory_buggy.py"),
            ("src/mcp_agent_benchmark/legacy_search.py", "tasks/decoy_context_efficiency/seed/legacy_search.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from mcp_agent_benchmark.inventory import InventoryService, Product
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
        task_id="edge_case_coverage",
        task_file="tasks/edge_case_coverage/task.md",
        seed_include=(
            "src/mcp_agent_benchmark/__init__.py",
            "tests/test_inventory.py",
            "tasks/edge_case_coverage/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/mcp_agent_benchmark/inventory.py", "tasks/edge_case_coverage/seed/inventory_emptylist_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from mcp_agent_benchmark.inventory import InventoryService
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


register(
    TaskSpec(
        task_id="ledger_transfer_rollback",
        task_file="tasks/ledger_transfer_rollback/task.md",
        seed_include=(
            "src/ledger/__init__.py",
            "tests/test_ledger.py",
            "tasks/ledger_transfer_rollback/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/ledger/account.py", "tasks/ledger_transfer_rollback/seed/account_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from ledger.account import Account, Ledger
            l = Ledger([Account('A', 100), Account('B', 50)])
            l.transfer('A', 'B', 30)
            assert l.balance_of('A') == 70
            assert l.balance_of('B') == 80
            assert l.total_balance() == 150
            try:
                l.transfer('A', 'ZZZ', 10)
                assert False, 'expected KeyError'
            except KeyError:
                pass
            assert l.balance_of('A') == 70
            assert l.total_balance() == 150
        """,
    )
)

register(
    TaskSpec(
        task_id="calendar_booking_overlap",
        task_file="tasks/calendar_booking_overlap/task.md",
        seed_include=(
            "src/scheduler/__init__.py",
            "tests/test_calendar.py",
            "tasks/calendar_booking_overlap/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/scheduler/calendar.py", "tasks/calendar_booking_overlap/seed/calendar_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from scheduler.calendar import Calendar
            cal = Calendar()
            cal.book('R1', 540, 600)
            cal.book('R1', 600, 660)
            assert len(cal.bookings) == 2
            try:
                cal.book('R1', 590, 610)
                assert False, 'expected ValueError'
            except ValueError:
                pass
            cal.book('R2', 540, 600)
            assert len(cal.bookings) == 3
        """,
    )
)

register(
    TaskSpec(
        task_id="config_loader_backward_compat",
        task_file="tasks/config_loader_backward_compat/task.md",
        seed_include=(
            "src/configloader/__init__.py",
            "tests/test_configloader.py",
            "tasks/config_loader_backward_compat/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/configloader/loader.py", "tasks/config_loader_backward_compat/seed/loader_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from configloader.loader import load_timeout, load_retries
            assert load_timeout({'timeout': 45}) == 45
            assert load_retries({'retries': 5}) == 5
            assert load_timeout({'network': {'timeout': 99}}) == 99
            assert load_timeout({'network': {'timeout': 99}, 'timeout': 1}) == 99
            assert load_timeout({}) == 30
            assert load_retries({}) == 3
        """,
    )
)

register(
    TaskSpec(
        task_id="batch_partial_failure_recovery",
        task_file="tasks/batch_partial_failure_recovery/task.md",
        seed_include=(
            "src/batch/__init__.py",
            "tests/test_batch.py",
            "tasks/batch_partial_failure_recovery/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/batch/processor.py", "tasks/batch_partial_failure_recovery/seed/processor_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        # The visible suite only exercises the all-success path - never a
        # batch with a failing item, which is exactly what this checks.
        behavior_check="""
            from batch.processor import process_batch
            def worker(x):
                if x == 2:
                    raise ValueError('boom')
                return x * 10
            r = process_batch([1, 2, 3], worker)
            assert r.succeeded == [10, 30]
            assert len(r.failed) == 1
            assert r.failed[0][0] == 2
            r2 = process_batch([1, 2, 3], lambda x: x + 1)
            assert r2.succeeded == [2, 3, 4]
            assert r2.failed == []
        """,
    )
)

register(
    TaskSpec(
        task_id="lru_cache_eviction_invariant",
        task_file="tasks/lru_cache_eviction_invariant/task.md",
        seed_include=(
            "src/cache/__init__.py",
            "tests/test_lru_cache.py",
            "tasks/lru_cache_eviction_invariant/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/cache/lru.py", "tasks/lru_cache_eviction_invariant/seed/lru_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from cache.lru import LRUCache
            c = LRUCache(2)
            c.put('a', 1)
            c.put('b', 2)
            c.get('a')
            c.put('c', 3)
            assert c.get('a') == 1
            assert c.get('b') is None
            assert c.get('c') == 3
        """,
    )
)

register(
    TaskSpec(
        task_id="template_render_decoy",
        task_file="tasks/template_render_decoy/task.md",
        seed_include=(
            "src/templating/__init__.py",
            "tests/test_templating.py",
            "tasks/template_render_decoy/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/templating/render.py", "tasks/template_render_decoy/seed/render_buggy.py"),
            ("src/templating/legacy_render.py", "tasks/template_render_decoy/seed/legacy_render.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from templating.render import render
            assert render('Hello {{ name }}!', {'name': 'Ada'}) == 'Hello Ada!'
            assert render('Hi {{name}}', {'name': 'Bo'}) == 'Hi Bo'
            assert render('{{ missing }}', {}) == '{{ missing }}'
        """,
    )
)

register(
    TaskSpec(
        task_id="pricing_discount_rounding",
        task_file="tasks/pricing_discount_rounding/task.md",
        seed_include=(
            "src/pricing/__init__.py",
            "tests/test_pricing.py",
            "tasks/pricing_discount_rounding/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/pricing/cart.py", "tasks/pricing_discount_rounding/seed/cart_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from pricing.cart import Cart, LineItem
            cart = Cart([LineItem('A', 13, 1) for _ in range(5)])
            assert cart.total_with_discount_cents(9) == 59
            assert cart.total_with_discount_cents(0) == cart.subtotal_cents()
        """,
    )
)

register(
    TaskSpec(
        task_id="notes_tag_rename_generalization",
        task_file="tasks/notes_tag_rename_generalization/task.md",
        seed_include=(
            "src/notes/__init__.py",
            "tests/test_notes.py",
            "tasks/notes_tag_rename_generalization/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/notes/store.py", "tasks/notes_tag_rename_generalization/seed/store_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from notes.store import Note, NoteStore
            n1 = Note('N1', 'Standup notes', ('work', 'daily'))
            n2 = Note('N2', 'Repair notes', ('workshop',))
            n3 = Note('N3', 'Extra notes', ('homework',))
            store = NoteStore([n1, n2, n3])
            changed = store.rename_tag('work', 'job')
            assert changed == 1
            by_id = {n.note_id: n for n in store.notes}
            assert by_id['N1'].tags == ('job', 'daily')
            assert by_id['N2'].tags == ('workshop',)
            assert by_id['N3'].tags == ('homework',)
            assert [n.note_id for n in store.find_by_tag('shop')] == ['N2']
        """,
    )
)

register(
    TaskSpec(
        task_id="shipping_quote_root_cause",
        task_file="tasks/shipping_quote_root_cause/task.md",
        seed_include=(
            "src/shipping/__init__.py",
            "src/shipping/quote.py",
            "tests/test_shipping.py",
            "tasks/shipping_quote_root_cause/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/shipping/rates.py", "tasks/shipping_quote_root_cause/seed/rates_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from shipping.quote import quote_cents
            assert quote_cents('standard', 2000) == 800
            assert quote_cents('standard', 1500) == 800
            assert quote_cents('standard', 1) == 400
            assert quote_cents('express', 2500) == 2700
            try:
                quote_cents('overnight', 1000)
                assert False, 'expected ValueError'
            except ValueError:
                pass
        """,
    )
)

register(
    TaskSpec(
        task_id="dependency_resolver_cycle_detection",
        task_file="tasks/dependency_resolver_cycle_detection/task.md",
        seed_include=(
            "src/deps/__init__.py",
            "tests/test_deps.py",
            "tasks/dependency_resolver_cycle_detection/task.md",
            "requirements.txt",
            "pyproject.toml",
        ),
        buggy_sources=(
            ("src/deps/resolver.py", "tasks/dependency_resolver_cycle_detection/seed/resolver_buggy.py"),
        ),
        regression_test_path="tests/test_task_regression.py",
        behavior_check="""
            from deps.resolver import resolve_order
            order = resolve_order({'app': ['lib'], 'lib': []})
            assert order.index('lib') < order.index('app')
            order2 = resolve_order({'app': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': []})
            assert order2.index('d') < order2.index('b') and order2.index('d') < order2.index('c')
            try:
                resolve_order({'a': ['b'], 'b': ['a']})
                assert False, 'expected ValueError for a direct cycle'
            except ValueError:
                pass
            try:
                resolve_order({'a': ['b'], 'b': ['c'], 'c': ['a']})
                assert False, 'expected ValueError for a longer cycle'
            except ValueError:
                pass
        """,
    )
)
