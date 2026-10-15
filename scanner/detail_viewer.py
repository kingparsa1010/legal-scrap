"""
پنجره اختصاصی مشاهده پرونده اظهارنامه با استفاده از Edge WebView2 ویندوز
Declaration Detail Viewer using Native Windows Edge WebView2 (Zero Chrome / Zero Playwright)
"""
import sys
import os

# اطمینان از دسترسی به ماژول‌های پروژه حتی در صورت اجرای مستقیم به عنوان اسکریپت
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import time
import json
import re
import threading
import subprocess
import webbrowser
import webview

# تنظیم مسیر ریشه پروژه
from scanner import BASE_DIR as ROOT_DIR, DATA_DIR, webview_start_kwargs
from scanner.logger import get_logger
from scanner.auth import get_saved_credentials
from scanner.login_window import build_autofill_js

logger = get_logger("detail")
SESSION_FILE = os.path.join(DATA_DIR, "session_auth.json")


class DetailViewerApi:
    """رابط تعاملی جاوااسکریپت و پایتون جهت کپی لینک و مدیریت پنجره."""
    def __init__(self, target_url: str):
        self.target_url = target_url

    def copy_link(self) -> bool:
        """کپی کردن آدرس اینترنتی پرونده در حافظه کلیپ‌بورد ویندوز."""
        try:
            subprocess.run(["clip"], input=self.target_url.encode("utf-16"), check=True)
            return True
        except Exception:
            return False

    def open_in_external_browser(self) -> bool:
        """باز کردن پرونده در مرورگر پیش‌فرض سیستم کاربر."""
        try:
            webbrowser.open(self.target_url)
            return True
        except Exception:
            return False

    def get_url(self) -> str:
        return self.target_url


