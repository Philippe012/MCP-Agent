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
        try:
            succeeded.append(worker(item))
        except Exception as exc:
            failed.append((item, str(exc)))
    return BatchResult(succeeded=succeeded, failed=failed)
