"""
سامانه پایش هوشمند علائم تجاری سازمان ثبت اسناد و املاک کشور (SSAA)
نقطه ورود و اجرای برنامه
"""
import sys
import os
import json

# اطمینان از قرارگیری مسیر ریشه پروژه در PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# پشتیبانی از باز کردن پنجره لاگین در فرآیند فرزند مستقل (هم فایل EXE و هم سورس کد)
if len(sys.argv) > 1 and sys.argv[1] == '--login':
    from scanner.logger import setup_logging as _setup
    _setup()
    try:
        from scanner.login_window import run_login
        res = run_login()
    except Exception as _e:
        # هرگز نباید فرزند با اکسپشن مدیریت‌نشده بمیرد (پنجره کرش والد را معطل می‌کند)
        res = {"success": False, "user_name": "", "error": str(_e)[:300]}
    print("\n---RESULT---")
    # فقط ASCII چاپ می‌شود: نام فارسی با ensure_ascii=False روی stdout با
    # انکدینگ cp1252 در حالت EXE می‌ترکد (UnicodeEncodeError) و لاگین قفل می‌شود
    try:
        print(json.dumps(res, ensure_ascii=True))
    except Exception:
        print('{"success": false, "user_name": "", "error": "result-print-failed"}')
    sys.exit(0)

# ابزار تشخیصی دامپ DOM صفحه ورود (عیب‌یابی پر کردن خودکار)
if len(sys.argv) > 1 and sys.argv[1] == '--dump-login-dom':
    from scanner.dom_inspector import run_dom_dump
    target = sys.argv[2] if len(sys.argv) > 2 else "https://ipm.ssaa.ir/CA/DeclarationList"
    run_dom_dump(target)
    sys.exit(0)

# پشتیبانی از باز کردن پنجره WebView2 در حالت فایل کامپایل‌شده (EXE)
if len(sys.argv) > 1 and sys.argv[1] == '--view-detail':
    from scanner.logger import setup_logging as _setup
    _setup()
    from scanner.detail_viewer import open_detail_viewer
    target_url = sys.argv[2] if len(sys.argv) > 2 else ""
    brand_title = sys.argv[3] if len(sys.argv) > 3 else "مشاهده پرونده"
    if target_url:
        open_detail_viewer(target_url, brand_title)
    sys.exit(0)

from gui.app import run_app

def main():
    print("==================================================")
    print("  Legal Scrap - Trademark Monitoring Engine       ")
    print("  Iranian Intellectual Property Center (SSAA)     ")
    print("==================================================")
    run_app()

if __name__ == '__main__':
    main()
