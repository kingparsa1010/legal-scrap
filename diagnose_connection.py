"""
اسکریپت جامع عیب‌یابی و آزمایش ارتباط با سامانه ثبت اسناد و املاک (SSAA)
Comprehensive Diagnostic Tool for ipm.ssaa.ir Connection & Persistent Session
"""
import sys
import os
import socket
import ssl
import time
import json

# تنظیم مسیر ریشه پروژه
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from scanner.logger import setup_logging, get_logger, get_log_file_path
from scanner.auth import (
    SESSION_FILE, STORAGE_STATE_FILE, START_URL, USER_AGENT,
    has_saved_session, get_saved_user_name, get_saved_cookies
)

setup_logging("DEBUG")
logger = get_logger("diagnostic")


def print_step(title: str):
    print("\n" + "=" * 65)
    print(f"  🔍 {title}")
    print("=" * 65)


def test_dns_and_socket():
    print_step("مرحله ۱: بررسی DNS و اتصال شبکه (Socket & TLS)")
    host = "ipm.ssaa.ir"
    port = 443

    # ۱. تحلیل DNS
    try:
        ip_list = socket.gethostbyname_ex(host)[2]
        print(f"✅ تحلیل DNS موفقیت‌آمیز بود. آی‌پی‌های سرور: {', '.join(ip_list)}")
        logger.info(f"DNS resolved {host} -> {ip_list}")
    except Exception as e:
        print(f"❌ خطا در تحلیل DNS: {e}")
        logger.error(f"DNS resolution failed: {e}")
        return False

    # ۲. برقراری سوکت TCP
    try:
        t0 = time.time()
        sock = socket.create_connection((host, port), timeout=10)
        tcp_time = (time.time() - t0) * 1000
        print(f"✅ اتصال TCP به پورت ۴۴۳ برقرار شد (زمان تأخیر: {tcp_time:.1f} میلی‌ثانیه)")
        logger.info(f"TCP connection established in {tcp_time:.1f}ms")
    except Exception as e:
        print(f"❌ خطا در اتصال TCP به پورت ۴۴۳: {e}")
        logger.error(f"TCP connection failed: {e}")
        return False

    # ۳. دست‌تکانی امنیتی TLS/SSL
    try:
        t0 = time.time()
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            tls_version = ssock.version()
            cipher = ssock.cipher()
            tls_time = (time.time() - t0) * 1000
            print(f"✅ دست‌تکانی TLS برقرار شد ({tls_version}, {cipher[0]} - {tls_time:.1f}ms)")
            logger.info(f"TLS handshake success: {tls_version}, {cipher[0]} in {tls_time:.1f}ms")
    except Exception as e:
        print(f"❌ خطا در دست‌تکانی TLS/SSL: {e}")
        print("💡 نکته: این خطا معمولاً هنگام روشن بودن VPN یا مسدودسازی توسط فایروال رخ می‌دهد.")
        logger.error(f"TLS handshake failed: {e}")
        return False

    return True


