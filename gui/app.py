"""
رابط کاربری دسکتاپ سامانه پایش و استخراج علائم تجاری
Persian RTL Desktop GUI — light/dark/system themes, responsive layout
"""
import sys
import os
import re
import subprocess
import time
import webbrowser
from typing import List, Optional, Tuple, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QGroupBox, QSpinBox,
    QMessageBox, QFrame, QScrollArea, QSizePolicy, QAbstractItemView,
    QSplitter, QStyleFactory, QDialog, QPlainTextEdit, QMenu, QStackedWidget,
    QRadioButton, QButtonGroup, QStyledItemDelegate, QStyleOptionViewItem
)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal, QTimer, QRect, QPoint, QEvent, QModelIndex, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor, QCursor, QPalette, QPainter, QPen, QBrush, QIcon


from scanner import DATA_DIR
from scanner.logger import (
    setup_logging, set_log_level, get_logger,
    get_log_file_path, read_latest_logs, clear_log_file
)
from scanner.client import SSAAClient
from scanner.worker import ScanWorker
from scanner.auth import (
    perform_browser_login,
    get_saved_user_name, has_account_saved_data, has_saved_session
)
from scanner.declaration_worker import DeclarationScrapeWorker, WORD_OUTPUT_PATH
from scanner.parser import is_finally_registered, to_english_digits, ensure_record_fields
from scanner.store import (
    DATA_STORE_PATH, load_store, save_store, load_class5_store, save_class5_store, store_counts
)
from scanner.comparator import compare_default_stores
from scanner.database import (
    init_db, add_watchlist_item,
    save_search_history, get_search_history
)
from scanner.exporter import export_scan_to_excel, DEFAULT_REPORTS_DIR
from services.search_request_service import build_search_request, SearchRequestError

logger = get_logger("gui")




# ----------------------------------------------------------------------
# Themes
# ----------------------------------------------------------------------
LIGHT_QSS = """
QMainWindow, QWidget#Central { background: #EEF1F5; }
QWidget { font-family: Tahoma, Vazirmatn, "Segoe UI"; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QWidget#SidebarInner { background: transparent; }

QFrame#Header { background: white; border: 1px solid #E2E8F0; border-radius: 12px; }
QLabel#AppTitle { font-size: 15pt; font-weight: bold; color: #0F172A; background: transparent; }
QLabel#AppSubtitle { font-size: 9pt; color: #64748B; background: transparent; }
QLabel#StatePill { font-size: 9pt; font-weight: bold; padding: 6px 14px; border-radius: 14px;
    background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
QLabel#StatePill[mood="running"] { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
QLabel#StatePill[mood="success"] { background: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
QLabel#StatePill[mood="error"]   { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }

QGroupBox#Card { background: white; border: 1px solid #E2E8F0; border-radius: 12px;
    margin-top: 14px; padding-top: 10px; font-weight: bold; color: #0F172A; }
QGroupBox#Card::title { subcontrol-origin: margin; subcontrol-position: top right;
    right: 14px; top: 2px; padding: 2px 10px; background: #0F172A; color: white;
    border-radius: 8px; font-size: 9pt; }
QGroupBox#SubCard { background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 10px;
    margin-top: 10px; font-weight: bold; color: #334155; }
QGroupBox#SubCard::title { subcontrol-origin: margin; subcontrol-position: top right;
    right: 10px; padding: 0 8px; color: #475569; background: transparent; }

QLabel { color: #0F172A; background: transparent; }
QLabel#Hint { color: #64748B; font-size: 8.5pt; background: transparent; }
QLabel#FieldLabel { color: #334155; font-size: 9pt; font-weight: bold; background: transparent; }
QLabel#StatValue { font-size: 18pt; font-weight: bold; background: transparent; }
QLabel#StatCaption { font-size: 8.5pt; color: #64748B; background: transparent; }
QLabel#EmptyState { color: #64748B; font-size: 10pt; background: transparent; padding: 18px; }

QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #CBD5E1;
    border-radius: 8px; padding: 8px 10px; font-size: 9.5pt; color: #0F172A;
    selection-background-color: #DBEAFE; selection-color: #0F172A; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1.5px solid #2563EB; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #F1F5F9; color: #94A3B8; }
QComboBox QAbstractItemView { background: white; color: #0F172A; selection-background-color: #EFF6FF; selection-color: #0F172A; }
QSpinBox::up-button, QSpinBox::down-button { background: #F1F5F9; border: none; width: 24px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #E2E8F0; }
QLineEdit#CaptchaInput { font-size: 14pt; font-weight: bold; letter-spacing: 6px; }

QPushButton { border-radius: 8px; padding: 8px 14px; font-size: 9.5pt; }
QPushButton#Primary { background: #15803D; color: white; font-weight: bold; font-size: 11pt; padding: 12px; border: none; }
QPushButton#Primary:hover { background: #166534; }
QPushButton#Primary:disabled { background: #CBD5E1; color: #F8FAFC; }
QPushButton#Secondary { background: white; color: #0F172A; border: 1px solid #CBD5E1; }
QPushButton#Secondary:hover { background: #F8FAFC; border-color: #94A3B8; }
QPushButton#Secondary:disabled { color: #94A3B8; background: #F1F5F9; }
QPushButton#Accent { background: #1D4ED8; color: white; font-weight: bold; border: none; }
QPushButton#Accent:hover { background: #1E40AF; }
QPushButton#Accent:disabled { background: #CBD5E1; color: #F8FAFC; }
QPushButton#TodayBtn { background: #0D9488; color: white; font-weight: bold; font-size: 9.5pt; padding: 10px 8px; border: none; }
QPushButton#TodayBtn:hover { background: #0F766E; }
QPushButton#TodayBtn:disabled { background: #CBD5E1; color: #F8FAFC; }
QPushButton#SearchBtn { background: #2563EB; color: white; font-weight: bold; font-size: 9.5pt; padding: 10px 8px; border: none; }
QPushButton#SearchBtn:hover { background: #1D4ED8; }
QPushButton#SearchBtn:disabled { background: #CBD5E1; color: #F8FAFC; }
QPushButton#ClearBtn { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; font-weight: bold; font-size: 9pt; padding: 7px 10px; }
QPushButton#ClearBtn:hover { background: #FEE2E2; border-color: #F87171; color: #B91C1C; }
QPushButton#ClearBtn:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
QPushButton#Ghost { background: transparent; border: none; color: #2563EB; font-weight: bold; }
QPushButton#Ghost:hover { background: #EFF6FF; }
QPushButton#RowBtn { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;
    padding: 5px 10px; font-size: 8.5pt; border-radius: 6px; }
QPushButton#RowBtn:hover { background: #DBEAFE; }
QPushButton#RowBtn:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
QPushButton#CopyBtn { background: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 9.5pt; }
QPushButton#CopyBtn:hover { background: #E2E8F0; color: #0F172A; }
QPushButton#CopyBtn:disabled { background: #F1F5F9; color: #CBD5E1; border-color: #E2E8F0; }

QLabel#CaptchaImage { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; color: #64748B; font-size: 9pt; }
QProgressBar { background: #E2E8F0; border: none; border-radius: 5px; height: 10px; text-align: center; font-size: 8pt; color: #475569; }
QProgressBar::chunk { background: #15803D; border-radius: 5px; }
QFrame#Stat { background: white; border: 1px solid #E2E8F0; border-radius: 12px; }

QTabWidget::pane { background: white; border: 1px solid #E2E8F0; border-radius: 0 0 12px 12px; }
QTabBar::tab { background: #E2E8F0; color: #475569; padding: 10px 22px; margin-left: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: bold; font-size: 9.5pt; }
QTabBar::tab:selected { background: white; color: #0F172A; border: 1px solid #E2E8F0; border-bottom: none; }
QTableWidget { background: white; border: 1px solid #CBD5E1; border-radius: 8px; gridline-color: #CBD5E1;
    alternate-background-color: #F8FAFC; font-size: 9.5pt; color: #0F172A; }
QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #CBD5E1; border-right: 1px solid #CBD5E1; }
QTableWidget::item:selected { background: #DBEAFE; color: #1E3A8A; }
QHeaderView::section { background: #F1F5F9; color: #1E293B; font-weight: bold;
    padding: 9px 8px; border: 1px solid #CBD5E1; border-top: none; border-bottom: 2px solid #64748B; font-size: 9.5pt; }

QScrollBar:vertical { background: #F1F5F9; width: 12px; margin: 0; border: none; border-radius: 6px; }
QScrollBar::handle:vertical { background: #CBD5E1; min-height: 30px; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #94A3B8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; border: none; }
QScrollBar:horizontal { background: #F1F5F9; height: 12px; border: none; border-radius: 6px; }
QScrollBar::handle:horizontal { background: #CBD5E1; min-width: 30px; border-radius: 6px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; background: none; border: none; }

QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 6px; }

QMessageBox { background: white; }
QMessageBox QLabel { color: #0F172A; background: transparent; font-size: 10pt; }
QToolTip { background: #0F172A; color: white; border: none; padding: 6px 8px; font-size: 9pt; }
"""

DARK_QSS = """
QMainWindow, QWidget#Central { background: #0B1220; }
QWidget { font-family: Tahoma, Vazirmatn, "Segoe UI"; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QWidget#SidebarInner { background: transparent; }

QFrame#Header { background: #111C33; border: 1px solid #24334F; border-radius: 12px; }
QLabel#AppTitle { font-size: 15pt; font-weight: bold; color: #F1F5F9; background: transparent; }
QLabel#AppSubtitle { font-size: 9pt; color: #94A3B8; background: transparent; }
QLabel#StatePill { font-size: 9pt; font-weight: bold; padding: 6px 14px; border-radius: 14px;
    background: #1E293B; color: #CBD5E1; border: 1px solid #334155; }
QLabel#StatePill[mood="running"] { background: #1E3A8A; color: #DBEAFE; border: 1px solid #3B82F6; }
QLabel#StatePill[mood="success"] { background: #14532D; color: #BBF7D0; border: 1px solid #22C55E; }
QLabel#StatePill[mood="error"]   { background: #7F1D1D; color: #FECACA; border: 1px solid #EF4444; }

QGroupBox#Card { background: #111C33; border: 1px solid #24334F; border-radius: 12px;
    margin-top: 14px; padding-top: 10px; font-weight: bold; color: #F1F5F9; }
QGroupBox#Card::title { subcontrol-origin: margin; subcontrol-position: top right;
    right: 14px; top: 2px; padding: 2px 10px; background: #38BDF8; color: #082F49;
    border-radius: 8px; font-size: 9pt; }
QGroupBox#SubCard { background: #0F2440; border: 1px dashed #33507A; border-radius: 10px;
    margin-top: 10px; font-weight: bold; color: #CBD5E1; }
QGroupBox#SubCard::title { subcontrol-origin: margin; subcontrol-position: top right;
    right: 10px; padding: 0 8px; color: #94A3B8; background: transparent; }

QLabel { color: #E2E8F0; background: transparent; }
QLabel#Hint { color: #94A3B8; font-size: 8.5pt; background: transparent; }
QLabel#FieldLabel { color: #CBD5E1; font-size: 9pt; font-weight: bold; background: transparent; }
QLabel#StatValue { font-size: 18pt; font-weight: bold; background: transparent; }
QLabel#StatCaption { font-size: 8.5pt; color: #94A3B8; background: transparent; }
QLabel#EmptyState { color: #94A3B8; font-size: 10pt; background: transparent; padding: 18px; }

QLineEdit, QComboBox, QSpinBox { background: #0F2440; border: 1px solid #33507A;
    border-radius: 8px; padding: 8px 10px; font-size: 9.5pt; color: #F1F5F9;
    selection-background-color: #1D4ED8; selection-color: white; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1.5px solid #38BDF8; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #1E293B; color: #64748B; }
QComboBox QAbstractItemView { background: #111C33; color: #F1F5F9; selection-background-color: #1D4ED8; }
QSpinBox::up-button, QSpinBox::down-button { background: #1E3A5F; border: none; width: 24px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #2A4A73; }
QLineEdit#CaptchaInput { font-size: 14pt; font-weight: bold; letter-spacing: 6px; }

QPushButton { border-radius: 8px; padding: 8px 14px; font-size: 9.5pt; }
QPushButton#Primary { background: #16A34A; color: white; font-weight: bold; font-size: 11pt; padding: 12px; border: none; }
QPushButton#Primary:hover { background: #15803D; }
QPushButton#Primary:disabled { background: #334155; color: #64748B; }
QPushButton#Secondary { background: #1E293B; color: #F1F5F9; border: 1px solid #475569; }
QPushButton#Secondary:hover { background: #273449; border-color: #64748B; }
QPushButton#Secondary:disabled { color: #64748B; background: #1E293B; }
QPushButton#Accent { background: #2563EB; color: white; font-weight: bold; border: none; }
QPushButton#Accent:hover { background: #1D4ED8; }
QPushButton#Accent:disabled { background: #334155; color: #64748B; }
QPushButton#TodayBtn { background: #0D9488; color: white; font-weight: bold; font-size: 9.5pt; padding: 10px 8px; border: none; }
QPushButton#TodayBtn:hover { background: #14B8A6; }
QPushButton#TodayBtn:disabled { background: #334155; color: #64748B; }
QPushButton#SearchBtn { background: #2563EB; color: white; font-weight: bold; font-size: 9.5pt; padding: 10px 8px; border: none; }
QPushButton#SearchBtn:hover { background: #3B82F6; }
QPushButton#SearchBtn:disabled { background: #334155; color: #64748B; }
QPushButton#ClearBtn { background: #2A1215; color: #F87171; border: 1px solid #7F1D1D; font-weight: bold; font-size: 9pt; padding: 7px 10px; }
QPushButton#ClearBtn:hover { background: #451A1D; border-color: #EF4444; color: #FCA5A5; }
QPushButton#ClearBtn:disabled { background: #1E293B; color: #64748B; border-color: #334155; }
QPushButton#Ghost { background: transparent; border: none; color: #7DD3FC; font-weight: bold; }
QPushButton#Ghost:hover { background: #16283F; }
QPushButton#RowBtn { background: #16283F; color: #7DD3FC; border: 1px solid #33507A;
    padding: 5px 10px; font-size: 8.5pt; border-radius: 6px; }
QPushButton#RowBtn:hover { background: #1E3A5F; }
QPushButton#RowBtn:disabled { background: #1E293B; color: #64748B; border-color: #334155; }
QPushButton#CopyBtn { background: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 9.5pt; }
QPushButton#CopyBtn:hover { background: #334155; color: #F8FAFC; }
QPushButton#CopyBtn:disabled { background: #0F172A; color: #475569; border-color: #1E293B; }

QLabel#CaptchaImage { background: #F8FAFC; border: 1px solid #33507A; border-radius: 10px; color: #475569; font-size: 9pt; }
QProgressBar { background: #1E293B; border: none; border-radius: 5px; height: 10px; text-align: center; font-size: 8pt; color: #CBD5E1; }
QProgressBar::chunk { background: #22C55E; border-radius: 5px; }
QFrame#Stat { background: #111C33; border: 1px solid #24334F; border-radius: 12px; }

QTabWidget::pane { background: #111C33; border: 1px solid #24334F; border-radius: 0 0 12px 12px; }
QTabBar::tab { background: #1E293B; color: #94A3B8; padding: 10px 22px; margin-left: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: bold; font-size: 9.5pt; }
QTabBar::tab:selected { background: #111C33; color: #F1F5F9; border: 1px solid #24334F; border-bottom: none; }
QTableWidget { background: #0B132B; border: 1px solid #33507A; border-radius: 8px; gridline-color: #2D4668;
    alternate-background-color: #101B34; font-size: 9.5pt; color: #F1F5F9; }
QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #243B5A; border-right: 1px solid #243B5A; }
QTableWidget::item:selected { background: #1D4ED8; color: white; }
QHeaderView::section { background: #16283F; color: #F1F5F9; font-weight: bold;
    padding: 9px 8px; border: 1px solid #33507A; border-top: none; border-bottom: 2px solid #38BDF8; font-size: 9.5pt; }

QScrollBar:vertical { background: #111C33; width: 12px; margin: 0; border: none; border-radius: 6px; }
QScrollBar::handle:vertical { background: #33507A; min-height: 30px; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #475569; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; border: none; }
QScrollBar:horizontal { background: #111C33; height: 12px; border: none; border-radius: 6px; }
QScrollBar::handle:horizontal { background: #33507A; min-width: 30px; border-radius: 6px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; background: none; border: none; }

QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 6px; }

QMessageBox { background: #111C33; }
QMessageBox QLabel { color: #F1F5F9; background: transparent; font-size: 10pt; }
QToolTip { background: #F1F5F9; color: #0F172A; border: none; padding: 6px 8px; font-size: 9pt; }
"""


