"""
پردازشگر پس‌زمینه استخراج اظهارنامه‌ها (DeclarationList) با پشتیبانی از بررسی اقلام جدید و اسکن کامل
Background QThread Worker for Public DeclarationList Scraping with Dual Scan Modes and Similarity Matching
"""
import os
from PyQt6.QtCore import QThread, pyqtSignal
import urllib3

from scanner.logger import get_logger
from scanner.auth import (
    get_authenticated_session, has_saved_session, get_saved_user_name,
    START_URL,
)
from scanner.store import DATA_STORE_PATH, load_store
from services.declaration_scan_service import collect_declarations, enrich_with_details, IncompleteFullScan
from services.declaration_completion_service import complete_declaration_scan
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("decl_worker")


from scanner import BASE_DIR, DATA_DIR
WORD_OUTPUT_PATH = os.path.join(DATA_DIR, "brands.docx")


class DeclarationScrapeWorker(QThread):
    """
    نخ پردازشی اجرای استخراج لیست اظهارنامه‌ها با نشست مستقیم HTTP (بدون Playwright و بدون نیاز به کروم)
    """
    progress_changed = pyqtSignal(int, str)
    record_found = pyqtSignal(dict)
    scan_completed = pyqtSignal(int, int, int, str)  # total_scraped, new_count, alerts_count, docx_path
    scan_cancelled = pyqtSignal()
    scan_failed = pyqtSignal(str)

    def __init__(
        self,
        mode: str = "new_only",  # "new_only" یا "full_rescan"
        max_pages: int = 500,
        docx_path: str = WORD_OUTPUT_PATH,
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.max_pages = max_pages
        self.docx_path = docx_path
        self._is_running = True
        self._session = None

    def stop(self):
        self._is_running = False
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass

    def run(self):
        # آخرین سد دفاعی: هیچ اکسپشنی نباید از run() نخ Qt بیرون بزند،
        # چون در حالت windowed کل برنامه بی‌صدا بسته می‌شود.
        try:
            self._run_inner()
        except Exception as exc:
            logger.exception("Unhandled error in DeclarationScrapeWorker")
            try:
                if self._is_running:
                    self.scan_failed.emit(f"خطای سیستمی در اجرای اسکن: {exc}")
                else:
                    self.scan_cancelled.emit()
            except Exception:
                pass

    def _run_inner(self):
        self.progress_changed.emit(5, "بررسی نشست ذخیره‌شده...")
        logger.info(f"شروع اجرای اسکن اظهارنامه‌ها با حالت: {self.mode} (موتور سبک HTTP)")

        if not has_saved_session():
            logger.warning("هیچ نشستی در سامانه یافت نشد.")
            self.scan_failed.emit(
                "نشستی در برنامه ذخیره نشده است.\n"
                "لطفاً از دکمه «ورود به سامانه» برای ورود به حساب خود استفاده فرمایید."
            )
            return

        user_name = get_saved_user_name() or "کاربر سامانه"
        self.progress_changed.emit(8, f"راه‌اندازی ارتباط امن برای {user_name}...")
        logger.info(f"اتصال مستقیم HTTP با کوکی‌های کاربر: {user_name}")

        self._session = get_authenticated_session()
        session = self._session

        self.progress_changed.emit(12, "در حال اتصال به لیست اظهارنامه‌ها...")
        logger.info(f"در حال ارسال درخواست به: {START_URL}")

        try:
            resp = session.get(START_URL, timeout=40, verify=False)
            status_code = resp.status_code
            logger.info(f"پاسخ دریافت شد: کد={status_code}, آدرس نهایی={resp.url}")
            html_page_1 = resp.text
        except Exception as e:
            if not self._is_running:
                self.progress_changed.emit(0, "اسکن توسط کاربر متوقف شد.")
                self.scan_cancelled.emit()
                return
            err_text = str(e)
            logger.error(f"خطای شبکه در session.get: {e}")
            if any(w in err_text for w in ["ERR_CONNECTION_CLOSED", "ERR_TIMED_OUT", "ERR_NAME_NOT_RESOLVED", "SSL", "EOF", "Connection", "Timeout"]):
                self.scan_failed.emit(
                    "⚠️ خطا در برقراری ارتباط با سامانه ثبت (ipm.ssaa.ir).\n\n"
                    "علت: سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور و فیلترشکن (VPN) را مسدود می‌کنند (Geo-blocking).\n\n"
                    "لطفاً فیلترشکن (VPN) خود را خاموش فرمایید و دوباره روی دکمه اسکن کلیک کنید."
                )
            else:
                self.scan_failed.emit(f"خطا در اتصال به سامانه ثبت اسناد: {e}")
            return

        # بررسی وجود المان‌های جدول و کاربر در HTML
        soup = BeautifulSoup(html_page_1, "html.parser")
        user_data = soup.find(id="userData")
        data_list = soup.find(id="DataList")

        if not user_data and not data_list:
            logger.warning(f"نشست کاربری تأیید نشد. کد={status_code}, آدرس={resp.url}")
            if status_code == 500:
                self.scan_failed.emit(
                    "⚠️ سرور ثبت اسناد خطای داخلی ۵۰۰ (Internal Server Error) بازگرداند.\n\n"
                    "کوکی‌های نشست منقضی یا از سمت سرور باطل شده‌اند.\n"
                    "لطفاً با کلیک بر روی دکمه «تغییر حساب / ورود به سامانه» مجدداً وارد شوید تا نشست تازه ذخیره گردد."
                )
            elif "SignIn" in resp.url or "Login" in resp.url or "Account" in resp.url:
                self.scan_failed.emit(
                    "نشست کاربری شما منقضی شده و سامانه به صفحه ورود هدایت کرد.\n"
                    "لطفاً با زدن دکمه «تغییر حساب / ورود به سامانه» یک‌بار دیگر وارد شوید تا نشست تازه ذخیره گردد."
                )
            else:
                self.scan_failed.emit(
                    f"نشست کاربری شما معتبر تشخیص داده نشد (کد وضعیت: {status_code}).\n"
                    "لطفاً با زدن دکمه «تغییر حساب / ورود به سامانه» یک‌بار دیگر وارد شوید."
                )
            return

        existing_store = load_store(DATA_STORE_PATH) if self.mode == "new_only" else {}
        try:
            store, newly_scraped, new_count, total_records = collect_declarations(
                session=session,
                first_html=html_page_1,
                mode=self.mode,
                max_pages=self.max_pages,
                existing_store=existing_store,
                is_running=lambda: self._is_running,
                on_progress=self.progress_changed.emit,
                on_record=self.record_found.emit,
            )
        except IncompleteFullScan as exc:
            self.scan_failed.emit(f"{exc} داده‌های قبلی بدون تغییر حفظ شدند.")
            return

        if not self._is_running:
            self.progress_changed.emit(0, "اسکن متوقف شد؛ داده ناقص ذخیره نشد.")
            self.scan_cancelled.emit()
            return

        # تکمیل فیلدهای جدید (شماره ثبت، تاریخ تمدید، لینک گواهی) از صفحه جزئیات
        if newly_scraped:
            try:
                self.progress_changed.emit(91, "در حال تکمیل شماره ثبت و تاریخ تمدید از صفحه جزئیات...")
                enrich_with_details(
                    session,
                    newly_scraped,
                    is_running=lambda: self._is_running,
                    on_progress=self.progress_changed.emit,
                    limit=300,
                )
            except Exception:
                pass

        try:
            complete_declaration_scan(
                mode=self.mode,
                total_records=total_records,
                store=store,
                new_records=newly_scraped,
                user_name=user_name,
                docx_path=self.docx_path,
                on_progress=self.progress_changed.emit,
            )
        except Exception as exc:
            logger.exception("خطا در ثبت یا خروجی اسکن کامل")
            self.scan_failed.emit(f"اسکن جمع‌آوری شد اما ثبت نهایی ناموفق بود: {exc}")
            return

        message = (f"تکمیل شد! {new_count} مورد جدید افزوده شد." if self.mode == "new_only"
                   else f"اسکن کامل تکمیل شد! {len(store)} رکورد به‌روزرسانی شد.")
        self.progress_changed.emit(100, message)
        self.scan_completed.emit(len(store), new_count, 0, self.docx_path)

