"""
اسکریپت جامع عیب‌یابی و آزمایش ارتباط با سامانه ثبت اسناد و املاک (SSAA)
Comprehensive Diagnostic Tool for ipm.ssaa.ir Connection & Edge WebView2 Session
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

# تنظیم انکودینگ UTF-8 برای ترمینال ویندوز
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scanner.logger import setup_logging, get_logger, get_log_file_path
from scanner.auth import (
    SESSION_FILE, START_URL, USER_AGENT,
    has_saved_session, get_saved_user_name, get_saved_cookies,
    get_authenticated_session
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
        t_conn = time.time() - t0
        print(f"✅ اتصال TCP سوکت به پورت ۴۴۳ برقرار شد (زمان: {t_conn:.2f} ثانیه)")
        logger.info(f"TCP socket established in {t_conn:.2f}s")
    except Exception as e:
        print(f"❌ برقراری اتصال TCP ناموفق بود: {e}")
        logger.error(f"TCP socket failed: {e}")
        return False

    # ۳. دست‌تکانی امنیتی TLS/SSL
    try:
        context = ssl.create_default_context()
        t0 = time.time()
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            t_ssl = time.time() - t0
            cipher = ssock.cipher()
            version = ssock.version()
            print(f"✅ دست‌تکانی امنیتی TLS برقرار شد (نسخه: {version}، رمزگذاری: {cipher[0]}، زمان: {t_ssl:.2f} ثانیه)")
            logger.info(f"TLS handshake success: {version}, {cipher}")
    except Exception as e:
        print(f"⚠️ دست‌تکانی TLS به صورت استاندارد رد شد یا مسدود گردید: {e}")
        logger.warning(f"TLS handshake warning: {e}")
        return True

    return True


def test_webview2_environment():
    print_step("مرحله ۲: بررسی محیط Edge WebView2 و کتابخانه PyWebView")
    try:
        import webview
        print("✅ کتابخانه pywebview با موفقیت بارگذاری شد.")
        try:
            import webview.platforms.winforms as wf
            is_chrom = getattr(wf, "is_chromium", False)
            if is_chrom:
                print("✅ موتور بومی Microsoft Edge WebView2 ویندوز فعال و آماده به کار است.")
                print("   (کاملاً مستقل از Google Chrome و بدون نیاز به نصب Playwright)")
            else:
                print("⚠️ موتور WebView2 گزارش نشد، حالت پیش‌فرض ویندوز فعال است.")
        except Exception as e:
            print(f"ℹ️ اطلاعات موتور وب‌ویو: {e}")
    except ImportError:
        print("❌ کتابخانه pywebview نصب نیست. لطفاً با دستور 'pip install pywebview' آن را نصب فرمایید.")


def test_session_files():
    print_step("مرحله ۳: بررسی فایل‌های نشست و اعتبار لاگین")
    has_session = has_saved_session()
    user_name = get_saved_user_name()
    cookies = get_saved_cookies()

    if has_session:
        print(f"✅ فایل نشست موجود است: {SESSION_FILE}")
        print(f"   • نام کاربر واردشده: {user_name if user_name else 'کاربر سامانه'}")
        print(f"   • تعداد کوکی‌های ذخیره‌شده: {len(cookies)}")
        for k in list(cookies.keys())[:5]:
            print(f"     - کوکی: {k}")
    else:
        print(f"⚠️ هنوز هیچ نشستی ذخیره نشده است ({SESSION_FILE} موجود نیست).")
        print("   کاربر برای اسکن اظهارنامه‌ها باید یک‌بار دکمه «ورود به سامانه» را کلیک کند.")

    return has_session


def test_http_session_request():
    print_step("مرحله ۴: تست مستقیم ارسال درخواست HTTP به سامانه با نشست فعال")
    try:
        import requests
        from bs4 import BeautifulSoup
        session = get_authenticated_session()
        print(f"🌐 در حال ارسال درخواست HTTP GET به {START_URL} ...")
        t0 = time.time()
        resp = session.get(START_URL, timeout=30, verify=False)
        elapsed = time.time() - t0

        print(f"📊 نتایج پاسخ سرور:")
        print(f"   • کد وضعیت HTTP: {resp.status_code}")
        print(f"   • زمان پاسخ‌دهی: {elapsed:.2f} ثانیه")
        print(f"   • آدرس نهایی: {resp.url}")

        soup = BeautifulSoup(resp.text, "html.parser")
        user_elem = soup.select_one("#userData")
        table_elem = soup.select_one("#DataList")

        has_user = bool(user_elem and user_elem.get_text(strip=True))
        has_table = bool(table_elem)

        print(f"   • وجود شناسه کاربر (#userData): {'✅ بله' if has_user else '❌ خیر'}")
        print(f"   • وجود جدول اظهارنامه‌ها (#DataList): {'✅ بله' if has_table else '❌ خیر'}")

        if has_user:
            print(f"\n🎉 تبریک! نشست شما کاملاً معتبر و فعال است:")
            print(f"   مشخصات کاربر: {user_elem.get_text(strip=True)}")
        elif has_table:
            print("\n✅ دسترسی به جدول اظهارنامه‌ها با موفقیت تأیید شد.")
        else:
            print("\n⚠️ نشست ذخیره‌شده در این درخواست شناسایی نشد (ممکن است نیاز به ورود مجدد باشد).")

    except Exception as e:
        print(f"❌ خطا در ارسال درخواست HTTP: {e}")
        logger.error(f"HTTP test request failed: {e}")


def main():
    print("===============================================================")
    print("  ابزار تخصصی عیب‌یابی و آزمایش ارتباط با سامانه ثبت اسناد")
    print("  Iranian Intellectual Property (SSAA) Diagnostic Tool")
    print("===============================================================")
    print("توجه: پیش از اجرای این تست، لطفاً مطمئن شوید که فیلترشکن (VPN) خاموش است.")

    net_ok = test_dns_and_socket()
    test_webview2_environment()
    test_session_files()

    if net_ok:
        test_http_session_request()
    else:
        print("\n❌ به دلیل عدم برقراری اتصال شبکه با ipm.ssaa.ir، ادامه تست لغو شد.")

    print("\n" + "=" * 65)
    print(f"📁 گزارش کامل این عملیات در فایل لاگ ثبت شد: {get_log_file_path()}")
    print("===============================================================\n")


if __name__ == '__main__':
    main()
