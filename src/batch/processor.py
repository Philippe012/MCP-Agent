from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BatchResult:
    succeeded: list
    failed: list  # list of (item, error_message) tuples


def process_batch(items: list, worker: Callable) -> BatchResult:
    """Run worker(item) for every item in order. One item's failure must
    not abort the batch or discard results already computed for other
    items - every item gets a chance to run, and every outcome (success or
    failure) is reported."""
    succeeded = []
    failed = []
    for item in items:
        try:
            succeeded.append(worker(item))
        except Exception as exc:
            failed.append((item, str(exc)))
    return BatchResult(succeeded=succeeded, failed=failed)
