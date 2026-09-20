"""
پردازشگر پس‌زمینه استخراج اظهارنامه‌ها (DeclarationList) با پشتیبانی از بررسی اقلام جدید و اسکن کامل
Background QThread Worker for Public DeclarationList Scraping with Dual Scan Modes and Similarity Matching
"""
import os
import re
import json
import time
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal
import requests
import urllib3

from scanner.logger import get_logger
from scanner.auth import (
    get_authenticated_session, check_session_alive,
    has_saved_session, get_saved_cookies, get_saved_user_name,
    STORAGE_STATE_FILE, USER_AGENT
)
from scanner.similarity import TrademarkSimilarityEngine
from scanner.database import (
    get_watchlist, create_scan_session, save_declarations_batch,
    update_scan_stats, DB_FILE
)
from scanner.word_exporter import export_declarations_to_word
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("decl_worker")


BASE_LIST_URL = (
    "https://ipm.ssaa.ir/CA/DeclarationList"
    "?DeclarationType=&decNo=&FromDate=&ToDate=&DeclarationState="
    "&dTitle=&DeclarationSort=1&TotalRecord={total_record}&p={page}"
)
START_URL = "https://ipm.ssaa.ir/CA/DeclarationList"
DATA_STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_store.json")
WORD_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brands.docx")


def parse_declaration_page(html: str) -> List[Dict[str, Any]]:
    """تجزیه HTML جدول اظهارنامه‌ها و استخراج ستون‌ها."""
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody", id="DataList")
    if not tbody:
        return []

    rows = []
    for tr in tbody.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 8:
            continue

        row_num = tds[0].get_text(strip=True)

        img_a = tds[1].find("a")
        image_url = img_a["href"].strip() if img_a and img_a.has_attr("href") else ""

        dec_a = tds[2].find("a")
        dec_no_display = dec_a.get_text(strip=True) if dec_a else tds[2].get_text(strip=True)
        detail_url = dec_a["href"].strip() if dec_a and dec_a.has_attr("href") else ""
        m = re.search(r"DecNo=(\d+)", detail_url)
        dec_no_id = m.group(1) if m else dec_no_display

        title = tds[3].get_text(strip=True)
        office = tds[4].get_text(strip=True)

        owner_b = tds[5].find("b")
        percent = ""
        owner_name = ""
        if owner_b:
            percent_i = owner_b.find("i")
            percent = percent_i.get_text(strip=True) if percent_i else ""
            owner_name = owner_b.get_text(separator=" ", strip=True)
            if percent:
                owner_name = owner_name.replace(percent, "").strip()
        else:
            owner_name = tds[5].get_text(strip=True)

        date_text = tds[6].get_text(separator="|", strip=True)
        date_parts = [p for p in date_text.split("|") if p]
        reg_date = date_parts[0] if len(date_parts) > 0 else ""
        reg_time = date_parts[1] if len(date_parts) > 1 else ""

        status_span = tds[7].find("span")
        status = status_span.get_text(strip=True) if status_span else tds[7].get_text(strip=True)

        rows.append({
            "dec_no_id": dec_no_id,
            "row_num": row_num,
            "dec_no_display": dec_no_display,
            "declaration_no": dec_no_display,
            "title": title,
            "office": office,
            "owner_name": owner_name,
            "owner_percent": percent,
            "reg_date": reg_date,
            "declaration_date": reg_date,
            "reg_time": reg_time,
            "status": status,
            "image_url": image_url,
            "detail_url": detail_url,
            "is_rejected": 1 if ("رد" in status or "ابطال" in status) else 0,
            "classes": "5",
        })
    return rows


def load_store(path: str = DATA_STORE_PATH) -> Dict[str, Any]:
    """بارگذاری حافظه محلی رکوردهای قبلی."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_store(store: Dict[str, Any], path: str = DATA_STORE_PATH):
    """ذخیره دیکشنری رکوردها در فایل JSON."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Store] Error saving store: {e}")


