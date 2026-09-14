# LLD Practice

Reference solutions for classic LLD / machine-coding interview problems, in Python.
Every file follows the same shape: models → service → driver with assertion-based
tests (happy path, invalid input, boundary cases).

## Problems

| File | Problem | Core idea |
| --- | --- | --- |
| `lru_ordereddict.py` | LRU cache with pluggable eviction | Strategy pattern, cache composes an `EvictionPolicy` |
| `kv_store.py` | KV store with nested transactions | Stack of write layers, tombstones, read-your-writes |
| `booking.py` | Seat booking with concurrency | Per-seat locks, atomic check-and-set, race test |
| `logger.py` | Logger with pluggable sinks | Chain of Responsibility vs Observer |
| `product_search.py` | Product search + sponsored ranking | Filter chain, sort strategy, ranking policy |
| `filesystem.py` | In-memory filesystem | Composite (N-ary tree), path resolution |
| `splitwise.py` | Expense splitting | Strategy for split types, ledger invariants |
| `vending_machine.py` | Vending machine | State machine, transitions per lifecycle |

## Run

```bash
python3 <file>.py   # → "all checks passed"
```
