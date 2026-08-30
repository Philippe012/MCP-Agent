from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BatchResult:
    succeeded: list
    failed: list 


def process_batch(items: list, worker: Callable) -> BatchResult:
    succeeded = []
    failed = []
    for item in items:
        # BUG: no error handling - the first failing item's exception
        # propagates straight out of this function, aborting the whole
        # batch and discarding every result already computed.
        succeeded.append(worker(item))
    return BatchResult(succeeded=succeeded, failed=failed)
