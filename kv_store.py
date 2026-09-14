# In-memory KV store with nested transactions.
# C++ picture:
#   unordered_map<string, string> base_store
#   vector<unordered_map<string, ValueOrTombstone>> txn_stack
# Top of the vector = innermost transaction (the one currently being written to).

# Unique sentinel object. Identity compare with `is`, never `==`.
# C++ analogue: a dedicated enum tag, not a real value — so we can store
# "this key was deleted in this layer" without colliding with any user string.
TOMBSTONE = object()


class KVStore:
    def __init__(self):
        self.base_store = {}
        self.txn_stack = []

    def set(self, key, value):
        if self.txn_stack:
            # Writes go to the innermost scratch layer, not the permanent store.
            self.txn_stack[-1][key] = value
        else:
            self.base_store[key] = value

    def get(self, key):
        # Walk innermost -> outermost, then base. First hit wins.
        # A TOMBSTONE hit means "deleted in this layer" — stop, don't look further.
        for i in range(len(self.txn_stack) - 1, -1, -1):
            layer = self.txn_stack[i]
            if key in layer:
                val = layer[key]
                if val is TOMBSTONE:
                    return None
                return val
        if key in self.base_store:
            return self.base_store[key]
        return None

    def delete(self, key):
        if self.txn_stack:
            # Tombstone, not a real remove: the outer layer may still have the key.
            self.txn_stack[-1][key] = TOMBSTONE
        else:
            if key in self.base_store:
                del self.base_store[key]

    def begin(self):
        self.txn_stack.append({})

    def rollback(self):
        if not self.txn_stack:
            raise Exception("no transaction to rollback")
        self.txn_stack.pop()

    def commit(self):
        if not self.txn_stack:
            raise Exception("no transaction to commit")

        # Pop the innermost transaction
        innermost = self.txn_stack.pop()

        if self.txn_stack:
            # Case 1: Nested transaction exists.
            # Merge into the parent transaction layer.
            # Tombstones and updates both overwrite the parent layer.
            for key, val in innermost.items():
                self.txn_stack[-1][key] = val
        else:
            # Case 2: Outermost transaction committed.
            # Apply changes permanently to base_store.
            for key, val in innermost.items():
                if val is TOMBSTONE:
                    if key in self.base_store:
                        del self.base_store[key]
                else:
                    self.base_store[key] = val

    def dump(self):
        print("base_store:", self.base_store)
        print("txn_stack :", self.txn_stack)


if __name__ == "__main__":
    kv = KVStore()

    kv.set("a", "1")
    kv.begin()          # txn 0 (outer)
    kv.set("a", "2")
    kv.begin()          # txn 1 (middle)
    kv.set("b", "x")
    kv.begin()          # txn 2 (inner)
    kv.set("c", "y")
    kv.delete("a")

    print("--- before any commit ---")
    kv.dump()
    print("get(a) =", kv.get("a"), "  (expect None — inner deleted it)")
    print("get(b) =", kv.get("b"), "  (expect x)")
    print("get(c) =", kv.get("c"), "  (expect y)")

    print("\n--- commit innermost ---")
    kv.commit()
    kv.dump()
    print("get(a) =", kv.get("a"), "  (expect None — still shadowed by tombstone in middle)")
    print("get(c) =", kv.get("c"), "  (expect y — now living in the middle layer)")
    print("base_store must still be {'a': '1'} — inner commit is NOT permanent")

    print("\n--- commit middle ---")
    kv.commit()
    kv.dump()
    print("base_store must STILL be {'a': '1'} — outer txn not committed yet")

    print("\n--- commit outer ---")
    kv.commit()
    kv.dump()
    print("get(a) =", kv.get("a"), "  (expect None — tombstone finally applied to base)")
    print("get(b) =", kv.get("b"), "  (expect x)")
    print("get(c) =", kv.get("c"), "  (expect y)")
    print("base_store after outer commit should have b=x, c=y, and a gone")