def inject_toolbar_script(url: str, title: str) -> str:
    """ایجاد اسکریپت جاوااسکریپت جهت تزریق نوار ابزار بالا با قابلیت کپی لینک."""
    safe_url = url.replace('"', '\\"')
    safe_title = title.replace('"', '\\"').replace("'", "\\'")

    return f"""
    (function() {{
        if (document.getElementById('legal-scrap-toolbar')) return;

        // تنظیم فاصله بالای صفحه برای دیده شدن محتوای زیر نوار ابزار
        try {{
            document.body.style.paddingTop = '50px';
        }} catch(e) {{}}

        var tb = document.createElement('div');
        tb.id = 'legal-scrap-toolbar';
        tb.style.position = 'fixed';
        tb.style.top = '0';
        tb.style.left = '0';
        tb.style.right = '0';
        tb.style.height = '48px';
        tb.style.backgroundColor = '#0f172a';
        tb.style.borderBottom = '1px solid #334155';
        tb.style.color = '#f8fafc';
        tb.style.zIndex = '2147483647';
        tb.style.display = 'flex';
        tb.style.alignItems = 'center';
        tb.style.justifyContent = 'space-between';
        tb.style.padding = '0 14px';
        tb.style.fontFamily = 'Tahoma, Segoe UI, sans-serif';
        tb.style.fontSize = '12px';
        tb.style.direction = 'rtl';
        tb.style.boxShadow = '0 3px 10px rgba(0,0,0,0.3)';

        // عنوان پرونده در سمت راست
        var rightSection = document.createElement('div');
        rightSection.style.display = 'flex';
        rightSection.style.alignItems = 'center';
        rightSection.style.gap = '8px';
        rightSection.style.minWidth = '220px';

        var icon = document.createElement('span');
        icon.innerText = '📑';
        icon.style.fontSize = '15px';
        rightSection.appendChild(icon);

        var titleSpan = document.createElement('span');
        titleSpan.innerText = "{safe_title}";
        titleSpan.style.fontWeight = 'bold';
        titleSpan.style.color = '#e2e8f0';
        titleSpan.style.whiteSpace = 'nowrap';
        titleSpan.style.overflow = 'hidden';
        titleSpan.style.textOverflow = 'ellipsis';
        titleSpan.style.maxWidth = '300px';
        rightSection.appendChild(titleSpan);

        tb.appendChild(rightSection);

        // بخش میانی: نمایش آدرس اینترنتی و دکمه کپی
        var midSection = document.createElement('div');
        midSection.style.display = 'flex';
        midSection.style.alignItems = 'center';
        midSection.style.gap = '8px';
        midSection.style.flex = '1';
        midSection.style.maxWidth = '680px';
        midSection.style.margin = '0 16px';

        var input = document.createElement('input');
        input.id = 'ls-url-box';
        input.type = 'text';
        input.readOnly = true;
        input.value = "{safe_url}";
        input.style.width = '100%';
        input.style.padding = '6px 12px';
        input.style.borderRadius = '6px';
        input.style.border = '1px solid #475569';
        input.style.backgroundColor = '#1e293b';
        input.style.color = '#93c5fd';
        input.style.fontSize = '11.5px';
        input.style.direction = 'ltr';
        input.style.outline = 'none';
        input.style.cursor = 'text';
        input.onclick = function() {{ this.select(); }};
        midSection.appendChild(input);

        var copyBtn = document.createElement('button');
        copyBtn.id = 'ls-copy-btn';
        copyBtn.innerHTML = '📋 <b>کپی لینک</b>';
        copyBtn.style.padding = '6px 14px';
        copyBtn.style.backgroundColor = '#2563eb';
        copyBtn.style.color = '#ffffff';
        copyBtn.style.border = 'none';
        copyBtn.style.borderRadius = '6px';
        copyBtn.style.cursor = 'pointer';
        copyBtn.style.fontSize = '11.5px';
        copyBtn.style.whiteSpace = 'nowrap';
        copyBtn.style.transition = 'background-color 0.2s';

        copyBtn.onmouseenter = function() {{ this.style.backgroundColor = '#1d4ed8'; }};
        copyBtn.onmouseleave = function() {{
            if (!this.getAttribute('data-copied')) {{
                this.style.backgroundColor = '#2563eb';
            }}
        }};

        copyBtn.onclick = function() {{
            var urlToCopy = "{safe_url}";
            // ۱. تلاش با API کپی مرورگر
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(urlToCopy);
            }}
            // ۲. کپی از طریق انتخاب ورودی
            input.select();
            try {{
                document.execCommand('copy');
            }} catch(e) {{}}

            // ۳. صدا زدن API پایتون جهت تضمین کپی در ویندوز
            try {{
                if (window.pywebview && window.pywebview.api && window.pywebview.api.copy_link) {{
                    window.pywebview.api.copy_link();
                }}
            }} catch(e) {{}}

            copyBtn.setAttribute('data-copied', '1');
            copyBtn.innerHTML = '✅ <b>کپی شد!</b>';
            copyBtn.style.backgroundColor = '#16a34a';

            setTimeout(function() {{
                copyBtn.removeAttribute('data-copied');
                copyBtn.innerHTML = '📋 <b>کپی لینک</b>';
                copyBtn.style.backgroundColor = '#2563eb';
            }}, 2500);
        }};
        midSection.appendChild(copyBtn);

        tb.appendChild(midSection);

        // بخش سمت چپ: دکمه‌های ناوبری و مرورگر سیستم
        var leftSection = document.createElement('div');
        leftSection.style.display = 'flex';
        leftSection.style.alignItems = 'center';
        leftSection.style.gap = '8px';

        var openBtn = document.createElement('button');
        openBtn.innerText = '🌐 مرورگر سیستم';
        openBtn.title = 'باز کردن در مرورگر پیش‌فرض ویندوز';
        openBtn.style.padding = '6px 11px';
        openBtn.style.backgroundColor = '#334155';
        openBtn.style.color = '#cbd5e1';
        openBtn.style.border = '1px solid #475569';
        openBtn.style.borderRadius = '6px';
        openBtn.style.cursor = 'pointer';
        openBtn.style.fontSize = '11px';
        openBtn.onmouseenter = function() {{ this.style.backgroundColor = '#475569'; }};
        openBtn.onmouseleave = function() {{ this.style.backgroundColor = '#334155'; }};
        openBtn.onclick = function() {{
            try {{
                if (window.pywebview && window.pywebview.api && window.pywebview.api.open_in_external_browser) {{
                    window.pywebview.api.open_in_external_browser();
                }} else {{
                    window.open("{safe_url}", "_blank");
                }}
            }} catch(e) {{
                window.open("{safe_url}", "_blank");
            }}
        }};
        leftSection.appendChild(openBtn);

        var refreshBtn = document.createElement('button');
        refreshBtn.innerText = '🔄';
        refreshBtn.title = 'تازه‌سازی صفحه';
        refreshBtn.style.padding = '6px 10px';
        refreshBtn.style.backgroundColor = '#334155';
        refreshBtn.style.color = '#cbd5e1';
        refreshBtn.style.border = '1px solid #475569';
        refreshBtn.style.borderRadius = '6px';
        refreshBtn.style.cursor = 'pointer';
        refreshBtn.style.fontSize = '11px';
        refreshBtn.onclick = function() {{ location.reload(); }};
        leftSection.appendChild(refreshBtn);

        tb.appendChild(leftSection);

        // افزودن نوار به ابتدای بدنه سند
        if (document.body) {{
            document.body.insertBefore(tb, document.body.firstChild);
        }} else {{
            document.documentElement.appendChild(tb);
        }}
    }})();
    """


