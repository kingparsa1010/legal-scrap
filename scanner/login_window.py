"""
پنجره ورود بومی سامانه با استفاده از Edge WebView2 ویندوز (بدون نیاز به کروم یا Playwright)
Native Windows WebView2 Login Window for ipm.ssaa.ir (Zero Playwright / Zero Chrome)
"""
import sys
import os
import time
import json
import re
import threading
from typing import Dict, Any, List
import webview

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(ROOT_DIR, "session_auth.json")
START_URL = "https://ipm.ssaa.ir/CA/DeclarationList"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def monitor_login(window: webview.Window, result: Dict[str, Any], timeout_seconds: int = 360):
    """حلقه نظارت پس‌زمینه بر وضعیت ورود کاربر به سامانه."""
    start_time = time.time()

    # کمی مهلت اولیه برای بارگذاری صفحه اول
    time.sleep(2)

    while time.time() - start_time < timeout_seconds:
        try:
            # اجرای اسکریپت جاوااسکریپت برای تشخیص ورود
            js_code = """
                (function() {
                    var u = document.querySelector('#userData');
                    if (u && u.innerText && u.innerText.trim().length > 0) {
                        return { logged_in: true, user: u.innerText.trim() };
                    }
                    var d = document.querySelector('#DataList');
                    if (d) {
                        return { logged_in: true, user: 'کاربر سامانه' };
                    }
                    return { logged_in: false, user: '' };
                })()
            """
            eval_res = window.evaluate_js(js_code)

            if eval_res and isinstance(eval_res, dict) and eval_res.get("logged_in"):
                user_raw = eval_res.get("user", "")
                user_name = re.sub(r'\s+', ' ', user_raw).replace("خروج", "").replace("سلام", "").strip() or "کاربر سامانه"

                # تأخیر کوتاه برای تثبیت کوکی‌ها در مرورگر
                time.sleep(1)

                # استخراج کوکی‌ها از موتور بومی WebView2
                raw_cookies = window.get_cookies()
                cookies_dict = {}
                cookie_list = []

                if raw_cookies:
                    for c in raw_cookies:
                        try:
                            # هر c یک شیء SimpleCookie است
                            for name, morsel in c.items():
                                cookies_dict[name] = morsel.value
                                cookie_list.append({
                                    "name": name,
                                    "value": morsel.value,
                                    "domain": morsel["domain"] or "ipm.ssaa.ir",
                                    "path": morsel["path"] or "/",
                                    "secure": bool(morsel["secure"]),
                                    "httponly": bool(morsel["httponly"])
                                })
                        except Exception:
                            # در صورتی که ساختار دیکشنری مستقیم باشد
                            if isinstance(c, dict):
                                name = c.get("name", c.get("key"))
                                val = c.get("value")
                                if name and val:
                                    cookies_dict[name] = val
                                    cookie_list.append(c)

                # ذخیره اطلاعات ورود در فایل نشست
                payload = {
                    "user_name": user_name,
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "cookies": cookies_dict,
                    "cookie_list": cookie_list
                }
                with open(SESSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                result["success"] = True
                result["user_name"] = user_name
                result["cookies_count"] = len(cookies_dict)

                # بستن پنجره لاگین
                window.destroy()
                return

        except Exception as e:
            # در حین بارگذاری یا انتقال صفحات ممکن است evaluate_js موقتاً ناموفق باشد
            pass

        time.sleep(1.2)

    # پایان مهلت زمانی
    try:
        window.destroy()
    except Exception:
        pass


def run_login() -> Dict[str, Any]:
    """اجرای پنجره لاگین بومی با Microsoft Edge WebView2."""
    result = {
        "success": False,
        "user_name": "",
        "error": "window_closed"
    }

    # ایجاد پنجره Edge WebView2 بومی ویندوز
    window = webview.create_window(
        title="ورود به سامانه مالکیت معنوی (SSAA)",
        url=START_URL,
        width=1150,
        height=750,
        resizable=True,
        text_select=True,
        confirm_close=False
    )

    # اجرای ناظر در نخ پس‌زمینه
    t = threading.Thread(target=monitor_login, args=(window, result), daemon=True)
    t.start()

    # شروع لوپ پیام‌های گرافیکی WebView2 در ترد اصلی
    # استفاده از edgechromium روی ویندوز (بدون نیاز به کروم یا نصب مرورگر دیگر)
    webview.start(gui="edgechromium", debug=False)

    return result


if __name__ == "__main__":
    res = run_login()
    # چاپ نتیجه نهایی به صورت JSON در خروجی استاندارد
    print("\n---RESULT---")
    print(json.dumps(res, ensure_ascii=False))
