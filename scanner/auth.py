import os
import sys
import json
import re
import time
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional, List
import requests
import urllib3

from scanner.logger import get_logger
from scanner.store import (
    DATA_STORE_PATH, load_store, save_store,
    load_account_store, save_account_store,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("auth")

from scanner import BASE_DIR as ROOT_DIR, DATA_DIR
SESSION_FILE = os.path.join(DATA_DIR, "session_auth.json")
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")
WORD_OUTPUT_PATH = os.path.join(DATA_DIR, "brands.docx")

START_URL = "https://ipm.ssaa.ir/CA/DeclarationList"
# صفحه ورود اختصاصی سامانه؛ سشنی که از این درگاه ساخته می‌شود برای همه صفحات
# داخلی (از جمله CA/Steps) معتبر است، برخلاف ورود از فرم جاسازی‌شده لیست عمومی.
SIGNIN_URL = "https://ipm.ssaa.ir/SignIn"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"

# فایل محلی اطلاعات ثابت ورود (داخل data/ و gitignore شده؛ هرگز در سورس‌کد هاردکد نکنید)
ACCOUNT_FILE = os.path.join(DATA_DIR, "account.json")


def sanitize_account_name(name: str) -> str:
    """تبدیل نام حساب به رشته‌ای ایمن برای نام پوشه در ویندوز."""
    clean = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    return clean if clean else "default_user"


def get_account_dir(user_name: str) -> str:
    """مسیر پوشه اختصاصی حساب کاربری را برمی‌گرداند و در صورت نیاز می‌سازد."""
    folder_name = sanitize_account_name(user_name)
    acc_dir = os.path.join(ACCOUNTS_DIR, folder_name)
    os.makedirs(acc_dir, exist_ok=True)
    return acc_dir


def has_account_saved_data(user_name: str) -> Tuple[bool, int, str]:
    """
    بررسی وجود سوابق اسکن‌شده برای یک حساب:
    خروجی: (آیا داده موجود است؟، تعداد رکوردها، تاریخ آخرین اسکن)
    """
    acc_dir = get_account_dir(user_name)
    meta_file = os.path.join(acc_dir, "meta.json")

    try:
        data = load_account_store(user_name)
        count = len(data)

        last_date = ""
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                last_date = meta.get("last_scan_date", "")

        return count > 0, count, last_date
    except Exception as e:
        logger.warning(f"خطا در بررسی سوابق حساب {user_name}: {e}")
        return False, 0, ""


def save_account_data(user_name: str, store: Dict[str, Any], docx_path: str = ""):
    """ذخیره و همگام‌سازی فایل‌های یک حساب در پوشه اختصاصی آن."""
    if not user_name:
        return

    acc_dir = get_account_dir(user_name)
    acc_meta = os.path.join(acc_dir, "meta.json")

    try:
        # ۱. ذخیره در فضای حساب داخل پایگاه داده واحد
        save_account_store(user_name, store)

        # ۲. کپی فایل Word در صورت وجود
        if docx_path and os.path.exists(docx_path):
            acc_docx = os.path.join(acc_dir, "brands.docx")
            shutil.copy2(docx_path, acc_docx)

        # ۳. ثبت متادیتا
        meta_payload = {
            "user_name": user_name,
            "total_records": len(store),
            "last_scan_date": time.strftime("%Y/%m/%d %H:%M:%S")
        }
        with open(acc_meta, "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"اطلاعات اسکن مربوط به حساب '{user_name}' با {len(store)} رکورد در پوشه {acc_dir} ذخیره گردید.")
    except Exception as e:
        logger.error(f"خطا در ذخیره داده‌های حساب {user_name}: {e}")


def restore_account_data(user_name: str) -> Tuple[Dict[str, Any], str]:
    """بازیابی داده‌های ذخیره‌شده حساب به فایل‌های فعال برنامه."""
    acc_dir = get_account_dir(user_name)
    acc_docx = os.path.join(acc_dir, "brands.docx")

    store = load_account_store(user_name)
    if store:
        save_store(store, DATA_STORE_PATH)

    restored_docx = ""
    if os.path.exists(acc_docx):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(WORD_OUTPUT_PATH)), exist_ok=True)
            shutil.copy2(acc_docx, WORD_OUTPUT_PATH)
            restored_docx = WORD_OUTPUT_PATH
        except Exception as e:
            logger.error(f"خطا در رونوشت brands.docx: {e}")

    logger.info(f"داده‌های حساب '{user_name}' بازیابی شدند ({len(store)} رکورد).")
    return store, restored_docx


