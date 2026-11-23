"""Deterministic Bloom filter with portable JSON snapshots. Standard library only."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path


class BloomFilter:
    def __init__(self, capacity, error_rate=0.01):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError('capacity must be a positive integer')
        if not math.isfinite(error_rate) or not 0 < error_rate < 1:
            raise ValueError('error_rate must be between 0 and 1')
        self.capacity = capacity
        self.error_rate = error_rate
        self.bit_count = max(8, math.ceil(-capacity * math.log(error_rate) / math.log(2) ** 2))
        self.hash_count = max(1, round(self.bit_count / capacity * math.log(2)))
        self.bits = bytearray((self.bit_count + 7) // 8)
        self.additions = 0

    def _positions(self, value):
        if not isinstance(value, str):
            raise TypeError('values must be strings')
        data = value.encode('utf-8')
        for index in range(self.hash_count):
            digest = hashlib.sha256(index.to_bytes(8, 'big') + data).digest()
            yield int.from_bytes(digest, 'big') % self.bit_count

    def add(self, value):
        for position in self._positions(value):
            self.bits[position // 8] |= 1 << (position % 8)
        self.additions += 1

    def __contains__(self, value):
        return all(self.bits[p // 8] & (1 << (p % 8)) for p in self._positions(value))

    @property
    def occupancy(self):
        return sum(b.bit_count() for b in self.bits) / self.bit_count

    @property
    def estimated_error_rate(self):
        return self.occupancy ** self.hash_count

    def merge(self, other):
        if (self.capacity, self.error_rate) != (other.capacity, other.error_rate):
            raise ValueError('filters must have identical parameters')
        result = BloomFilter(self.capacity, self.error_rate)
        result.bits = bytearray(a | b for a, b in zip(self.bits, other.bits))
        result.additions = self.additions + other.additions
        return result

    def save(self, path):
        data = dict(version=1, capacity=self.capacity, error_rate=self.error_rate,
                    additions=self.additions, bits=base64.b64encode(self.bits).decode('ascii'))
        Path(path).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('version') != 1:
            raise ValueError('unsupported snapshot version')
        result = cls(data['capacity'], data['error_rate'])
        bits = base64.b64decode(data['bits'], validate=True)
        if len(bits) != len(result.bits):
            raise ValueError('incorrect bit array length')
        if result.bit_count % 8 and bits[-1] >> (result.bit_count % 8):
            raise ValueError('nonzero padding bits')
        additions = data['additions']
        if isinstance(additions, bool) or not isinstance(additions, int) or additions < 0:
            raise ValueError('invalid additions count')
        result.bits = bytearray(bits)
        result.additions = additions
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('input', help='UTF-8 file, one string per line')
    build.add_argument('output')
    build.add_argument('--capacity', type=int, required=True)
    build.add_argument('--error-rate', type=float, default=0.01)
    check = sub.add_parser('check')
    check.add_argument('snapshot')
    check.add_argument('values', nargs='+')
    args = parser.parse_args()
    if args.command == 'build':
        bloom = BloomFilter(args.capacity, args.error_rate)
        for line in Path(args.input).read_text(encoding='utf-8').splitlines():
            bloom.add(line)
        bloom.save(args.output)
        print(json.dumps(dict(bits=bloom.bit_count, hashes=bloom.hash_count,
                              additions=bloom.additions, occupancy=bloom.occupancy,
                              estimated_error_rate=bloom.estimated_error_rate)))
    else:
        bloom = BloomFilter.load(args.snapshot)
        for value in args.values:
            print(json.dumps(dict(value=value, result='maybe' if value in bloom else 'absent')))


if __name__ == '__main__':
    main()
