"""
سیستم جامع ثبت گزارش‌ها (Logging) با سطوح مختلف (DEBUG, INFO, WARNING, ERROR)
Logging framework with file rotation, console streaming, and Qt UI integration.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
DEFAULT_LOG_FILE = os.path.join(LOGS_DIR, "app.log")

# سطوح لاگ معتبر
LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_current_level_name = "DEBUG"
_file_handler: Optional[RotatingFileHandler] = None
_console_handler: Optional[logging.Handler] = None
_qt_handler = None


class Utf8StreamHandler(logging.StreamHandler):
    """هندلر کنسول با رمزگذاری امن یونیکد روی تمامی محیط‌های ویندوز."""
    def emit(self, record):
        try:
            msg = self.format(record)
            if hasattr(self.stream, "buffer"):
                enc = getattr(self.stream, "encoding", None) or "utf-8"
                data = (msg + self.terminator).encode(enc, errors="backslashreplace")
                self.stream.buffer.write(data)
                self.stream.buffer.flush()
            else:
                self.stream.write(msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)



def setup_logging(level_name: str = "DEBUG") -> logging.Logger:
    """راه‌اندازی اولیه سیستم لاگ با چرخش فایل و کنسول."""
    global _current_level_name, _file_handler, _console_handler

    os.makedirs(LOGS_DIR, exist_ok=True)
    level = LEVELS.get(level_name.upper(), logging.DEBUG)
    _current_level_name = level_name.upper()

    logger = logging.getLogger("legal_scrap")
    logger.setLevel(level)
    logger.propagate = False

    # پاکسازی هندلرهای قبلی در صورت راه‌اندازی مجدد
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | [%(name)s:%(lineno)d] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ۱. هندلر چرخش فایل (حداکثر ۵ مگابایت، ۳ فایل پشتیبان)
    try:
        _file_handler = RotatingFileHandler(
            DEFAULT_LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        _file_handler.setLevel(level)
        _file_handler.setFormatter(formatter)
        logger.addHandler(_file_handler)
    except Exception as e:
        print(f"[Logging] Could not create file handler: {e}")

    # ۲. هندلر خروجی کنسول/ترمینال
    _console_handler = Utf8StreamHandler(sys.stdout)
    _console_handler.setLevel(level)
    _console_handler.setFormatter(formatter)
    logger.addHandler(_console_handler)

    logger.info(f"سیستم لاگ با سطح {level_name.upper()} فعال شد. مسیر فایل لاگ: {DEFAULT_LOG_FILE}")
    return logger


def set_log_level(level_name: str):
    """تغییر پویای سطح لاگ در زمان اجرای برنامه."""
    global _current_level_name, _file_handler, _console_handler
    level = LEVELS.get(level_name.upper(), logging.INFO)
    _current_level_name = level_name.upper()

    logger = logging.getLogger("legal_scrap")
    logger.setLevel(level)

    if _file_handler:
        _file_handler.setLevel(level)
    if _console_handler:
        _console_handler.setLevel(level)

    logger.info(f"سطح ثبت لاگ‌ها به {level_name.upper()} تغییر یافت.")


def get_logger(module_name: str = "") -> logging.Logger:
    """دریافت لاگر اختصاصی هر ماژول."""
    if not module_name:
        return logging.getLogger("legal_scrap")
    return logging.getLogger(f"legal_scrap.{module_name}")


def get_log_file_path() -> str:
    """مسیر کامل فایل لاگ جاری."""
    return os.path.abspath(DEFAULT_LOG_FILE)


def get_logs_dir() -> str:
    """مسیر پوشه فایل‌های لاگ."""
    return os.path.abspath(LOGS_DIR)


def read_latest_logs(max_lines: int = 500) -> str:
    """خواندن آخرین خطوط از فایل لاگ برای نمایش در رابط کاربری."""
    if not os.path.exists(DEFAULT_LOG_FILE):
        return "فایل لاگ هنوز ایجاد نشده است."
    try:
        with open(DEFAULT_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-max_lines:])
    except Exception as e:
        return f"خطا در خواندن فایل لاگ: {e}"


def clear_log_file() -> bool:
    """پاکسازی محتوای فایل لاگ."""
    try:
        if os.path.exists(DEFAULT_LOG_FILE):
            with open(DEFAULT_LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        return True
    except Exception:
        return False

