import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from download_binance_wide import month_of, parse_listing  # noqa: E402

NS = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'


class ListingTests(unittest.TestCase):
    def test_prefix_listing_with_marker(self):
        xml = (
            f'<ListBucketResult {NS}><IsTruncated>true</IsTruncated>'
            "<NextMarker>data/x/B/</NextMarker>"
            "<CommonPrefixes><Prefix>data/x/A/</Prefix></CommonPrefixes>"
            "<CommonPrefixes><Prefix>data/x/B/</Prefix></CommonPrefixes></ListBucketResult>"
        ).encode()
        p, k, trunc, nxt = parse_listing(xml)
        self.assertEqual(p, ["data/x/A/", "data/x/B/"])
        self.assertEqual(k, [])
        self.assertTrue(trunc)
        self.assertEqual(nxt, "data/x/B/")

    def test_key_listing_and_months(self):
        xml = (
            f'<ListBucketResult {NS}><IsTruncated>false</IsTruncated>'
            "<Contents><Key>a/BTCUSDT-1d-2024-03.zip</Key></Contents>"
            "<Contents><Key>a/BTCUSDT-1d-2024-03.zip.CHECKSUM</Key></Contents></ListBucketResult>"
        ).encode()
        _, keys, trunc, nxt = parse_listing(xml)
        self.assertFalse(trunc)
        self.assertEqual(month_of(keys[0]), "2024-03")
        self.assertIsNone(month_of(keys[1]))  # checksum files are ignored
        self.assertIsNone(nxt)


if __name__ == "__main__":
    unittest.main()
