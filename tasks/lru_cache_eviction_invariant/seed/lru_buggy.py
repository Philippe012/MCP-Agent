class LRUCache:
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data: dict = {}
        self._order: list = []  # least-recently-used first

    def _touch(self, key) -> None:
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def get(self, key):
        if key not in self._data:
            return None
        # BUG: reading a key doesn't refresh its recency, so a key that was
        # just read can still be evicted next, as if it had never been
        # touched.
        return self._data[key]

    def put(self, key, value) -> None:
        if key not in self._data and len(self._data) >= self.capacity:
            lru_key = self._order.pop(0)
            del self._data[lru_key]
        self._data[key] = value
        self._touch(key)

    def keys_by_recency(self) -> list:
        return list(self._order)