def monitor_and_inject(window: webview.Window, url: str, title: str):
    """تزریق مکرر نوار ابزار کپی لینک هنگام بارگذاری یا تغییر تب‌ها در صفحه."""
    time.sleep(1.5)
    js = inject_toolbar_script(url, title)
    for _ in range(6):
        try:
            window.evaluate_js(js)
        except Exception:
            pass
        time.sleep(1.5)


def log_page_state(window: webview.Window, url: str, delay_seconds: int = 12):
    """ثبت تشخیصی وضعیت صفحه پرونده در لاگ (برای عیب‌یابی نشست و بارگذاری)."""
    time.sleep(delay_seconds)
    try:
        state = window.evaluate_js(
            "(function(){ try { return { url: location.href, title: document.title, "
            "hasLogin: !!document.querySelector('#UserName,input[id$=\"UserName\"]'), "
            "hasUser: !!(document.querySelector('#userData') && "
            "document.querySelector('#userData').innerText.trim()) }; } "
            "catch(e) { return { error: String(e).slice(0,120) }; } })()"
        )
        logger.info("وضعیت پنجره پرونده %s: %s", url[:60], state)
    except Exception as e:
        logger.warning("خواندن وضعیت پنجره پرونده ممکن نشد: %s", str(e)[:150])
    # مقایسه قطعی: کوکی‌های داخل مرورگر در برابر فایل نشست
    try:
        raw = window.get_cookies()
        names = sorted({m for c in (raw or []) for m in (
            list(c.keys()) if hasattr(c, "keys") else [])} |
            {c.get("name", c.get("key", "")) for c in (raw or []) if isinstance(c, dict)})
        names = [n for n in names if n]
    except Exception as e:
        names = [f"cookie-read-error: {str(e)[:80]}"]
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                file_count = len((json.load(f) or {}).get("cookies", {}))
        else:
            file_count = -1
    except Exception:
        file_count = -2
    logger.info("کوکی مرورگر پرونده (%s عدد): %s | کوکی فایل نشست: %s",
                len(names), names, file_count)


def _parse_raw_cookies(raw_cookies) -> tuple:
    """تبدیل خروجی window.get_cookies() به (دیکشنری ساده، فهرست کامل)."""
    cookies_dict = {}
    cookie_list = []
    if raw_cookies:
        for c in raw_cookies:
            try:
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
                if isinstance(c, dict):
                    name = c.get("name", c.get("key"))
                    val = c.get("value")
                    if name and val:
                        cookies_dict[name] = val
                        cookie_list.append(c)
    return cookies_dict, cookie_list


