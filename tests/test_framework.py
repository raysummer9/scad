from __future__ import annotations

import csv
import json
import tempfile
import time
import unittest
from pathlib import Path

from gov_procurement_framework.core.proxy_manager import ProxyManager
from gov_procurement_framework.core.rate_limiter import RateLimiter
from gov_procurement_framework.core.retry_engine import RetryEngine
from gov_procurement_framework.exporters.csv_exporter import CsvExporter
from gov_procurement_framework.exporters.json_exporter import JsonExporter
from gov_procurement_framework.models.tender_schema import (
    REQUIRED_TENDER_KEYS,
    ensure_tender_schema,
)


class ProxyManagerTests(unittest.TestCase):
    def test_disables_proxy_after_failure_threshold(self) -> None:
        manager = ProxyManager(proxies=["http://p1:8000", "http://p2:8000"])
        proxy = manager.get_proxy()
        self.assertIsNotNone(proxy)
        for _ in range(3):
            manager.report_failure(proxy)

        # After failures, the same proxy should not be selected immediately.
        next_proxy = manager.get_proxy()
        self.assertIsNotNone(next_proxy)
        self.assertNotEqual(proxy["id"], next_proxy["id"])

    def test_fallback_to_direct_when_all_disabled(self) -> None:
        manager = ProxyManager(proxies=["http://p1:8000"])
        proxy = manager.get_proxy()
        self.assertIsNotNone(proxy)
        for _ in range(3):
            manager.report_failure(proxy)
        self.assertIsNone(manager.get_proxy())


class RetryEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_exhaustion_raises(self) -> None:
        retry = RetryEngine(max_retries=2, base_backoff_delay=0.001)
        attempts: list[int] = []

        async def operation(attempt: int) -> str:
            attempts.append(attempt)
            raise TimeoutError("transient")

        with self.assertRaises(TimeoutError):
            await retry.run(operation=operation)

        # attempt values: 0, 1, 2
        self.assertEqual(attempts, [0, 1, 2])


class RateLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limit_exhaustion_introduces_wait(self) -> None:
        limiter = RateLimiter(global_rate=1.0, domain_rates={"default": 1.0, "example.com": 1.0})

        start = time.monotonic()
        await limiter.acquire("example.com")  # immediate (initial token)
        await limiter.acquire("example.com")  # should wait for refill
        elapsed = time.monotonic() - start

        self.assertGreaterEqual(elapsed, 0.9)


class ExportAndSchemaTests(unittest.TestCase):
    def test_exporters_write_valid_artifacts(self) -> None:
        sample = [
            ensure_tender_schema(
                {
                    "source": "test_source",
                    "scraped_at": "2026-03-01T00:00:00+00:00",
                    "country": "Testland",
                    "state": "Test State",
                    "ministry": "Test Ministry",
                    "tender": {
                        "tender_id": "t-1",
                        "title": "Test Tender",
                        "budget": "1000",
                        "currency": "USD",
                        "published_date": "2026-02-01",
                        "closing_date": "2026-02-28",
                        "category": "goods",
                        "description": "Sample",
                        "documents": [{"name": "doc", "url": "https://example.com/doc.pdf"}],
                    },
                    "winning_company": {
                        "name": "ACME Ltd",
                        "company_details": {
                            "registration_number": "REG-1",
                            "address": "123 Main St",
                            "email": "acme@example.com",
                            "phone": "+1-555-0100",
                            "website": "https://acme.example.com",
                            "country": "Testland",
                            "state": "Test State",
                        },
                    },
                }
            )
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            JsonExporter(output_dir=str(output)).export(sample, "sample.json")
            CsvExporter(output_dir=str(output)).export(sample, "sample.csv")

            json_path = output / "sample.json"
            csv_path = output / "sample.csv"
            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())

            loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded_json), 1)
            self.assertEqual(set(loaded_json[0].keys()), REQUIRED_TENDER_KEYS)

            with open(csv_path, "r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertIn("tender_documents", rows[0])
            self.assertIn("https://example.com/doc.pdf", rows[0]["tender_documents"])
            self.assertEqual(rows[0]["winning_company_name"], "ACME Ltd")
            self.assertEqual(rows[0]["company_registration_number"], "REG-1")

    def test_schema_normalization_fills_defaults(self) -> None:
        record = ensure_tender_schema({"source": "x", "title": "y"})
        self.assertEqual(set(record.keys()), REQUIRED_TENDER_KEYS)
        self.assertEqual(record["tender"]["documents"], [])


if __name__ == "__main__":
    unittest.main()