def build_palette(dark: bool) -> QPalette:
    pal = QPalette()
    if dark:
        pal.setColor(QPalette.ColorRole.Window, QColor("#0B1220"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#F1F5F9"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#111C33"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#0F1D33"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#F1F5F9"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#1E293B"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#F1F5F9"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#1D4ED8"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#F1F5F9"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#0F172A"))
    else:
        pal.setColor(QPalette.ColorRole.Window, QColor("#EEF1F5"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFC"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#DBEAFE"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0F172A"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    return pal


def detect_system_dark(app: QApplication) -> bool:
    try:
        hints = app.styleHints()
        if hasattr(hints, "colorScheme"):
            return hints.colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        pass
    # fallback: lightness of window color
    try:
        c = app.palette().color(QPalette.ColorRole.Window)
        return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) < 128
    except Exception:
        return False


class NumericTableWidgetItem(QTableWidgetItem):
    """آیتم جدول عددی برای مرتب‌سازی صحیح مقادیر عددی (جلوگیری از قرارگیری ۱۷ بین ۱۶۹ و ۱۷۰)."""
    def __init__(self, value: int | float, text: str = None):
        super().__init__(str(value) if text is None else text)
        self._val = float(value) if value is not None else 0.0
        self.setData(Qt.ItemDataRole.UserRole, self._val)

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            other_data = other.data(Qt.ItemDataRole.UserRole)
            if other_data is not None:
                try:
                    return self._val < float(other_data)
                except (ValueError, TypeError):
                    pass
        return super().__lt__(other)


def _parse_jalali_key(date_raw: str) -> tuple:
    """تبدیل رشته تاریخ به کلید قابل مقایسه؛ هر دو فرمت YMD و DMY."""
    en = to_english_digits(str(date_raw or ''))
    nums = [int(n) for n in re.findall(r'\d+', en)]
    y, m, d, hh, mm = 0, 0, 0, 0, 0
    if len(nums) >= 3:
        a, b, c = nums[0], nums[1], nums[2]
        if a > 31 and c <= 31:
            y, m, d = a, b, c
        elif c > 31 and a <= 31:
            d, m, y = a, b, c
        elif a >= 1000:
            y, m, d = a, b, c
        elif c >= 1000:
            d, m, y = a, b, c
        else:
            y, m, d = a, b, c
        if len(nums) >= 5:
            hh, mm = nums[3], nums[4]
        elif len(nums) == 4:
            hh = nums[3]
    elif len(nums) == 2:
        a, b = nums[0], nums[1]
        if a >= 1000:
            y, m = a, b
        elif b >= 1000:
            m, y = a, b
        else:
            y, m = a, b
    elif len(nums) == 1:
        y = nums[0]
    return (y, m, d, hh, mm)


class DateTableWidgetItem(QTableWidgetItem):
    """آیتم تاریخ شمسی برای مرتب‌سازی تقویمی با کلیک روی هدر (هر دو فرمت روز/ماه/سال و سال/ماه/روز)."""
    def __init__(self, date_text: str):
        super().__init__(str(date_text or "—"))
        self._key = _parse_jalali_key(date_text)
        self.setData(Qt.ItemDataRole.UserRole, self._key)
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            other_data = other.data(Qt.ItemDataRole.UserRole)
            if isinstance(other_data, tuple):
                return self._key < other_data
        return super().__lt__(other)


class LoginWorker(QThread):

    status_updated = pyqtSignal(str)
    login_finished = pyqtSignal(bool, str)

    def run(self):
        success, user_name = perform_browser_login(
            timeout_seconds=360,
            on_status_update=lambda msg: self.status_updated.emit(msg)
        )
        self.login_finished.emit(success, user_name)


class SessionCheckWorker(QThread):
    """بررسی پس‌زمینه اعتبار نشست ذخیره‌شده با سرور، بدون انجماد رابط کاربری."""
    session_checked = pyqtSignal(str, str)  # status, message

    def run(self):
        try:
            from scanner.auth import validate_saved_session
            status, msg = validate_saved_session()
            self.session_checked.emit(status, msg)
        except Exception as e:
            self.session_checked.emit("unknown", str(e))


class ComparisonWorker(QThread):
    """نخ پس‌زمینه اجرای مقایسه دو فایل داده بدون انجماد رابط کاربری."""
    comparison_finished = pyqtSignal(list)
    comparison_failed = pyqtSignal(str)

    def run(self):
        try:
            matches = compare_default_stores()
            self.comparison_finished.emit(matches)
        except Exception as e:
            self.comparison_failed.emit(str(e))


class CaptchaWorker(QThread):
    """نخ پس‌زمینه دریافت تصویر کد امنیتی (کپچا) بدون انجماد رابط کاربری."""
    captcha_loaded = pyqtSignal(bytes)
    captcha_failed = pyqtSignal(str)

    def __init__(self, client: SSAAClient, parent=None):
        super().__init__(parent)
        self.client = client

    def run(self):
        try:
            img_bytes = self.client.get_captcha_image()
            if img_bytes:
                self.captcha_loaded.emit(img_bytes)
            else:
                err = getattr(self.client, "last_error", "")
                self.captcha_failed.emit(err)
        except Exception as e:
            self.captcha_failed.emit(str(e))


class LogViewerDialog(QDialog):
    """پنجره مشاهده زنده و مدیریت فایل گزارش‌ها."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("گزارش‌ها و رویدادهای سیستم")
        self.resize(920, 560)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # نوار ابزار بالا
        top_layout = QHBoxLayout()
        lbl_info = QLabel(f"مسیر فایل گزارش‌ها: {get_log_file_path()}", self)
        lbl_info.setStyleSheet("color: #64748B; font-size: 8.5pt;")
        top_layout.addWidget(lbl_info)
        top_layout.addStretch()

        btn_refresh = QPushButton("🔄 به‌روزرسانی", self)
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.clicked.connect(self.refresh_logs)
        top_layout.addWidget(btn_refresh)

        btn_copy = QPushButton("📋 کپی متن", self)
        btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy.clicked.connect(self.copy_to_clipboard)
        top_layout.addWidget(btn_copy)

        btn_clear = QPushButton("🗑️ پاکسازی گزارش‌ها", self)
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self.clear_logs)
        top_layout.addWidget(btn_clear)

        btn_open = QPushButton("📂 باز کردن فایل", self)
        btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open.clicked.connect(self.open_external)
        top_layout.addWidget(btn_open)

        layout.addLayout(top_layout)

        # جعبه متنی لاگ‌ها
        self.text_area = QPlainTextEdit(self)
        self.text_area.setReadOnly(True)
        self.text_area.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.text_area.setFont(QFont("Consolas", 9))
        self.text_area.setStyleSheet(
            "background: #0F172A; color: #E2E8F0; border: 1px solid #334155; "
            "border-radius: 8px; padding: 10px; line-height: 1.4;"
        )
        layout.addWidget(self.text_area)

        self.refresh_logs()

    def refresh_logs(self):
        content = read_latest_logs(1000)
        self.text_area.setPlainText(content)
        vbar = self.text_area.verticalScrollBar()
        if vbar:
            vbar.setValue(vbar.maximum())

    def copy_to_clipboard(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.text_area.toPlainText())
            QMessageBox.information(self, "کپی شد", "متن گزارش‌ها در حافظه موقت کپی شد.")

    def clear_logs(self):
        reply = QMessageBox.question(
            self, "تأیید پاکسازی",
            "آیا از پاکسازی کامل فایل گزارش‌ها اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_log_file()
            self.refresh_logs()

    def open_external(self):
        log_path = get_log_file_path()
        if os.path.exists(log_path):
            try:
                if hasattr(os, "startfile"):
                    os.startfile(log_path)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f"file://{log_path}")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"باز کردن فایل ممکن نشد:\n{e}")
        else:
            QMessageBox.information(self, "فایل وجود ندارد", "هنوز لاگی در فایل ثبت نشده است.")


class ActionCellDelegate(QStyledItemDelegate):
    """
    نماینده ترسیمی سبک و سریع برای دکمه‌های ستون اقدام (مشاهده و کپی لینک).
    به جای ساخت و تزریق هزاران شیء ویجت سنگین در سلول‌ها، دکمه‌ها را به صورت وکتور ترسیم کرده
    و کلیک‌ها را بلافاصله هدایت می‌کند (سرعت ۱۰۰ برابری در بارگذاری داده‌ها).
    """
    def __init__(self, parent_app, parent_table=None):
        super().__init__(parent_table or parent_app)
        self.app = parent_app
        self._hover_row = -1
        self._hover_col = -1
        self._hover_btn: Optional[str] = None
        self._copied_cell: Optional[Tuple[int, int]] = None

    def _get_btn_rects(self, cell_rect: QRect):
        h = 24
        y = cell_rect.y() + (cell_rect.height() - h) // 2
        spacing = 4
        w_copy = 28
        w_view = max(50, min(70, cell_rect.width() - w_copy - spacing - 8))
        total_w = w_view + spacing + w_copy
        start_x = cell_rect.x() + (cell_rect.width() - total_w) // 2

        view_rect = QRect(start_x, y, w_view, h)
        copy_rect = QRect(start_x + w_view + spacing, y, w_copy, h)
        return view_rect, copy_rect

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(125, 36)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        data = index.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("url", "")
        has_url = bool(url)

        view_rect, copy_rect = self._get_btn_rects(option.rect)
        is_hover = (index.row() == self._hover_row and index.column() == self._hover_col)
        dark = getattr(self.app, "_dark_active", False)

        # ۱. دکمه مشاهده
        if has_url:
            if is_hover and self._hover_btn == "view":
                bg_v = QColor("#1E3A5F") if dark else QColor("#DBEAFE")
            else:
                bg_v = QColor("#16283F") if dark else QColor("#EFF6FF")
            fg_v = QColor("#7DD3FC") if dark else QColor("#1D4ED8")
            border_v = QColor("#33507A") if dark else QColor("#BFDBFE")
        else:
            bg_v = QColor("#1E293B") if dark else QColor("#F1F5F9")
            fg_v = QColor("#64748B") if dark else QColor("#94A3B8")
            border_v = QColor("#334155") if dark else QColor("#E2E8F0")

        painter.setPen(QPen(border_v, 1))
        painter.setBrush(QBrush(bg_v))
        painter.drawRoundedRect(view_rect, 5, 5)

        painter.setPen(fg_v)
        f = painter.font()
        f.setPointSize(8)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(view_rect, Qt.AlignmentFlag.AlignCenter, "مشاهده")

        # ۲. دکمه کپی 📋
        is_copied = (self._copied_cell == (index.row(), index.column()))
        if has_url:
            if is_hover and self._hover_btn == "copy":
                bg_c = QColor("#334155") if dark else QColor("#E2E8F0")
            else:
                bg_c = QColor("#1E293B") if dark else QColor("#F8FAFC")
            fg_c = QColor("#94A3B8") if dark else QColor("#475569")
            border_c = QColor("#33507A") if dark else QColor("#CBD5E1")
        else:
            bg_c = QColor("#0F172A") if dark else QColor("#F1F5F9")
            fg_c = QColor("#475569") if dark else QColor("#CBD5E1")
            border_c = QColor("#1E293B") if dark else QColor("#E2E8F0")

        painter.setPen(QPen(border_c, 1))
        painter.setBrush(QBrush(bg_c))
        painter.drawRoundedRect(copy_rect, 5, 5)

        painter.setPen(fg_c)
        painter.drawText(copy_rect, Qt.AlignmentFlag.AlignCenter, "✅" if is_copied else "📋")

        painter.restore()

    def editorEvent(self, event: QEvent, model, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        if not index.isValid():
            return False

        data = index.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("url", "")
        title = data.get("title", "")
        if not url:
            return False

        view_rect, copy_rect = self._get_btn_rects(option.rect)
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        table = option.widget

        if event.type() == QEvent.Type.MouseMove:
            if view_rect.contains(pos):
                if self._hover_row != index.row() or self._hover_col != index.column() or self._hover_btn != "view":
                    self._hover_row = index.row()
                    self._hover_col = index.column()
                    self._hover_btn = "view"
                    if table:
                        table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        table.viewport().update(option.rect)
            elif copy_rect.contains(pos):
                if self._hover_row != index.row() or self._hover_col != index.column() or self._hover_btn != "copy":
                    self._hover_row = index.row()
                    self._hover_col = index.column()
                    self._hover_btn = "copy"
                    if table:
                        table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        table.viewport().update(option.rect)
            else:
                if self._hover_row != -1:
                    self._hover_row = -1
                    self._hover_col = -1
                    self._hover_btn = None
                    if table:
                        table.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                        table.viewport().update(option.rect)
            return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                if view_rect.contains(pos):
                    if hasattr(self.app, "open_in_webview"):
                        self.app.open_in_webview(url, title)
                    return True
                elif copy_rect.contains(pos):
                    if hasattr(self.app, "copy_url_to_clipboard"):
                        self.app.copy_url_to_clipboard(url, title)
                    self._copied_cell = (index.row(), index.column())
                    if table:
                        table.viewport().update(option.rect)
                    def reset_copied():
                        self._copied_cell = None
                        if table:
                            table.viewport().update(option.rect)
                    QTimer.singleShot(1500, reset_copied)
                    return True
            elif event.button() == Qt.MouseButton.RightButton:
                if view_rect.contains(pos) or copy_rect.contains(pos):
                    self._show_context_menu(table, pos, url, title)
                    return True

        return super().editorEvent(event, model, option, index)

    def _show_context_menu(self, widget, pos, url: str, title: str):
        menu = QMenu(widget)
        act_web = menu.addAction("📑 مشاهده در پنجره پرونده")
        act_copy = menu.addAction("📋 کپی لینک پرونده")
        act_browser = menu.addAction("🌐 باز کردن در مرورگر سیستم")
        global_pos = widget.mapToGlobal(pos) if widget else pos
        action = menu.exec(global_pos)
        if action == act_web and hasattr(self.app, "open_in_webview"):
            self.app.open_in_webview(url, title)
        elif action == act_copy and hasattr(self.app, "copy_url_to_clipboard"):
            self.app.copy_url_to_clipboard(url, title)
        elif action == act_browser:
            webbrowser.open(url)


class TrademarkApp(QMainWindow):

    """پنجره اصلی — سایدبار مرحله‌ای، آمار زنده، تم روشن/تیره/سیستم."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("سامانه پایش علائم تجاری")
        self.resize(1320, 880)
        self.setMinimumSize(1024, 680)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFont(QFont("Tahoma", 9))

        init_db()
        self.client = SSAAClient()
        self.current_worker: Optional[ScanWorker] = None
        self.decl_worker: Optional[DeclarationScrapeWorker] = None
        self._comparison_worker: Optional[ComparisonWorker] = None
        self.last_excel_path = ""
        self.current_scan_id = 0

        # حالت فعال: 0 = لیست عمومی (حالت ۱)، 1 = جستجوی هدفمند (حالت ۲)
        self._current_mode = 0
        self._matched_results: List[dict] = []
        self._data_store_count = 0
        self._class5_store_count = 0

        # شمارنده‌های حالت ۱
        self._total = 0
        self._active = 0
        self._rejected = 0
        # شمارنده‌های حالت ۲
        self._class5 = 0
        self._matched = 0
        self._matched_high = 0
        self._matched_medium = 0

        os.makedirs(DATA_DIR, exist_ok=True)
        self.settings = QSettings(os.path.join(DATA_DIR, "settings.ini"), QSettings.Format.IniFormat)
        self._theme = str(self.settings.value("theme", "light"))
        if self._theme not in ("light", "dark", "system"):
            self._theme = "light"
        self._dark_active = False

        self._log_level = str(self.settings.value("log_level", "DEBUG"))
        set_log_level(self._log_level)

        # ترتیب نمایش حالت ۱ بر اساس تاریخ ثبت: newest (جدیدترین اول، پیش‌فرض) یا oldest
        self._mode1_sort = str(self.settings.value("mode1_sort", "newest"))
        if self._mode1_sort not in ("newest", "oldest"):
            self._mode1_sort = "newest"

        self._captcha_worker: Optional[CaptchaWorker] = None
        self._captcha_loading = False

        self.init_ui()
        self.apply_theme(self._theme)

        # نمایش آنی پنجره در کسری از ثانیه (کمتر از ۰.۲ ثانیه)
        # و موکول کردن بارگذاری جدول‌ها و نشست به ۴۰ میلی‌ثانیه بعد از رندر پنجره
        QTimer.singleShot(40, self._deferred_startup)

    def _deferred_startup(self):
        """بارگذاری سبک و سریع داده‌های ذخیره‌شده پس از نمایش آنی پنجره."""
        self.load_search_history_combo()
        self._refresh_store_counts()
        self._load_data_store_table()
        self._load_class5_table_from_store()
        self.check_session_on_startup()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._auto_fit_all_tables)

    def _auto_fit_all_tables(self):
        """تنظیم خودکار ابعاد تمام ستون‌های جداول برنامه متناسب با محتوای آنها."""
        for tbl in (getattr(self, "table_all", None),
                    getattr(self, "table_active", None),
                    getattr(self, "table_class5", None),
                    getattr(self, "table_matched", None)):
            if tbl is not None:
                self.auto_fit_table_columns(tbl)



    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _resolve_dark(self, theme: str) -> bool:
        if theme == "dark":
            return True
        if theme == "light":
            return False
        app = QApplication.instance()
        assert app is not None
        return detect_system_dark(app)

    def apply_theme(self, theme: str):
        self._theme = theme
        self.settings.setValue("theme", theme)
        dark = self._resolve_dark(theme)
        self._dark_active = dark
        app = QApplication.instance()
        assert app is not None
        try:
            if "Fusion" in QStyleFactory.keys():
                app.setStyle(QStyleFactory.create("Fusion"))
        except Exception:
            pass
        app.setPalette(build_palette(dark))
        app.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)
        # sync combo without recursion
        if hasattr(self, "combo_theme"):
            idx = {"light": 0, "dark": 1, "system": 2}[theme]
            self.combo_theme.blockSignals(True)
            self.combo_theme.setCurrentIndex(idx)
            self.combo_theme.blockSignals(False)
        self._refresh_stat_colors()

    def _refresh_stat_colors(self):
        if hasattr(self, "lbl_logo") and self.lbl_logo.pixmap().isNull():
            self._load_logo()
        if not hasattr(self, "stat_total_value"):
            return
        if self._dark_active:
            self.stat_total_value.setStyleSheet("color:#F1F5F9;")
            self.stat_active_value.setStyleSheet("color:#4ADE80;")
            self.stat_rejected_value.setStyleSheet("color:#94A3B8;")
            self.stat_extra_value.setStyleSheet("color:#7DD3FC;")
        else:
            self.stat_total_value.setStyleSheet("color:#0F172A;")
            self.stat_active_value.setStyleSheet("color:#15803D;")
            self.stat_rejected_value.setStyleSheet("color:#64748B;")
            self.stat_extra_value.setStyleSheet("color:#1D4ED8;")

    def _update_stat_captions(self):
        """عنوان کارت‌های آمار متناسب با حالت فعال."""
        if not hasattr(self, "stat_total_caption"):
            return
        if self._current_mode == 0:
            self.stat_total_caption.setText("کل رکوردها")
            self.stat_active_caption.setText("ثبت قطعی شده")
            self.stat_rejected_caption.setText("رد شده")
            self.stat_extra_caption.setText("در جریان")
        else:
            self.stat_total_caption.setText("رکوردهای یافت‌شده")
            self.stat_active_caption.setText("موارد منطبق")
            self.stat_rejected_caption.setText("خطر بالا")
            self.stat_extra_caption.setText("خطر متوسط")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("Central")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(14, 14, 14, 14)

        self._build_header(main_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        main_layout.addWidget(splitter, stretch=1)

        # نتایج ابتدا ساخته می‌شوند تا on_mode_changed به ویجت‌های تب دسترسی داشته باشد
        results = self._build_results()
        sidebar = self._build_sidebar()
        # RTL: first widget goes right → sidebar right, results left
        splitter.addWidget(sidebar)
        splitter.addWidget(results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 900])
        splitter.splitterMoved.connect(lambda *_: self._refresh_captcha_image())
        self.splitter = splitter

    def _load_logo(self):
        """بارگذاری تصویر لوگو از مسیر assets/logo.png یا نمایش تایپوگرافی مدرن در صورت نبود تصویر."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "logo.png"),
            os.path.join(os.path.dirname(__file__), "logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.jpg"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.svg"),
        ]
        found_path = None
        for p in possible_paths:
            if os.path.exists(p):
                found_path = p
                break

        if found_path:
            pixmap = QPixmap(found_path)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
                self.lbl_logo.setPixmap(scaled)
                self.lbl_logo.setText("")
                self.lbl_logo.setToolTip("سامانه پایش علائم تجاری")
                return

        accent_color = "#38BDF8" if getattr(self, "_dark_active", False) else "#0284C7"
        text_color = "#F1F5F9" if getattr(self, "_dark_active", False) else "#0F172A"
        sub_color = "#94A3B8" if getattr(self, "_dark_active", False) else "#64748B"

        html = (
            f"<div style='line-height: 22px; text-align: center;'>"
            f"<span style='font-size: 13pt; margin-left: 6px;'>⚖️</span>"
            f"<span style='font-size: 11pt; font-weight: 800; color: {accent_color}; font-family: Tahoma, Segoe UI;'>سامانه پایش حقوقی</span>"
            f"<span style='font-size: 11pt; font-weight: 700; color: {text_color}; font-family: Tahoma, Segoe UI;'> علائم تجاری</span>"
            f"<span style='font-size: 8.5pt; color: {sub_color}; margin-right: 8px; font-weight: normal;'> • مرکز مالکیت معنوی</span>"
            f"</div>"
        )
        self.lbl_logo.setText(html)
        self.lbl_logo.setToolTip("سامانه هوشمند پایش و استعلام علائم تجاری")

    def _show_settings_menu(self):
        menu = QMenu(self)

        theme_menu = menu.addMenu("🎨 تم پوسته")
        act_light = theme_menu.addAction("تم روشن")
        act_light.triggered.connect(lambda: self.apply_theme("light"))
        act_dark = theme_menu.addAction("تم تیره")
        act_dark.triggered.connect(lambda: self.apply_theme("dark"))
        act_sys = theme_menu.addAction("تم سیستم (ویندوز)")
        act_sys.triggered.connect(lambda: self.apply_theme("system"))

        menu.addSeparator()

        log_level_fa = {
            "DEBUG": "اشکال‌زدایی کامل",
            "INFO": "اطلاعات عادی",
            "WARNING": "فقط هشدارها",
            "ERROR": "فقط خطاها"
        }
        curr_lvl = log_level_fa.get(self._log_level, self._log_level)
        log_menu = menu.addMenu(f"📊 سطح ثبت گزارش‌ها ({curr_lvl})")
        for lvl, fa_lbl in [
            ("DEBUG", "ثبت تمامی جزئیات (اشکال‌زدایی)"),
            ("INFO", "گزارش‌های عادی (اطلاعات)"),
            ("WARNING", "فقط هشدارها"),
            ("ERROR", "فقط خطاها")
        ]:
            act = log_menu.addAction(fa_lbl)
            act.triggered.connect(lambda checked=False, l=lvl: self._on_log_level_changed(l))

        act_logs = menu.addAction("📋 مشاهده گزارش‌ها و رویدادها")
        act_logs.triggered.connect(self.open_log_viewer)

        act_reports = menu.addAction("📁 باز کردن پوشه گزارش‌ها")
        act_reports.triggered.connect(self.open_reports_dir)

        menu.addSeparator()
        menu.exec(self.btn_header_settings.mapToGlobal(self.btn_header_settings.rect().bottomLeft()))

    def _build_header(self, parent_layout):
        header = QFrame(self)
        header.setObjectName("Header")
        header.setFixedHeight(38)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(6)

        # دکمه منوی تنظیمات ظریف در گوشه
        self.btn_header_settings = QPushButton("⚙", self)
        self.btn_header_settings.setObjectName("Ghost")
        self.btn_header_settings.setFixedSize(26, 26)
        self.btn_header_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_header_settings.setToolTip("تنظیمات تم، لاگ و گزارش‌ها")
        self.btn_header_settings.clicked.connect(self._show_settings_menu)
        layout.addWidget(self.btn_header_settings)

        layout.addStretch()

        # نمایش لوگوی برنامه در مرکز نوار بالا
        self.lbl_logo = QLabel(self)
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_logo)
        self._load_logo()

        layout.addStretch()

        # ویجت‌های پنهان برای حفظ سازگاری کامل کدهای قبلی
        self.lbl_scan_state = QLabel(self)
        self.lbl_scan_state.setVisible(False)
        self.combo_log_level = QComboBox(self)
        self.combo_log_level.setVisible(False)
        self.combo_theme = QComboBox(self)
        self.combo_theme.addItems(["تم روشن", "تم تیره", "تم سیستم"])
        self.combo_theme.setVisible(False)
        self.btn_view_logs = QPushButton(self)
        self.btn_view_logs.setVisible(False)

        parent_layout.addWidget(header)

    def _on_log_level_changed(self, level: str):
        self._log_level = level
        self.settings.setValue("log_level", level)
        set_log_level(level)
        logger.info(f"سطح لاگ توسط کاربر به {level} تغییر یافت.")

    def open_log_viewer(self):
        dlg = LogViewerDialog(self)
        dlg.exec()

    def _on_theme_changed(self, index: int):
        mapping = {0: "light", 1: "dark", 2: "system"}
        self.apply_theme(mapping.get(index, "light"))


    def _build_sidebar(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(320)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        inner = QWidget()
        inner.setObjectName("SidebarInner")
        inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout = QVBoxLayout(inner)
        sidebar_layout.setSpacing(6)
        sidebar_layout.setContentsMargins(6, 4, 6, 4)

        self.card_mode = self._build_mode_card()
        self.card_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.card_mode)

        self.card_declaration_list = self._build_declaration_list_card()
        self.card_declaration_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.card_declaration_list)

        self.card_captcha = self._build_captcha_card()
        self.card_captcha.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.card_captcha)

        self.card_search = self._build_search_card()
        self.card_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.card_search)

        self.card_run = self._build_run_card()
        self.card_run.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.card_run)

        sidebar_layout.addStretch()

        scroll.setWidget(inner)

        # تنظیم حالت پیش‌فرض (لیست عمومی)
        self.on_mode_changed(0)
        return scroll

    def _build_mode_card(self) -> QGroupBox:
        card = QGroupBox("حالت پایش سامانه", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        self.combo_mode = QComboBox(self)
        self.combo_mode.addItem("⚡ پایش عمومی آخرین اظهارنامه‌ها", "declaration_list")
        self.combo_mode.addItem("🔍 جستجوی پیشرفته و هدفمند", "targeted_search")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.combo_mode)
        return card

    def _build_declaration_list_card(self) -> QGroupBox:
        card = QGroupBox("پایش لیست عمومی اظهارنامه‌ها", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # وضعیت نشست و دکمه ورود
        session_box = QHBoxLayout()
        self.lbl_session_status = QLabel("در حال بررسی نشست…", self)
        self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #64748B;")
        self.lbl_session_status.setWordWrap(True)
        session_box.addWidget(self.lbl_session_status, stretch=1)

        self.btn_login_session = QPushButton("ورود به سامانه", self)
        self.btn_login_session.setObjectName("Secondary")
        self.btn_login_session.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_login_session.clicked.connect(self.on_login_session_clicked)
        session_box.addWidget(self.btn_login_session)

        self.btn_logout_session = QPushButton("خروج", self)
        self.btn_logout_session.setObjectName("ClearBtn")
        self.btn_logout_session.setToolTip("خروج از حساب و حذف نشست ذخیره‌شده (بعد از این باید دوباره وارد شوید)")
        self.btn_logout_session.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_logout_session.clicked.connect(self.on_logout_session_clicked)
        self.btn_logout_session.setVisible(False)
        session_box.addWidget(self.btn_logout_session)
        layout.addLayout(session_box)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(sep)

        # دکمه ۱: جستجوی موارد جدید
        self.btn_decl_new = QPushButton("🔍 جستجوی موارد جدید (سریع)", self)
        self.btn_decl_new.setObjectName("Primary")
        self.btn_decl_new.setMinimumHeight(44)
        self.btn_decl_new.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_decl_new.setToolTip("استخراج موارد جدید و توقف خودکار در اولین رکورد تکراری قبلی")
        self.btn_decl_new.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_new.clicked.connect(lambda: self.start_declaration_scan(mode="new_only"))
        layout.addWidget(self.btn_decl_new)

        lbl_hint_new = QLabel("توقف در اولین رکورد تکراری و درج موارد جدید از ردیف ۱ سند ورد", self)
        lbl_hint_new.setObjectName("Hint")
        lbl_hint_new.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint_new.setWordWrap(True)
        layout.addWidget(lbl_hint_new)

        # دکمه ۲: اسکن کامل
        self.btn_decl_full = QPushButton("🔄 اسکن کامل و مجدد", self)
        self.btn_decl_full.setObjectName("Secondary")
        self.btn_decl_full.setMinimumHeight(38)
        self.btn_decl_full.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_decl_full.setToolTip("اسکن کامل تمامی صفحات تا ۱۰۱ رکورد")
        self.btn_decl_full.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_full.clicked.connect(lambda: self.start_declaration_scan(mode="full_rescan"))
        layout.addWidget(self.btn_decl_full)

        # ردیف دکمه‌های کنترل: توقف و پاکسازی
        decl_actions = QHBoxLayout()
        decl_actions.setSpacing(6)

        # دکمه ۳: توقف
        self.btn_decl_stop = QPushButton("⏹️ توقف اسکن", self)
        self.btn_decl_stop.setObjectName("Secondary")
        self.btn_decl_stop.setEnabled(False)
        self.btn_decl_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_decl_stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_stop.clicked.connect(self.stop_declaration_scan)
        decl_actions.addWidget(self.btn_decl_stop, stretch=1)

        # دکمه ۴: پاکسازی لیست اظهارنامه‌ها (Clear)
        self.btn_decl_clear = QPushButton("🗑️ پاکسازی لیست", self)
        self.btn_decl_clear.setObjectName("ClearBtn")
        self.btn_decl_clear.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_decl_clear.setToolTip("پاکسازی تمام رکوردهای اظهارنامه‌ها (پایگاه داده SQLite) و جدول‌ها")
        self.btn_decl_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_clear.clicked.connect(self.clear_declaration_list_data)
        decl_actions.addWidget(self.btn_decl_clear, stretch=1)

        layout.addLayout(decl_actions)


        # پروگرس بار و پیام وضعیت
        self.decl_progress_bar = QProgressBar(self)
        self.decl_progress_bar.setRange(0, 100)
        self.decl_progress_bar.setValue(0)
        self.decl_progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.decl_progress_bar)

        self.lbl_decl_status = QLabel("آماده برای اسکن لیست عمومی.", self)
        self.lbl_decl_status.setObjectName("Hint")
        self.lbl_decl_status.setWordWrap(True)
        layout.addWidget(self.lbl_decl_status)

        return card

    def on_mode_changed(self, index: int):
        is_decl = (index == 0)
        self._current_mode = 0 if is_decl else 1
        self.card_declaration_list.setVisible(is_decl)
        self.card_captcha.setVisible(not is_decl)
        self.card_search.setVisible(not is_decl)
        self.card_run.setVisible(not is_decl)
        if hasattr(self, 'btn_export_word_tb'):
            self.btn_export_word_tb.setVisible(is_decl)
        if hasattr(self, 'combo_search_history'):
            self.combo_search_history.setVisible(not is_decl)
        if hasattr(self, 'lbl_hist'):
            self.lbl_hist.setVisible(not is_decl)
        if hasattr(self, 'results_stack'):
            self.results_stack.setCurrentIndex(0 if is_decl else 1)
        if hasattr(self, 'lbl_store_counts'):
            self._refresh_store_counts()
        if hasattr(self, 'btn_compare'):
            self._update_compare_button_state()
        if not is_decl and hasattr(self, 'lbl_captcha'):
            if not self.lbl_captcha.pixmap() or self.lbl_captcha.pixmap().isNull():
                self.load_captcha()
        self._update_stat_captions()
        self._refresh_stats()
        if is_decl and hasattr(self, "table_all") and hasattr(self, "tabs_mode1"):
            active_tbl = self.table_all if self.tabs_mode1.currentIndex() == 0 else self.table_active
            self.auto_fit_table_columns(active_tbl)
        elif not is_decl and hasattr(self, "table_class5") and hasattr(self, "tabs_mode2"):
            active_tbl = self.table_class5 if self.tabs_mode2.currentIndex() == 0 else self.table_matched
            self.auto_fit_table_columns(active_tbl)


    def _build_captcha_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۱ — کد امنیتی", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        hint = QLabel("تصویر زیر را بخوانید و عدد ۴ رقمی را وارد کنید.", self)
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        vpn_note = QLabel("⚠️ برای دسترسی به سامانه ثبت، فیلترشکن باید خاموش باشد.", self)
        vpn_note.setStyleSheet("color: #D97706; font-size: 8.5pt; font-weight: bold;")
        vpn_note.setWordWrap(True)
        layout.addWidget(vpn_note)

        self.lbl_captcha = QLabel(self)
        self.lbl_captcha.setObjectName("CaptchaImage")
        self.lbl_captcha.setMinimumHeight(68)
        self.lbl_captcha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_captcha.setText("در حال دریافت تصویر…")
        self.lbl_captcha.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.lbl_captcha)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.txt_captcha = QLineEdit(self)
        self.txt_captcha.setObjectName("CaptchaInput")
        self.txt_captcha.setPlaceholderText("مثلاً ۴۸۲۱")
        self.txt_captcha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_captcha.setMaxLength(4)
        self.txt_captcha.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.txt_captcha.setToolTip("کد امنیتی ۴ رقمی داخل تصویر")
        row.addWidget(self.txt_captcha, stretch=3)

        self.btn_refresh_captcha = QPushButton("کد جدید", self)
        self.btn_refresh_captcha.setObjectName("Secondary")
        self.btn_refresh_captcha.setToolTip("دریافت تصویر امنیتی جدید")
        self.btn_refresh_captcha.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh_captcha.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_refresh_captcha.setMinimumWidth(85)
        self.btn_refresh_captcha.clicked.connect(self.load_captcha)
        row.addWidget(self.btn_refresh_captcha, stretch=2)
        layout.addLayout(row)
        return card

    def _field(self, label_text: str, widget: QWidget, tooltip: str = "") -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(3)
        lbl = QLabel(label_text, self)
        lbl.setObjectName("FieldLabel")
        lbl.setWordWrap(True)
        box.addWidget(lbl)
        if tooltip:
            widget.setToolTip(tooltip)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        box.addWidget(widget)
        return box

    def _on_person_type_changed(self, idx: int):
        is_legal = (idx == 1)
        self.box_real_person.setVisible(not is_legal)
        self.box_legal_person.setVisible(is_legal)

    def _build_search_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۲ — فیلترهای جستجوی علائم", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        # ردیف ۱: تاریخ انتشار آگهی
        grid_issue = QGridLayout()
        grid_issue.setHorizontalSpacing(8)
        grid_issue.setVerticalSpacing(6)
        grid_issue.setColumnStretch(0, 1)
        grid_issue.setColumnStretch(1, 1)
        self.txt_from_issue_date = QLineEdit(self)
        self.txt_from_issue_date.setPlaceholderText("مثال: ۱۴۰۴/۰۱/۰۱")
        self.txt_from_issue_date.setMinimumWidth(0)
        self.txt_from_issue_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_issue.addLayout(self._field("تاریخ انتشار از", self.txt_from_issue_date, "شروع بازه انتشار آگهی رسمی"), 0, 0)

        self.txt_to_issue_date = QLineEdit(self)
        self.txt_to_issue_date.setPlaceholderText("اختیاری — تا امروز")
        self.txt_to_issue_date.setMinimumWidth(0)
        self.txt_to_issue_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_issue.addLayout(self._field("تاریخ انتشار تا", self.txt_to_issue_date, "پایان بازه انتشار آگهی رسمی"), 0, 1)
        layout.addLayout(grid_issue)

        # نام‌های مستعار برای سازگاری کامل کدهای قبلی و تست‌ها
        self.txt_from_date = self.txt_from_issue_date
        self.txt_to_date = self.txt_to_issue_date

        # ردیف ۲: عنوان علامت
        self.txt_item_title = QLineEdit(self)
        self.txt_item_title.setPlaceholderText("بخشی از نام یا عین علامت — خالی = همه")
        self.txt_item_title.setMinimumWidth(0)
        self.txt_item_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addLayout(self._field("عنوان علامت", self.txt_item_title))

        # ردیف ۳: تطابق بر مبنای
        self.combo_title_like = QComboBox(self)
        self.combo_title_like.addItems([
            "مشابه عبارت وارد شده (۳)",
            "یکی از کلمات وارد شده (۲)",
            "عین عبارت وارد شده (۱)"
        ])
        self.combo_title_like.setCurrentIndex(0)
        self.combo_title_like.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_title_like.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_title_like.setMinimumContentsLength(10)
        layout.addLayout(self._field("تطابق بر مبنای", self.combo_title_like))

        # ردیف ۴: طبقه بندی کالا و تصویر + سقف صفحات
        grid_class = QGridLayout()
        grid_class.setHorizontalSpacing(8)
        grid_class.setVerticalSpacing(6)
        grid_class.setColumnStretch(0, 1)
        grid_class.setColumnStretch(1, 1)
        grid_class.setColumnStretch(2, 1)
        self.txt_class = QLineEdit(self)
        self.txt_class.setPlaceholderText("پیش‌فرض: ۵")
        self.txt_class.setText("5")
        self.txt_class.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_class.setMinimumWidth(0)
        self.txt_class.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_class.addLayout(self._field("طبقه بندی کالا", self.txt_class, "شماره طبقه کالا و خدمات (مثال: ۵)"), 0, 0)

        self.txt_image_stage = QLineEdit(self)
        self.txt_image_stage.setPlaceholderText("اختیاری")
        self.txt_image_stage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_image_stage.setMinimumWidth(0)
        self.txt_image_stage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_class.addLayout(self._field("طبقه بندی تصویر", self.txt_image_stage, "کد طبقه تصویر وین (اختیاری)"), 0, 1)

        self.spin_pages = QSpinBox(self)
        self.spin_pages.setRange(1, 100)
        self.spin_pages.setValue(15)
        self.spin_pages.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.spin_pages.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_pages.setMinimumWidth(0)
        self.spin_pages.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.spin_pages.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.spin_pages.setToolTip("حداکثر تعداد صفحات استخراج (هر صفحه حدود ۱۰ رکورد است)")
        grid_class.addLayout(self._field("سقف صفحات", self.spin_pages), 0, 2)
        layout.addLayout(grid_class)

        # پنل تاشو برای سایر فیلترهای رسمی سامانه (شماره‌ها، تاریخ اظهارنامه و مشخصات مالک)
        self.btn_toggle_advanced = QPushButton("فیلترهای تکمیلی (شماره‌ها، مالک) ▾", self)
        self.btn_toggle_advanced.setObjectName("Ghost")
        self.btn_toggle_advanced.setCheckable(True)
        self.btn_toggle_advanced.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_toggle_advanced.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_advanced.clicked.connect(self.toggle_advanced_panel)
        layout.addWidget(self.btn_toggle_advanced)

        self.advanced_box = QGroupBox("فیلترهای تکمیلی سامانه ثبت", self)
        self.advanced_box.setObjectName("SubCard")
        self.advanced_box.setVisible(False)
        self.advanced_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        adv_layout = QVBoxLayout(self.advanced_box)
        adv_layout.setSpacing(8)

        # ردیف شماره‌ها: شماره ثبت / شماره اظهارنامه / شماره اظهارنامه بین‌المللی
        grid_nos = QGridLayout()
        grid_nos.setHorizontalSpacing(8)
        grid_nos.setVerticalSpacing(6)
        grid_nos.setColumnStretch(0, 1)
        grid_nos.setColumnStretch(1, 1)
        grid_nos.setColumnStretch(2, 1)
        self.txt_reg_no = QLineEdit(self)
        self.txt_reg_no.setPlaceholderText("اختیاری")
        self.txt_reg_no.setMinimumWidth(0)
        self.txt_reg_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_nos.addLayout(self._field("شماره ثبت", self.txt_reg_no), 0, 0)

        self.txt_dec_no = QLineEdit(self)
        self.txt_dec_no.setPlaceholderText("اختیاری")
        self.txt_dec_no.setMinimumWidth(0)
        self.txt_dec_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_nos.addLayout(self._field("شماره اظهارنامه", self.txt_dec_no), 0, 1)

        self.txt_manual_no = QLineEdit(self)
        self.txt_manual_no.setPlaceholderText("اختیاری")
        self.txt_manual_no.setMinimumWidth(0)
        self.txt_manual_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_nos.addLayout(self._field("شماره اظهارنامه بین‌المللی", self.txt_manual_no), 0, 2)
        adv_layout.addLayout(grid_nos)

        # ردیف تاریخ اظهارنامه و نوع شخص
        grid_dec_dates = QGridLayout()
        grid_dec_dates.setHorizontalSpacing(8)
        grid_dec_dates.setVerticalSpacing(6)
        grid_dec_dates.setColumnStretch(0, 1)
        grid_dec_dates.setColumnStretch(1, 1)
        grid_dec_dates.setColumnStretch(2, 1)
        self.txt_from_dec_date = QLineEdit(self)
        self.txt_from_dec_date.setPlaceholderText("اختیاری")
        self.txt_from_dec_date.setMinimumWidth(0)
        self.txt_from_dec_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_dec_dates.addLayout(self._field("تاریخ اظهارنامه از", self.txt_from_dec_date), 0, 0)

        self.txt_to_dec_date = QLineEdit(self)
        self.txt_to_dec_date.setPlaceholderText("اختیاری")
        self.txt_to_dec_date.setMinimumWidth(0)
        self.txt_to_dec_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid_dec_dates.addLayout(self._field("تاریخ اظهارنامه تا", self.txt_to_dec_date), 0, 1)

        self.combo_person_type = QComboBox(self)
        self.combo_person_type.addItems(["حقیقی (۱)", "حقوقی (۲)"])
        self.combo_person_type.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_person_type.currentIndexChanged.connect(self._on_person_type_changed)
        grid_dec_dates.addLayout(self._field("نوع شخص", self.combo_person_type), 0, 2)
        adv_layout.addLayout(grid_dec_dates)

        # بخش مشخصات مالک حقیقی
        self.box_real_person = QWidget(self)
        self.box_real_person.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout_real = QGridLayout(self.box_real_person)
        layout_real.setContentsMargins(0, 0, 0, 0)
        layout_real.setHorizontalSpacing(8)
        layout_real.setVerticalSpacing(6)
        layout_real.setColumnStretch(0, 1)
        layout_real.setColumnStretch(1, 1)
        layout_real.setColumnStretch(2, 1)
        self.txt_owner_name = QLineEdit(self)
        self.txt_owner_name.setPlaceholderText("نام مالک")
        self.txt_owner_name.setMinimumWidth(0)
        self.txt_owner_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_real.addLayout(self._field("نام", self.txt_owner_name), 0, 0)

        self.txt_owner_family = QLineEdit(self)
        self.txt_owner_family.setPlaceholderText("نام خانوادگی مالک")
        self.txt_owner_family.setMinimumWidth(0)
        self.txt_owner_family.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_real.addLayout(self._field("نام خانوادگی", self.txt_owner_family), 0, 1)

        self.txt_national_code = QLineEdit(self)
        self.txt_national_code.setPlaceholderText("کد ملی ۱۰ رقمی")
        self.txt_national_code.setMinimumWidth(0)
        self.txt_national_code.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_real.addLayout(self._field("شماره ملی", self.txt_national_code), 0, 2)
        adv_layout.addWidget(self.box_real_person)

        # بخش مشخصات مالک حقوقی
        self.box_legal_person = QWidget(self)
        self.box_legal_person.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.box_legal_person.setVisible(False)
        layout_legal = QGridLayout(self.box_legal_person)
        layout_legal.setContentsMargins(0, 0, 0, 0)
        layout_legal.setHorizontalSpacing(8)
        layout_legal.setVerticalSpacing(6)
        layout_legal.setColumnStretch(0, 1)
        layout_legal.setColumnStretch(1, 1)
        self.txt_legal_record_no = QLineEdit(self)
        self.txt_legal_record_no.setPlaceholderText("شماره ثبت شرکت")
        self.txt_legal_record_no.setMinimumWidth(0)
        self.txt_legal_record_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_legal.addLayout(self._field("شماره ثبت شرکت", self.txt_legal_record_no), 0, 0)

        self.txt_legal_national_no = QLineEdit(self)
        self.txt_legal_national_no.setPlaceholderText("شناسه ملی ۱۱ رقمی شرکت")
        self.txt_legal_national_no.setMinimumWidth(0)
        self.txt_legal_national_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_legal.addLayout(self._field("شناسه ملی شخص حقوقی", self.txt_legal_national_no), 0, 1)
        adv_layout.addWidget(self.box_legal_person)

        layout.addWidget(self.advanced_box)
        return card

    def _build_run_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۳ — اجرا و نتیجه", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # دکمه ۱: نمایش اظهارنامه‌های منتشر شده امروز (روزنامه جاری)
        self.btn_today_issues = QPushButton("📅 نمایش اظهارنامه‌های امروز", self)
        self.btn_today_issues.setObjectName("TodayBtn")
        self.btn_today_issues.setMinimumHeight(42)
        self.btn_today_issues.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_today_issues.setToolTip("اسکن مستقیم و سریع جدیدترین آگهی‌های رسمی شماره جاری روزنامه ثبت")
        self.btn_today_issues.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_today_issues.clicked.connect(self.start_today_scan)
        layout.addWidget(self.btn_today_issues)

        # دکمه ۲: جستجوی علائم تجاری (بر اساس فیلترهای تعیین‌شده)
        self.btn_search = QPushButton("🔍 جستجوی علائم تجاری", self)
        self.btn_search.setObjectName("SearchBtn")
        self.btn_search.setMinimumHeight(42)
        self.btn_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_search.setToolTip("جستجوی پیشرفته در پایگاه داده علائم با فیلترهای مشخص‌شده بالا")
        self.btn_search.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_search.clicked.connect(self.start_custom_search)
        layout.addWidget(self.btn_search)

        # نام مستعار برای سازگاری کامل کدهای قبلی
        self.btn_start = self.btn_search

        # ردیف دکمه‌های کنترل: توقف و پاکسازی
        run_actions = QHBoxLayout()
        run_actions.setSpacing(6)

        self.btn_stop = QPushButton("⏹️ توقف اسکن", self)
        self.btn_stop.setObjectName("Secondary")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(34)
        self.btn_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_stop.setToolTip("توقف اسکن جاری")
        self.btn_stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stop.clicked.connect(self.stop_scan)
        run_actions.addWidget(self.btn_stop, stretch=1)

        self.btn_clear_search = QPushButton("🗑️ پاکسازی نتایج", self)
        self.btn_clear_search.setObjectName("ClearBtn")
        self.btn_clear_search.setMinimumHeight(34)
        self.btn_clear_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_clear_search.setToolTip("پاکسازی تمام رکوردهای استخراج‌شده و نتایج مقایسه (شروع مجدد جستجو)")
        self.btn_clear_search.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear_search.clicked.connect(self.clear_advanced_search_data)
        run_actions.addWidget(self.btn_clear_search, stretch=1)

        layout.addLayout(run_actions)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("کد امنیتی را وارد کنید و «شروع اسکن» را بزنید.", self)
        self.lbl_status.setObjectName("Hint")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)
        return card

    def _build_results(self) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(480)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # آمار زنده (کارت‌ها متناسب با حالت فعال بازنویسی می‌شوند)
        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_total_value, _, self.stat_total_caption = self._stat_card(stats, "کل رکوردها", "0")
        self.stat_active_value, _, self.stat_active_caption = self._stat_card(stats, "ثبت قطعی شده", "0")
        self.stat_rejected_value, _, self.stat_rejected_caption = self._stat_card(stats, "رد شده", "0")
        self.stat_extra_value, _, self.stat_extra_caption = self._stat_card(stats, "در جریان", "0")
        layout.addLayout(stats)

        # نوار ابزار مشترک (تاریخچه فقط حالت ۲، Word فقط حالت ۱)
        toolbar = QFrame(self)
        toolbar.setObjectName("Header")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        self.lbl_hist = QLabel("جستجوهای قبلی:", self)
        tb.addWidget(self.lbl_hist)
        self.combo_search_history = QComboBox(self)
        self.combo_search_history.setMinimumWidth(200)
        self.combo_search_history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_search_history.setToolTip("انتخاب یک جستجوی قبلی برای پر کردن خودکار فیلترها")
        self.combo_search_history.currentIndexChanged.connect(self.on_search_history_selected)
        tb.addWidget(self.combo_search_history, stretch=1)

        self.btn_export_excel = QPushButton("خروجی اکسل", self)
        self.btn_export_excel.setObjectName("Accent")
        self.btn_export_excel.setToolTip("ساخت و باز کردن گزارش اکسل متناسب با حالت فعال")
        self.btn_export_excel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export_excel.clicked.connect(self.export_current_excel)
        tb.addWidget(self.btn_export_excel)

        self.btn_export_word_tb = QPushButton("📄 خروجی سند ورد", self)
        self.btn_export_word_tb.setObjectName("Primary")
        self.btn_export_word_tb.setToolTip("باز کردن فایل جدول‌بندی‌شده راست‌به‌چپ پرونده‌ها در قالب سند ورد")
        self.btn_export_word_tb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export_word_tb.clicked.connect(self.open_current_word)
        tb.addWidget(self.btn_export_word_tb)

        self.btn_open_reports_folder = QPushButton("📁 پوشه گزارش‌ها", self)
        self.btn_open_reports_folder.setObjectName("Secondary")
        self.btn_open_reports_folder.setToolTip("باز کردن پوشه فایل‌های خروجی اکسل و ورد")
        self.btn_open_reports_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_reports_folder.clicked.connect(self.open_reports_dir)
        tb.addWidget(self.btn_open_reports_folder)
        layout.addWidget(toolbar)

        # پشته نتایج: ایندکس ۰ = حالت ۱، ایندکس ۱ = حالت ۲ (کاملاً مستقل)
        self.results_stack = QStackedWidget(self)
        self.results_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.results_stack, stretch=1)

        self.results_stack.addWidget(self._build_mode1_panel())
        self.results_stack.addWidget(self._build_mode2_panel())

        self._update_stat_captions()
        self._refresh_stats()
        return panel

    # ------------------------------------------------------------------
    # Mode 1 panel — ALL SCRAPED RECORDS + ACTIVE ONLY
    # ------------------------------------------------------------------
    def _build_mode1_panel(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # نوار ترتیب نمایش بر اساس تاریخ ثبت
        sort_bar = QFrame(self)
        sort_bar.setObjectName("Header")
        sb = QHBoxLayout(sort_bar)
        sb.setContentsMargins(12, 8, 12, 8)
        lbl_sort = QLabel("ترتیب نمایش بر اساس تاریخ ثبت:", self)
        lbl_sort.setObjectName("Hint")
        sb.addWidget(lbl_sort)
        self.combo_mode1_sort = QComboBox(self)
        self.combo_mode1_sort.addItem("جدیدترین اول ↓ (پیش‌فرض)", "newest")
        self.combo_mode1_sort.addItem("قدیمی‌ترین اول ↑", "oldest")
        self.combo_mode1_sort.setToolTip("مرتب‌سازی جدول‌های حالت ۱ بر اساس تاریخ ثبت پرونده")
        self.combo_mode1_sort.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_mode1_sort.setCurrentIndex(0 if self._mode1_sort == "newest" else 1)
        self.combo_mode1_sort.currentIndexChanged.connect(self.on_mode1_sort_changed)
        sb.addWidget(self.combo_mode1_sort)
        sb.addStretch()
        v.addWidget(sort_bar)

        self.tabs_mode1 = QTabWidget(self)
        v.addWidget(self.tabs_mode1, stretch=1)

        # تب ۱: ALL SCRAPED RECORDS
        self.tab_all = QWidget()
        all_layout = QVBoxLayout(self.tab_all)
        all_layout.setContentsMargins(10, 10, 10, 10)
        all_hint = QLabel("تمامی اظهارنامه‌های استخراج‌شده از لیست عمومی، بدون هیچ‌گونه فیلتر.", self)
        all_hint.setObjectName("Hint")
        all_layout.addWidget(all_hint)
        self.table_all = self.create_table([
            "ردیف", "شماره اظهارنامه", "نام علامت لاتین", "نام علامت فارسی",
            "وضعیت پرونده", "شماره ثبت", "تاریخ ثبت", "تاریخ تمدید",
            "لینک دانلود گواهی ثبت"
        ])
        self.table_all.setItemDelegateForColumn(8, ActionCellDelegate(self, self.table_all))
        self.table_all.setMouseTracking(True)
        self.table_all.setColumnWidth(8, 140)
        self.table_all.cellDoubleClicked.connect(self._on_table_all_double_click)
        all_layout.addWidget(self.table_all, stretch=1)
        self.all_empty = QLabel("هنوز اسکنی انجام نشده — نتایج کامل استخراج اینجا نمایش داده می‌شود.", self)
        self.all_empty.setObjectName("EmptyState")
        self.all_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_empty.setWordWrap(True)
        all_layout.addWidget(self.all_empty)
        self.tabs_mode1.addTab(self.tab_all, "کل اظهارنامه‌های استخراج‌شده")
        self.tabs_mode1.setTabToolTip(0, "تمامی اظهارنامه‌های استخراج‌شده بدون فیلتر")

        # تب ۲: ACTIVE ONLY (ثبت قطعی شده)
        self.tab_active = QWidget()
        active_layout = QVBoxLayout(self.tab_active)
        active_layout.setContentsMargins(10, 10, 10, 10)
        active_hint = QLabel("فقط پرونده‌هایی که وضعیت آن‌ها در سامانه ثبت «ثبت قطعی شده» است.", self)
        active_hint.setObjectName("Hint")
        active_layout.addWidget(active_hint)
        self.table_active = self.create_table([
            "ردیف", "شماره اظهارنامه", "نام علامت لاتین", "نام علامت فارسی",
            "وضعیت پرونده", "شماره ثبت", "تاریخ ثبت", "تاریخ تمدید",
            "لینک دانلود گواهی ثبت"
        ])
        self.table_active.setItemDelegateForColumn(8, ActionCellDelegate(self, self.table_active))
        self.table_active.setMouseTracking(True)
        self.table_active.setColumnWidth(8, 140)
        self.table_active.cellDoubleClicked.connect(self._on_table_active_double_click)
        active_layout.addWidget(self.table_active, stretch=1)
        self.active_empty = QLabel("هنوز پرونده‌ای با وضعیت «ثبت قطعی شده» یافت نشده است.", self)
        self.active_empty.setObjectName("EmptyState")
        self.active_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_empty.setWordWrap(True)
        active_layout.addWidget(self.active_empty)
        self.tabs_mode1.addTab(self.tab_active, "فقط ثبت قطعی شده")
        self.tabs_mode1.setTabToolTip(1, "فقط موارد دارای وضعیت «ثبت قطعی شده»")
        self.tabs_mode1.currentChanged.connect(
            lambda idx: self.auto_fit_table_columns(self.table_all if idx == 0 else self.table_active)
        )

        return container

    # ------------------------------------------------------------------
    # Mode 2 panel — CAPTURED CLASS 5 + MATCHED
    # ------------------------------------------------------------------
    def _build_mode2_panel(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # نوار وضعیت مخازن + دکمه مقایسه دستی
        status_bar = QFrame(self)
        status_bar.setObjectName("Header")
        sb = QHBoxLayout(status_bar)
        sb.setContentsMargins(12, 8, 12, 8)
        self.lbl_store_counts = QLabel("", self)
        self.lbl_store_counts.setObjectName("Hint")
        sb.addWidget(self.lbl_store_counts, stretch=1)
        self.btn_clear_mode2_tb = QPushButton("🗑️ پاکسازی نتایج", self)
        self.btn_clear_mode2_tb.setObjectName("ClearBtn")
        self.btn_clear_mode2_tb.setToolTip("پاکسازی تمام رکوردهای استخراج‌شده و نتایج مقایسه (شروع مجدد جستجو)")
        self.btn_clear_mode2_tb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear_mode2_tb.clicked.connect(self.clear_advanced_search_data)
        sb.addWidget(self.btn_clear_mode2_tb)

        self.btn_compare = QPushButton("🔄 مقایسه هوشمند با پرونده‌ها", self)
        self.btn_compare.setObjectName("Accent")
        self.btn_compare.setToolTip(
            "مقایسه هوشمند تمام عناوین پرونده‌های مرجع با رکوردهای استخراج‌شده\n"
            "(اجرا به صورت دستی با این دکمه)"
        )
        self.btn_compare.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_compare.clicked.connect(self.run_comparison)
        sb.addWidget(self.btn_compare)
        v.addWidget(status_bar)

        self.tabs_mode2 = QTabWidget(self)
        v.addWidget(self.tabs_mode2, stretch=1)

        # تب ۱: رکوردهای یافت‌شده
        self.tab_class5 = QWidget()
        c5_layout = QVBoxLayout(self.tab_class5)
        c5_layout.setContentsMargins(10, 10, 10, 10)
        c5_hint = QLabel("رکوردهای استخراج‌شده از جستجوی هدفمند در این نشست.", self)
        c5_hint.setObjectName("Hint")
        c5_layout.addWidget(c5_hint)
        self.table_class5 = self.create_table([
            "ردیف", "عنوان علامت", "شماره اظهارنامه", "تاریخ اظهارنامه",
            "وضعیت پرونده", "طبقات", "اقدام"
        ])
        self.table_class5.setItemDelegateForColumn(6, ActionCellDelegate(self, self.table_class5))
        self.table_class5.setMouseTracking(True)
        self.table_class5.setColumnWidth(6, 120)
        self.table_class5.cellDoubleClicked.connect(self._on_table_class5_double_click)
        c5_layout.addWidget(self.table_class5, stretch=1)
        self.class5_empty = QLabel(
            "هنوز رکوردی استخراج نشده است — فیلترهای جستجو را تنظیم و «جستجوی علائم تجاری» را بزنید.", self
        )
        self.class5_empty.setObjectName("EmptyState")
        self.class5_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class5_empty.setWordWrap(True)
        c5_layout.addWidget(self.class5_empty)
        self.tabs_mode2.addTab(self.tab_class5, "رکوردهای یافت‌شده")
        self.tabs_mode2.setTabToolTip(0, "کلیه رکوردهای استخراج‌شده از جستجوی هدفمند")

        # تب ۲: موارد منطبق
        self.tab_matched = QWidget()
        m_layout = QVBoxLayout(self.tab_matched)
        m_layout.setContentsMargins(10, 10, 10, 10)
        m_hint = QLabel(
            "نتیجه مقایسه عناوین پرونده‌های مرجع با رکوردهای استخراج‌شده (شباهت ۷۰٪ به بالا). "
            "برای به‌روزرسانی دکمه «مقایسه هوشمند با پرونده‌ها» را بزنید.", self
        )
        m_hint.setObjectName("Hint")
        m_hint.setWordWrap(True)
        m_layout.addWidget(m_hint)
        self.table_matched = self.create_table([
            "ردیف", "درصد شباهت", "سطح ریسک",
            "عنوان علامت مرجع", "شماره اظهارنامه",
            "عنوان علامت استخراج‌شده", "شماره اظهارنامه",
            "تاریخ", "پرونده مرجع", "پرونده استخراج‌شده"
        ])
        self.table_matched.setItemDelegateForColumn(8, ActionCellDelegate(self, self.table_matched))
        self.table_matched.setItemDelegateForColumn(9, ActionCellDelegate(self, self.table_matched))
        self.table_matched.setMouseTracking(True)
        self.table_matched.setColumnWidth(8, 115)
        self.table_matched.setColumnWidth(9, 115)
        self.table_matched.cellDoubleClicked.connect(self._on_table_matched_double_click)
        m_layout.addWidget(self.table_matched, stretch=1)
        self.matched_empty = QLabel(
            "هنوز مقایسه‌ای انجام نشده است — ابتدا اسکن یا جستجو را اجرا کرده و سپس «مقایسه هوشمند با پرونده‌ها» را بزنید.", self
        )
        self.matched_empty.setObjectName("EmptyState")
        self.matched_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.matched_empty.setWordWrap(True)
        m_layout.addWidget(self.matched_empty)
        self.tabs_mode2.addTab(self.tab_matched, "موارد منطبق")
        self.tabs_mode2.setTabToolTip(1, "جفت‌های منطبق بین عناوین پرونده‌های مرجع و رکوردهای استخراج‌شده")
        self.tabs_mode2.currentChanged.connect(
            lambda idx: self.auto_fit_table_columns(self.table_class5 if idx == 0 else self.table_matched)
        )

        return container

    def _stat_card(self, parent_layout, caption: str, initial: str):
        card = QFrame(self)
        card.setObjectName("Stat")
        box = QVBoxLayout(card)
        box.setSpacing(2)
        box.setContentsMargins(12, 10, 12, 10)
        value = QLabel(initial, self)
        value.setObjectName("StatValue")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(caption, self)
        cap.setObjectName("StatCaption")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(value)
        box.addWidget(cap)
        parent_layout.addWidget(card, stretch=1)
        return value, card, cap

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def create_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget(self)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setHighlightSections(False)
        header.setMinimumSectionSize(60)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(36)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(True)
        table.setWordWrap(False)
        table.setMinimumHeight(220)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return table

    def auto_fit_table_columns(self, table: QTableWidget, extra_padding: int = 24):
        """
        تنظیم خودکار و دقیق اندازه تمام ستون‌ها و سلول‌های جدول متناسب با محتوای آن‌ها،
        مشابه عملکرد دابل‌کلیک بر روی جداکننده ستون‌ها (Resize to Contents).
        """
        if not table or table.columnCount() == 0:
            return
        table.resizeColumnsToContents()

        # افزودن حاشیه امن برای نمایش شکیل بدون فشردگی و بدون بریدگی متن
        for col in range(table.columnCount()):
            cur_w = table.columnWidth(col)
            min_w = 55 if col == 0 else 95
            table.setColumnWidth(col, max(min_w, cur_w + extra_padding))

    def _schedule_auto_fit(self, table: QTableWidget):
        """تنظیم خودکار ابعاد ستون‌ها در هنگام افزودن زنده داده‌ها بدون افت کارایی."""
        if not hasattr(self, "_autofit_timers"):
            self._autofit_timers = {}
        timer = self._autofit_timers.get(table)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(200)
            timer.timeout.connect(lambda t=table: self.auto_fit_table_columns(t))
            self._autofit_timers[table] = timer
        timer.start()

    # ------------------------------------------------------------------
    # Dialogs — always themed (FIX #2: black QMessageBox)
    # ------------------------------------------------------------------
    def _msg(self, kind: str, title: str, text: str):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        if kind == "information":
            box.setIcon(QMessageBox.Icon.Information)
        elif kind == "warning":
            box.setIcon(QMessageBox.Icon.Warning)
        else:
            box.setIcon(QMessageBox.Icon.Critical)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _set_state(self, text: str, mood: str = "idle"):
        self.lbl_scan_state.setText(text)
        self.lbl_scan_state.setProperty("mood", mood)
        self.lbl_scan_state.style().unpolish(self.lbl_scan_state)
        self.lbl_scan_state.style().polish(self.lbl_scan_state)

    def _refresh_stats(self):
        if not hasattr(self, "stat_total_value"):
            return
        if self._current_mode == 0:
            # حالت ۱: کل / ثبت قطعی / رد شده / در جریان
            self.stat_total_value.setText(str(self._total))
            self.stat_active_value.setText(str(self._active))
            self.stat_rejected_value.setText(str(self._rejected))
            self.stat_extra_value.setText(str(max(0, self._total - self._active - self._rejected)))
            self.tabs_mode1.setTabText(0, f"کل اظهارنامه‌های استخراج‌شده ({self._total})")
            self.tabs_mode1.setTabText(1, f"فقط ثبت قطعی شده ({self._active})")
            # وضعیت خالی بودن تب‌ها
            self.all_empty.setVisible(self._total == 0)
            if self._total == 0 and self.current_scan_id:
                self.all_empty.setText(
                    "اسکن تمام شد اما رکوردی با این فیلترها پیدا نشد — بازه تاریخ را بازتر کنید."
                )
            self.active_empty.setVisible(self._active == 0)
            if self._active == 0 and self._total > 0:
                self.active_empty.setText(
                    "رکوردی با وضعیت «ثبت قطعی شده» یافت نشد — جزئیات در تب کل اظهارنامه‌ها مشاهده می‌شود."
                )
            elif self._active == 0:
                self.active_empty.setText("هنوز پرونده‌ای با وضعیت «ثبت قطعی شده» یافت نشده است.")
        else:
            # حالت ۲: رکوردهای یافت‌شده / منطبق / خطر بالا / خطر متوسط
            self.stat_total_value.setText(str(self._class5))
            self.stat_active_value.setText(str(self._matched))
            self.stat_rejected_value.setText(str(self._matched_high))
            self.stat_extra_value.setText(str(self._matched_medium))
            self.tabs_mode2.setTabText(0, f"رکوردهای یافت‌شده ({self._class5})")
            self.tabs_mode2.setTabText(1, f"موارد منطبق ({self._matched})")
            self.class5_empty.setVisible(self._class5 == 0)
            self.matched_empty.setVisible(self._matched == 0)
            if self._matched == 0 and self._class5 > 0 and self._data_store_count > 0:
                self.matched_empty.setText(
                    "اسکن انجام شد اما موردی بالای ۷۰٪ شباهت یافت نشد — یا دکمه «مقایسه هوشمند با پرونده‌ها» را بزنید."
                )
            elif self._matched == 0:
                self.matched_empty.setText(
                    "هنوز مقایسه‌ای انجام نشده است — ابتدا هر دو بخش را بررسی و سپس «مقایسه هوشمند با پرونده‌ها» را بزنید."
                )

    def _reset_counters(self):
        self._total = 0
        self._active = 0
        self._rejected = 0
        self._class5 = 0
        self._matched = 0
        self._matched_high = 0
        self._matched_medium = 0
        self._refresh_stats()

    def _reset_mode1_tables(self):
        self.table_all.setRowCount(0)
        self.table_active.setRowCount(0)

    def _reset_mode2_tables(self):
        self.table_class5.setRowCount(0)
        self.table_matched.setRowCount(0)
        self._matched_results = []

    # ------------------------------------------------------------------
    # Store counts
    # ------------------------------------------------------------------
    def _refresh_store_counts(self):
        counts = store_counts()
        self._data_store_count = counts.get("data", 0)
        self._class5_store_count = counts.get("class5", 0)
        if hasattr(self, "lbl_store_counts"):
            self.lbl_store_counts.setText(
                f"مخزن پرونده‌ها: {self._data_store_count} عنوان مرجع  |  {self._class5_store_count} رکورد جستجو"
            )
        if hasattr(self, "btn_compare"):
            self._update_compare_button_state()

    def _update_compare_button_state(self):
        can_compare = self._data_store_count > 0 and self._class5_store_count > 0
        self.btn_compare.setEnabled(can_compare)
        if can_compare:
            self.btn_compare.setToolTip(
                "مقایسه هوشمند تمام عناوین مرجع با رکوردهای جستجو شده"
            )
        else:
            missing = []
            if self._data_store_count == 0:
                missing.append("عناوین مرجع (پایش اظهارنامه‌ها)")
            if self._class5_store_count == 0:
                missing.append("رکوردهای جستجو شده")
            self.btn_compare.setToolTip(
                "برای مقایسه ابتدا «" + "» و «".join(missing) + "» را کامل کنید."
            )

    # ------------------------------------------------------------------
    # Behaviours
    # ------------------------------------------------------------------
    def toggle_advanced_panel(self):
        is_visible = self.btn_toggle_advanced.isChecked()
        self.advanced_box.setVisible(is_visible)
        arrow = "▴" if is_visible else "▾"
        self.btn_toggle_advanced.setText(f"فیلترهای تکمیلی (شماره‌ها، مالک) {arrow}")

    def load_captcha(self):
        if self._captcha_loading:
            return
        self._captcha_loading = True
        self.lbl_captcha.setText("در حال دریافت تصویر…")
        self.txt_captcha.clear()
        if hasattr(self, 'btn_refresh_captcha'):
            self.btn_refresh_captcha.setEnabled(False)

        self._captcha_worker = CaptchaWorker(self.client, self)
        self._captcha_worker.captcha_loaded.connect(self._on_captcha_loaded)
        self._captcha_worker.captcha_failed.connect(self._on_captcha_failed)
        self._captcha_worker.start()

    def _refresh_captcha_image(self):
        if hasattr(self, "_current_captcha_pixmap") and self._current_captcha_pixmap and not self._current_captcha_pixmap.isNull():
            w = max(180, self.lbl_captcha.width() - 8)
            scaled = self._current_captcha_pixmap.scaled(
                w,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_captcha.setPixmap(scaled)

    def _on_captcha_loaded(self, img_bytes: bytes):
        self._captcha_loading = False
        if hasattr(self, 'btn_refresh_captcha'):
            self.btn_refresh_captcha.setEnabled(True)
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        self._current_captcha_pixmap = pixmap
        self._refresh_captcha_image()
        self.lbl_status.setText("کد امنیتی دریافت شد. عدد ۴ رقمی را وارد کنید.")
        self.txt_captcha.setFocus()

    def _on_captcha_failed(self, err: str):
        self._captcha_loading = False
        if hasattr(self, 'btn_refresh_captcha'):
            self.btn_refresh_captcha.setEnabled(True)
        if err == "vpn_timeout":
            self.lbl_captcha.setText("خطای اتصال به سرور\n(فیلترشکن را خاموش کنید)")
            self.lbl_status.setText(
                "⚠️ سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور را مسدود می‌کنند.\n"
                "در صورت روشن بودن فیلترشکن، لطفاً آن را خاموش کرده و «کد جدید» را بزنید."
            )
        else:
            self.lbl_captcha.setText("خطا در بارگذاری — «کد جدید» را بزنید")
            self.lbl_status.setText("دریافت تصویر کد امنیتی ناموفق بود. اتصال اینترنت را بررسی و «کد جدید» را بزنید.")

    def load_search_history_combo(self):
        history = get_search_history(limit=30)
        self.combo_search_history.blockSignals(True)
        self.combo_search_history.clear()
        self.combo_search_history.addItem("انتخاب از جستجوهای قبلی…", None)
        for h in history:
            label = f"{h['title']} ({h['created_at']})"
            self.combo_search_history.addItem(label, h['params'])
        self.combo_search_history.blockSignals(False)

    def on_search_history_selected(self, index: int):
        if index <= 0:
            return
        params = self.combo_search_history.currentData()
        if not params or not isinstance(params, dict):
            return

        if params.get("FromIssueDate"):
            self.txt_from_issue_date.setText(str(params["FromIssueDate"]))
        else:
            self.txt_from_issue_date.clear()

        if params.get("ToIssueDate"):
            self.txt_to_issue_date.setText(str(params["ToIssueDate"]))
        else:
            self.txt_to_issue_date.clear()

        if params.get("SignProductId"):
            self.txt_class.setText(str(params["SignProductId"]))
        else:
            self.txt_class.setText("5")

        if params.get("SignImageStage"):
            self.txt_image_stage.setText(str(params["SignImageStage"]))
        else:
            self.txt_image_stage.clear()

        if params.get("ItemTitle"):
            self.txt_item_title.setText(str(params["ItemTitle"]))
        else:
            self.txt_item_title.clear()

        like_val = str(params.get("SearchItemTitleAsLike", "3"))
        like_idx = {"3": 0, "2": 1, "1": 2}.get(like_val, 0)
        self.combo_title_like.setCurrentIndex(like_idx)

        # فیلترهای تکمیلی
        reg_no = params.get("RegisterNo") or ""
        dec_no = params.get("DeclarationNo") or ""
        manual_no = params.get("ManualNo") or ""
        from_dec = params.get("FromDeclarationDateRange") or ""
        to_dec = params.get("ToDeclarationDateRange") or ""
        self.txt_reg_no.setText(str(reg_no))
        self.txt_dec_no.setText(str(dec_no))
        self.txt_manual_no.setText(str(manual_no))
        self.txt_from_dec_date.setText(str(from_dec))
        self.txt_to_dec_date.setText(str(to_dec))

        ptype = str(params.get("personType", "1"))
        ptype_idx = 1 if ptype == "2" else 0
        self.combo_person_type.setCurrentIndex(ptype_idx)
        self._on_person_type_changed(ptype_idx)

        owner_name = params.get("RealOwnerName") or ""
        owner_family = params.get("RealOwnerFamily") or ""
        nat_code = params.get("RealOwnerNationalityCode") or ""
        legal_rec = params.get("LegalOwnerRecordNo") or ""
        legal_nat = params.get("LegalOwnerNationalityNo") or ""

        self.txt_owner_name.setText(str(owner_name))
        self.txt_owner_family.setText(str(owner_family))
        self.txt_national_code.setText(str(nat_code))
        self.txt_legal_record_no.setText(str(legal_rec))
        self.txt_legal_national_no.setText(str(legal_nat))

        has_adv = any([reg_no, dec_no, manual_no, from_dec, to_dec,
                       owner_name, owner_family, nat_code, legal_rec, legal_nat])
        if has_adv:
            self.btn_toggle_advanced.setChecked(True)
            self.advanced_box.setVisible(True)
            self.btn_toggle_advanced.setText("سایر فیلترهای سامانه ثبت (شماره‌ها، تاریخ اظهارنامه، مشخصات مالک) ▴")

        self.lbl_status.setText("فیلترهای جستجوی قبلی بازیابی شد. کد امنیتی جدید را وارد فرمایید.")
        self._set_state("پیش‌نویس آماده", "idle")

    def start_today_scan(self):
        """اسکن سریع و مستقیم جدیدترین آگهی‌های شماره جاری روزنامه ثبت (منتشر شده امروز)."""
        self._execute_scan(is_today=True)

    def start_custom_search(self):
        """جستجوی علائم تجاری بر اساس فیلترهای مشخص‌شده در فرم."""
        self._execute_scan(is_today=False)

    def start_scan(self):
        """نام مستعار برای سازگاری کامل با تست‌ها و کدهای قبلی."""
        self.start_custom_search()

    def _execute_scan(self, is_today: bool):
        captcha = self.txt_captcha.text().strip()
        if len(captcha) < 4:
            self._msg("warning", "کد امنیتی ناقص",
                      "لطفاً عدد ۴ رقمی داخل تصویر «مرحله ۱» را کامل وارد کنید.")
            self.txt_captcha.setFocus()
            return

        values = {
            "class": self.txt_class.text(),
            "image_stage": self.txt_image_stage.text(),
            "from_issue_date": self.txt_from_issue_date.text(),
            "to_issue_date": self.txt_to_issue_date.text(),
            "item_title": self.txt_item_title.text(),
            "title_like": {0: "3", 1: "2", 2: "1"}.get(self.combo_title_like.currentIndex(), "3"),
            "register_no": self.txt_reg_no.text(),
            "declaration_no": self.txt_dec_no.text(),
            "manual_no": self.txt_manual_no.text(),
            "from_declaration_date": self.txt_from_dec_date.text(),
            "to_declaration_date": self.txt_to_dec_date.text(),
            "person_type": {0: "1", 1: "2"}.get(self.combo_person_type.currentIndex(), "1"),
            "owner_name": self.txt_owner_name.text(),
            "owner_family": self.txt_owner_family.text(),
            "national_code": self.txt_national_code.text(),
            "legal_record_no": self.txt_legal_record_no.text(),
            "legal_national_no": self.txt_legal_national_no.text(),
        }
        try:
            request = build_search_request(values, is_today)
        except SearchRequestError as exc:
            self._msg("warning", "شرایط جستجو خیلی کلی است", str(exc))
            self.txt_from_issue_date.setFocus()
            return
        params = request.params
        scan_date = request.scan_date
        title_summary = request.title_summary

        save_search_history(title_summary, params)
        self.load_search_history_combo()

        # ریست تب‌های حالت ۲ (کلاس ۵ + منطبق)
        self._reset_mode2_tables()
        self._class5 = 0
        self._matched = 0
        self._matched_high = 0
        self._matched_medium = 0
        self._refresh_stats()
        # نمایش زنده در تب CAPTURED CLASS 5
        if self._current_mode != 1:
            self.combo_mode.setCurrentIndex(1)
        self.tabs_mode2.setCurrentIndex(0)

        self.btn_today_issues.setEnabled(False)
        self.btn_search.setEnabled(False)
        self.btn_stop.setEnabled(True)
        if hasattr(self, 'btn_clear_search'):
            self.btn_clear_search.setEnabled(False)
        if hasattr(self, 'btn_clear_mode2_tb'):
            self.btn_clear_mode2_tb.setEnabled(False)
        self.progress_bar.setValue(0)
        self._set_state("در حال اسکن…", "running")
        status_text = (
            "اسکن آگهی‌های امروز (شماره جاری) آغاز شد…" if is_today
            else "جستجوی علائم تجاری آغاز شد…"
        )
        self.lbl_status.setText(status_text + " نتایج به‌صورت زنده در جدول پایین درج می‌شوند.")

        self.current_worker = ScanWorker(
            client=self.client,
            search_params=params,
            captcha_value=captcha,
            scan_date=scan_date,
            max_pages=self.spin_pages.value()
        )
        self.current_worker.progress_changed.connect(self.on_progress)
        self.current_worker.record_found.connect(self._on_mode2_record)
        self.current_worker.scan_completed.connect(self.on_scan_completed)
        self.current_worker.scan_cancelled.connect(self.on_scan_cancelled)
        self.current_worker.scan_failed.connect(self.on_scan_failed)
        self.current_worker.finished.connect(self._ensure_scan_buttons_reset)
        self.current_worker.start()

    def stop_scan(self):
        if self.current_worker:
            self.current_worker.cancel()
            self.lbl_status.setText("در حال توقف اسکن…")
            self.btn_stop.setEnabled(False)

    def on_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(msg)

    def _on_mode1_record(self, r: dict, refresh_stats: bool = True):
        self._total += 1
        if r.get('is_active') or is_finally_registered(r.get('status', '')):
            self._active += 1
            r['is_active'] = 1
            self.add_to_table_active(r)
        if r.get('is_rejected'):
            self._rejected += 1
        self.add_to_table_all(r)
        if refresh_stats:
            self._refresh_stats()

    def _on_mode2_record(self, r: dict, refresh_stats: bool = True):
        # بررسی قطعی: اگر رکورد طبقه ۵ ندارد، نادیده گرفته شده و در جدول ثبت نمی‌شود
        if r.get('classes') and not r.get('has_class_5') and 5 not in r.get('classes', []):
            return
        self._class5 += 1
        self.add_to_table_class5(r)
        if refresh_stats:
            self._refresh_stats()

    def _normalize_url(self, url: str) -> str:
        """تبدیل آدرس‌های نسبی یا ناقص به آدرس کامل سامانه ثبت اسناد."""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("/"):
            return f"https://ipm.ssaa.ir{url}"
        if not url.startswith("http://") and not url.startswith("https://"):
            return f"https://ipm.ssaa.ir/{url}"
        return url

    def copy_url_to_clipboard(self, url: str, title: str = ""):
        """کپی آدرس پرونده به حافظه کلیپ‌بورد با بازخورد تصویری."""
        url = self._normalize_url(url)
        if not url:
            return
        try:
            cb = QApplication.clipboard()
            if cb:
                cb.setText(url)
            subprocess.run(["clip"], input=url.encode("utf-16"), check=False)
        except Exception:
            pass

        logger.info(f"آدرس پرونده در کلیپ‌بورد کپی شد: {url}")
        self.lbl_decl_status.setText(f"📋 لینک پرونده کپی شد: {title or url[:45]}")

    def open_in_webview(self, url: str, title: str = ""):
        """باز کردن پرونده در پنجره بومی WebView2 ویندوز با نوار ابزار کپی لینک."""
        url = self._normalize_url(url)
        if not url:
            self._msg("warning", "خطا", "آدرس پرونده موجود نیست یا قابل باز شدن نمی‌باشد.")
            return

        try:
            logger.info(f"باز کردن پرونده در WebView2: {url}")
            if not has_saved_session():
                self.lbl_decl_status.setText("⚠️ هنوز وارد سامانه نشده‌اید؛ در صورت نیاز داخل همین پنجره وارد شوید (فقط بار اول).")
            else:
                self.lbl_decl_status.setText(f"در حال باز کردن پرونده: {title or url[:40]}...")
            
            # در صورتی که برنامه به فایل exe تبدیل شده باشد
            if getattr(sys, 'frozen', False):
                subprocess.Popen(
                    [sys.executable, '--view-detail', url, title or "مشاهده پرونده"],
                    shell=False
                )
                return

            # در حالت اجرای عادی پایتون (سورس‌کد)
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_script = os.path.join(root_dir, "main.py")
            viewer_script = os.path.join(root_dir, "scanner", "detail_viewer.py")

            if os.path.exists(main_script):
                subprocess.Popen(
                    [sys.executable, main_script, '--view-detail', url, title or "مشاهده پرونده"],
                    shell=False
                )
                return
            elif os.path.exists(viewer_script):
                subprocess.Popen(
                    [sys.executable, viewer_script, url, title or "مشاهده پرونده"],
                    shell=False
                )
                return
        except Exception as e:
            logger.error(f"خطا در اجرای detail_viewer: {e}")

        # در صورت نبود اسکریپت یا خطا، باز کردن در مرورگر سیستم
        webbrowser.open(url)

    def _open_button(self, url: str, compact: bool = False, title: str = "") -> QWidget:
        """ایجاد ویجت ترکیبی دکمه مشاهده پرونده (در وب‌ویو) و دکمه کپی لینک."""
        normalized_url = self._normalize_url(url)
        container = QWidget(self)
        hlayout = QHBoxLayout(container)
        hlayout.setContentsMargins(4, 2, 4, 2)
        hlayout.setSpacing(4)

        btn_view = QPushButton("مشاهده" if compact else "مشاهده پرونده", container)
        btn_view.setObjectName("RowBtn")
        btn_view.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        btn_copy = QPushButton("📋", container)
        btn_copy.setObjectName("CopyBtn")
        btn_copy.setFixedWidth(28)
        btn_copy.setFixedHeight(26)
        btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        if normalized_url:
            btn_view.setToolTip("کلیک: مشاهده در پنجره پرونده\nکلیک راست: گزینه‌های دیگر")
            btn_view.clicked.connect(lambda _, u=normalized_url, t=title: self.open_in_webview(u, t))

            # منوی کلیک راست
            btn_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            def on_context_menu(pos, u=normalized_url, t=title):
                menu = QMenu(self)
                act_web = menu.addAction("📑 مشاهده در پنجره پرونده")
                act_copy = menu.addAction("📋 کپی لینک پرونده")
                act_browser = menu.addAction("🌐 باز کردن در مرورگر سیستم")
                action = menu.exec(btn_view.mapToGlobal(pos))
                if action == act_web:
                    self.open_in_webview(u, t)
                elif action == act_copy:
                    self.copy_url_to_clipboard(u, t)
                elif action == act_browser:
                    webbrowser.open(u)

            btn_view.customContextMenuRequested.connect(on_context_menu)

            btn_copy.setToolTip("کپی مستقیم آدرس پرونده به حافظه موقت")
            def on_copy_click(_, u=normalized_url, t=title, b=btn_copy):
                self.copy_url_to_clipboard(u, t)
                b.setText("✅")
                QTimer.singleShot(1600, lambda: b.setText("📋"))

            btn_copy.clicked.connect(on_copy_click)
        else:
            btn_view.setEnabled(False)
            btn_view.setToolTip("لینک پرونده موجود نیست")
            btn_copy.setEnabled(False)
            btn_copy.setToolTip("لینک پرونده موجود نیست")

        hlayout.addWidget(btn_view)
        hlayout.addWidget(btn_copy)
        return container

    def _risk_colors(self, risk: str):
        if self._dark_active:
            if risk == 'high':
                return QColor("#7F1D1D"), QColor("#FECACA")
            return QColor("#78350F"), QColor("#FDE68A")
        if risk == 'high':
            return QColor("#FEE2E2"), QColor("#991B1B")
        return QColor("#FEF3C7"), QColor("#92400E")

    def _make_action_item(self, url: str, title: str = "") -> QTableWidgetItem:
        item = QTableWidgetItem()
        normalized = self._normalize_url(url)
        item.setData(Qt.ItemDataRole.UserRole, {"url": normalized, "title": title})
        if normalized:
            item.setToolTip("کلیک چپ: مشاهده در وب‌ویو یا کپی لینک | راست کلیک: گزینه‌ها")
        else:
            item.setToolTip("لینک پرونده موجود نیست")
        return item

    def _set_table_active_row_items(self, row: int, r: dict):
        r = ensure_record_fields(dict(r))
        title = r.get('title', '')
        dec_no = r.get('dec_no_display') or r.get('declaration_no', '')
        title_fa = r.get('title_fa') or title
        title_en = r.get('title_en', '')
        reg_no = r.get('register_no', '')
        reg_date = r.get('reg_date') or r.get('declaration_date', '')
        renewal = r.get('renewal_date', '')
        cert_url = r.get('certificate_url') or r.get('detail_url', '')

        self.table_active.setItem(row, 0, NumericTableWidgetItem(row + 1))
        self.table_active.setItem(row, 1, QTableWidgetItem(str(dec_no or "—")))
        self.table_active.setItem(row, 2, QTableWidgetItem(str(title_en or "—")))
        self.table_active.setItem(row, 3, QTableWidgetItem(str(title_fa or "—")))

        status_item = QTableWidgetItem(r.get('status', ''))
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setForeground(QColor("#15803D") if not self._dark_active else QColor("#4ADE80"))
        self.table_active.setItem(row, 4, status_item)

        self.table_active.setItem(row, 5, QTableWidgetItem(str(reg_no or "—")))
        self.table_active.setItem(row, 6, DateTableWidgetItem(str(reg_date or "")))
        self.table_active.setItem(row, 7, DateTableWidgetItem(str(renewal or "")))
        self.table_active.setItem(row, 8, self._make_action_item(cert_url, title))

    def _set_table_class5_row_items(self, row: int, r: dict):
        title = r.get('title', '')
        classes = r.get('classes', '')
        if isinstance(classes, list):
            classes = ','.join(map(str, classes))

        self.table_class5.setItem(row, 0, NumericTableWidgetItem(row + 1))
        self.table_class5.setItem(row, 1, QTableWidgetItem(title))
        self.table_class5.setItem(row, 2, QTableWidgetItem(
            r.get('dec_no_display') or r.get('declaration_no', '')
        ))
        self.table_class5.setItem(row, 3, QTableWidgetItem(
            r.get('declaration_date') or r.get('reg_date', '')
        ))

        status = r.get('status', '')
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if r.get('is_rejected'):
            status_item.setForeground(QColor("#DC2626") if not self._dark_active else QColor("#F87171"))
        elif r.get('is_active') or is_finally_registered(status):
            status_item.setForeground(QColor("#15803D") if not self._dark_active else QColor("#4ADE80"))
        self.table_class5.setItem(row, 4, status_item)

        self.table_class5.setItem(row, 5, QTableWidgetItem(str(classes)))
        self.table_class5.setItem(row, 6, self._make_action_item(r.get('detail_url', ''), title))

    def _set_table_matched_row_items(self, row: int, m: dict):
        score = float(m.get('score', 0.0))
        risk = m.get('risk', 'medium')
        risk_fa = "● شباهت بالا" if risk == 'high' else "● شباهت متوسط"
        bg, fg = self._risk_colors(risk)

        self.table_matched.setItem(row, 0, NumericTableWidgetItem(row + 1))

        item_score = NumericTableWidgetItem(score, f"{score:.0f}٪")
        item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_score.setBackground(bg)
        item_score.setForeground(fg)
        self.table_matched.setItem(row, 1, item_score)

        item_risk = QTableWidgetItem(risk_fa)
        item_risk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_risk.setForeground(fg)
        self.table_matched.setItem(row, 2, item_risk)

        title_a = m.get('title_a', '')
        title_b = m.get('title_b', '')
        dec_a = m.get('declaration_no_a', '')
        dec_b = m.get('declaration_no_b', '')
        date_a = m.get('declaration_date_a', '')
        date_b = m.get('declaration_date_b', '')

        self.table_matched.setItem(row, 3, QTableWidgetItem(title_a))
        self.table_matched.setItem(row, 4, QTableWidgetItem(dec_a))
        self.table_matched.setItem(row, 5, QTableWidgetItem(title_b))
        self.table_matched.setItem(row, 6, QTableWidgetItem(dec_b))
        self.table_matched.setItem(row, 7, QTableWidgetItem(date_a if date_a == date_b else f"{date_a} / {date_b}"))
        self.table_matched.setItem(row, 8, self._make_action_item(m.get('detail_url_a', ''), title_a))
        self.table_matched.setItem(row, 9, self._make_action_item(m.get('detail_url_b', ''), title_b))

    def _set_table_all_row_items(self, row: int, r: dict):
        r = ensure_record_fields(dict(r))
        title = r.get('title', '')
        dec_no = r.get('dec_no_display') or r.get('declaration_no', '')
        title_fa = r.get('title_fa') or title
        title_en = r.get('title_en', '')
        reg_no = r.get('register_no', '')
        reg_date = r.get('reg_date') or r.get('declaration_date', '')
        renewal = r.get('renewal_date', '')
        cert_url = r.get('certificate_url') or r.get('detail_url', '')

        self.table_all.setItem(row, 0, NumericTableWidgetItem(row + 1))
        self.table_all.setItem(row, 1, QTableWidgetItem(str(dec_no or "—")))
        self.table_all.setItem(row, 2, QTableWidgetItem(str(title_en or "—")))
        self.table_all.setItem(row, 3, QTableWidgetItem(str(title_fa or "—")))
        self.table_all.setItem(row, 4, QTableWidgetItem(r.get('status', '')))
        self.table_all.setItem(row, 5, QTableWidgetItem(str(reg_no or "—")))
        self.table_all.setItem(row, 6, DateTableWidgetItem(str(reg_date or "")))
        self.table_all.setItem(row, 7, DateTableWidgetItem(str(renewal or "")))
        self.table_all.setItem(row, 8, self._make_action_item(cert_url, title))

    def add_to_table_active(self, r: dict):
        sorting = self.table_active.isSortingEnabled()
        self.table_active.setSortingEnabled(False)
        row = self.table_active.rowCount()
        self.table_active.insertRow(row)
        self._set_table_active_row_items(row, r)
        self.table_active.setSortingEnabled(sorting)
        self._schedule_auto_fit(self.table_active)

    def add_to_table_class5(self, r: dict):
        sorting = self.table_class5.isSortingEnabled()
        self.table_class5.setSortingEnabled(False)
        row = self.table_class5.rowCount()
        self.table_class5.insertRow(row)
        self._set_table_class5_row_items(row, r)
        self.table_class5.setSortingEnabled(sorting)
        self._schedule_auto_fit(self.table_class5)

    def add_to_table_matched(self, m: dict):
        sorting = self.table_matched.isSortingEnabled()
        self.table_matched.setSortingEnabled(False)
        row = self.table_matched.rowCount()
        self.table_matched.insertRow(row)
        self._set_table_matched_row_items(row, m)
        self.table_matched.setSortingEnabled(sorting)
        self._schedule_auto_fit(self.table_matched)

    def add_to_table_all(self, r: dict):
        sorting = self.table_all.isSortingEnabled()
        self.table_all.setSortingEnabled(False)
        row = self.table_all.rowCount()
        self.table_all.insertRow(row)
        self._set_table_all_row_items(row, r)
        self.table_all.setSortingEnabled(sorting)
        self._schedule_auto_fit(self.table_all)

    def _on_table_all_double_click(self, row: int, col: int):
        item = self.table_all.item(row, 8)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("url"):
                self.open_in_webview(data["url"], data.get("title", ""))

    def _on_table_active_double_click(self, row: int, col: int):
        item = self.table_active.item(row, 8)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("url"):
                self.open_in_webview(data["url"], data.get("title", ""))

    def _on_table_class5_double_click(self, row: int, col: int):
        item = self.table_class5.item(row, 6)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("url"):
                self.open_in_webview(data["url"], data.get("title", ""))

    def _on_table_matched_double_click(self, row: int, col: int):
        target_col = 9 if col in (5, 6, 7, 9) else 8
        item = self.table_matched.item(row, target_col)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("url"):
                self.open_in_webview(data["url"], data.get("title", ""))


    def on_scan_completed(self, scan_id: int, excel_path: str, total: int, alerts: int):
        self._ensure_scan_buttons_reset()
        self.last_excel_path = excel_path
        self.current_scan_id = scan_id
        self.progress_bar.setValue(100)
        self.load_captcha()
        self._refresh_store_counts()
        self._refresh_stats()

        if total == 0:
            self._set_state("نتیجه‌ای نبود", "idle")
            self.lbl_status.setText("اسکن تمام شد — رکوردی با این فیلترها پیدا نشد.")
            self.tabs_mode2.setCurrentIndex(0)
            self.auto_fit_table_columns(self.table_class5)
        else:
            self._set_state("تکمیل شد", "success")
            self.lbl_status.setText(
                f"جستجو تمام شد — {total} رکورد استخراج گردید. "
                "برای یافتن موارد مشابه دکمه «مقایسه هوشمند با پرونده‌ها» را بزنید."
            )
            self.tabs_mode2.setCurrentIndex(0)
            self.auto_fit_table_columns(self.table_class5)

        msg = f"کل رکوردهای استخراج‌شده: {total}"
        msg += f"\n\nتعداد کل در مخزن جستجو: {self._class5_store_count}"
        msg += "\n\nقدم بعدی: دکمه «🔄 مقایسه هوشمند با پرونده‌ها» را بزنید تا تب موارد منطبق تکمیل گردد."
        self._msg("information", "اتمام جستجوی علائم تجاری", msg)

    def on_scan_failed(self, error_msg: str):
        self._ensure_scan_buttons_reset()
        self._set_state("خطای اتصال", "error")
        self.lbl_status.setText(f"خطا: {error_msg}")
        self._msg("critical", "خطا در ارتباط با سامانه ثبت", error_msg)
        self.load_captcha()

    def on_scan_cancelled(self):
        self._ensure_scan_buttons_reset()
        self._refresh_store_counts()
        self._refresh_stats()
        self._set_state("متوقف شد", "idle")
        self.lbl_status.setText("اسکن توسط کاربر متوقف گردید.")
        self.load_captcha()

    def _ensure_scan_buttons_reset(self):
        if hasattr(self, 'btn_today_issues'):
            self.btn_today_issues.setEnabled(True)
        if hasattr(self, 'btn_search'):
            self.btn_search.setEnabled(True)
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setEnabled(False)
        if hasattr(self, 'btn_clear_search'):
            self.btn_clear_search.setEnabled(True)
        if hasattr(self, 'btn_clear_mode2_tb'):
            self.btn_clear_mode2_tb.setEnabled(True)

    def export_current_excel(self):
        """ساخت گزارش اکسل متناسب با حالت فعال و باز کردن آن."""
        try:
            data_store = load_store(DATA_STORE_PATH)
            if self._current_mode == 0:
                all_recs = [ensure_record_fields(dict(r)) for r in data_store.values()]
                active_recs = [
                    r for r in all_recs
                    if r.get('is_active') or is_finally_registered(r.get('status', ''))
                ]
                if not all_recs:
                    self._msg("information", "داده‌ای نیست",
                              "هنوز رکوردی در مخزن داده‌ها ذخیره نشده است.\nابتدا اسکن لیست عمومی را اجرا فرمایید.")
                    return
                path = export_scan_to_excel(
                    scan_info={'scan_date': time.strftime("%Y/%m/%d %H:%M")},
                    all_records=all_recs,
                    active=active_recs,
                    prefix="گزارش_حالت_۱",
                )
            else:
                class5_recs = list(load_class5_store().values())
                if not class5_recs and not self._matched_results:
                    self._msg("information", "داده‌ای نیست",
                              "هنوز رکوردی از جستجوی هدفمند استخراج نشده است.\nابتدا جستجو را اجرا فرمایید.")
                    return
                path = export_scan_to_excel(
                    scan_info={'scan_date': time.strftime("%Y/%m/%d %H:%M")},
                    class5_records=class5_recs,
                    matched=self._matched_results if self._matched_results else [],
                    prefix="گزارش_حالت_۲",
                )
            self.last_excel_path = path
            logger.info(f"گزارش اکسل ساخته شد: {path}")
            if hasattr(os, "startfile"):
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                webbrowser.open(f"file://{path}")
        except Exception as e:
            logger.error(f"خطا در ساخت گزارش اکسل: {e}")
            self._msg("warning", "خطا", f"ساخت فایل اکسل ممکن نشد:\n{e}")

    def open_reports_dir(self):
        os.makedirs(DEFAULT_REPORTS_DIR, exist_ok=True)
        try:
            if hasattr(os, "startfile"):
                os.startfile(DEFAULT_REPORTS_DIR)  # type: ignore[attr-defined]
            else:
                webbrowser.open(f"file://{DEFAULT_REPORTS_DIR}")
        except Exception as e:
            self._msg("warning", "خطا", f"باز کردن پوشه ممکن نشد:\n{e}")

    # ------------------------------------------------------------------
    # DeclarationList Scraper & In-App Authentication Methods
    # ------------------------------------------------------------------
    def check_session_on_startup(self):
        """بررسی نشست ذخیره‌شده هنگام شروع برنامه؛ فقط در صورت انقضای واقعی لاگین می‌خواهد."""
        try:
            saved_name = get_saved_user_name()
            if saved_name:
                self.lbl_session_status.setText(f"⏳ در حال بررسی نشست ذخیره‌شده ({saved_name})…")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #64748B;")
                self.btn_login_session.setText("تغییر حساب")
                self.btn_logout_session.setVisible(True)
                # اعتبارسنجی واقعی با سرور در نخ پس‌زمینه تا رابط قفل نشود
                self._session_check_worker = SessionCheckWorker(self)
                self._session_check_worker.session_checked.connect(self.on_session_check_finished)
                self._session_check_worker.start()
            else:
                self.lbl_session_status.setText("⚠️ نیاز به ورود به سامانه")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #D97706;")
                self.btn_login_session.setText("ورود به سامانه")
                self.btn_logout_session.setVisible(False)
        except Exception:
            pass

    def on_session_check_finished(self, status: str, info: str):
        """نتیجه بررسی نشست ذخیره‌شده: معتبر → بدون لاگین؛ منقضی → درخواست ورود."""
        try:
            if status == "valid":
                self.lbl_session_status.setText(f"✅ نشست فعال: {info} (بدون نیاز به ورود مجدد)")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #15803D;")
                self.btn_login_session.setText("تغییر حساب")
                self.btn_logout_session.setVisible(True)
                logger.info(f"نشست ذخیره‌شده معتبر است: {info}")
            elif status == "expired":
                from scanner.auth import clear_saved_session
                clear_saved_session()
                self.lbl_session_status.setText("⚠️ نشست قبلی منقضی شده — لطفاً دوباره وارد شوید")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #D97706;")
                self.btn_login_session.setText("ورود به سامانه")
                self.btn_logout_session.setVisible(False)
            else:  # unknown: خطای شبکه — سشن حفظ می‌شود و لاگین خواسته نمی‌شود
                saved_name = get_saved_user_name() or "کاربر سامانه"
                self.lbl_session_status.setText(f"💾 نشست ذخیره‌شده: {saved_name} (بررسی نشد)")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #64748B;")
                self.btn_login_session.setText("تغییر حساب")
                self.btn_logout_session.setVisible(True)
                logger.warning(f"وضعیت نشست نامشخص ماند، سشن حفظ شد: {info}")
        except Exception:
            pass

    def on_logout_session_clicked(self):
        """خروج صریح از حساب و حذف نشست ذخیره‌شده (تنها راه پایان دادن به لاگین دائمی)."""
        reply = QMessageBox.question(
            self,
            "تأیید خروج از حساب",
            "آیا مطمئن هستید که می‌خواهید از حساب خارج شوید؟\n\n"
            "با این کار نشست ذخیره‌شده حذف می‌شود و برای استفاده بعدی باید دوباره وارد شوید.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from scanner.auth import clear_saved_session
            clear_saved_session()
        except Exception as e:
            logger.error(f"خطا در خروج از حساب: {e}")
        self.lbl_session_status.setText("⚠️ نیاز به ورود به سامانه")
        self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #D97706;")
        self.btn_login_session.setText("ورود به سامانه")
        self.btn_logout_session.setVisible(False)
        self.lbl_decl_status.setText("از حساب خارج شدید.")

    def on_login_session_clicked(self):
        logger.info("کاربر روی دکمه ورود / تغییر حساب کلیک کرد.")
        self.lbl_decl_status.setText("در حال باز کردن پنجره ورود به سامانه…")
        self.btn_login_session.setEnabled(False)
        self._login_worker = LoginWorker(self)
        self._login_worker.status_updated.connect(lambda msg: self.lbl_decl_status.setText(msg))
        self._login_worker.login_finished.connect(self._on_login_finished)
        self._login_worker.start()

    def _on_login_finished(self, success: bool, user_name: str):
        self.btn_login_session.setEnabled(True)
        if success:
            logger.info(f"ورود موفق کاربر: {user_name}")
            self.lbl_session_status.setText(f"✅ نشست فعال: {user_name}")
            self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #15803D;")
            self.btn_login_session.setText("تغییر حساب")
            self.btn_logout_session.setVisible(True)
            self.lbl_decl_status.setText(f"ورود موفق: {user_name}")

            # بررسی وجود اطلاعات اسکن‌شده قبلی برای این حساب
            from scanner.auth import has_account_saved_data, restore_account_data
            has_data, prev_count, last_date = has_account_saved_data(user_name)
            self._refresh_store_counts()

            if has_data:
                date_str = f" (تاریخ ثبت: {last_date})" if last_date else ""
                reply = QMessageBox.question(
                    self,
                    "بازیابی اطلاعات جلسه قبلی",
                    f"شما با حساب «{user_name}» وارد شدید.\n\n"
                    f"سوابق اسکن‌شده قبلی این حساب{date_str} شامل {prev_count} رکورد در سیستم موجود است.\n\n"
                    f"آیا مایلید اطلاعات جلسه قبلی بازیابی و در جدول‌های برنامه بارگذاری شود؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    store, docx_path = restore_account_data(user_name)
                    self.load_store_into_gui(store)
                    self.lbl_decl_status.setText(f"اطلاعات قبلی {user_name} ({len(store)} رکورد) بارگذاری شد.")
                    self._msg("information", "بازیابی موفق", f"تعداد {len(store)} رکورد از جلسه قبلی با موفقیت بارگذاری گردید.")
                else:
                    self.lbl_decl_status.setText("آماده برای اسکن جدید.")
            else:
                self._msg("information", "ورود موفق", f"ورود با موفقیت انجام شد.\nحساب کاربری: {user_name}")
        else:
            logger.warning(f"ورود ناموفق یا بسته شدن پنجره: {user_name}")
            self.lbl_decl_status.setText("فرآیند ورود انجام نشد.")
            self._msg("warning", "خطای ورود", f"ورود انجام نشد یا پنجره بسته شد:\n{user_name}")

    @staticmethod
    def _mode1_date_key(r: dict) -> tuple:
        """کلید مرتب‌سازی تاریخ ثبت؛ هر دو فرمت سال/ماه/روز و روز/ماه/سال پشتیبانی می‌شود."""
        y, m, d, hh, mm = _parse_jalali_key(str(r.get('reg_date') or r.get('declaration_date') or ''))
        dec_raw = str(r.get('dec_no_display') or r.get('declaration_no') or r.get('dec_no_id') or '0')
        dec_en = re.sub(r'\D', '', to_english_digits(dec_raw)) or '0'
        try:
            dec_num = int(dec_en)
        except ValueError:
            dec_num = 0
        return (y, m, d, hh, mm, dec_num)

    def _sorted_mode1(self, records: list) -> list:
        """مرتب‌سازی بر اساس انتخاب کاربر: جدیدترین اول یا قدیمی‌ترین اول."""
        reverse = (self._mode1_sort != "oldest")
        return sorted(records, key=self._mode1_date_key, reverse=reverse)

    def on_mode1_sort_changed(self, index: int):
        """تغییر ترتیب نمایش جدول‌های حالت ۱ و بارگذاری مجدد از مخزن."""
        data = self.combo_mode1_sort.itemData(index) if hasattr(self, 'combo_mode1_sort') else "newest"
        self._mode1_sort = str(data or "newest")
        if self._mode1_sort not in ("newest", "oldest"):
            self._mode1_sort = "newest"
        try:
            self.settings.setValue("mode1_sort", self._mode1_sort)
        except Exception:
            pass
        try:
            store = load_store(DATA_STORE_PATH)
            if store:
                self.load_store_into_gui(store)
        except Exception as e:
            logger.warning(f"اعمال ترتیب نمایش ممکن نشد: {e}")

    def load_store_into_gui(self, store: dict):
        """بارگذاری فوق‌سریع و بهینه رکوردهای ذخیره‌شده جلسه قبلی در تب‌های حالت ۱."""
        self._reset_mode1_tables()
        self._total = 0
        self._active = 0
        self._rejected = 0

        if not store:
            self._refresh_store_counts()
            self._refresh_stats()
            return

        all_records = self._sorted_mode1(list(store.values()))
        active_records = [
            r for r in all_records
            if r.get('is_active') or is_finally_registered(r.get('status', ''))
        ]
        self._total = len(all_records)
        self._active = len(active_records)
        self._rejected = sum(1 for r in all_records if r.get('is_rejected'))

        sorting_all = self.table_all.isSortingEnabled()
        sorting_act = self.table_active.isSortingEnabled()
        self.table_all.setSortingEnabled(False)
        self.table_active.setSortingEnabled(False)
        self.table_all.setUpdatesEnabled(False)
        self.table_active.setUpdatesEnabled(False)

        try:
            self.table_all.setRowCount(len(all_records))
            for row, r in enumerate(all_records):
                self._set_table_all_row_items(row, r)

            self.table_active.setRowCount(len(active_records))
            for row, r in enumerate(active_records):
                self._set_table_active_row_items(row, r)
        finally:
            self.table_all.setUpdatesEnabled(True)
            self.table_active.setUpdatesEnabled(True)
            self.table_all.setSortingEnabled(sorting_all)
            self.table_active.setSortingEnabled(sorting_act)
            self._schedule_auto_fit(self.table_all)
            self._schedule_auto_fit(self.table_active)
            self._refresh_stats()

        self._refresh_store_counts()
        if self._current_mode == 0:
            self.tabs_mode1.setCurrentIndex(0)

    def closeEvent(self, event):
        """هنگام بستن برنامه فقط نخ‌ها متوقف می‌شوند؛ نشست لاگین حفظ می‌شود تا ورود دائمی بماند."""
        logger.info("بستن برنامه: توقف نخ‌های فعال (نشست لاگین حفظ می‌شود)...")
        try:
            if hasattr(self, "decl_worker") and self.decl_worker and self.decl_worker.isRunning():
                self.decl_worker.stop()
                self.decl_worker.wait(1000)
            if hasattr(self, "current_worker") and self.current_worker and self.current_worker.isRunning():
                self.current_worker.cancel()
                self.current_worker.wait(1000)
            if hasattr(self, "_comparison_worker") and self._comparison_worker and self._comparison_worker.isRunning():
                self._comparison_worker.quit()
                self._comparison_worker.wait(1000)
        except Exception:
            pass

        event.accept()


    def start_declaration_scan(self, mode: str):
        logger.info(f"شروع فرآیند اسکن اظهارنامه‌ها با مود: '{mode}'")
        # ریست فقط تب‌های حالت ۱ در صورت اسکن کامل — در حالت new_only داده‌های قبلی حفظ می‌شوند
        if mode == "full_rescan":
            self._reset_mode1_tables()
            self._total = 0
            self._active = 0
            self._rejected = 0
            self._refresh_stats()

        # نمایش زنده در تب ALL SCRAPED RECORDS
        if self._current_mode != 0:
            self.combo_mode.setCurrentIndex(0)
        self.tabs_mode1.setCurrentIndex(0)

        self.btn_decl_new.setEnabled(False)
        self.btn_decl_full.setEnabled(False)
        self.btn_decl_stop.setEnabled(True)
        if hasattr(self, 'btn_decl_clear'):
            self.btn_decl_clear.setEnabled(False)
        self.decl_progress_bar.setValue(0)
        self._set_state("در حال اسکن لیست عمومی…", "running")
        self.lbl_decl_status.setText("آغاز استخراج اظهارنامه‌ها…")

        self.decl_worker = DeclarationScrapeWorker(mode=mode, max_pages=500)
        self.decl_worker.progress_changed.connect(self.on_decl_progress)
        self.decl_worker.record_found.connect(self._on_mode1_record)
        self.decl_worker.scan_completed.connect(self.on_decl_scan_completed)
        self.decl_worker.scan_cancelled.connect(self.on_decl_scan_cancelled)
        self.decl_worker.scan_failed.connect(self.on_decl_scan_failed)
        self.decl_worker.finished.connect(self._ensure_decl_buttons_reset)
        self.decl_worker.start()

    def stop_declaration_scan(self):
        if self.decl_worker:
            logger.info("درخواست توقف اسکن توسط کاربر ارسال شد.")
            self.decl_worker.stop()
            self.lbl_decl_status.setText("در حال توقف اسکن…")
            self.btn_decl_stop.setEnabled(False)

    def on_decl_progress(self, pct: int, msg: str):
        self.decl_progress_bar.setValue(pct)
        self.lbl_decl_status.setText(msg)

    def on_decl_scan_completed(self, total: int, new_count: int, alerts: int, docx_path: str):
        logger.info(f"اسکن لیست اظهارنامه‌ها تکمیل شد. کل: {total}، جدید: {new_count}")
        # بارگذاری مجدد استور در جدول‌ها تا تمامی رکوردهای قدیمی و جدید همراه با آمار دقیق نمایش داده شوند
        store = load_store(DATA_STORE_PATH)
        if store:
            self.load_store_into_gui(store)

        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        self._refresh_store_counts()
        self._set_state("تکمیل شد", "success")
        msg = (
            f"اسکن لیست عمومی با موفقیت به پایان رسید.\n"
            f"کل رکوردهای موجود در مخزن: {total}\n"
            f"موارد جدید افزوده شده: {new_count}\n"
            f"رکوردهای «ثبت قطعی شده»: {self._active}"
        )
        self.lbl_decl_status.setText(f"اسکن پایان یافت. {new_count} مورد جدید ثبت شد.")
        self._msg("information", "اتمام اسکن لیست عمومی", f"{msg}\n\nفایل جدول ورد در مسیر زیر به‌روزرسانی گردید:\n{docx_path}")

    def on_decl_scan_cancelled(self):
        logger.info("اسکن لیست اظهارنامه‌ها متوقف شد.")
        store = load_store(DATA_STORE_PATH)
        if store:
            self.load_store_into_gui(store)
        self._refresh_store_counts()
        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        self._set_state("متوقف شد", "idle")
        self.lbl_decl_status.setText("اسکن توسط کاربر متوقف گردید.")

    def _ensure_decl_buttons_reset(self):
        self._refresh_store_counts()
        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        if hasattr(self, 'btn_decl_clear'):
            self.btn_decl_clear.setEnabled(True)

    def on_decl_scan_failed(self, error_msg: str):
        logger.error(f"اسکن اظهارنامه‌ها با شکست مواجه شد: {error_msg}")
        self._refresh_store_counts()
        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        self._set_state("خطای اسکن", "error")
        self.lbl_decl_status.setText("اسکن متوقف شد.")
        self._msg("critical", "خطا در اسکن لیست عمومی", error_msg)

    # ------------------------------------------------------------------
    # Mode 2 — manual comparison (no auto-compare)
    # ------------------------------------------------------------------
    def run_comparison(self):
        """مقایسه هوشمند عناوین پرونده‌های مرجع با رکوردهای استخراج‌شده — فقط با فشردن دکمه."""
        self._refresh_store_counts()
        if self._data_store_count == 0:
            self._msg(
                "warning", "عناوین مرجع یافت نشد",
                "هنوز عنوانی در بخش اظهارنامه‌های کاربر ذخیره نشده است.\n"
                "ابتدا در بخش پایش عمومی یک اسکن اجرا کنید."
            )
            return
        if self._class5_store_count == 0:
            self._msg(
                "warning", "رکوردهای جستجو یافت نشد",
                "هنوز رکوردی از جستجوی هدفمند در مخزن ذخیره نشده است.\n"
                "ابتدا جستجوی علائم تجاری را اجرا کنید."
            )
            return

        logger.info(
            f"شروع مقایسه هوشمند: عناوین مرجع={self._data_store_count} × "
            f"رکوردهای استخراج‌شده={self._class5_store_count}"
        )
        self.btn_compare.setEnabled(False)
        self.btn_compare.setText("در حال مقایسه…")
        self.lbl_status.setText("در حال مقایسه عنوان‌ها بدون مسدودسازی رابط کاربری…")

        self._comparison_worker = ComparisonWorker(self)
        self._comparison_worker.comparison_finished.connect(self._on_comparison_finished)
        self._comparison_worker.comparison_failed.connect(self._on_comparison_failed)
        self._comparison_worker.start()

    def _on_comparison_finished(self, matches: list):
        self._matched_results = matches
        self._reset_matched_table_only()
        self._matched = len(matches)
        self._matched_high = sum(1 for m in matches if m.get('risk') == 'high')
        self._matched_medium = self._matched - self._matched_high

        sorting = self.table_matched.isSortingEnabled()
        self.table_matched.setSortingEnabled(False)
        self.table_matched.setUpdatesEnabled(False)
        self.table_matched.setRowCount(len(matches))
        try:
            for row, m in enumerate(matches):
                self._set_table_matched_row_items(row, m)
        finally:
            self.table_matched.setUpdatesEnabled(True)
            self.table_matched.setSortingEnabled(sorting)

        self.btn_compare.setText("🔄 مقایسه هوشمند با پرونده‌ها")
        self._update_compare_button_state()
        self._refresh_stats()
        self.tabs_mode2.setCurrentIndex(1)
        self.auto_fit_table_columns(self.table_matched)

        if matches:
            self.lbl_status.setText(
                f"مقایسه انجام شد: {self._matched} مورد مشابه "
                f"({self._matched_high} خطر بالا، {self._matched_medium} خطر متوسط)."
            )
            self._msg(
                "information", "مقایسه کامل شد",
                f"تعداد منطبق‌ها: {self._matched}\n"
                f"خطر بالا: {self._matched_high}\n"
                f"خطر متوسط: {self._matched_medium}\n\n"
                "نتایج در تب موارد منطبق نمایش داده شد."
            )
        else:
            self.lbl_status.setText("مقایسه انجام شد — موردی بالای ۷۰٪ شباهت یافت نشد.")
            self._msg(
                "information", "بدون نتیجه",
                "هیچ جفتی بالای ۷۰٪ شباهت بین عناوین مرجع و رکوردهای استخراج‌شده یافت نشد."
            )

    def _on_comparison_failed(self, error_msg: str):
        logger.error(f"خطا در مقایسه فروشگاه‌ها: {error_msg}")
        self.btn_compare.setText("🔄 مقایسه هوشمند با پرونده‌ها")
        self._update_compare_button_state()
        self.lbl_status.setText("خطا در انجام مقایسه.")
        self._msg("critical", "خطا در مقایسه", f"مقایسه انجام نشد:\n{error_msg}")

    def _reset_matched_table_only(self):
        self.table_matched.setRowCount(0)

    def _load_class5_table_from_store(self):
        """بارگذاری رکوردهای استخراج‌شده در تب رکوردهای یافت‌شده هنگام شروع برنامه."""
        store = load_class5_store()
        if not store:
            return
        c5_records = [
            e for e in store.values()
            if e.get('has_class_5') or not e.get('classes') or 5 in e.get('classes', [])
        ]
        self._class5 = len(c5_records)

        sorting = self.table_class5.isSortingEnabled()
        self.table_class5.setSortingEnabled(False)
        self.table_class5.setUpdatesEnabled(False)
        self.table_class5.setRowCount(len(c5_records))
        try:
            for row, entry in enumerate(c5_records):
                self._set_table_class5_row_items(row, entry)
        finally:
            self.table_class5.setUpdatesEnabled(True)
            self.table_class5.setSortingEnabled(sorting)
        self._schedule_auto_fit(self.table_class5)
        self._refresh_stats()

    def _load_data_store_table(self):
        """بارگذاری data_store در تب‌های حالت ۱ هنگام شروع برنامه."""
        store = load_store(DATA_STORE_PATH)
        if store:
            self.load_store_into_gui(store)

    def clear_advanced_search_data(self):
        """پاکسازی تمام رکوردهای استخراج‌شده و نتایج مقایسه و جداول مربوطه."""
        if hasattr(self, "current_worker") and self.current_worker and self.current_worker.isRunning():
            self._msg("warning", "اسکن در حال اجرا", "لطفاً ابتدا اسکن جاری را متوقف کنید، سپس اقدام به پاکسازی نمایید.")
            return

        reply = QMessageBox.question(
            self,
            "تأیید پاکسازی نتایج جستجو",
            "آیا مطمئن هستید که می‌خواهید تمام رکوردهای استخراج‌شده و نتایج مقایسه را پاک کنید؟\n\n"
            "با این کار اطلاعات جدول‌های «رکوردهای یافت‌شده» و «موارد منطبق» پاک شده و برای مقایسه باید مجدداً اسکن انجام دهید.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        logger.info("کاربر درخواست پاکسازی داده‌های استخراج‌شده و مقایسه را تأیید کرد.")
        save_class5_store({}, DATA_STORE_PATH)

        self.table_class5.setRowCount(0)
        self.table_matched.setRowCount(0)
        self._matched_results = []
        self._class5 = 0
        self._matched = 0
        self._matched_high = 0
        self._matched_medium = 0

        if hasattr(self, "class5_empty"):
            self.class5_empty.setVisible(True)
        if hasattr(self, "matched_empty"):
            self.matched_empty.setVisible(True)

        self.progress_bar.setValue(0)
        self._refresh_stats()
        self._refresh_store_counts()
        self._update_compare_button_state()

        self.lbl_status.setText("داده‌های استخراج‌شده و مقایسه پاکسازی شدند. برای شروع، اسکن جدید انجام دهید.")
        self._msg("information", "پاکسازی موفق", "تمامی رکوردهای استخراج‌شده و نتایج مقایسه با موفقیت پاک شدند.")

    def clear_declaration_list_data(self):
        """پاکسازی تمام داده‌های لیست اظهارنامه‌ها و جداول مربوطه."""
        if hasattr(self, "decl_worker") and self.decl_worker and self.decl_worker.isRunning():
            self._msg("warning", "اسکن در حال اجرا", "لطفاً ابتدا اسکن جاری را متوقف کنید، سپس اقدام به پاکسازی نمایید.")
            return

        reply = QMessageBox.question(
            self,
            "تأیید پاکسازی لیست اظهارنامه‌ها",
            "آیا مطمئن هستید که می‌خواهید تمام رکوردهای ذخیره‌شده اظهارنامه‌ها را پاک کنید؟\n\n"
            "با این کار جدول‌های «کل اظهارنامه‌های استخراج‌شده» و «فقط ثبت قطعی شده» خالی شده و باید مجدداً اسکن انجام دهید.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        logger.info("کاربر درخواست پاکسازی داده‌های اظهارنامه‌ها را تأیید کرد.")
        save_store({}, DATA_STORE_PATH)

        self.table_all.setRowCount(0)
        self.table_active.setRowCount(0)
        self._total = 0
        self._active = 0
        self._rejected = 0

        if hasattr(self, "all_empty"):
            self.all_empty.setVisible(True)
        if hasattr(self, "active_empty"):
            self.active_empty.setVisible(True)

        self.decl_progress_bar.setValue(0)
        self._refresh_stats()
        self._refresh_store_counts()
        self._update_compare_button_state()

        self.lbl_decl_status.setText("لیست اظهارنامه‌ها پاکسازی شد. برای شروع، اسکن جدید انجام دهید.")
        self._msg("information", "پاکسازی موفق", "تمامی رکوردهای اظهارنامه‌ها با موفقیت پاک شدند.")

    def open_current_word(self):
        docx_path = os.path.abspath(WORD_OUTPUT_PATH)
        if os.path.exists(docx_path):
            try:
                if hasattr(os, "startfile"):
                    os.startfile(docx_path)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f"file://{docx_path}")
            except Exception as e:
                self._msg("warning", "خطا", f"باز کردن سند ورد ممکن نشد:\n{e}")
        else:
            self._msg("information", "فایلی نیست",
                      "هنوز فایل سند ورد ساخته نشده است.\nلطفاً ابتدا یکی از اسکن‌های لیست عمومی را اجرا فرمایید.")



def run_app():
    # راه‌اندازی اولیه سیستم ثبت وقایع و لاگ‌ها
    setup_logging("DEBUG")

    # تنظیم شناسه پردازش ویندوز برای نمایش صحیح لوگو در تسک‌بار
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LegalScrap.SSAA.TrademarkMonitor.1.0")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    # تنظیم آیکون اختصاصی برای پنجره و تسک‌بار ویندوز
    base_proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_proj_dir, "assets", "logo.ico")
    png_path = os.path.join(base_proj_dir, "assets", "logo.png")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))
    elif os.path.exists(png_path):
        app.setWindowIcon(QIcon(png_path))

    try:
        if "Fusion" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("Fusion"))
    except Exception:
        pass
    window = TrademarkApp()
    if os.path.exists(ico_path):
        window.setWindowIcon(QIcon(ico_path))
    elif os.path.exists(png_path):
        window.setWindowIcon(QIcon(png_path))
    # پیگیری تغییرات تم روشن/تیره در سیستم‌عامل ویندوز
    try:
        hints = app.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(
                lambda *_: window.apply_theme(window._theme) if window._theme == "system" else None
            )
    except Exception:
        pass
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()

