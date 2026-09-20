"""
کلاینت ارتباط مستقیم با وب‌سرویس سامانه مالکیت معنوی (SSAA)
Direct HTTP Client for ipm.ssaa.ir
"""
import random
import json
import re
import urllib3
from typing import Dict, Any, Tuple, Optional
import requests

# غیرفعال‌سازی هشدارهای SSL در صورت بروز مشکل گواهی سرورهای داخلی
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://ipm.ssaa.ir"
SEARCH_PAGE_URL = f"{BASE_URL}/Issue-IssueTrademark"
CAPTCHA_URL = f"{BASE_URL}/Captcha"
SEARCH_ENDPOINT = f"{BASE_URL}/serv/Issue-Trademark.Sabt"


class SSAAConnectionError(Exception):
    """خطای برقراری ارتباط با سامانه ثبت (تایم‌اوت، مسدودی فایروال یا فیلترشکن)."""
    pass


class SSAAServerError(Exception):
    """خطای سمت سرور سامانه ثبت اسناد."""
    pass


class SSAAClient:
    """
    کلاینت مدیریت نشست، دریافت کپچا و استخراج صفحات اظهارنامه‌ها
    """

    def __init__(self, timeout: int = 25):
        self.session = requests.Session()
        self.timeout = timeout
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
            "Referer": SEARCH_PAGE_URL,
            "Origin": BASE_URL,
        })
        self.is_initialized = False
        self.last_error = ""

    def init_session(self) -> bool:
        """بارگذاری صفحه نخست جهت ایجاد نشست و کوکی‌های معتبر."""
        try:
            self.last_error = ""
            resp = self.session.get(SEARCH_PAGE_URL, timeout=self.timeout, verify=False)
            self.is_initialized = resp.status_code == 200
            return self.is_initialized
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            self.last_error = "vpn_timeout"
            print(f"[SSAAClient] Error initializing session (likely VPN / Geo-block): {e}")
            return False
        except Exception as e:
            self.last_error = str(e)
            print(f"[SSAAClient] Error initializing session: {e}")
            return False

    def get_captcha_image(self) -> Optional[bytes]:
        """دریافت تصویر کپچا مستقیماً به صورت بایت‌های خام."""
        try:
            self.last_error = ""
            if not self.is_initialized:
                if not self.init_session():
                    return None

            rnd = random.random()
            url = f"{CAPTCHA_URL}?w=200&rnd={rnd}"
            resp = self.session.get(url, timeout=self.timeout, verify=False)
            if resp.status_code == 200:
                return resp.content
            self.last_error = f"http_{resp.status_code}"
            return None
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            self.last_error = "vpn_timeout"
            print(f"[SSAAClient] Error fetching captcha (likely VPN / Geo-block): {e}")
            return None
        except Exception as e:
            self.last_error = str(e)
            print(f"[SSAAClient] Error fetching captcha: {e}")
            return None

    def build_search_payload(self, params: Dict[str, Any]) -> str:
        """
        ساخت دیکشنری پارامترهای جستجو منطبق بر تابع ser('.EXCol') سامانه
        """
        sobject = {
            "FromIssueDate": params.get("FromIssueDate") or None,
            "ToIssueDate": params.get("ToIssueDate") or None,
            "ItemTitle": params.get("ItemTitle") or None,
            "SearchItemTitleAsLike": str(params.get("SearchItemTitleAsLike", "3")),
            "SignProductId": str(params.get("SignProductId", "5")),
            "SignImageStage": params.get("SignImageStage") or None,
            "RegisterNo": params.get("RegisterNo") or None,
            "DeclarationNo": params.get("DeclarationNo") or None,
            "ManualNo": params.get("ManualNo") or None,
            "FromDeclarationDateRange": params.get("FromDeclarationDateRange") or None,
            "ToDeclarationDateRange": params.get("ToDeclarationDateRange") or None,
            "personType": str(params.get("personType", "1")),
            "RealOwnerName": params.get("RealOwnerName") or None,
            "RealOwnerFamily": params.get("RealOwnerFamily") or None,
            "RealOwnerNationalityCode": params.get("RealOwnerNationalityCode") or None,
            "LegalOwnerRecordNo": params.get("LegalOwnerRecordNo") or None,
            "LegalOwnerNationalityNo": params.get("LegalOwnerNationalityNo") or None,
            "GetCurrentIssue": False
        }
        return json.dumps(sobject, ensure_ascii=False)

    def search_first_page(self, params: Dict[str, Any], captcha_val: str) -> Tuple[str, int]:
        """
        ارسال اولین درخواست جستجو (صفحه ۱).
        خروجی: (محتوای HTML نتایج, تعداد کل رکوردها)
        """
        data_json = self.build_search_payload(params)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{SEARCH_PAGE_URL}#page-1"
        }

        payload = {
            "data": data_json,
            "captcha": str(captcha_val).strip()
        }

        try:
            resp = self.session.post(
                SEARCH_ENDPOINT,
                data=payload,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            raise SSAAConnectionError(
                "خطا در برقراری ارتباط با سامانه مالکیت معنوی (ipm.ssaa.ir).\n\n"
                "علت: سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور را مسدود می‌کنند (Geo-blocking).\n"
                "در صورت روشن بودن فیلترشکن (VPN)، لطفاً آن را خاموش کنید یا آی‌پی‌های ایران را مستثنی (Bypass) نمایید."
            ) from e
        except requests.exceptions.Timeout as e:
            raise SSAAConnectionError(
                "پاسخ از سرور سامانه ثبت در زمان مقرر دریافت نشد (Timeout).\n"
                "لطفاً ارتباط اینترنت یا وضعیت فیلترشکن (VPN) را بررسی فرمایید."
            ) from e
        except Exception as e:
            raise SSAAConnectionError(f"خطا در اتصال به سامانه ثبت اسناد: {e}") from e

        if resp.status_code != 200:
            raise SSAAServerError(
                f"سرور ثبت کد خطای {resp.status_code} بازگرداند. ممکن است سرور موقتاً از دسترس خارج باشد."
            )

        html = resp.text
        # جایگزینی حرف ي عربی با ی فارسی مشابه اسکریپت سامانه
        html = html.replace('ي', 'ی')

        # ذخیره آخرین پاسخ جهت عیب‌یابی آنی
        try:
            os.makedirs("logs", exist_ok=True)
            with open(os.path.join("logs", "last_search_response.html"), "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

        # استخراج تعداد کل از متن پاسخ در صورت وجود
        total_records = 0
        match = re.search(r'id=["\']tResult["\'][^>]*>([\d,]+)<', html)
        if match:
            total_str = match.group(1).replace(',', '')
            try:
                total_records = int(total_str)
            except ValueError:
                pass

        return html, total_records

    def get_page(
        self, page_num: int, params: Dict[str, Any], captcha_val: str, total_records: int = 0
    ) -> str:
        """
        دریافت صفحات بعدی (صفحه ۲ به بعد) با ارسال پارامتر extra
        """
        data_json = self.build_search_payload(params)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{SEARCH_PAGE_URL}#page-{page_num}"
        }

        # فرمت ارسال در تابع goto سامانه:
        # data={...}&captcha={...}&extra=2&tRecords=...
        body_data = {
            "data": data_json,
            "captcha": str(captcha_val).strip(),
            "extra": str(page_num),
            "tRecords": str(total_records) if total_records > 0 else ""
        }

        try:
            resp = self.session.post(
                SEARCH_ENDPOINT,
                data=body_data,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            raise SSAAConnectionError(
                f"ارتباط با سامانه ثبت حین دریافت صفحه {page_num} قطع شد.\n"
                "در صورت روشن بودن فیلترشکن، آن را خاموش نمایید."
            ) from e
        except Exception as e:
            raise SSAAConnectionError(f"خطا در دریافت صفحه {page_num}: {e}") from e

        if resp.status_code != 200:
            raise SSAAServerError(f"خطای {resp.status_code} از سرور ثبت در صفحه {page_num}.")

        html = resp.text.replace('ي', 'ی')
        return html
