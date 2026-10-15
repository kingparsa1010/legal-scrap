import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scanner.store as store


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "scans.db")
        self.legacy = str(Path(self.tmp.name) / "data_store.json")
        self.patches = [patch.object(store, "DB_PATH", self.db), patch.object(store, "DATA_STORE_PATH", self.legacy)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_replace_round_trip(self):
        store.save_store({"1": {"dec_no_id": "1", "title": "الف"}}, self.legacy)
        self.assertEqual(store.load_store(self.legacy)["1"]["title"], "الف")

    def test_failed_replacement_preserves_previous_snapshot(self):
        store.save_store({"1": {"dec_no_id": "1", "title": "old"}}, self.legacy)
        with self.assertRaises(TypeError):
            store.save_store({"2": {"dec_no_id": "2", "bad": {1}}}, self.legacy)
        self.assertIn("1", store.load_store(self.legacy))
        self.assertNotIn("2", store.load_store(self.legacy))


if __name__ == "__main__":
    unittest.main()
