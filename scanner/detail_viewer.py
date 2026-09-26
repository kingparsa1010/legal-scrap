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
import threading
import subprocess
import webbrowser
import webview

# تنظیم مسیر ریشه پروژه
from scanner import BASE_DIR as ROOT_DIR
SESSION_FILE = os.path.join(ROOT_DIR, "session_auth.json")


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


def open_detail_viewer(url: str, title: str = "مشاهده پرونده اظهارنامه"):
    """اجرای پنجره بومی WebView2 برای مشاهده پرونده با قابلیت کپی لینک."""
    if not url:
        return

    # نرمال‌سازی آدرس پرونده
    url = url.strip()
    if url.startswith("/"):
        url = f"https://ipm.ssaa.ir{url}"
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://ipm.ssaa.ir/{url}"

    api = DetailViewerApi(url)

    # ایجاد پنجره Edge WebView2
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

    # شروع لوپ پیام‌های گرافیکی WebView2 بومی ویندوز
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else ""
    brand_title = sys.argv[2] if len(sys.argv) > 2 else "مشاهده پرونده"

    if not target_url:
        print("Error: Target declaration URL is required.")
        sys.exit(1)

    open_detail_viewer(target_url, brand_title)