def has_saved_session() -> bool:
    """بررسی وجود نشست معتبر ذخیره‌شده در فایل."""
    return os.path.exists(SESSION_FILE)


def get_saved_cookies() -> Dict[str, str]:
    """خواندن کوکی‌های ذخیره‌شده از فایل نشست."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cookies = data.get("cookies", {})
                    if cookies:
                        return cookies
        except Exception as e:
            logger.warning(f"خطا در خواندن session_auth.json: {e}")
    return {}


def get_saved_cookie_list() -> List[Dict[str, Any]]:
    """خواندن فهرست کامل کوکی‌ها همراه با خصوصیات امنیتی."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cookie_list", [])
        except Exception:
            pass
    return []


def save_cookies(cookies: Dict[str, str], user_name: str = ""):
    """ذخیره کوکی‌ها و اطلاعات نشست در فایل."""
    try:
        payload = {
            "user_name": user_name,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cookies": cookies
        }
        os.makedirs(os.path.dirname(os.path.abspath(SESSION_FILE)), exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"اطلاعات نشست کاربر '{user_name}' با {len(cookies)} کوکی ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره سازی نشست: {e}")


def get_saved_user_agent() -> str:
    """خواندن User-Agent اختصاصی ذخیره‌شده از نشست مرورگر WebView2."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                ua = data.get("user_agent")
                if ua:
                    return ua
        except Exception:
            pass
    return USER_AGENT


def get_authenticated_session() -> requests.Session:
    """ایجاد یا بازیابی نشست requests با کوکی‌های ذخیره‌شده."""
    session = requests.Session()
    ua = get_saved_user_agent()
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fa,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Referer": START_URL,
    })

    # ابتدا کوکی‌های ساختاریافته کامل را بارگذاری کنیم
    cookie_list = get_saved_cookie_list()
    if cookie_list:
        for c in cookie_list:
            session.cookies.set(
                name=c.get("name", ""),
                value=c.get("value", ""),
                domain=c.get("domain") or "ipm.ssaa.ir",
                path=c.get("path") or "/",
                secure=bool(c.get("secure", False))
            )
    else:
        # در غیر این صورت دیکشنری ساده کوکی‌ها
        cookies = get_saved_cookies()
        for k, v in cookies.items():
            session.cookies.set(k, v, domain="ipm.ssaa.ir", path="/")

    return session


def get_saved_user_name() -> str:
    """خواندن نام کاربر از نشست جاری."""
    if not os.path.exists(SESSION_FILE):
        return ""
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("user_name", "")
    except Exception:
        return ""


def get_saved_credentials() -> Tuple[str, str]:
    """خواندن نام‌کاربری و رمز ثابت از فایل محلی data/account.json.

    خروجی: (username, password)؛ در صورت نبود فایل، رشته‌های خالی.
    """
    for path in (ACCOUNT_FILE, os.path.join(ROOT_DIR, "account.json")):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                username = str(data.get("username", "") or "").strip()
                password = str(data.get("password", "") or "")
                if username and password:
                    return username, password
        except Exception as e:
            logger.warning(f"خطا در خواندن {path}: {e}")
    return "", ""


def save_credentials(username: str, password: str) -> bool:
    """ذخیره نام‌کاربری و رمز ثابت در فایل محلی gitignore شده."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(ACCOUNT_FILE)), exist_ok=True)
        with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
            json.dump({"username": username.strip(), "password": password}, f, ensure_ascii=False, indent=2)
        logger.info("اطلاعات ثابت ورود در account.json ذخیره شد.")
        return True
    except Exception as e:
        logger.error(f"خطا در ذخیره اطلاعات ورود: {e}")
        return False