def test_session_files():
    print_step("مرحله ۲: بررسی فایل‌های ذخیره‌شده نشست کاربر")
    has_session = has_saved_session()
    print(f"آیا فایل نشستی ذخیره شده است؟ {'✅ بله' if has_session else '❌ خیر'}")

    if os.path.exists(STORAGE_STATE_FILE):
        size_kb = os.path.getsize(STORAGE_STATE_FILE) / 1024
        try:
            with open(STORAGE_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            cookies = state_data.get("cookies", [])
            origins = state_data.get("origins", [])
            print(f"✅ فایل storage_state موجود است: {STORAGE_STATE_FILE} ({size_kb:.1f} KB)")
            print(f"   • تعداد کل کوکی‌ها با جزئیات کامل امنیتی: {len(cookies)}")
            print(f"   • منشأهای محلی ذخیره شده (Origins): {len(origins)}")
            for c in cookies[:5]:
                print(f"     - کوکی: {c.get('name')} (دامنه: {c.get('domain')}, امن: {c.get('secure')})")
        except Exception as e:
            print(f"⚠️ خطا در خواندن storage_state: {e}")
    else:
        print(f"⚠️ فایل {STORAGE_STATE_FILE} هنوز ایجاد نشده است.")

    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
            user_name = auth_data.get("user_name", "نامشخص")
            saved_at = auth_data.get("saved_at", "نامشخص")
            print(f"✅ فایل session_auth موجود است. کاربر: '{user_name}' | تاریخ ذخیره: {saved_at}")
        except Exception as e:
            print(f"⚠️ خطا در خواندن session_auth: {e}")
    else:
        print(f"⚠️ فایل {SESSION_FILE} موجود نیست.")

    return has_session


def test_playwright_navigation():
    print_step("مرحله ۳: اجرای مرورگر Chromium و تست اعتبار نشست در سامانه")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ کتابخانه playwright نصب نیست.")
        return

    print("🚀 در حال اجرای مرورگر Chromium در پس‌زمینه (Headless)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            if os.path.exists(STORAGE_STATE_FILE):
                print(f"📂 در حال بارگذاری وضعیت نشست از: {STORAGE_STATE_FILE}")
                context = browser.new_context(
                    storage_state=STORAGE_STATE_FILE,
                    viewport={"width": 1280, "height": 800},
                    user_agent=USER_AGENT
                )
            else:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=USER_AGENT
                )
                cookies = get_saved_cookies()
                if cookies:
                    print(f"🔑 تزریق {len(cookies)} کوکی متنی به مرورگر...")
                    context.add_cookies([
                        {"name": k, "value": v, "domain": "ipm.ssaa.ir", "path": "/"}
                        for k, v in cookies.items()
                    ])

            page = context.new_page()
            print(f"🌐 در حال پیمایش به {START_URL} ...")
            t0 = time.time()
            resp = page.goto(START_URL, timeout=45000)
            elapsed = time.time() - t0

            status_code = resp.status if resp else "None"
            final_url = page.url
            title = page.title()

            print(f"\n📊 نتایج پاسخ سرور:")
            print(f"   • کد وضعیت HTTP: {status_code}")
            print(f"   • زمان پاسخ‌دهی: {elapsed:.2f} ثانیه")
            print(f"   • آدرس نهایی: {final_url}")
            print(f"   • عنوان صفحه: '{title}'")

            user_data_count = page.locator("#userData").count()
            data_list_count = page.locator("#DataList").count()
            print(f"   • وجود شناسه کاربر (#userData): {'✅ بله' if user_data_count > 0 else '❌ خیر'}")
            print(f"   • وجود جدول اظهارنامه‌ها (#DataList): {'✅ بله' if data_list_count > 0 else '❌ خیر'}")

            if user_data_count > 0:
                user_text = page.locator("#userData").inner_text().strip()
                print(f"\n🎉 تبریک! نشست شما کاملاً معتبر و فعال است:")
                print(f"   مشخصات کاربر وارد شده: {user_text}")
            elif data_list_count > 0:
                print(f"\n✅ دسترسی به جدول اظهارنامه‌ها با موفقیت تأیید شد.")
            else:
                print(f"\n⚠️ نشست شما توسط سرور تأیید نشد.")
                if status_code == 500:
                    print("🛑 سرور خطای داخلی ۵۰۰ داده است (احتمالاً توکن‌ها در سرور منقضی شده‌اند).")
                    print("👉 راه‌حل: در برنامه دکمه «تغییر حساب / ورود به سامانه» را بزنید و یک‌بار وارد شوید.")
                elif "Login" in final_url or "Account" in final_url:
                    print("🛑 سامانه به صفحه ورود هدایت کرد (نیاز به ورود مجدد).")
                else:
                    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
                    shot_path = os.path.join(ROOT_DIR, "logs", "diagnostic_screenshot.png")
                    html_path = os.path.join(ROOT_DIR, "logs", "diagnostic_page.html")
                    page.screenshot(path=shot_path)
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print(f"📷 تصویر صفحه خطا در {shot_path} ذخیره شد.")
                    print(f"📄 فایل HTML در {html_path} ذخیره شد.")

            browser.close()

    except Exception as e:
        print(f"❌ خطا در اجرای Playwright: {e}")
        logger.error(f"Playwright navigation failed: {e}")


def main():
    print("===============================================================")
    print("  ابزار تخصصی عیب‌یابی و آزمایش ارتباط با سامانه ثبت اسناد")
    print("  Iranian Intellectual Property (SSAA) Diagnostic Tool")
    print("===============================================================")
    print("توجه: پیش از اجرای این تست، لطفاً مطمئن شوید که فیلترشکن (VPN) خاموش است.")

    net_ok = test_dns_and_socket()
    test_session_files()

    if net_ok:
        test_playwright_navigation()
    else:
        print("\n❌ به دلیل عدم برقراری اتصال شبکه با ipm.ssaa.ir، تست مرورگر لغو شد.")

    print("\n" + "=" * 65)
    print(f"📁 گزارش کامل این عملیات در فایل لاگ ثبت شد: {get_log_file_path()}")
    print("===============================================================\n")


if __name__ == '__main__':
    main()
