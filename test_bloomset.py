import json
import tempfile
import unittest
from pathlib import Path
from bloomset import BloomFilter


class BloomTests(unittest.TestCase):
    def test_no_false_negatives(self):
        f = BloomFilter(1000)
        for i in range(1000):
            f.add(str(i))
        self.assertTrue(all(str(i) in f for i in range(1000)))

    def test_empty_filter(self):
        self.assertNotIn('anything', BloomFilter(10))

    def test_unicode_and_empty(self):
        f = BloomFilter(20)
        for x in ['', 'café', '東京', '🐍', 'a\nb']:
            f.add(x)
            self.assertIn(x, f)

    def test_deterministic(self):
        a, b = BloomFilter(100), BloomFilter(100)
        for x in ['alpha', 'beta', 'gamma']:
            a.add(x)
            b.add(x)
        self.assertEqual(a.bits, b.bits)

    def test_duplicates(self):
        f = BloomFilter(10)
        f.add('x')
        before = bytes(f.bits)
        f.add('x')
        self.assertEqual(before, bytes(f.bits))
        self.assertEqual(f.additions, 2)

    def test_merge(self):
        a, b = BloomFilter(100), BloomFilter(100)
        a.add('alpha')
        b.add('beta')
        c = a.merge(b)
        self.assertIn('alpha', c)
        self.assertIn('beta', c)
        self.assertEqual(c.additions, 2)
        self.assertEqual(a.additions, 1)

    def test_incompatible_merge(self):
        with self.assertRaises(ValueError):
            BloomFilter(10).merge(BloomFilter(20))

    def test_round_trip(self):
        f = BloomFilter(50)
        f.add('portable')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'filter.json'
            f.save(path)
            restored = BloomFilter.load(path)
            self.assertEqual(restored.bits, f.bits)
            self.assertIn('portable', restored)

    def test_corrupt_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'filter.json'
            BloomFilter(50).save(path)
            data = json.loads(path.read_text())
            data['bits'] = 'AA=='
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                BloomFilter.load(path)

    def test_bad_capacity(self):
        for value in [0, -1, True, 1.5]:
            with self.assertRaises(ValueError):
                BloomFilter(value)

    def test_bad_rate(self):
        for value in [0, 1, -0.5, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                BloomFilter(10, value)

    def test_non_string(self):
        with self.assertRaises(TypeError):
            BloomFilter(10).add(9)

    def test_sizing(self):
        f = BloomFilter(1000, .01)
        self.assertEqual(f.bit_count, 9586)
        self.assertEqual(f.hash_count, 7)

    def test_empirical_rate(self):
        f = BloomFilter(1000, .01)
        for i in range(1000):
            f.add('member-' + str(i))
        positives = sum('outsider-' + str(i) in f for i in range(10000))
        self.assertLess(positives / 10000, .025)
        self.assertGreater(f.estimated_error_rate, 0)
        self.assertLess(f.estimated_error_rate, .025)


if __name__ == '__main__':
    unittest.main()