def check_session_alive(session: Optional[requests.Session] = None) -> Tuple[bool, str]:
    """بررسی وجود نام کاربر در فایل نشست."""
    if not has_saved_session():
        return False, "no_session"

    user_name = get_saved_user_name()
    if user_name:
        return True, user_name
    return True, "کاربر سامانه"


def validate_saved_session(timeout: int = 20) -> Tuple[str, str]:
    """اعتبارسنجی واقعی نشست ذخیره‌شده با سرور سامانه (بدون نیاز به رمز).

    خروجی: (وضعیت، پیام)
    - "valid": نشست معتبر است؛ لاگین مجدد لازم نیست.
    - "expired": سرور نشست را قبول نکرد؛ باید دوباره وارد شد.
    - "unknown": خطای شبکه/سرور؛ نمی‌توان نظر داد و سشن حفظ می‌شود.
    """
    if not has_saved_session():
        return "expired", "نشستی ذخیره نشده است."

    session = get_authenticated_session()
    try:
        resp = session.get(START_URL, timeout=timeout, verify=False)
    except Exception as e:
        logger.warning(f"بررسی نشست ممکن نشد (خطای شبکه): {e}")
        return "unknown", "عدم دسترسی به سامانه جهت بررسی (اینترنت/VPN را بررسی کنید)."

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        user_elem = soup.select_one("#userData")
        has_user = bool(user_elem and user_elem.get_text(strip=True))
        has_table = bool(soup.select_one("#DataList"))
    except Exception:
        has_user, has_table = False, False

    lowered_url = str(getattr(resp, "url", "")).lower()
    redirected_to_login = any(k in lowered_url for k in ("signin", "login", "account"))

    if has_user or has_table:
        return "valid", get_saved_user_name() or "کاربر سامانه"
    if redirected_to_login or resp.status_code in (401, 403):
        logger.info("نشست ذخیره‌شده توسط سامانه معتبر شناخته نشد (منقضی شده).")
        return "expired", "نشست قبلی منقضی شده است؛ لطفاً دوباره وارد شوید."
    if resp.status_code >= 500:
        logger.warning(f"سرور سامانه خطای {resp.status_code} داد؛ وضعیت نشست نامشخص.")
        return "unknown", f"سرور سامانه فعلاً پاسخ‌گو نیست (کد {resp.status_code})."
    logger.info("نشست معتبر تشخیص داده نشد و به صفحه ورود هدایت نشده؛ وضعیت نامشخص.")
    return "unknown", "وضعیت نشست مشخص نشد؛ سشن حفظ شد."


def clear_active_session():
    """
    حذف توکن‌ها و نشست جاری در هنگام بستن برنامه یا خروج از حساب.
    اطلاعات آرشیو شده هر حساب در پوشه accounts/ دست‌نخورده باقی می‌ماند.
    پروفایل مشترک WebView2 هم پاک می‌شود تا نشست مرورگریِ پنجره‌های مشاهده
    با نشست اسکرپر ناسازگار نماند (در غیر این صورت جزئیات بدون لاگین باز می‌شد
    ولی اسکن نیاز به ورود داشت). حذف best-effort است چون ممکن است پنجره‌ای باز باشد.
    """
    for fname in ["session_auth.json", "session_storage.json"]:
        for base in [DATA_DIR, ROOT_DIR]:
            p = os.path.join(base, fname)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    logger.info(f"فایل توکن موقت {p} هنگام خروج پاکسازی شد.")
                except Exception as e:
                    logger.warning(f"عدم امکان حذف {p}: {e}")
    try:
        from scanner import WEBVIEW_PROFILE_DIR
        if os.path.isdir(WEBVIEW_PROFILE_DIR):
            shutil.rmtree(WEBVIEW_PROFILE_DIR, ignore_errors=True)
            logger.info("پروفایل مشترک WebView2 هنگام خروج پاکسازی شد.")
    except Exception as e:
        logger.warning(f"عدم امکان پاکسازی پروفایل WebView2: {e}")


def clear_saved_session():
    """حذف دستی نشست ذخیره‌شده."""
    clear_active_session()


