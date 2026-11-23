# bloomset

A small Bloom filter in Python 3.10+, with no dependencies. Use it to rule out values that are definitely absent before consulting a slower exact store.

A positive result means **maybe present**, not proof of membership. There is no delete operation. Inserting more than the planned capacity increases the false-positive rate. Do not use this as the only source of truth for security, billing or deduplication.

## Quick start

```sh
printf 'apple\nbanana\npear\n' > words.txt
python bloomset.py build words.txt words.json --capacity 1000 --error-rate 0.01
python bloomset.py check words.json apple orange
python -m unittest -v
```

The build command reads UTF-8 lines, preserving spaces and accepting empty strings. The check command prints one JSON object per query: `maybe` or `absent`.

## Python API

```python
from bloomset import BloomFilter

seen = BloomFilter(capacity=1000, error_rate=0.01)
seen.add('example')
assert 'example' in seen
seen.save('seen.json')
restored = BloomFilter.load('seen.json')
```

`left.merge(right)` creates a new union filter when sizing parameters match. The source filters are unchanged. `additions` counts calls, including duplicates; it is not an estimate of unique values.

## Design

The standard sizing equations choose the bit count and number of hashes. SHA-256 with a fixed integer prefix provides deterministic positions across processes, rather than Python's randomized `hash()`. Snapshots include a format version, base64 bit array, sizing parameters and addition count. Loading rejects wrong lengths, unsupported versions and nonzero padding bits. Snapshots are not authenticated and must come from a trusted source.

The occupancy-based error estimate is `fraction_of_set_bits ** hash_count`. It is a model, not a guarantee. SHA-256 is chosen for portability and simplicity, not maximum throughput. Hashing each position independently costs more than double hashing but avoids a degenerate step in a compact teaching implementation.

## Tests

14 deterministic tests cover sizing, empty filters, duplicate inserts, Unicode, no false negatives, merge behavior, snapshot round trips and corrupt data, invalid inputs and a fixed 10,000-query false-positive experiment. Run with `python -m unittest -v`.

## Limits

Strings only. No deletion, resizing, synchronization, compression or memory-mapped storage. Merge requires the same declared capacity and error rate. Snapshot loading is intended for small local files, not arbitrary untrusted input. This is an educational implementation, not a production replacement for a tuned approximate-membership library.