def monitor_and_capture_session(window: webview.Window, poll_seconds: int = 5, timeout_seconds: int = 1800,
                                continue_url: str = ""):
    """اگر کاربر داخل همین پنجره پرونده لاگین کند، کوکی‌ها در session_auth.json ذخیره می‌شود.

    با این کار لاگین از هر پنجره‌ای (ورود یا مشاهده) فقط یک‌بار انجام می‌شود و
    کل برنامه — اسکن‌ها و پنجره‌های بعدی — همان نشست را استفاده می‌کنند.
    بعد از اولین ثبت نشست، در صورت نیاز به‌صورت خودکار به صفحه پرونده برمی‌گردد.
    """
    time.sleep(4)
    deadline = time.time() + timeout_seconds
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
    while time.time() < deadline:
        try:
            res = window.evaluate_js(js_code)
            if res and isinstance(res, dict) and res.get("logged_in"):
                try:
                    raw = window.get_cookies()
                except Exception:
                    raw = None
                cookies_dict, cookie_list = _parse_raw_cookies(raw)
                if cookies_dict:
                    existing = {}
                    try:
                        if os.path.exists(SESSION_FILE):
                            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                                existing = json.load(f) or {}
                    except Exception:
                        existing = {}
                    user_raw = res.get("user", "") or existing.get("user_name", "") or "کاربر سامانه"
                    user_name = re.sub(r'\s+', ' ', user_raw).replace("خروج", "").replace("سلام", "").strip() or "کاربر سامانه"
                    payload = {
                        "user_name": user_name,
                        "user_agent": existing.get("user_agent") or "",
                        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "cookies": cookies_dict,
                        "cookie_list": cookie_list
                    }
                    os.makedirs(os.path.dirname(os.path.abspath(SESSION_FILE)), exist_ok=True)
                    with open(SESSION_FILE, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    logger.info("نشست از پنجره پرونده ذخیره شد (%s کوکی).", len(cookies_dict))
                    # بازگشت خودکار به صفحه پرونده پس از لاگین داخل همین پنجره
                    if continue_url:
                        try:
                            cur = window.evaluate_js("location.href") or ""
                        except Exception:
                            cur = ""
                        if continue_url not in (cur or ""):
                            try:
                                logger.info("بازگشت خودکار به صفحه پرونده پس از ورود.")
                                window.load_url(continue_url)
                            except Exception as e:
                                logger.warning("بازگشت خودکار به پرونده ممکن نشد: %s", str(e)[:120])
                    return
        except Exception:
            pass
        time.sleep(poll_seconds)


# صفحه خانگی پورتال (فعلاً استفاده نمی‌شود؛ نگه داشته شده برای آینده)
PORTAL_HOME_URL = "https://ipm.ssaa.ir/CA/DeclarationList"

_AUTH_CHECK_JS = (
    "(function(){ try {"
    "var u=document.querySelector('#userData');"
    "if(u&&u.innerText&&u.innerText.trim())return true;"
    "return !!document.querySelector('#DataList');"
    "} catch(e){ return false; } })()"
)


def autofill_login_form(window: webview.Window, timeout_seconds: int = 1800):
    """پر کردن خودکار نام‌کاربری/رمز در فرم ورودِ داخل پنجره پرونده.

    اگر پنجره پرونده روی فرم ورود فرود آمد (نشست منقضی یا نرسیده)، همان منطق
    پنجره لاگین اجرا می‌شود تا کاربر فقط کپچا را وارد کند؛ کپچا هرگز نوشته نمی‌شود.
    با اولین ورود موفق یا پایان مهلت متوقف می‌شود.
    """
    try:
        username, password = get_saved_credentials()
    except Exception:
        return
    if not username or not password:
        return
    try:
        fill_js = build_autofill_js(username, password)
    except Exception as e:
        logger.warning("ساخت اسکریپت پر کردن خودکار ممکن نشد: %s", str(e)[:120])
        return
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            res = window.evaluate_js(fill_js)
            if isinstance(res, dict) and (res.get("filledUser") or res.get("filledPass")):
                logger.info("فرم ورود داخل پنجره پرونده به صورت خودکار پر شد.")
                return
            try:
                if window.evaluate_js(_AUTH_CHECK_JS):
                    return
            except Exception:
                pass
        except Exception:
            pass
        time.sleep(2)


def open_detail_viewer(url: str, title: str = "مشاهده پرونده اظهارنامه"):
    """پنجره بومی WebView2 برای مشاهده پرونده با نشست یکپارچه.

    آدرس پرونده مستقیم باز می‌شود (بدون معطلی)؛ اگر سامانه فرم ورود نشان داد،
    نام‌کاربری/رمز خودکار پر می‌شود و پس از ورود، خودکار به پرونده برمی‌گردد.
    """
    if not url:
        return

    # نرمال‌سازی آدرس پرونده
    url = url.strip()
    if url.startswith("/"):
        url = f"https://ipm.ssaa.ir{url}"
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://ipm.ssaa.ir/{url}"

    api = DetailViewerApi(url)

    # ایجاد پنجره Edge WebView2 — آدرس پرونده مستقیم و بدون معطلی باز می‌شود
    window = webview.create_window(
        title=f"پرونده اظهارنامه — {title}",
        url=url,
        width=1200,
        height=820,
        resizable=True,
        text_select=True,
        js_api=api,
        confirm_close=False
    )

    # تزریق نوار ابزار در نخ پس‌زمینه پس از بارگذاری صفحه
    t = threading.Thread(target=monitor_and_inject, args=(window, url, title), daemon=True)
    t.start()

    # ثبت تشخیصی وضعیت صفحه برای عیب‌یابی نشست
    t_state = threading.Thread(target=log_page_state, args=(window, url), daemon=True)
    t_state.start()

    # پر کردن خودکار فرم ورود اگر پنجره روی فرم ورود فرود آمد (فقط کپچا دستی)
    t_af = threading.Thread(target=autofill_login_form, args=(window,), daemon=True)
    t_af.start()

    # ناظر ذخیره نشست: اگر کاربر داخل همین پنجره لاگین کند، سشن برای کل برنامه ثبت
    # و به‌صورت خودکار به صفحه پرونده برمی‌گردد
    t2 = threading.Thread(target=monitor_and_capture_session,
                          args=(window, 5, 1800, url), daemon=True)
    t2.start()

    # شروع لوپ پیام‌های گرافیکی WebView2 بومی ویندوز با پروفایل مشترک ماندگار؛
    # چون پنجره ورود هم از همین پروفایل استفاده می‌کند، نشست لاگین حفظ شده
    # و مشاهده پرونده/گواهی بدون ورود مجدد انجام می‌شود.
    webview.start(**webview_start_kwargs())


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else ""
    brand_title = sys.argv[2] if len(sys.argv) > 2 else "مشاهده پرونده"

    if not target_url:
        print("Error: Target declaration URL is required.")
        sys.exit(1)

    open_detail_viewer(target_url, brand_title)
