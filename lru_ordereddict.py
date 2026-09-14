import threading
from abc import ABC, abstractmethod
from collections import OrderedDict


# ---------------- Policy interface ----------------
class EvictionPolicy(ABC):
    @abstractmethod
    def key_accessed(self, key): ...

    # called when an existing key is read/updated

    @abstractmethod
    def key_added(self, key): ...

    # called when a brand-new key enters the cache

    @abstractmethod
    def evict(self): ...

    # return the key that should be removed


# ---------------- LRU policy ----------------
class LRUPolicy(EvictionPolicy):
    """front = LRU (oldest), back = MRU (newest)"""

    def __init__(self):
        self.order = OrderedDict()

    def key_accessed(self, key):
        self.order.move_to_end(key)  # touched → most recent

    def key_added(self, key):
        self.order[key] = None  # new → most recent (back)

    def evict(self):
        key, _ = self.order.popitem(last=False)  # remove front (LRU)
        return key


# ---------------- Cache ----------------
class Cache:
    def __init__(self, capacity: int, policy: EvictionPolicy):
        if capacity < 0:
            raise ValueError("capacity must be >= 0")
        self.cap = capacity
        self.store = {}  # key -> value (pure storage)
        self.policy = policy  # swappable eviction strategy
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key not in self.store:
                return -1
            self.policy.key_accessed(key)  # key guaranteed present in policy
            return self.store[key]

    def put(self, key, value):
        with self._lock:
            if self.cap == 0:
                return  # nothing can be stored

            if key in self.store:  # update existing
                self.store[key] = value
                self.policy.key_accessed(key)  # key present in policy too
                return

            if len(self.store) >= self.cap:  # full → evict
                victim = self.policy.evict()
                del self.store[victim]

            self.store[key] = value  # insert new
            self.policy.key_added(key)  # tell policy about it

    # helpful for demos / debugging
    def __len__(self):
        return len(self.store)


# ---------------- Demo ----------------
if __name__ == "__main__":
    lru = Cache(2, LRUPolicy())

    lru.put(1, 10)
    lru.put(2, 20)
    print(lru.get(1))  # 10  → 1 becomes MRU
    lru.put(3, 30)  # evicts 2 (LRU), since 1 was just used
    print(lru.get(2))  # -1  (evicted)
    print(lru.get(3))  # 30
    print(lru.get(1))  # 10

    # swap policy → same Cache, different eviction
    # from your_other_policy import LFUPolicy
    # lfu = Cache(2, LFUPolicy())
