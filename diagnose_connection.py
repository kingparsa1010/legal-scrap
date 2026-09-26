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
    print(f"  [>] {title}")
    print("=" * 65)


def test_dns_and_socket():
    print_step("Step 1: Checking DNS & Network Socket (Socket & TLS)")
    host = "ipm.ssaa.ir"
    port = 443

    # 1. DNS Resolution
    try:
        ip_list = socket.gethostbyname_ex(host)[2]
        print(f"[+] DNS resolution successful. Resolved IPs: {', '.join(ip_list)}")
        logger.info(f"DNS resolved {host} -> {ip_list}")
    except Exception as e:
        print(f"[-] DNS resolution failed: {e}")
        logger.error(f"DNS resolution failed: {e}")
        return False

    # 2. TCP Socket Connection
    try:
        t0 = time.time()
        sock = socket.create_connection((host, port), timeout=10)
        t_conn = time.time() - t0
        print(f"[+] TCP socket connection to port 443 established ({t_conn:.2f}s)")
        logger.info(f"TCP socket established in {t_conn:.2f}s")
    except Exception as e:
        print(f"[-] TCP connection failed: {e}")
        logger.error(f"TCP socket failed: {e}")
        return False

    # 3. TLS/SSL Handshake
    try:
        context = ssl.create_default_context()
        t0 = time.time()
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            t_ssl = time.time() - t0
            cipher = ssock.cipher()
            version = ssock.version()
            print(f"[+] TLS handshake established (version: {version}, cipher: {cipher[0]}, time: {t_ssl:.2f}s)")
            logger.info(f"TLS handshake success: {version}, {cipher}")
    except Exception as e:
        print(f"[!] Standard TLS handshake warning/bypass: {e}")
        logger.warning(f"TLS handshake warning: {e}")
        return True

    return True


def test_webview2_environment():
    print_step("Step 2: Checking Edge WebView2 & PyWebView Environment")
    try:
        import webview
        print("[+] pywebview library loaded successfully.")
        try:
            import webview.platforms.winforms as wf
            is_chrom = getattr(wf, "is_chromium", False)
            if is_chrom:
                print("[+] Microsoft Edge WebView2 runtime is active and ready.")
                print("    (Independent of Google Chrome / No Playwright required)")
            else:
                print("[!] WebView2 not reported, fallback default engine active.")
        except Exception as e:
            print(f"[*] WebView engine info: {e}")
    except ImportError:
        print("[-] pywebview is not installed. Please run: pip install pywebview")


def test_session_files():
    print_step("Step 3: Checking Session Files & Login Auth")
    has_session = has_saved_session()
    user_name = get_saved_user_name()
    cookies = get_saved_cookies()

    if has_session:
        print(f"[+] Session file found: {SESSION_FILE}")
        print(f"    - Authenticated user: {user_name if user_name else 'System User'}")
        print(f"    - Cookies stored: {len(cookies)}")
        for k in list(cookies.keys())[:5]:
            print(f"      * Cookie: {k}")
    else:
        print(f"[!] No active session file found ({SESSION_FILE} does not exist).")
        print("    Please launch the application and click 'Login to System' first.")

    return has_session


def test_http_session_request():
    print_step("Step 4: Testing Direct HTTP Session Request to SSAA Portal")
    try:
        import requests
        from bs4 import BeautifulSoup
        session = get_authenticated_session()
        print(f"[*] Sending HTTP GET request to {START_URL} ...")
        t0 = time.time()
        resp = session.get(START_URL, timeout=30, verify=False)
        elapsed = time.time() - t0

        print(f"[*] Server Response Summary:")
        print(f"    - HTTP Status Code: {resp.status_code}")
        print(f"    - Response Time: {elapsed:.2f}s")
        print(f"    - Final URL: {resp.url}")

        soup = BeautifulSoup(resp.text, "html.parser")
        user_elem = soup.select_one("#userData")
        table_elem = soup.select_one("#DataList")

        has_user = bool(user_elem and user_elem.get_text(strip=True))
        has_table = bool(table_elem)

        print(f"    - User profile element (#userData): {'[+] Present' if has_user else '[-] Absent'}")
        print(f"    - Declaration table (#DataList): {'[+] Present' if has_table else '[-] Absent'}")

        if has_user:
            print(f"\n[+] Success! Your session is authenticated and valid:")
            print(f"    User info: {user_elem.get_text(strip=True)}")
        elif has_table:
            print("\n[+] Access to DeclarationList table confirmed successfully.")
        else:
            print("\n[!] Saved session was not recognized by the portal (re-login may be required).")

    except Exception as e:
        print(f"[-] HTTP request error: {e}")
        logger.error(f"HTTP test request failed: {e}")


def main():
    print("===============================================================")
    print("  Iranian Intellectual Property (SSAA) Diagnostic Tool")
    print("===============================================================")
    print("Note: Before running this test, please ensure VPN is turned off.")

    net_ok = test_dns_and_socket()
    test_webview2_environment()
    test_session_files()

    if net_ok:
        test_http_session_request()
    else:
        print("\n[-] Network connection to ipm.ssaa.ir failed, aborting remaining tests.")

    print("\n" + "=" * 65)
    print(f"[*] Detailed diagnostic log written to: {get_log_file_path()}")
    print("===============================================================\n")


if __name__ == '__main__':
    main()
