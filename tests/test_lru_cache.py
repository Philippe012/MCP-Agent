import pytest

from cache.lru import LRUCache


def test_capacity_is_never_exceeded():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache.keys_by_recency()) == 2


def test_write_order_eviction_evicts_the_oldest_write():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # "a" was never touched again, must be evicted
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        LRUCache(0)
