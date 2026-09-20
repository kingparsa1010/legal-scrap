"""
پردازشگر پس‌زمینه اسکن و استخراج داده‌ها بدون مسدودسازی رابط کاربری
Background QThread Worker for Continuous Scanning & Similarity Processing
"""
import time
import re
from typing import Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal

from scanner.client import SSAAClient, SSAAConnectionError, SSAAServerError
from scanner.parser import parse_search_results
from scanner.similarity import TrademarkSimilarityEngine
from scanner.database import (
    create_scan_session, save_declarations_batch, update_scan_stats,
    get_watchlist, get_scan_declarations, DB_FILE
)
from scanner.exporter import export_scan_to_excel


class ScanWorker(QThread):
    """
    نخ پس‌زمینه اجرای اسکن و ثبت داده‌ها
    """
    progress_changed = pyqtSignal(int, str)      # درصد پیشرفت, پیام وضعیت
    record_found = pyqtSignal(dict)              # ارسال رکورد جدید به جدول GUI
    scan_completed = pyqtSignal(int, str, int, int)  # scan_id, excel_path, total, alerts
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
        self.similarity_engine = TrademarkSimilarityEngine()

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            self.progress_changed.emit(5, "در حال ایجاد نوبت اسکن در پایگاه داده...")
            scan_id = create_scan_session(self.scan_date, self.search_params)
            watchlist = get_watchlist()

            self.progress_changed.emit(10, "ارسال درخواست اولیه به سامانه (صفحه ۱)...")
            html_p1, total_records = self.client.search_first_page(
                self.search_params, self.captcha_value
            )

            if "کد امنیتی نادرست است" in html_p1 or "کد امنیتی اشتباه" in html_p1:
                self.scan_failed.emit("کد امنیتی (کپچا) اشتباه وارد شده است. لطفاً کد جدید را امتحان کنید.")
                return

            all_collected: List[Dict[str, Any]] = []
            seen_dec_nos = set()

            # پردازش صفحه ۱
            records_p1 = parse_search_results(html_p1)
            if not records_p1:
                if "موردی یافت نشد" in html_p1:
                    self.progress_changed.emit(100, "جستجو انجام شد: هیچ اظهارنامه‌ای با این مشخصات یافت نشد.")
                    self.scan_completed.emit(scan_id, "", 0, 0)
                    return
                elif not html_p1.strip():
                    self.scan_failed.emit(
                        "پاسخ دریافتی از سامانه ثبت خالی بود.\n"
                        "در صورت روشن بودن فیلترشکن (VPN) آن را خاموش کرده و مجدداً تلاش نمایید."
                    )
                    return
                else:
                    # سرور پاسخی غیرعادی بازگردانده است
                    clean_snippet = re.sub(r'<[^>]+>', ' ', html_p1).strip()
                    clean_snippet = ' '.join(clean_snippet.split())[:120]
                    self.scan_failed.emit(
                        f"پاسخ غیرمنتظره از سرور ثبت دریافت شد:\n«{clean_snippet}»\n\n"
                        "احتمال انقضای کد امنیتی یا فیلتر بودن ارتباط وجود دارد. "
                        "لطفاً فیلترشکن را خاموش کرده، «کد جدید» را بزنید و مجدداً اسکن کنید."
                    )
                    return

            for r in records_p1:
                dec_no = r.get('declaration_no')
                if dec_no and dec_no not in seen_dec_nos:
                    seen_dec_nos.add(dec_no)
                    # محاسبه شباهت
                    score, brand, risk = self.similarity_engine.evaluate_against_watchlist(
                        r.get('title', ''), watchlist
                    )
                    r['matched_brand'] = brand
                    r['similarity_score'] = score
                    r['risk_level'] = risk
                    all_collected.append(r)
                    self.record_found.emit(r)

            self.progress_changed.emit(20, f"صفحه ۱ دریافت شد ({len(records_p1)} رکورد).")

            # ادامه استخراج صفحات بعدی تا حداکثر تعیین‌شده یا اتمام رکوردها
            page = 2
            while page <= self.max_pages and not self.is_cancelled:
                percent = min(90, int(20 + (page / self.max_pages) * 70))
                self.progress_changed.emit(percent, f"در حال استخراج صفحه {page}...")

                time.sleep(1.0)  # وقفه کوتاه جهت پیشگیری از فشار روی سرور
                html_page = self.client.get_page(
                    page, self.search_params, self.captcha_value, total_records
                )

                page_records = parse_search_results(html_page)
                if not page_records:
                    # دیگر رکوردی در صفحات بعدی وجود ندارد
                    break

                new_on_page = 0
                for r in page_records:
                    dec_no = r.get('declaration_no')
                    if dec_no and dec_no not in seen_dec_nos:
                        seen_dec_nos.add(dec_no)
                        score, brand, risk = self.similarity_engine.evaluate_against_watchlist(
                            r.get('title', ''), watchlist
                        )
                        r['matched_brand'] = brand
                        r['similarity_score'] = score
                        r['risk_level'] = risk
                        all_collected.append(r)
                        self.record_found.emit(r)
                        new_on_page += 1

                if new_on_page == 0:
                    # رکوردهای تکراری بود یا به انتها رسیدیم
                    break

                page += 1

            # ذخیره در دیتابیس
            self.progress_changed.emit(92, "در حال ذخیره رکوردهای استخراج‌شده در پایگاه داده...")
            save_declarations_batch(scan_id, all_collected)

            # آمارگیری
            total_count = len(all_collected)
            class5_count = sum(1 for r in all_collected if r.get('has_class_5'))
            alerts_count = sum(
                1 for r in all_collected
                if r.get('has_class_5') and not r.get('is_rejected') and r.get('risk_level') in ('high', 'medium')
            )
            update_scan_stats(scan_id, total_count, class5_count, alerts_count)

            # خروجی اکسل
            self.progress_changed.emit(96, "در حال تولید گزارش اکسل سه برگه‌ای...")
            alerts_list = get_scan_declarations(scan_id, 'alerts')
            rejected_list = get_scan_declarations(scan_id, 'rejected')
            all_decs_list = get_scan_declarations(scan_id, 'all')

            excel_path = export_scan_to_excel(
                scan_info={'scan_date': self.scan_date},
                alerts=alerts_list,
                rejected=rejected_list,
                all_records=all_decs_list
            )

            self.progress_changed.emit(100, f"اسکن با موفقیت به پایان رسید. ({alerts_count} هشدار شناسایی شد)")
            self.scan_completed.emit(scan_id, excel_path, total_count, alerts_count)

        except SSAAConnectionError as ce:
            self.scan_failed.emit(str(ce))
        except SSAAServerError as se:
            self.scan_failed.emit(str(se))
        except Exception as e:
            err_text = str(e)
            if any(k in err_text for k in ("ConnectTimeout", "ConnectionRefused", "timed out", "Max retries exceeded")):
                self.scan_failed.emit(
                    "خطا در برقراری ارتباط با سامانه مالکیت معنوی (ipm.ssaa.ir).\n\n"
                    "علت احتمالی: سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور را مسدود می‌کنند (Geo-blocking).\n"
                    "در صورت روشن بودن فیلترشکن (VPN)، لطفاً آن را خاموش کرده یا سایت‌های ایران را Bypass نمایید."
                )
            else:
                self.scan_failed.emit(f"خطای سیستمی در اجرای اسکن: {err_text}")