def _read_session_if_fresh(since_mtime: float) -> Tuple[str, int]:
    """خواندن نشست فقط اگر بعد از شروع پنجره ورود نوشته شده باشد.

    چون نشست‌ها بین اجراها حفظ می‌شوند، وجود فایل به‌تنهایی به معنی ورود تازه نیست.
    خروجی: (user_name, cookie_count) یا ("", 0).
    """
    try:
        if not os.path.exists(SESSION_FILE):
            return "", 0
        if os.path.getmtime(SESSION_FILE) <= since_mtime:
            return "", 0
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        cookies = data.get("cookies", {}) or {}
        if not cookies:
            return "", 0
        return data.get("user_name", "کاربر سامانه") or "کاربر سامانه", len(cookies)
    except Exception as e:
        logger.error(f"خطا در خواندن فایل نشست پس از ورود: {e}")
        return "", 0


def perform_browser_login(timeout_seconds: int = 360, on_status_update=None) -> Tuple[bool, str]:
    """
    باز کردن پنجره ورود بومی با استفاده از Microsoft Edge WebView2 ویندوز.
    (کاملاً مستقل از Playwright و بدون نیاز به نصب مرورگر Google Chrome)
    """
    msg = "در حال باز کردن پنجره ورود با موتور وب‌ویوی بومی ویندوز (Edge WebView2)..."
    logger.info(msg)
    if on_status_update:
        on_status_update(msg)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if ROOT_DIR not in env.get("PYTHONPATH", "").split(os.pathsep):
        env["PYTHONPATH"] = f"{ROOT_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}".strip(os.pathsep)

    # تعیین دستور فرآیند فرزند برای اجرای پنجره ورود
    if getattr(sys, 'frozen', False):
        # در فایل اجرایی کامپایل‌شده (EXE):
        # مستقیماً خود فایل اجرایی با سوییچ --login فراخوانی می‌شود
        cmd = [sys.executable, '--login']
    else:
        # در حالت سورس پایتون:
        main_script = os.path.join(ROOT_DIR, "main.py")
        login_script = os.path.join(ROOT_DIR, "scanner", "login_window.py")
        if os.path.exists(main_script):
            cmd = [sys.executable, main_script, '--login']
        elif os.path.exists(login_script):
            cmd = [sys.executable, login_script]
        else:
            cmd = [sys.executable, "-m", "scanner.login_window"]

    try:
        logger.info(f"اجرای فرآیند پنجره لاگین: {' '.join(cmd)}")
        try:
            session_before = os.path.getmtime(SESSION_FILE)
        except OSError:
            session_before = 0.0
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=ROOT_DIR,
            env=env
        )

        stdout, stderr = proc.communicate(timeout=timeout_seconds)

        if proc.returncode != 0 and not os.path.exists(SESSION_FILE):
            logger.warning(f"خطا در اجرای پنجره ورود (کد {proc.returncode}): {stderr}")
            err_msg = stderr.strip() if stderr.strip() else f"کد خروجی: {proc.returncode}"
            return False, f"خطا در باز کردن پنجره ورود: {err_msg[:200]}"

        # موفقیت فقط وقتی که فایل نشست در همین اجرا تازه نوشته شده باشد
        # (فایل قدیمیِ باقی‌مانده از اجراهای قبل موفقیت حساب نمی‌شود)
        user_name, cookie_count = _read_session_if_fresh(session_before)
        if cookie_count:
            logger.info(f"ورود با موفقیت انجام شد: کاربر='{user_name}'، تعداد کوکی‌ها={cookie_count}")
            return True, user_name

        # در صورتی که کاربری ذخیره نشده باشد
        return False, "پنجره ورود بدون لاگین بسته شد یا مهلت زمانی به پایان رسید."

    except subprocess.TimeoutExpired:
        logger.warning("مهلت زمان ورود کاربر به پایان رسید.")
        try:
            proc.kill()
        except Exception:
            pass
        try:
            user_name, cookie_count = _read_session_if_fresh(session_before)
        except Exception:
            user_name, cookie_count = "", 0
        if cookie_count:
            logger.info(f"ورود با موفقیت انجام شد (پس از پایان مهلت): کاربر='{user_name}'")
            return True, user_name
        return False, "مهلت زمان ورود به پایان رسید."
    except Exception as e:
        logger.critical(f"خطا در فرآیند ورود: {e}")
        return False, f"خطا در فرآیند ورود: {e}"



