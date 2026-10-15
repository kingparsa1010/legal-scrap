"""
پنجره ورود بومی سامانه با استفاده از Edge WebView2 ویندوز (بدون نیاز به کروم یا Playwright)
Native Windows WebView2 Login Window for ipm.ssaa.ir (Zero Playwright / Zero Chrome)
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
from typing import Dict, Any, List
import webview

from scanner import BASE_DIR as ROOT_DIR, DATA_DIR, webview_start_kwargs
from scanner.auth import get_saved_credentials, SIGNIN_URL
from scanner.logger import get_logger

logger = get_logger("login")
SESSION_FILE = os.path.join(DATA_DIR, "session_auth.json")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"


def build_autofill_js(username: str, password: str) -> str:
    """ساخت اسکریپت پر کردن خودکار نام‌کاربری و رمز در فرم ورود سامانه.

    دو گذر مستقل (برای فرم‌های تک‌مرحله‌ای و چندمرحله‌ای):
    - گذر نام‌کاربری هر وقت فیلد کاربری دیده شود، حتی اگر فیلد رمزی در صفحه نباشد.
    - گذر رمز هر وقت فیلد رمز دیده شود.
    چیدمان فرم ورود: ۱ نام کاربری، ۲ رمز عبور، ۳ کد امنیتی کپچا.
    فیلد دارای لیبل کپچا هرگز نوشته نمی‌شود و خالی می‌ماند (فقط فوکوس).
    فیلدهای پرشده دست نمی‌خورند. ساختار فرم هم برای عیب‌یابی برمی‌گردد.
    """
    u = json.dumps(username)
    p = json.dumps(password)
    return f"""
    (function() {{
        try {{
            var docs = [document];
            try {{
                for (var i = 0; i < window.frames.length; i++) {{
                    try {{ docs.push(window.frames[i].document); }} catch(e) {{}}
                }}
            }} catch(e) {{}}
            var CAPTCHA_KW = ['کد امنیتی', 'captcha', 'کپچا', 'کد تصویر', 'عبارت امنیتی',
                'کد نمایش', 'security code', 'تصویر امنیتی', 'حروف تصویر'];
            var USER_KW = ['نام کاربری', 'username', 'user name', 'کدملی', 'کد ملی',
                'national', 'mobile', 'موبایل', 'همراه', 'تلفن', 'phone',
                'کاربر', 'شناسه', 'email', 'پست الکترونیک'];
            var SKIP_TYPES = {{password:1,hidden:1,submit:1,button:1,checkbox:1,radio:1,file:1,image:1,reset:1}};
            function visible(el) {{
                if (!el || el.disabled) return false;
                var t = (el.type || '').toLowerCase();
                if (SKIP_TYPES[t]) return false;
                try {{
                    var r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }} catch(e) {{ return false; }}
            }}
            function hintText(el) {{
                var parts = [];
                try {{
                    if (el.labels && el.labels.length) {{
                        for (var i = 0; i < el.labels.length; i++) {{
                            parts.push(el.labels[i].innerText || '');
                        }}
                    }}
                    var ph = el.getAttribute('placeholder'); if (ph) parts.push(ph);
                    var nm = el.getAttribute('name'); if (nm) parts.push(nm);
                    var id = el.getAttribute('id'); if (id) parts.push(id);
                    if (id && el.ownerDocument) {{
                        var lab = el.ownerDocument.querySelector('label[for="' + id + '"]');
                        if (lab) parts.push(lab.innerText || '');
                    }}
                    var pEl = el.parentElement;
                    if (pEl) parts.push((pEl.innerText || '').slice(0, 150));
                    var prev = el.previousElementSibling;
                    if (prev) parts.push((prev.innerText || '').slice(0, 150));
                }} catch(e) {{}}
                return parts.join(' ');
            }}
            function hasKw(s, kws) {{
                s = s || '';
                for (var i = 0; i < kws.length; i++) {{
                    if (s.indexOf(kws[i]) >= 0) return true;
                }}
                return false;
            }}
            function fire(el) {{
                try {{
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} catch(e) {{}}
            }}
            function setVal(el, v) {{
                // سازگار با safeKeypad و jQuery: اول از طریق jQuery بعد مستقیم
                try {{
                    if (window.jQuery) {{
                        window.jQuery(el).val(v).trigger('input').trigger('change');
                    }} else {{
                        el.value = v; fire(el);
                    }}
                }} catch(e) {{
                    try {{ el.value = v; fire(el); }} catch(e2) {{}}
                }}
                try {{ return el.value === v; }} catch(e) {{ return false; }}
            }}
            function tabIdx(el) {{
                try {{
                    var t = el.getAttribute('tabindex');
                    if (t === null || t === undefined) return 9999;
                    var n = parseInt(t, 10);
                    return isNaN(n) ? 9999 : n;
                }} catch(e) {{ return 9999; }}
            }}
            function byIdSuffix(doc, suffix) {{
                // ID دقیق اول، بعد ID پیشونددار ASP.NET مثل ctl01_UserName؛
                // حتی اگر افزونه صفحه‌کلید مجازی فیلد اصلی را مخفی کرده باشد برمی‌گردد،
                // چون فیلد مخفی هم همراه فرم ارسال می‌شود و پر کردنش بی‌ضرر است.
                try {{
                    var el = doc.getElementById(suffix);
                    if (el) return el;
                    var list = doc.querySelectorAll("input[id$='" + suffix + "']");
                    for (var i = 0; i < list.length; i++) {{
                        return list[i];
                    }}
                }} catch(e) {{}}
                return null;
            }}
            var userVal = {u}, passVal = {p};
            var filledUser = false, filledPass = false, focusedCaptcha = false;
            var autoUser = false, autoPass = false;
            var revertedUser = false, revertedPass = false, fingerprint = [];
            // تشخیص تایپ واقعی کاربر (فقط ایونت‌های مورداعتماد مرورگر)؛
            // فوکوس خودکار صفحه (autofocus) تایپ حساب نمی‌شود تا فیلد نام‌کاربری
            // که با autofocus فوکوس می‌گیرد هم خودکار پر شود.
            if (!window.__ls_kbd) {{
                window.__ls_kbd = true;
                window.__ls_userTyped = false;
                ['keydown', 'input'].forEach(function(ev) {{
                    try {{
                        document.addEventListener(ev, function(e) {{
                            if (e && e.isTrusted) window.__ls_userTyped = true;
                        }}, true);
                    }} catch(x) {{}}
                }});
            }}
            function isFocused(el) {{
                try {{ return document.activeElement === el; }} catch(e) {{ return false; }}
            }}
            function userInteracting() {{
                try {{
                    var ae = document.activeElement;
                    return ae && ae !== document.body && ae.tagName
                        && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName);
                }} catch(e) {{ return false; }}
            }}
            for (var d = 0; d < docs.length; d++) {{
                var doc = docs[d];
                if (d === 0) {{
                    var all = doc.querySelectorAll('input, select, textarea');
                    for (var f = 0; f < all.length && fingerprint.length < 15; f++) {{
                        var fel = all[f];
                        fingerprint.push({{
                            t: fel.type || '', id: fel.id || '',
                            nm: fel.name || '',
                            ph: (fel.getAttribute('placeholder') || '').slice(0, 40)
                        }});
                    }}
                }}
                var idUser = byIdSuffix(doc, 'UserName');
                var idPass = byIdSuffix(doc, 'Password');
                var idCaptcha = byIdSuffix(doc, 'txtCaptcha');
                var pwds = Array.prototype.filter.call(
                    doc.querySelectorAll('input[type="password"]'), visible);
                var pwd = idPass || (pwds.length ? pwds[0] : null);
                var allInputs = Array.prototype.filter.call(
                    doc.querySelectorAll('input'), visible);
                // ترتیب قطعی فرم ورود سامانه: ۱ نام کاربری، ۲ رمز عبور، ۳ کد امنیتی.
                // کپچا: اول با ID واقعی، بعد لیبل، بعد آخرین tabindex؛
                // هرگز در آن چیزی نوشته نمی‌شود و خالی می‌ماند (فقط فوکوس).
                var captchaEl = idCaptcha, ci;
                if (!captchaEl) {{
                    for (ci = 0; ci < allInputs.length; ci++) {{
                        if (hasKw(hintText(allInputs[ci]), CAPTCHA_KW)) {{
                            captchaEl = allInputs[ci]; break;
                        }}
                    }}
                }}
                if (!captchaEl && allInputs.length > 1) {{
                    var lastEl = allInputs[0], lastTi = -1;
                    for (ci = 0; ci < allInputs.length; ci++) {{
                        var ti = tabIdx(allInputs[ci]);
                        if (ti >= lastTi) {{ lastTi = ti; lastEl = allInputs[ci]; }}
                    }}
                    captchaEl = lastEl;
                }}
                // نام‌کاربری: اول با ID واقعی، بعد لیبل، بعد اولین tabindex، بعد اولین در DOM؛
                // هیچ‌وقت فیلد کپچا انتخاب نمی‌شود حتی اگر اول باشد.
                var userEl = (idUser && idUser !== captchaEl) ? idUser : null;
                if (!userEl) {{
                    for (ci = 0; ci < allInputs.length; ci++) {{
                        if (allInputs[ci] !== captchaEl
                            && hasKw(hintText(allInputs[ci]), USER_KW)) {{
                            userEl = allInputs[ci]; break;
                        }}
                    }}
                }}
                if (!userEl) {{
                    var firstEl = null, firstTi = 999999;
                    for (ci = 0; ci < allInputs.length; ci++) {{
                        if (allInputs[ci] === captchaEl) continue;
                        var tj = tabIdx(allInputs[ci]);
                        if (tj < firstTi) {{ firstTi = tj; firstEl = allInputs[ci]; }}
                    }}
                    userEl = firstEl;
                }}
                if (!userEl) {{
                    for (ci = 0; ci < allInputs.length; ci++) {{
                        if (allInputs[ci] !== captchaEl) {{
                            userEl = allInputs[ci]; break;
                        }}
                    }}
                }}
                // فیلد خالی پر می‌شود حتی اگر فوکوس خودکار صفحه رویش باشد؛
                // فقط وقتی کاربر واقعاً تایپ کرده (کلید واقعی) به فیلد دست نمی‌زنیم
                if (userEl && !userEl.value && (!isFocused(userEl) || !window.__ls_userTyped)) {{
                    if (setVal(userEl, userVal)) {{ filledUser = true; autoUser = true; }}
                    else {{ revertedUser = true; }}
                }} else if (userEl && userEl.value) {{ filledUser = true; }}
                // اگر فیلد اصلی مخفی است (صفحه‌کلید مجازی افزونه) و فیلد نمایشی
                // قابل‌مشاهده‌ای هم هست، آن را هم با همان مقدار پر کن تا کاربر ببیند
                if (userEl && filledUser) {{
                    var uHidden = false;
                    try {{ uHidden = !visible(userEl); }} catch(e) {{}}
                    if (uHidden) {{
                        for (var pi = 0; pi < allInputs.length; pi++) {{
                            var cand = allInputs[pi];
                            if (cand !== userEl && cand !== captchaEl
                                && hasKw(hintText(cand), USER_KW)) {{
                                try {{
                                    if (!cand.value && !isFocused(cand)) {{
                                        setVal(cand, userVal);
                                    }}
                                }} catch(e2) {{}}
                                break;
                            }}
                        }}
                    }}
                }}
                // گذر رمز: مستقل از حضور فیلد کاربری (فرم‌های چندمرحله‌ای)
                if (pwd && !pwd.value && (!isFocused(pwd) || !window.__ls_userTyped)) {{
                    if (setVal(pwd, passVal)) {{ filledPass = true; autoPass = true; }}
                    else {{ revertedPass = true; }}
                }} else if (pwd && pwd.value) {{ filledPass = true; }}
                var target = captchaEl;
                if (!target) {{
                    for (var j = 0; j < allInputs.length; j++) {{
                        if (allInputs[j] !== userEl && !allInputs[j].value) {{
                            target = allInputs[j]; break;
                        }}
                    }}
                }}
                // فوکوس کپچا فقط یک‌بار در هر صفحه و فقط تا قبل از تایپ واقعی کاربر؛
                // فوکوس خودکار صفحه مانع نیست، ولی بعد از اولین کلید واقعی دیگر مزاحم نمی‌شویم
                if (target && !window.__ls_userTyped) {{
                    var pageKey = 'ls_' + location.href;
                    if (window.__ls_focus_key !== pageKey) {{
                        window.__ls_focus_key = pageKey;
                        try {{ target.focus(); }} catch(e) {{}}
                    }}
                    focusedCaptcha = true;
                }}
                if (filledUser && filledPass) break;
            }}
            return {{ filledUser: filledUser, filledPass: filledPass, focusedCaptcha: focusedCaptcha, autoUser: autoUser, autoPass: autoPass, revertedUser: revertedUser, revertedPass: revertedPass, fingerprint: fingerprint }};
        }} catch(e) {{ return {{ filledUser: false, filledPass: false, error: String(e) }}; }}
    }})()
    """


def monitor_login(window: webview.Window, result: Dict[str, Any], timeout_seconds: int = 360):
    """حلقه نظارت پس‌زمینه بر وضعیت ورود کاربر به سامانه."""
    start_time = time.time()

    # اطلاعات ثابت ورود برای پر کردن خودکار (کاربر فقط کپچا را وارد می‌کند)
    saved_username, saved_password = get_saved_credentials()
    autofill_js = build_autofill_js(saved_username, saved_password) if saved_username and saved_password else ""
    if not autofill_js:
        logger.warning("فایل account.json یافت نشد؛ پر کردن خودکار نام‌کاربری/رمز غیرفعال است.")
    else:
        logger.info("پر کردن خودکار نام‌کاربری/رمز فعال است.")

    # کمی مهلت اولیه برای بارگذاری صفحه اول
    time.sleep(2)

    fp_logged = False
    user_fill_logged = False
    pass_fill_logged = False
    revert_logged = False
    eval_fail_count = 0

    while time.time() - start_time < timeout_seconds:
        try:
            # پر کردن خودکار نام‌کاربری و رمز در صورت خالی بودن فیلدها
            if autofill_js:
                try:
                    af_res = window.evaluate_js(autofill_js)
                    if isinstance(af_res, dict):
                        if not fp_logged and af_res.get("fingerprint"):
                            logger.info("ساختار فرم ورود سامانه: %s", af_res["fingerprint"])
                            fp_logged = True
                        if af_res.get("autoUser") and not user_fill_logged:
                            logger.info("نام‌کاربری به صورت خودکار پر شد.")
                            user_fill_logged = True
                        elif af_res.get("filledUser") and not user_fill_logged:
                            logger.info("فیلد نام‌کاربری مقدار دارد (احتمالاً دستی وارد شده).")
                            user_fill_logged = True
                        if af_res.get("autoPass") and not pass_fill_logged:
                            logger.info("رمز عبور به صورت خودکار پر شد.")
                            pass_fill_logged = True
                        elif af_res.get("filledPass") and not pass_fill_logged:
                            logger.info("فیلد رمز عبور مقدار دارد (احتمالاً دستی وارد شده).")
                            pass_fill_logged = True
                        if (af_res.get("revertedUser") or af_res.get("revertedPass")) and not revert_logged:
                            logger.warning("مقدار پرشده توسط صفحه برگردانده شد (تداخل افزونه صفحه‌کلید مجازی؟).")
                            revert_logged = True
                except Exception as e:
                    eval_fail_count += 1
                    if eval_fail_count in (1, 5) or eval_fail_count % 30 == 0:
                        logger.warning("اجرای اسکریپت پر کردن خودکار ناموفق بود (%s بار): %s",
                                       eval_fail_count, str(e)[:200])

            # اجرای اسکریپت جاوااسکریپت برای تشخیص ورود
            js_code = """
                (function() {
                    var u = document.querySelector('#userData');
                    if (u && u.innerText && u.innerText.trim().length > 0) {
                        return { logged_in: true, user: u.innerText.trim(), ua: navigator.userAgent };
                    }
                    var d = document.querySelector('#DataList');
                    if (d) {
                        return { logged_in: true, user: 'کاربر سامانه', ua: navigator.userAgent };
                    }
                    return { logged_in: false, user: '', ua: navigator.userAgent };
                })()
            """
            eval_res = window.evaluate_js(js_code)

            if eval_res and isinstance(eval_res, dict) and eval_res.get("logged_in"):
                user_raw = eval_res.get("user", "")
                captured_ua = eval_res.get("ua", "").strip() or USER_AGENT
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

                # ذخیره اطلاعات ورود در فایل نشست همراه با User-Agent اختصاصی موتور وب‌ویو
                payload = {
                    "user_name": user_name,
                    "user_agent": captured_ua,
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "cookies": cookies_dict,
                    "cookie_list": cookie_list
                }
                os.makedirs(os.path.dirname(os.path.abspath(SESSION_FILE)), exist_ok=True)
                with open(SESSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                result["success"] = True
                result["user_name"] = user_name
                result["cookies_count"] = len(cookies_dict)

                # مهلت تثبیت کوکی‌ها در پروفایل مشترک تا پنجره‌های بعدی (مشاهده پرونده)
                # همان نشست را بدون لاگین مجدد ببینند؛ بعد مخفی و نابودی قطعی پنجره
                logger.info("ورود شناسایی شد؛ تثبیت نشست (%s کوکی) و بستن پنجره…", len(cookies_dict))
                time.sleep(3)
                try:
                    window.hide()
                except Exception:
                    pass
                try:
                    window.destroy()
                except Exception:
                    pass
                # نگهبان خروج قطعی: اگر حلقه WebView2 بعد از نابودی گیر کرد،
                # فرآیند را ببند تا والد معطل نماند (فایل نشست قبلاً ذخیره شده)
                def _force_exit():
                    time.sleep(8)
                    try:
                        os._exit(0)
                    except Exception:
                        pass
                threading.Thread(target=_force_exit, daemon=True).start()
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

    # ایجاد پنجره Edge WebView2 بومی ویندوز — از درگاه ورود اختصاصی سامانه
    # تا نشست ساخته‌شده برای همه صفحات داخلی (از جمله پرونده‌ها) معتبر باشد
    window = webview.create_window(
        title="ورود به سامانه مرکز مالکیت معنوی سازمان ثبت اسناد و املاک کشور",
        url=SIGNIN_URL,
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
    # پروفایل مشترک ماندگار: کوکی‌های ورود در همین پروفایل ذخیره می‌شوند تا
    # پنجره‌های مشاهده پرونده/گواهی بعدا بدون لاگین مجدد باز شوند.
    webview.start(**webview_start_kwargs())

    return result


if __name__ == "__main__":
    res = run_login()
    # چاپ نتیجه نهایی به صورت JSON در خروجی استاندارد
    print("\n---RESULT---")
    print(json.dumps(res, ensure_ascii=False))
