"""
پردازشگر پس‌زمینه اسکن و استخراج داده‌ها بدون مسدودسازی رابط کاربری
Background QThread Worker for Mode-2 Targeted Search (Class-5 Scraping)
"""
from typing import Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal

from scanner.client import SSAAClient, SSAAConnectionError, SSAAServerError
from scanner.database import create_scan_session
from services.scan_persistence_service import publish_targeted_scan
from services.targeted_scan_service import collect_targeted_scan, ScanValidationError
from scanner.logger import get_logger

logger = get_logger("worker")


class ScanWorker(QThread):
    """
    نخ پردازشی اجرای اسکن جستجوی هدفمند (حالت ۲) و ذخیره رکوردهای کلاس ۵
    """
    progress_changed = pyqtSignal(int, str)      # درصد پیشرفت, پیام وضعیت
    record_found = pyqtSignal(dict)              # ارسال رکورد جدید به جدول GUI
    scan_completed = pyqtSignal(int, str, int, int)  # scan_id, excel_path, total, alerts
    scan_cancelled = pyqtSignal()
    scan_failed = pyqtSignal(str)                # پیام خطا

    def __init__(
        self,
        client: SSAAClient,
        search_params: Dict[str, Any],
        captcha_value: str,
        scan_date: str,
        max_pages: int = 20,
        parent=None
    ):
        super().__init__(parent)
        self.client = client
        self.search_params = search_params
        self.captcha_value = captcha_value
        self.scan_date = scan_date
        self.max_pages = max_pages
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            self.progress_changed.emit(5, "در حال ایجاد نوبت اسکن در پایگاه داده...")
            scan_id = create_scan_session(self.scan_date, self.search_params)
            records = collect_targeted_scan(
                client=self.client,
                params=self.search_params,
                captcha=self.captcha_value,
                max_pages=self.max_pages,
                is_cancelled=lambda: self.is_cancelled,
                on_progress=self.progress_changed.emit,
                on_record=self.record_found.emit,
            )
            if self.is_cancelled:
                self.progress_changed.emit(0, "اسکن توسط کاربر متوقف شد؛ داده ناقص ذخیره نشد.")
                self.scan_cancelled.emit()
                return

            self.progress_changed.emit(92, "در حال ثبت نتیجه کامل در پایگاه داده...")
            added, _ = publish_targeted_scan(scan_id, records)
            total = len(records)
            self.progress_changed.emit(100, f"اسکن کامل شد ({total} رکورد، {added} مورد جدید).")
            self.scan_completed.emit(scan_id, "", total, 0)
        except ScanValidationError as exc:
            self.scan_failed.emit(str(exc))
        except (SSAAConnectionError, SSAAServerError) as exc:
            if self.is_cancelled:
                self.scan_cancelled.emit()
            else:
                self.scan_failed.emit(str(exc))
        except Exception as exc:
            if self.is_cancelled:
                self.scan_cancelled.emit()
            else:
                logger.exception("Targeted scan failed")
                self.scan_failed.emit(f"خطای سیستمی در اجرای اسکن: {exc}")
