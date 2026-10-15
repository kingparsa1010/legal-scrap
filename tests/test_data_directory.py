import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scanner import BASE_DIR, DATA_DIR, get_data_dir
import scanner.database as db
import scanner.store as store
import scanner.auth as auth
import scanner.logger as log
import scanner.exporter as exporter
import scanner.word_exporter as word_exp


class DataDirectoryStructureTests(unittest.TestCase):
    def test_paths_are_inside_data_dir(self):
        """All persistent data paths must be located under DATA_DIR."""
        self.assertTrue(db.DB_FILE.startswith(DATA_DIR), f"{db.DB_FILE} not in {DATA_DIR}")
        self.assertTrue(store.DB_PATH.startswith(DATA_DIR), f"{store.DB_PATH} not in {DATA_DIR}")
        self.assertTrue(store.DATA_STORE_PATH.startswith(DATA_DIR), f"{store.DATA_STORE_PATH} not in {DATA_DIR}")
        self.assertTrue(auth.ACCOUNTS_DIR.startswith(DATA_DIR), f"{auth.ACCOUNTS_DIR} not in {DATA_DIR}")
        self.assertTrue(auth.SESSION_FILE.startswith(DATA_DIR), f"{auth.SESSION_FILE} not in {DATA_DIR}")
        self.assertTrue(auth.WORD_OUTPUT_PATH.startswith(DATA_DIR), f"{auth.WORD_OUTPUT_PATH} not in {DATA_DIR}")
        self.assertTrue(log.LOGS_DIR.startswith(DATA_DIR), f"{log.LOGS_DIR} not in {DATA_DIR}")
        self.assertTrue(log.DEFAULT_LOG_FILE.startswith(DATA_DIR), f"{log.DEFAULT_LOG_FILE} not in {DATA_DIR}")
        self.assertTrue(exporter.DEFAULT_REPORTS_DIR.startswith(DATA_DIR), f"{exporter.DEFAULT_REPORTS_DIR} not in {DATA_DIR}")
        self.assertTrue(word_exp.CACHE_DIR.startswith(DATA_DIR), f"{word_exp.CACHE_DIR} not in {DATA_DIR}")


class DataDirectoryResetResilienceTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.fake_data_dir = os.path.join(self.test_dir, "data")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fresh_install_behavior_when_data_deleted(self):
        """
        When the 'data' directory is completely removed / does not exist:
        1. DB connection must automatically recreate directory and initialize schema with default watchlist.
        2. Stores must load clean empty state without crashing.
        3. Auth must report no active session.
        4. Logs must handle missing files gracefully.
        """
        # Ensure fake_data_dir does not exist (simulating deletion)
        self.assertFalse(os.path.exists(self.fake_data_dir))

        fake_db = os.path.join(self.fake_data_dir, "scans.db")
        fake_store_json = os.path.join(self.fake_data_dir, "data_store.json")
        fake_session = os.path.join(self.fake_data_dir, "session_auth.json")
        fake_logs = os.path.join(self.fake_data_dir, "logs")
        fake_log_file = os.path.join(fake_logs, "app.log")

        with patch.object(db, "DB_FILE", fake_db), \
             patch.object(store, "DB_PATH", fake_db), \
             patch.object(store, "DATA_STORE_PATH", fake_store_json), \
             patch.object(auth, "SESSION_FILE", fake_session), \
             patch.object(log, "LOGS_DIR", fake_logs), \
             patch.object(log, "DEFAULT_LOG_FILE", fake_log_file):

            with db.get_connection(fake_db) as conn:
                self.assertTrue(os.path.exists(fake_db))

            # Default watchlist item ('متاسنت') exists on fresh install
            watchlist = db.get_watchlist(fake_db)
            self.assertEqual(len(watchlist), 1)
            self.assertEqual(watchlist[0]["name_fa"], "متاسنت")

            # 2. Store queries load cleanly as empty dictionaries
            decls = store.load_store(fake_store_json)
            self.assertEqual(decls, {})
            class5 = store.load_class5_store()
            self.assertEqual(class5, {})

            # 3. Auth reports no active session
            self.assertFalse(auth.has_saved_session())
            self.assertEqual(auth.get_saved_cookies(), {})

            # 4. Logs handle missing folder gracefully
            self.assertIn("فایل لاگ هنوز ایجاد نشده است", log.read_latest_logs())
            self.assertTrue(log.clear_log_file())

            # 5. Simulate writing data, then deleting 'data' directory completely, and recovering
            store.save_store({"101": {"title": "تست ۱", "dec_no_id": "101"}}, fake_store_json)
            self.assertEqual(len(store.load_store(fake_store_json)), 1)
            auth.save_cookies({"auth_token": "abc123xyz"}, user_name="کاربر آزمایشی")
            self.assertTrue(auth.has_saved_session())

            # Now delete data directory completely!
            shutil.rmtree(self.fake_data_dir)
            self.assertFalse(os.path.exists(self.fake_data_dir))

            # After deletion: app behaves like a clean install again!
            new_watchlist = db.get_watchlist(fake_db)
            self.assertEqual(len(new_watchlist), 1)
            self.assertEqual(new_watchlist[0]["name_fa"], "متاسنت")

            new_decls = store.load_store(fake_store_json)
            self.assertEqual(new_decls, {})
            self.assertFalse(auth.has_saved_session())


if __name__ == "__main__":
    unittest.main()
