"""
اسکریپت خودکار ساخت فایل اجرایی پرتابل و مستقل (Single-file Portable EXE)
این اسکریپت تمام نیازمندی‌های PyInstaller، آیکون اختصاصی و تنظیمات ویندوز را اعمال می‌کند.
"""
import sys
import os
import subprocess

def prepare_icon(assets_dir: str) -> str:
    """اطمینان از تولید فایل logo.ico با کیفیت‌های مختلف از روی logo.png."""
    ico_path = os.path.join(assets_dir, "logo.ico")
    png_path = os.path.join(assets_dir, "logo.png")

    if not os.path.exists(ico_path) and os.path.exists(png_path):
        try:
            from PIL import Image
            img = Image.open(png_path)
            # ذخیره با ابعاد چندگانه برای نمایش شفاف در دسکتاپ و تسک‌بار
            icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(ico_path, format="ICO", sizes=icon_sizes)
            print("[✓] آیکون logo.ico با موفقیت از logo.png ساخته شد.")
        except Exception as e:
            print(f"[!] ساخت آیکون با خطا مواجه شد: {e}")

    return ico_path if os.path.exists(ico_path) else ""


def run_build():
    print("=" * 65)
    print("  شروع فرآیند بیلد تک‌فایل اجرایی پرتابل و مستقل (LegalScrap.exe)")
    print("=" * 65)

    # ۱. بررسی و نصب PyInstaller در صورت نیاز
    try:
        import PyInstaller
        print(f"[✓] PyInstaller شناسایی شد (نسخه {PyInstaller.__version__})")
    except ImportError:
        print("[!] PyInstaller نصب نیست. در حال نصب خودکار با pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[✓] PyInstaller با موفقیت نصب شد.")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(root_dir, "assets")

    # ۲. آماده‌سازی آیکون اختصاصی برنامه
    ico_path = prepare_icon(assets_dir)

    # ۳. پارامترهای بهینه‌شده PyInstaller برای ویندوز
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",           # تولید تک‌فایل مستقل بدون نیاز به ستاپ
        "--windowed",          # عدم نمایش پنجره سیاه ترمینال (GUI)
        "--name", "LegalScrap",
        # ماژول‌های حیاتی
        "--hidden-import", "PyQt6",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "webview.platforms.edgechromium",
        "--hidden-import", "openpyxl",
        "--hidden-import", "rapidfuzz",
        "--hidden-import", "docx",
        "--hidden-import", "jdatetime",
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "bs4",
        "--hidden-import", "scanner",
        "--hidden-import", "scanner.login_window",
        "--hidden-import", "scanner.detail_viewer",
        "--hidden-import", "scanner.auth",
        "--hidden-import", "scanner.store",
        "--hidden-import", "scanner.comparator",
        "--hidden-import", "scanner.database",
        "--hidden-import", "scanner.exporter",
        "--hidden-import", "scanner.word_exporter",
        "--hidden-import", "scanner.worker",
        "--hidden-import", "scanner.declaration_worker",
        "--hidden-import", "services",
        # جمع‌آوری تمپلیت‌ها و فایل‌های دیتای وب‌ویو بدون اسکن ماژول‌های اندروید/مک
        "--collect-data", "webview",
        # حذف ماژول‌های سیستم‌عامل‌های دیگر برای جلوگیری از هشدارهای ناخواسته (مانند اندروید، لینوکس و مک)
        "--exclude-module", "webview.platforms.android",
        "--exclude-module", "webview.platforms.cocoa",
        "--exclude-module", "webview.platforms.gtk",
        "--exclude-module", "webview.platforms.qt",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "torch",
    ]

    # ۴. ست کردن آیکون رسمی برنامه برای فایل EXE
    if ico_path:
        cmd.extend(["--icon", ico_path])
        print(f"[✓] آیکون فایل EXE تنظیم شد: {ico_path}")

    # ۵. افزودن پوشه assets به همراه لوگوها به داخل فایل نهایی
    if os.path.exists(assets_dir):
        cmd.extend(["--add-data", f"{assets_dir};assets"])

    # نقطه ورود اصلی پروژه
    cmd.append("main.py")

    print("\n[+] در حال کامپایل و فشرده‌سازی فایل اجرایی... (لطفاً صبور باشید)")
    result = subprocess.run(cmd, cwd=root_dir)

    if result.returncode == 0:
        exe_path = os.path.join(root_dir, "dist", "LegalScrap.exe")
        print("\n" + "=" * 65)
        print(" [✓] عملیات با موفقیت انجام شد!")
        print(f" فایل نهایی شما آماده است در مسیر:")
        print(f" {exe_path}")
        print("=" * 65)
        print("این تک‌فایل شامل لوگوی اختصاصی بوده و روی هر ویندوز ۱۰ و ۱۱ بدون نیاز به پایتون کار می‌کند.")
    else:
        print("\n[✗] خطا در زمان بیلد فایل اجرایی.")


if __name__ == "__main__":
    run_build()