class DeclarationScrapeWorker(QThread):
    """
    نخ پردازشی اجرای استخراج لیست اظهارنامه‌ها بدون مسدودسازی رابط گرافیکی
    """
    progress_changed = pyqtSignal(int, str)
    record_found = pyqtSignal(dict)
    scan_completed = pyqtSignal(int, int, int, str)  # total_scraped, new_count, alerts_count, docx_path
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
        self.similarity_engine = TrademarkSimilarityEngine()

    def stop(self):
        self._is_running = False

    def run(self):
        self.progress_changed.emit(5, "بررسی نشست ذخیره‌شده...")
        logger.info(f"شروع اجرای اسکن اظهارنامه‌ها با حالت: {self.mode}")

        if not has_saved_session():
            logger.warning("هیچ نشستی در سامانه یافت نشد.")
            self.scan_failed.emit(
                "نشستی در برنامه ذخیره نشده است.\n"
                "لطفاً از دکمه «ورود به سامانه» برای ورود به حساب خود استفاده فرمایید."
            )
            return

        user_name = get_saved_user_name() or "کاربر سامانه"
        self.progress_changed.emit(8, f"راه‌اندازی نشست برای {user_name}...")
        logger.info(f"استفاده از نشست ذخیره‌شده برای کاربر: {user_name}")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("کتابخانه playwright نصب نیست.")
            self.scan_failed.emit("کتابخانه playwright نصب نیست.")
            return

        try:
            with sync_playwright() as p:
                logger.debug("اجرای Chromium در حالت headless=True")
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )

                if os.path.exists(STORAGE_STATE_FILE):
                    logger.info(f"بارگذاری نشست کامل از فایل storage_state: {STORAGE_STATE_FILE}")
                    context = browser.new_context(
                        storage_state=STORAGE_STATE_FILE,
                        viewport={"width": 1280, "height": 800},
                        user_agent=USER_AGENT
                    )
                else:
                    logger.info("فایل storage_state یافت نشد؛ تزریق کوکی‌های متنی ذخیره‌شده...")
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        user_agent=USER_AGENT
                    )
                    cookies_data = get_saved_cookies()
                    if cookies_data:
                        cookie_list = [
                            {"name": k, "value": v, "domain": "ipm.ssaa.ir", "path": "/"}
                            for k, v in cookies_data.items()
                        ]
                        context.add_cookies(cookie_list)
                        logger.debug(f"{len(cookie_list)} کوکی به context تزریق شد.")

                page = context.new_page()

                self.progress_changed.emit(12, "در حال اتصال به لیست اظهارنامه‌ها...")
                logger.info(f"در حال باز کردن آدرس: {START_URL}")
                status_code = None
                try:
                    resp = page.goto(START_URL, timeout=45000)
                    status_code = resp.status if resp else None
                    logger.info(f"پاسخ اولیه سرور: کد وضعیت={status_code}, آدرس نهایی={page.url}, عنوان='{page.title()}'")
                except Exception as e:
                    browser.close()
                    err_text = str(e)
                    logger.error(f"خطای برقراری ارتباط در page.goto: {e}")
                    if any(w in err_text for w in ["ERR_CONNECTION_CLOSED", "ERR_TIMED_OUT", "ERR_NAME_NOT_RESOLVED", "SSL", "EOF"]):
                        self.scan_failed.emit(
                            "⚠️ خطا در برقراری ارتباط با سامانه ثبت (ipm.ssaa.ir).\n\n"
                            "علت: سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور و فیلترشکن (VPN) را مسدود می‌کنند (Geo-blocking).\n\n"
                            "لطفاً فیلترشکن (VPN) خود را خاموش فرمایید و دوباره روی دکمه اسکن کلیک کنید."
                        )
                    else:
                        self.scan_failed.emit(f"خطا در اتصال به سامانه ثبت اسناد: {e}")
                    return

                # ارزیابی وضعیت ورود
                user_data_count = page.locator("#userData").count()
                data_list_count = page.locator("#DataList").count()
                logger.debug(f"شمارش المان‌های هویتی: #userData={user_data_count}, #DataList={data_list_count}")

                if user_data_count == 0 and data_list_count == 0:
                    current_url = page.url
                    page_title = page.title()
                    logger.warning(f"نشست کاربری تأیید نشد. کد={status_code}, آدرس={current_url}, عنوان={page_title}")
                    browser.close()

                    if status_code == 500:
                        self.scan_failed.emit(
                            "⚠️ سرور ثبت اسناد خطای داخلی ۵۰۰ (Internal Server Error) بازگرداند.\n\n"
                            "کوکی‌های نشست منقضی یا از سمت سرور باطل شده‌اند.\n"
                            "لطفاً با کلیک بر روی دکمه «تغییر حساب / ورود به سامانه» مجدداً وارد شوید تا نشست تازه ذخیره گردد."
                        )
                    elif "Login" in current_url or "Account" in current_url:
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

                page_1_html = page.content()

                # استخراج تعداد کل رکوردها
                match = re.search(r'TotalRecord=(\d+)', page_1_html)
                if match:
                    total_records = int(match.group(1))
                else:
                    total_records = 1001

                calc_pages = max(1, (total_records + 19) // 20)
                actual_max_pages = min(self.max_pages, calc_pages)
                logger.info(f"تعداد کل اظهارنامه‌ها در سامانه: {total_records} (~{calc_pages} صفحه). حداکثر صفحات اسکن: {actual_max_pages}")
                self.progress_changed.emit(15, f"تعداد کل: {total_records} مورد (~{calc_pages} صفحه)")

                store = load_store(DATA_STORE_PATH)
                is_first_run = len(store) == 0
                logger.info(f"تعداد رکوردهای موجود در کش محلی: {len(store)} مورد")
                watchlist = get_watchlist(DB_FILE)

                newly_scraped = []
                new_count = 0
                alerts_count = 0

                page_num = 1
                while page_num <= actual_max_pages and self._is_running:
                    if page_num > 1:
                        url = BASE_LIST_URL.format(total_record=total_records, page=page_num)
                        try:
                            logger.debug(f"دریافت صفحه {page_num}: {url}")
                            page.goto(url, timeout=35000)
                            html = page.content()
                        except Exception as e:
                            logger.error(f"خطا در دریافت صفحه {page_num}: {e}")
                            break
                    else:
                        html = page_1_html

                    rows = parse_declaration_page(html)
                    if not rows:
                        logger.warning(f"هیچ ردیفی در صفحه {page_num} یافت نشد. پایان واکشی صفحات.")
                        break

                    new_on_this_page = 0
                    for entry in rows:
                        if not self._is_running:
                            break

                        dec_id = entry["dec_no_id"]

                        # ارزیابی شباهت با برندهای شرکت
                        title = entry.get("title", "")
                        sim_score, matched_brand, risk = self.similarity_engine.evaluate_against_watchlist(title, watchlist)
                        entry["similarity_score"] = sim_score
                        entry["matched_brand"] = matched_brand
                        entry["risk_level"] = risk

                        if risk in ["high", "medium"]:
                            alerts_count += 1
                            logger.info(f"هشدار شباهت: '{title}' با برند '{matched_brand}' ({sim_score}%) - سطح: {risk}")

                        if dec_id not in store:
                            newly_scraped.append(entry)
                            store[dec_id] = entry
                            new_on_this_page += 1
                            new_count += 1

                        # ارسال به جدول زنده رابط کاربری
                        self.record_found.emit(entry)

                    pct = min(90, int(15 + (page_num / actual_max_pages) * 75))
                    self.progress_changed.emit(pct, f"صفحه {page_num} از {actual_max_pages} ({new_count} مورد جدید)")

                    # شرط توقف زودهنگام در حالت «فقط موارد جدید»
                    if self.mode == "new_only" and not is_first_run and new_on_this_page == 0:
                        logger.info(f"در صفحه {page_num} هیچ رکورد جدیدی یافت نشد. توقف هوشمند اسکن سریع (Incremental Scan).")
                        self.progress_changed.emit(pct, "به رکوردهای قبلاً ثبت‌شده رسیدیم. توقف اسکن سریع.")
                        break

                    page_num += 1
                    time.sleep(0.2)

                browser.close()
                logger.debug("مرورگر پس‌زمینه با موفقیت بسته شد.")

        except Exception as e:
            logger.critical(f"خطای نامنتظره در اجرای اسکن: {e}")
            self.scan_failed.emit(f"خطای نامنتظره در اجرای اسکن: {e}")
            return

        if not self._is_running:
            logger.info("اسکن توسط کاربر متوقف شد.")
            self.progress_changed.emit(0, "اسکن توسط کاربر متوقف شد.")
            return

        # ذخیره در کش محلی JSON
        save_store(store, DATA_STORE_PATH)
        logger.info(f"کش محلی رکوردهای پایگاه داده با موفقیت به‌روزرسانی شد ({len(store)} رکورد).")

        # ذخیره در پایگاه داده SQLite
        try:
            scan_date = time.strftime("%Y/%m/%d %H:%M")
            scan_id = create_scan_session(
                scan_date=scan_date,
                search_params={"mode": self.mode, "source": "DeclarationList", "total": total_records},
                total_records=len(store),
                class5_count=0,
                alerts_count=alerts_count,
                db_path=DB_FILE
            )
            # رکوردهای جدید در پایگاه داده درج شوند
            if newly_scraped:
                save_declarations_batch(scan_id, newly_scraped, db_path=DB_FILE)
                logger.info(f"{len(newly_scraped)} رکورد جدید در پایگاه داده SQLite ذخیره شد.")
            elif store:
                save_declarations_batch(scan_id, list(store.values())[:100], db_path=DB_FILE)
        except Exception as e:
            logger.error(f"خطا در ثبت پایگاه داده: {e}")

        # آماده‌سازی لیست مرتب‌شده برای خروجی Word
        self.progress_changed.emit(92, "در حال نگارش و تولید فایل Word با قالب‌بندی راست‌به‌چپ...")

        all_entries_list = list(store.values())
        if newly_scraped:
            new_ids = {e["dec_no_id"] for e in newly_scraped}
            older_items = [e for e in all_entries_list if e["dec_no_id"] not in new_ids]
            ordered_for_docx = newly_scraped + older_items
        else:
            ordered_for_docx = all_entries_list

        logger.info(f"تولید فایل Word در مسیر: {self.docx_path} با {len(ordered_for_docx)} اظهارنامه...")
        auth_session = get_authenticated_session()
        try:
            export_declarations_to_word(
                declarations=ordered_for_docx,
                output_path=self.docx_path,
                session=auth_session,
                progress_callback=lambda cur, tot: self.progress_changed.emit(
                    min(99, 92 + int((cur / max(1, tot)) * 7)),
                    f"تعبیه تصاویر و پیوندها در Word ({cur}/{tot})..."
                )
            )
            logger.info(f"فایل Word با موفقیت ایجاد گردید: {self.docx_path}")
        except Exception as e:
            logger.error(f"خطا در ایجاد خروجی Word: {e}")

        self.progress_changed.emit(100, f"تکمیل شد! {new_count} مورد جدید افزوده شد.")
        self.scan_completed.emit(len(store), new_count, alerts_count, self.docx_path)

