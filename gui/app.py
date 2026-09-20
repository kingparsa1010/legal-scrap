"""
رابط کاربری دسکتاپ سامانه پایش و استخراج علائم تجاری
Persian RTL Desktop GUI — light/dark/system themes, responsive layout
"""
import sys
import os
import webbrowser
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QGroupBox, QSpinBox,
    QMessageBox, QFrame, QScrollArea, QSizePolicy, QAbstractItemView,
    QSplitter, QStyleFactory, QDialog, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor, QCursor, QPalette

from scanner.logger import (
    setup_logging, set_log_level, get_logger,
    get_log_file_path, read_latest_logs, clear_log_file
)
from scanner.client import SSAAClient
from scanner.worker import ScanWorker
from scanner.auth import check_session_alive, perform_browser_login
from scanner.declaration_worker import DeclarationScrapeWorker, WORD_OUTPUT_PATH
from scanner.database import (
    init_db, add_watchlist_item,
    get_all_scans, get_scan_declarations,
    save_search_history, get_search_history, DB_FILE
)
from scanner.exporter import export_scan_to_excel

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
QPushButton#Ghost { background: transparent; border: none; color: #2563EB; font-weight: bold; }
QPushButton#Ghost:hover { background: #EFF6FF; }
QPushButton#RowBtn { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;
    padding: 5px 10px; font-size: 8.5pt; border-radius: 6px; }
QPushButton#RowBtn:hover { background: #DBEAFE; }
QPushButton#RowBtn:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }

QLabel#CaptchaImage { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; color: #64748B; font-size: 9pt; }
QProgressBar { background: #E2E8F0; border: none; border-radius: 5px; height: 10px; text-align: center; font-size: 8pt; color: #475569; }
QProgressBar::chunk { background: #15803D; border-radius: 5px; }
QFrame#Stat { background: white; border: 1px solid #E2E8F0; border-radius: 12px; }

QTabWidget::pane { background: white; border: 1px solid #E2E8F0; border-radius: 0 0 12px 12px; }
QTabBar::tab { background: #E2E8F0; color: #475569; padding: 10px 22px; margin-left: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: bold; font-size: 9.5pt; }
QTabBar::tab:selected { background: white; color: #0F172A; border: 1px solid #E2E8F0; border-bottom: none; }
QTableWidget { background: white; border: none; gridline-color: #F1F5F9;
    alternate-background-color: #F8FAFC; font-size: 9pt; color: #0F172A; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: #DBEAFE; color: #0F172A; }
QHeaderView::section { background: #F8FAFC; color: #475569; font-weight: bold;
    padding: 10px 6px; border: none; border-bottom: 2px solid #E2E8F0; font-size: 9pt; }

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
QPushButton#Ghost { background: transparent; border: none; color: #7DD3FC; font-weight: bold; }
QPushButton#Ghost:hover { background: #16283F; }
QPushButton#RowBtn { background: #16283F; color: #7DD3FC; border: 1px solid #33507A;
    padding: 5px 10px; font-size: 8.5pt; border-radius: 6px; }
QPushButton#RowBtn:hover { background: #1E3A5F; }
QPushButton#RowBtn:disabled { background: #1E293B; color: #64748B; border-color: #334155; }

QLabel#CaptchaImage { background: #F8FAFC; border: 1px solid #33507A; border-radius: 10px; color: #475569; font-size: 9pt; }
QProgressBar { background: #1E293B; border: none; border-radius: 5px; height: 10px; text-align: center; font-size: 8pt; color: #CBD5E1; }
QProgressBar::chunk { background: #22C55E; border-radius: 5px; }
QFrame#Stat { background: #111C33; border: 1px solid #24334F; border-radius: 12px; }

QTabWidget::pane { background: #111C33; border: 1px solid #24334F; border-radius: 0 0 12px 12px; }
QTabBar::tab { background: #1E293B; color: #94A3B8; padding: 10px 22px; margin-left: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: bold; font-size: 9.5pt; }
QTabBar::tab:selected { background: #111C33; color: #F1F5F9; border: 1px solid #24334F; border-bottom: none; }
QTableWidget { background: #111C33; border: none; gridline-color: #1E293B;
    alternate-background-color: #0F1D33; font-size: 9pt; color: #E2E8F0; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: #1D4ED8; color: white; }
QHeaderView::section { background: #0B1830; color: #94A3B8; font-weight: bold;
    padding: 10px 6px; border: none; border-bottom: 2px solid #24334F; font-size: 9pt; }

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


class LoginWorker(QThread):
    """نخ پس‌زمینه اجرای فرآیند ورود به سامانه بدون انجماد رابط کاربری."""
    status_updated = pyqtSignal(str)
    login_finished = pyqtSignal(bool, str)

    def run(self):
        success, user_name = perform_browser_login(
            timeout_seconds=300,
            on_status_update=lambda msg: self.status_updated.emit(msg)
        )
        self.login_finished.emit(success, user_name)


class LogViewerDialog(QDialog):
    """پنجره مشاهده زنده و مدیریت فایل گزارش‌ها (Log Viewer)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("گزارش‌های سیستم (Log Viewer)")
        self.resize(920, 560)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # نوار ابزار بالا
        top_layout = QHBoxLayout()
        lbl_info = QLabel(f"مسیر فایل لاگ: {get_log_file_path()}", self)
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

        btn_clear = QPushButton("🗑️ پاکسازی لاگ", self)
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
            QMessageBox.information(self, "کپی شد", "متن لاگ‌ها در حافظه موقت (Clipboard) کپی شد.")

    def clear_logs(self):
        reply = QMessageBox.question(
            self, "تأیید پاکسازی",
            "آیا از پاک کردن کامل فایل لاگ اطمینان دارید؟",
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


class TrademarkApp(QMainWindow):

    """پنجره اصلی — سایدبار مرحله‌ای، آمار زنده، تم روشن/تیره/سیستم."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("سامانه پایش علائم تجاری | مرکز مالکیت معنوی")
        self.resize(1320, 880)
        self.setMinimumSize(1024, 680)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFont(QFont("Tahoma", 9))

        init_db()
        self.client = SSAAClient()
        self.current_worker: Optional[ScanWorker] = None
        self.decl_worker: Optional[DeclarationScrapeWorker] = None
        self.last_excel_path = ""
        self.current_scan_id = 0

        self._total = 0
        self._high = 0
        self._medium = 0
        self._rejected = 0

        self.settings = QSettings("LegalScrap", "TrademarkApp")
        self._theme = str(self.settings.value("theme", "light"))
        if self._theme not in ("light", "dark", "system"):
            self._theme = "light"
        self._dark_active = False

        self._log_level = str(self.settings.value("log_level", "DEBUG"))
        set_log_level(self._log_level)

        self.init_ui()
        self.apply_theme(self._theme)
        self.load_captcha()
        self.load_search_history_combo()
        self.check_session_on_startup()



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
        if not hasattr(self, "stat_total_value"):
            return
        if self._dark_active:
            self.stat_total_value.setStyleSheet("color:#F1F5F9;")
            self.stat_high_value.setStyleSheet("color:#FCA5A5;")
            self.stat_medium_value.setStyleSheet("color:#FCD34D;")
            self.stat_rejected_value.setStyleSheet("color:#94A3B8;")
        else:
            self.stat_total_value.setStyleSheet("color:#0F172A;")
            self.stat_high_value.setStyleSheet("color:#B91C1C;")
            self.stat_medium_value.setStyleSheet("color:#B45309;")
            self.stat_rejected_value.setStyleSheet("color:#64748B;")

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

        sidebar = self._build_sidebar()
        results = self._build_results()
        # RTL: first widget goes right → sidebar right, results left
        splitter.addWidget(sidebar)
        splitter.addWidget(results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 940])
        self.splitter = splitter

    def _build_header(self, parent_layout):
        header = QFrame(self)
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("سامانه پایش علائم تجاری", self)
        lbl_title.setObjectName("AppTitle")
        lbl_sub = QLabel("مرکز مالکیت معنوی • پایش و استخراج علائم تجاری", self)
        lbl_sub.setObjectName("AppSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        layout.addLayout(title_box)

        layout.addStretch()

        self.lbl_scan_state = QLabel("آماده", self)
        self.lbl_scan_state.setObjectName("StatePill")
        self.lbl_scan_state.setProperty("mood", "idle")
        layout.addWidget(self.lbl_scan_state)

        # انتخاب سطح لاگ (DEBUG, INFO, WARNING, ERROR)
        lbl_log = QLabel("سطح لاگ:", self)
        lbl_log.setStyleSheet("font-size: 8.5pt; color: #64748B; margin-right: 2px;")
        layout.addWidget(lbl_log)

        self.combo_log_level = QComboBox(self)
        self.combo_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.combo_log_level.setToolTip("انتخاب سطح جزئیات ثبت لاگ‌های سامانه")
        self.combo_log_level.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_log_level.setFixedWidth(95)
        curr_log_idx = self.combo_log_level.findText(self._log_level)
        if curr_log_idx >= 0:
            self.combo_log_level.setCurrentIndex(curr_log_idx)
        self.combo_log_level.currentTextChanged.connect(self._on_log_level_changed)
        layout.addWidget(self.combo_log_level)

        self.btn_view_logs = QPushButton("📋 گزارش لاگ‌ها", self)
        self.btn_view_logs.setObjectName("Secondary")
        self.btn_view_logs.setToolTip("مشاهده پنجره گزارش‌های سیستمی و خطایابی شبکه")
        self.btn_view_logs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_view_logs.clicked.connect(self.open_log_viewer)
        layout.addWidget(self.btn_view_logs)

        self.combo_theme = QComboBox(self)
        self.combo_theme.addItems(["تم روشن", "تم تیره", "تم سیستم"])
        self.combo_theme.setToolTip("انتخاب تم روشن / تیره / پیروی از ویندوز")
        self.combo_theme.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_theme.setFixedWidth(110)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.combo_theme)

        self.btn_open_reports_folder = QPushButton("پوشه گزارش‌ها", self)
        self.btn_open_reports_folder.setObjectName("Secondary")
        self.btn_open_reports_folder.setToolTip("باز کردن پوشه فایل‌های اکسل ذخیره‌شده")
        self.btn_open_reports_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_reports_folder.clicked.connect(self.open_reports_dir)
        layout.addWidget(self.btn_open_reports_folder)

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
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(420)
        scroll.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        inner = QWidget()
        inner.setObjectName("SidebarInner")
        sidebar_layout = QVBoxLayout(inner)
        sidebar_layout.setSpacing(4)
        sidebar_layout.setContentsMargins(2, 2, 6, 2)

        self.card_mode = self._build_mode_card()
        sidebar_layout.addWidget(self.card_mode)

        self.card_declaration_list = self._build_declaration_list_card()
        sidebar_layout.addWidget(self.card_declaration_list)

        self.card_captcha = self._build_captcha_card()
        sidebar_layout.addWidget(self.card_captcha)

        self.card_search = self._build_search_card()
        sidebar_layout.addWidget(self.card_search)

        self.card_run = self._build_run_card()
        sidebar_layout.addWidget(self.card_run)

        sidebar_layout.addStretch()

        scroll.setWidget(inner)
        scroll.setFixedWidth(360)

        # تنظیم حالت پیش‌فرض (لیست عمومی)
        self.on_mode_changed(0)
        return scroll

    def _build_mode_card(self) -> QGroupBox:
        card = QGroupBox("حالت پایش سامانه", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        self.combo_mode = QComboBox(self)
        self.combo_mode.addItem("⚡ پایش لیست عمومی اظهارنامه‌ها (DeclarationList)", "declaration_list")
        self.combo_mode.addItem("🔍 جستجوی هدفمند و پیشرفته (فیلتردار)", "targeted_search")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.combo_mode)
        return card

    def _build_declaration_list_card(self) -> QGroupBox:
        card = QGroupBox("پایش لیست عمومی (DeclarationList)", self)
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
        layout.addLayout(session_box)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(sep)

        # دکمه ۱: جستجوی موارد جدید
        self.btn_decl_new = QPushButton("🔍 جستجوی موارد جدید (سریع)", self)
        self.btn_decl_new.setObjectName("Primary")
        self.btn_decl_new.setMinimumHeight(44)
        self.btn_decl_new.setToolTip("استخراج موارد جدید و توقف خودکار در اولین رکورد تکراری قبلی")
        self.btn_decl_new.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_new.clicked.connect(lambda: self.start_declaration_scan(mode="new_only"))
        layout.addWidget(self.btn_decl_new)

        lbl_hint_new = QLabel("توقف در اولین رکورد تکراری و درج موارد جدید از ردیف ۱ Word", self)
        lbl_hint_new.setObjectName("Hint")
        lbl_hint_new.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hint_new)

        # دکمه ۲: اسکن کامل
        self.btn_decl_full = QPushButton("🔄 اسکن کامل (Full Rescan)", self)
        self.btn_decl_full.setObjectName("Secondary")
        self.btn_decl_full.setMinimumHeight(38)
        self.btn_decl_full.setToolTip("اسکن کامل تمامی صفحات تا ۱۰۱ رکورد")
        self.btn_decl_full.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_full.clicked.connect(lambda: self.start_declaration_scan(mode="full_rescan"))
        layout.addWidget(self.btn_decl_full)

        # دکمه ۳: توقف
        self.btn_decl_stop = QPushButton("توقف اسکن", self)
        self.btn_decl_stop.setObjectName("Secondary")
        self.btn_decl_stop.setEnabled(False)
        self.btn_decl_stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_decl_stop.clicked.connect(self.stop_declaration_scan)
        layout.addWidget(self.btn_decl_stop)

        # دکمه ۴: خروجی جدول Word
        self.btn_open_word = QPushButton("📝 خروجی جدول Word (brands.docx)", self)
        self.btn_open_word.setObjectName("Accent")
        self.btn_open_word.setMinimumHeight(40)
        self.btn_open_word.setToolTip("مشاهده فایل جدول‌بندی‌شده راست‌به‌چپ با لوگوهای تعبیه‌شده")
        self.btn_open_word.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_word.clicked.connect(self.open_current_word)
        layout.addWidget(self.btn_open_word)

        # پروگرس بار و پیام وضعیت
        self.decl_progress_bar = QProgressBar(self)
        self.decl_progress_bar.setRange(0, 100)
        self.decl_progress_bar.setValue(0)
        layout.addWidget(self.decl_progress_bar)

        self.lbl_decl_status = QLabel("آماده برای اسکن لیست عمومی.", self)
        self.lbl_decl_status.setObjectName("Hint")
        self.lbl_decl_status.setWordWrap(True)
        layout.addWidget(self.lbl_decl_status)

        return card

    def on_mode_changed(self, index: int):
        is_decl = (index == 0)
        self.card_declaration_list.setVisible(is_decl)
        self.card_captcha.setVisible(not is_decl)
        self.card_search.setVisible(not is_decl)
        self.card_run.setVisible(not is_decl)
        if hasattr(self, 'btn_export_word_tb'):
            self.btn_export_word_tb.setVisible(is_decl)


    def _build_captcha_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۱ — کد امنیتی", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        hint = QLabel("تصویر زیر را بخوانید و عدد ۴ رقمی را وارد کنید.", self)
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        vpn_note = QLabel("⚠️ برای دسترسی به سامانه ثبت، فیلترشکن (VPN) باید خاموش باشد.", self)
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
        self.txt_captcha = QLineEdit(self)
        self.txt_captcha.setObjectName("CaptchaInput")
        self.txt_captcha.setPlaceholderText("مثلاً ۴۸۲۱")
        self.txt_captcha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_captcha.setMaxLength(4)
        self.txt_captcha.setToolTip("کد امنیتی ۴ رقمی داخل تصویر")
        row.addWidget(self.txt_captcha, stretch=1)

        self.btn_refresh_captcha = QPushButton("کد جدید", self)
        self.btn_refresh_captcha.setObjectName("Secondary")
        self.btn_refresh_captcha.setToolTip("دریافت تصویر امنیتی جدید")
        self.btn_refresh_captcha.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh_captcha.clicked.connect(self.load_captcha)
        row.addWidget(self.btn_refresh_captcha)
        layout.addLayout(row)
        return card

    def _field(self, label_text: str, widget: QWidget, tooltip: str = "") -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(3)
        lbl = QLabel(label_text, self)
        lbl.setObjectName("FieldLabel")
        box.addWidget(lbl)
        if tooltip:
            widget.setToolTip(tooltip)
        box.addWidget(widget)
        return box

    def _build_search_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۲ — فیلتر جستجو", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.txt_from_date = QLineEdit(self)
        self.txt_from_date.setText("۱۴۰۴/۰۱/۰۱")
        self.txt_from_date.setPlaceholderText("۱۴۰۴/۰۱/۰۱")
        grid.addLayout(self._field("از تاریخ انتشار", self.txt_from_date, "تاریخ شروع بازه انتشار آگهی"), 0, 0)

        self.txt_to_date = QLineEdit(self)
        self.txt_to_date.setPlaceholderText("اختیاری — خالی = تا امروز")
        grid.addLayout(self._field("تا تاریخ انتشار", self.txt_to_date, "خالی بگذارید تا امروز در نظر گرفته شود"), 0, 1)

        self.txt_class = QLineEdit(self)
        self.txt_class.setPlaceholderText("مثلاً ۵ یا خالی برای تمام طبقات")
        self.txt_class.setText("")
        self.txt_class.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addLayout(self._field("طبقه بین‌المللی", self.txt_class, "شماره طبقه کالا و خدمات (یا خالی برای تمام طبقات)"), 1, 0)

        # FIX #4: QSpinBox in RTL overlapped buttons+text. Force LTR, centered
        # text, fixed button width and enough minimum width.
        self.spin_pages = QSpinBox(self)
        self.spin_pages.setRange(1, 100)
        self.spin_pages.setValue(15)
        self.spin_pages.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.spin_pages.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_pages.setMinimumWidth(110)
        self.spin_pages.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.spin_pages.setToolTip("هر صفحه حدود ۱۰ رکورد است. برای بازه بزرگ عدد بیشتری بگذارید.")
        grid.addLayout(self._field("سقف صفحات اسکن", self.spin_pages), 1, 1)

        layout.addLayout(grid)

        self.txt_target_brand = QLineEdit(self)
        self.txt_target_brand.setText("متاسنت Metacent")
        self.txt_target_brand.setPlaceholderText("نام برند خودتان — فارسی و لاتین")
        layout.addLayout(self._field(
            "برند مرجع (برند شما برای مقایسه شباهت)",
            self.txt_target_brand,
            "مثال: متاسنت Metacent — هشدارها نسبت به همین نام ساخته می‌شوند"
        ))

        self.btn_toggle_advanced = QPushButton("فیلترهای پیشرفته ▾", self)
        self.btn_toggle_advanced.setObjectName("Ghost")
        self.btn_toggle_advanced.setCheckable(True)
        self.btn_toggle_advanced.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_advanced.clicked.connect(self.toggle_advanced_panel)
        layout.addWidget(self.btn_toggle_advanced)

        self.advanced_box = QGroupBox("فیلترهای تکمیلی سامانه ثبت", self)
        self.advanced_box.setObjectName("SubCard")
        self.advanced_box.setVisible(False)
        adv = QGridLayout(self.advanced_box)
        adv.setHorizontalSpacing(8)
        adv.setVerticalSpacing(8)

        self.txt_item_title = QLineEdit(self)
        self.txt_item_title.setPlaceholderText("بخشی از نام علامت — خالی = همه")
        adv.addLayout(self._field("عنوان علامت", self.txt_item_title), 0, 0)

        self.combo_title_like = QComboBox(self)
        self.combo_title_like.addItems(["شامل و مشابه (۳)", "شروع شود با (۲)", "عین عبارت (۱)"])
        self.combo_title_like.setCurrentIndex(0)
        adv.addLayout(self._field("نوع تطابق عنوان", self.combo_title_like), 0, 1)

        self.txt_dec_no = QLineEdit(self)
        self.txt_dec_no.setPlaceholderText("اختیاری")
        adv.addLayout(self._field("شماره اظهارنامه", self.txt_dec_no), 1, 0)

        self.txt_reg_no = QLineEdit(self)
        self.txt_reg_no.setPlaceholderText("اختیاری")
        adv.addLayout(self._field("شماره ثبت", self.txt_reg_no), 1, 1)

        self.combo_person_type = QComboBox(self)
        self.combo_person_type.addItems(["حقیقی (۱)", "حقوقی (۲)"])
        adv.addLayout(self._field("نوع شخص مالک", self.combo_person_type), 2, 0)

        self.txt_owner_name = QLineEdit(self)
        self.txt_owner_name.setPlaceholderText("نام مالک")
        adv.addLayout(self._field("نام مالک", self.txt_owner_name), 2, 1)

        self.txt_owner_family = QLineEdit(self)
        self.txt_owner_family.setPlaceholderText("نام خانوادگی")
        adv.addLayout(self._field("نام خانوادگی مالک", self.txt_owner_family), 3, 0)

        self.txt_national_code = QLineEdit(self)
        self.txt_national_code.setPlaceholderText("کد ملی / شناسه ملی")
        adv.addLayout(self._field("کد / شناسه ملی", self.txt_national_code), 3, 1)

        layout.addWidget(self.advanced_box)
        return card

    def _build_run_card(self) -> QGroupBox:
        card = QGroupBox("مرحله ۳ — اجرا و نتیجه", self)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        self.btn_start = QPushButton("شروع اسکن", self)
        self.btn_start.setObjectName("Primary")
        self.btn_start.setMinimumHeight(46)
        self.btn_start.setToolTip("شروع استخراج اظهارنامه‌ها با فیلترهای بالا")
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.clicked.connect(self.start_scan)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("توقف اسکن", self)
        self.btn_stop.setObjectName("Secondary")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setToolTip("توقف اسکن جاری")
        self.btn_stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stop.clicked.connect(self.stop_scan)
        layout.addWidget(self.btn_stop)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
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

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_total_value, _ = self._stat_card(stats, "کل یافته‌ها", "0")
        self.stat_high_value, _ = self._stat_card(stats, "شباهت بالا", "0")
        self.stat_medium_value, _ = self._stat_card(stats, "شباهت متوسط", "0")
        self.stat_rejected_value, _ = self._stat_card(stats, "رد شده", "0")
        layout.addLayout(stats)

        toolbar = QFrame(self)
        toolbar.setObjectName("Header")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        lbl_hist = QLabel("جستجوهای قبلی:", self)
        tb.addWidget(lbl_hist)
        self.combo_search_history = QComboBox(self)
        self.combo_search_history.setMinimumWidth(200)
        self.combo_search_history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_search_history.setToolTip("انتخاب یک جستجوی قبلی برای پر کردن خودکار فیلترها")
        self.combo_search_history.currentIndexChanged.connect(self.on_search_history_selected)
        tb.addWidget(self.combo_search_history, stretch=1)

        self.btn_export_excel = QPushButton("خروجی اکسل", self)
        self.btn_export_excel.setObjectName("Accent")
        self.btn_export_excel.setToolTip("باز کردن فایل اکسل آخرین اسکن")
        self.btn_export_excel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export_excel.clicked.connect(self.open_current_excel)
        tb.addWidget(self.btn_export_excel)

        self.btn_export_word_tb = QPushButton("خروجی Word", self)
        self.btn_export_word_tb.setObjectName("Primary")
        self.btn_export_word_tb.setToolTip("باز کردن فایل Word جدول‌بندی‌شده راست‌به‌چپ (brands.docx)")
        self.btn_export_word_tb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export_word_tb.clicked.connect(self.open_current_word)
        tb.addWidget(self.btn_export_word_tb)
        layout.addWidget(toolbar)

        self.tabs = QTabWidget(self)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tabs, stretch=1)

        # تب ۱: matching, active brandings
        self.tab_alerts = QWidget()
        alerts_layout = QVBoxLayout(self.tab_alerts)
        alerts_layout.setContentsMargins(10, 10, 10, 10)
        alerts_hint = QLabel("پرونده‌های فعال و در جریان با شباهت ۶۵٪ به بالا به برندهای شرکت (موارد رد شده مستثنی شده‌اند).", self)
        alerts_hint.setObjectName("Hint")
        alerts_layout.addWidget(alerts_hint)
        self.table_alerts = self.create_table([
            "ردیف", "درصد شباهت", "سطح شباهت", "برند شرکت",
            "عنوان علامت متقاضی", "شماره اظهارنامه", "تاریخ اظهارنامه",
            "وضعیت پرونده", "طبقات", "اقدام"
        ])
        alerts_layout.addWidget(self.table_alerts, stretch=1)
        self.alerts_empty = QLabel("هنوز نتیجه‌ای نیست — یک اسکن اجرا کنید تا هشدارهای شباهت اینجا بیایند.", self)
        self.alerts_empty.setObjectName("EmptyState")
        self.alerts_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alerts_empty.setWordWrap(True)
        alerts_layout.addWidget(self.alerts_empty)
        self.tabs.addTab(self.tab_alerts, "Matching, Active Brandings")
        self.tabs.setTabToolTip(0, "اظهارنامه‌های فعال دارای شباهت با برند مرجع (موارد رد شده مستثنی شده‌اند)")

        # تب ۲: rejected
        self.tab_rejected = QWidget()
        rej_layout = QVBoxLayout(self.tab_rejected)
        rej_layout.setContentsMargins(10, 10, 10, 10)
        rej_hint = QLabel("اظهارنامه‌هایی که وضعیت پرونده آن‌ها در سامانه ثبت «رد شده» است.", self)
        rej_hint.setObjectName("Hint")
        rej_layout.addWidget(rej_hint)
        self.table_rejected = self.create_table([
            "ردیف", "عنوان علامت", "شماره اظهارنامه", "تاریخ اظهارنامه",
            "وضعیت پرونده", "طبقات", "اقدام"
        ])
        rej_layout.addWidget(self.table_rejected, stretch=1)
        self.rejected_empty = QLabel("در این اسکن پرونده رد شده‌ای وجود ندارد.", self)
        self.rejected_empty.setObjectName("EmptyState")
        self.rejected_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rejected_empty.setWordWrap(True)
        rej_layout.addWidget(self.rejected_empty)
        self.tabs.addTab(self.tab_rejected, "Rejected")
        self.tabs.setTabToolTip(1, "کلیه پرونده‌های رد شده")

        # تب ۳: ALL SCRAPED RECORDS
        self.tab_all = QWidget()
        all_layout = QVBoxLayout(self.tab_all)
        all_layout.setContentsMargins(10, 10, 10, 10)
        all_hint = QLabel("تمامی اظهارنامه‌های استخراج‌شده در این اسکن، بدون هیچ‌گونه فیلتر.", self)
        all_hint.setObjectName("Hint")
        all_layout.addWidget(all_hint)
        self.table_all = self.create_table([
            "ردیف", "عنوان علامت", "شماره اظهارنامه", "تاریخ اظهارنامه",
            "وضعیت پرونده", "وضعیت رد", "طبقات", "اقدام"
        ])
        all_layout.addWidget(self.table_all, stretch=1)
        self.all_empty = QLabel("هنوز اسکنی انجام نشده — نتایج کامل استخراج اینجا نمایش داده می‌شود.", self)
        self.all_empty.setObjectName("EmptyState")
        self.all_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_empty.setWordWrap(True)
        all_layout.addWidget(self.all_empty)
        self.tabs.addTab(self.tab_all, "ALL SCRAPED RECORDS")
        self.tabs.setTabToolTip(2, "تمامی اظهارنامه‌های استخراج‌شده بدون فیلتر")


        self._refresh_stats()
        return panel

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
        return value, card

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def create_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget(self)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setMinimumSectionSize(70)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setMinimumHeight(220)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        return table

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
        self.stat_total_value.setText(str(self._total))
        self.stat_high_value.setText(str(self._high))
        self.stat_medium_value.setText(str(self._medium))
        self.stat_rejected_value.setText(str(self._rejected))
        self.tabs.setTabText(0, f"Matching, Active Brandings ({self._high + self._medium})")
        self.tabs.setTabText(1, f"Rejected ({self._rejected})")
        self.tabs.setTabText(2, f"ALL SCRAPED RECORDS ({self._total})")
        # وضعیت خالی بودن تب‌ها
        if hasattr(self, "alerts_empty"):
            has_alerts = (self._high + self._medium) > 0
            self.alerts_empty.setVisible(not has_alerts)
            if not has_alerts:
                if self._total > 0:
                    self.alerts_empty.setText("اسکن انجام شد اما موردی با شباهت فعال یافت نشد — جزئیات در تب «ALL SCRAPED RECORDS».")
                else:
                    self.alerts_empty.setText("هنوز نتیجه‌ای نیست — یک اسکن اجرا کنید تا رکوردهای منطبق اینجا نمایش داده شوند.")
        if hasattr(self, "rejected_empty"):
            has_rej = self._rejected > 0
            self.rejected_empty.setVisible(not has_rej)
            if not has_rej:
                if self._total > 0:
                    self.rejected_empty.setText("در این اسکن هیچ پرونده رد شده‌ای یافت نشد.")
                else:
                    self.rejected_empty.setText("هنوز پرونده رد شده‌ای نیست.")
        if hasattr(self, "all_empty"):
            self.all_empty.setVisible(self._total == 0)
            if self._total == 0 and self.current_scan_id:
                self.all_empty.setText("اسکن تمام شد اما رکوردی با این فیلترها پیدا نشد — بازه تاریخ یا طبقه را بازتر کنید.")


    def _reset_counters(self):
        self._total = 0
        self._high = 0
        self._medium = 0
        self._rejected = 0
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Behaviours
    # ------------------------------------------------------------------
    def toggle_advanced_panel(self):
        is_visible = self.btn_toggle_advanced.isChecked()
        self.advanced_box.setVisible(is_visible)
        self.btn_toggle_advanced.setText(
            "بستن فیلترهای پیشرفته ▴" if is_visible else "فیلترهای پیشرفته ▾"
        )

    def load_captcha(self):
        self.lbl_captcha.setText("در حال دریافت تصویر…")
        self.txt_captcha.clear()
        img_bytes = self.client.get_captcha_image()
        if img_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(img_bytes)
            scaled = pixmap.scaled(
                self.lbl_captcha.width() or 320,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_captcha.setPixmap(scaled)
            self.lbl_status.setText("کد امنیتی را وارد کنید و «شروع اسکن» را بزنید.")
            self.txt_captcha.setFocus()
        else:
            err = getattr(self.client, "last_error", "")
            if err == "vpn_timeout":
                self.lbl_captcha.setText("خطای اتصال به سرور\n(فیلترشکن را خاموش کنید)")
                self.lbl_status.setText(
                    "⚠️ سرورهای سازمان ثبت، آی‌پی‌های خارج از کشور را مسدود می‌کنند.\n"
                    "در صورت روشن بودن فیلترشکن (VPN)، لطفاً آن را خاموش کرده و «کد جدید» را بزنید."
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
            self.txt_from_date.setText(str(params["FromIssueDate"]))
        if params.get("ToIssueDate"):
            self.txt_to_date.setText(str(params["ToIssueDate"]))
        if params.get("SignProductId"):
            self.txt_class.setText(str(params["SignProductId"]))
        if params.get("target_brand"):
            self.txt_target_brand.setText(str(params["target_brand"]))
        if params.get("ItemTitle"):
            self.txt_item_title.setText(str(params["ItemTitle"]))
        if params.get("DeclarationNo"):
            self.txt_dec_no.setText(str(params["DeclarationNo"]))
        if params.get("RegisterNo"):
            self.txt_reg_no.setText(str(params["RegisterNo"]))
        if params.get("RealOwnerName"):
            self.txt_owner_name.setText(str(params["RealOwnerName"]))
        if params.get("RealOwnerFamily"):
            self.txt_owner_family.setText(str(params["RealOwnerFamily"]))
        if params.get("RealOwnerNationalityCode"):
            self.txt_national_code.setText(str(params["RealOwnerNationalityCode"]))

        self.lbl_status.setText("فیلترهای جستجوی قبلی بازیابی شد. کد امنیتی جدید را وارد کنید.")
        self._set_state("پیش‌نویس آماده", "idle")

    def start_scan(self):
        captcha = self.txt_captcha.text().strip()
        if len(captcha) < 4:
            self._msg("warning", "کد امنیتی ناقص",
                      "لطفاً عدد ۴ رقمی داخل تصویر «مرحله ۱» را کامل وارد کنید.")
            self.txt_captcha.setFocus()
            return

        if not self.txt_from_date.text().strip():
            self._msg("warning", "تاریخ شروع خالی است", "لطفاً «از تاریخ انتشار» را پر کنید.")
            self.txt_from_date.setFocus()
            return

        target_brand_input = self.txt_target_brand.text().strip()
        if target_brand_input:
            parts = target_brand_input.split()
            name_fa = parts[0]
            name_en = parts[1] if len(parts) > 1 else ""
            add_watchlist_item(name_fa, name_en, self.txt_class.text().strip() or "5")

        like_map = {0: "3", 1: "2", 2: "1"}
        person_type_map = {0: "1", 1: "2"}

        params = {
            "FromIssueDate": self.txt_from_date.text().strip(),
            "ToIssueDate": self.txt_to_date.text().strip(),
            "SignProductId": self.txt_class.text().strip(),
            "ItemTitle": self.txt_item_title.text().strip(),
            "SearchItemTitleAsLike": like_map.get(self.combo_title_like.currentIndex(), "3"),
            "DeclarationNo": self.txt_dec_no.text().strip(),
            "RegisterNo": self.txt_reg_no.text().strip(),
            "personType": person_type_map.get(self.combo_person_type.currentIndex(), "1"),
            "RealOwnerName": self.txt_owner_name.text().strip(),
            "RealOwnerFamily": self.txt_owner_family.text().strip(),
            "RealOwnerNationalityCode": self.txt_national_code.text().strip(),
            "target_brand": target_brand_input
        }

        title_summary = f"طبقه {params['SignProductId'] or 'همه'}"
        if target_brand_input:
            title_summary += f" | {target_brand_input}"
        if params['FromIssueDate']:
            title_summary += f" از {params['FromIssueDate']}"
        save_search_history(title_summary, params)
        self.load_search_history_combo()

        self.table_alerts.setRowCount(0)
        self.table_rejected.setRowCount(0)
        self.table_all.setRowCount(0)
        self._reset_counters()
        # پرش به تب کلیه اظهارنامه‌ها حین اسکن برای مشاهده زنده رکوردها
        self.tabs.setCurrentIndex(2)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self._set_state("در حال اسکن…", "running")
        self.lbl_status.setText("اسکن شروع شد — نتایج به‌صورت زنده در جدول پایین می‌آیند.")

        self.current_worker = ScanWorker(
            client=self.client,
            search_params=params,
            captcha_value=captcha,
            scan_date=self.txt_from_date.text().strip() or "تاریخ جاری",
            max_pages=self.spin_pages.value()
        )
        self.current_worker.progress_changed.connect(self.on_progress)
        self.current_worker.record_found.connect(self.on_record_found)
        self.current_worker.scan_completed.connect(self.on_scan_completed)
        self.current_worker.scan_failed.connect(self.on_scan_failed)
        self.current_worker.start()

    def stop_scan(self):
        if self.current_worker:
            self.current_worker.cancel()
            self.lbl_status.setText("در حال توقف اسکن…")
            self.btn_stop.setEnabled(False)

    def on_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(msg)

    def on_record_found(self, r: dict):
        self._total += 1
        if r.get('is_rejected'):
            self._rejected += 1
            self.add_to_table_rejected(r)
        else:
            if r.get('risk_level') == 'high':
                self._high += 1
            elif r.get('risk_level') == 'medium':
                self._medium += 1

            if r.get('risk_level') in ('high', 'medium'):
                self.add_to_table_alerts(r)

        self.add_to_table_all(r)
        self._refresh_stats()

    def _open_button(self, url: str, compact: bool = False) -> QPushButton:
        btn = QPushButton("مشاهده پرونده" if not compact else "مشاهده", self)
        btn.setObjectName("RowBtn")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if url:
            btn.clicked.connect(lambda _, u=url: webbrowser.open(u))
        else:
            btn.setEnabled(False)
            btn.setToolTip("لینک پرونده موجود نیست")
        return btn

    def _risk_colors(self, risk: str):
        if self._dark_active:
            if risk == 'high':
                return QColor("#7F1D1D"), QColor("#FECACA")
            return QColor("#78350F"), QColor("#FDE68A")
        if risk == 'high':
            return QColor("#FEE2E2"), QColor("#991B1B")
        return QColor("#FEF3C7"), QColor("#92400E")

    def add_to_table_alerts(self, r: dict):
        sorting = self.table_alerts.isSortingEnabled()
        self.table_alerts.setSortingEnabled(False)
        row = self.table_alerts.rowCount()
        self.table_alerts.insertRow(row)

        score = float(r.get('similarity_score', 0.0))
        risk = r.get('risk_level', 'low')
        risk_fa = "● شباهت بالا" if risk == 'high' else "● شباهت متوسط"
        bg, fg = self._risk_colors(risk)

        self.table_alerts.setItem(row, 0, QTableWidgetItem(str(row + 1)))

        item_score = QTableWidgetItem(f"{score:.0f}٪")
        item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_score.setBackground(bg)
        item_score.setForeground(fg)
        self.table_alerts.setItem(row, 1, item_score)

        item_risk = QTableWidgetItem(risk_fa)
        item_risk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_risk.setForeground(fg)
        self.table_alerts.setItem(row, 2, item_risk)

        self.table_alerts.setItem(row, 3, QTableWidgetItem(r.get('matched_brand', '')))
        self.table_alerts.setItem(row, 4, QTableWidgetItem(r.get('title', '')))
        self.table_alerts.setItem(row, 5, QTableWidgetItem(r.get('declaration_no', '')))
        self.table_alerts.setItem(row, 6, QTableWidgetItem(r.get('declaration_date', '')))
        self.table_alerts.setItem(row, 7, QTableWidgetItem(r.get('status', '')))
        self.table_alerts.setItem(row, 8, QTableWidgetItem(str(r.get('classes', ''))))
        self.table_alerts.setCellWidget(row, 9, self._open_button(r.get('detail_url', '')))
        self.table_alerts.setSortingEnabled(sorting)

    def add_to_table_rejected(self, r: dict):
        sorting = self.table_rejected.isSortingEnabled()
        self.table_rejected.setSortingEnabled(False)
        row = self.table_rejected.rowCount()
        self.table_rejected.insertRow(row)

        self.table_rejected.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table_rejected.setItem(row, 1, QTableWidgetItem(r.get('title', '')))
        self.table_rejected.setItem(row, 2, QTableWidgetItem(r.get('declaration_no', '')))
        self.table_rejected.setItem(row, 3, QTableWidgetItem(r.get('declaration_date', '')))

        status_item = QTableWidgetItem(r.get('status', 'رد شده'))
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setForeground(QColor("#94A3B8") if not self._dark_active else QColor("#64748B"))
        self.table_rejected.setItem(row, 4, status_item)

        self.table_rejected.setItem(row, 5, QTableWidgetItem(str(r.get('classes', ''))))
        self.table_rejected.setCellWidget(row, 6, self._open_button(r.get('detail_url', ''), compact=True))
        self.table_rejected.setSortingEnabled(sorting)


    def add_to_table_all(self, r: dict):
        sorting = self.table_all.isSortingEnabled()
        self.table_all.setSortingEnabled(False)
        row = self.table_all.rowCount()
        self.table_all.insertRow(row)

        is_rej = r.get('is_rejected')
        rej_fa = "رد شده" if is_rej else "فعال"

        self.table_all.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table_all.setItem(row, 1, QTableWidgetItem(r.get('title', '')))
        self.table_all.setItem(row, 2, QTableWidgetItem(r.get('declaration_no', '')))
        self.table_all.setItem(row, 3, QTableWidgetItem(r.get('declaration_date', '')))
        self.table_all.setItem(row, 4, QTableWidgetItem(r.get('status', '')))

        item_rej = QTableWidgetItem(rej_fa)
        item_rej.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_rej:
            item_rej.setForeground(QColor("#94A3B8") if not self._dark_active else QColor("#64748B"))
        else:
            item_rej.setForeground(QColor("#15803D") if not self._dark_active else QColor("#4ADE80"))
        self.table_all.setItem(row, 5, item_rej)

        self.table_all.setItem(row, 6, QTableWidgetItem(str(r.get('classes', ''))))
        self.table_all.setCellWidget(row, 7, self._open_button(r.get('detail_url', ''), compact=True))
        self.table_all.setSortingEnabled(sorting)

    def on_scan_completed(self, scan_id: int, excel_path: str, total: int, alerts: int):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.last_excel_path = excel_path
        self.current_scan_id = scan_id
        self.progress_bar.setValue(100)
        self.load_captcha()
        self._refresh_stats()

        if total == 0:
            self._set_state("نتیجه‌ای نبود", "idle")
            self.lbl_status.setText("اسکن تمام شد — رکوردی با این فیلترها پیدا نشد.")
            self.tabs.setCurrentIndex(2)
        elif alerts > 0:
            self._set_state(f"{alerts} هشدار", "error")
            self.lbl_status.setText(f"اسکن تمام شد — {total} رکورد بررسی و {alerts} مورد مشابه فعال پیدا شد.")
            self.tabs.setCurrentIndex(0)
        else:
            self._set_state("پایان بدون هشدار", "success")
            self.lbl_status.setText(f"اسکن تمام شد — {total} رکورد بررسی شد و موردی با شباهت فعال یافت نشد.")
            self.tabs.setCurrentIndex(2)

        msg = f"کل رکوردهای بررسی‌شده: {total}\nتعداد هشدارهای شباهت: {alerts}"
        if excel_path:
            msg += f"\n\nفایل اکسل ذخیره شد:\n{excel_path}"
        else:
            msg += "\n\n(فایل اکسل ساخته نشد)"
        self._msg("information", "اتمام اسکن", msg)

    def on_scan_failed(self, error_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._set_state("خطای اتصال", "error")
        self.lbl_status.setText(f"خطا: {error_msg}")
        self._msg("critical", "خطا در ارتباط با سامانه ثبت", error_msg)
        self.load_captcha()

    def open_current_excel(self):
        if self.last_excel_path and os.path.exists(self.last_excel_path):
            try:
                if hasattr(os, "startfile"):
                    os.startfile(self.last_excel_path)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f"file://{self.last_excel_path}")
            except Exception as e:
                self._msg("warning", "خطا", f"باز کردن فایل ممکن نشد:\n{e}")
        else:
            self._msg("information", "فایلی نیست",
                      "هنوز در این نشست فایل اکسلی ساخته نشده است.\nیک اسکن اجرا کنید تا گزارش ساخته شود.")

    def open_reports_dir(self):
        rep_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        os.makedirs(rep_dir, exist_ok=True)
        try:
            if hasattr(os, "startfile"):
                os.startfile(rep_dir)  # type: ignore[attr-defined]
            else:
                webbrowser.open(f"file://{rep_dir}")
        except Exception as e:
            self._msg("warning", "خطا", f"باز کردن پوشه ممکن نشد:\n{e}")

    # ------------------------------------------------------------------
    # DeclarationList Scraper & In-App Authentication Methods
    # ------------------------------------------------------------------
    def check_session_on_startup(self):
        try:
            from scanner.auth import get_saved_user_name
            saved_name = get_saved_user_name()
            if saved_name:
                self.lbl_session_status.setText(f"✅ نشست ذخیره‌شده: {saved_name}")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #15803D;")
                self.btn_login_session.setText("تغییر حساب")
            else:
                self.lbl_session_status.setText("⚠️ نیاز به ورود به سامانه")
                self.lbl_session_status.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #D97706;")
                self.btn_login_session.setText("ورود به سامانه")
        except Exception:
            pass

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
            self.lbl_decl_status.setText("ورود موفقیت‌آمیز بود و نشست ذخیره شد.")
            self._msg("information", "ورود موفق", f"ورود با موفقیت انجام شد.\nنشست شما ({user_name}) ذخیره گردید و در دفعات بعدی نیازی به لاگین نخواهید داشت.")
        else:
            logger.warning(f"ورود ناموفق یا بسته شدن پنجره: {user_name}")
            self.lbl_decl_status.setText("فرآیند ورود انجام نشد.")
            self._msg("warning", "خطای ورود", f"ورود انجام نشد یا پنجره بسته شد:\n{user_name}")

    def start_declaration_scan(self, mode: str):
        logger.info(f"شروع فرآیند اسکن اظهارنامه‌ها با مود: '{mode}'")
        self.table_alerts.setRowCount(0)
        self.table_rejected.setRowCount(0)
        self.table_all.setRowCount(0)
        self._reset_counters()
        # نمایش زنده در تب کلیه اظهارنامه‌ها
        self.tabs.setCurrentIndex(2)

        self.btn_decl_new.setEnabled(False)
        self.btn_decl_full.setEnabled(False)
        self.btn_decl_stop.setEnabled(True)
        self.decl_progress_bar.setValue(0)
        self._set_state("در حال اسکن لیست عمومی…", "running")
        self.lbl_decl_status.setText("آغاز استخراج اظهارنامه‌ها…")

        self.decl_worker = DeclarationScrapeWorker(mode=mode, max_pages=500)
        self.decl_worker.progress_changed.connect(self.on_decl_progress)
        self.decl_worker.record_found.connect(self.on_record_found)
        self.decl_worker.scan_completed.connect(self.on_decl_scan_completed)
        self.decl_worker.scan_failed.connect(self.on_decl_scan_failed)
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
        logger.info(f"اسکن لیست اظهارنامه‌ها تکمیل شد. کل: {total}، جدید: {new_count}، هشدارها: {alerts}")
        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        self._set_state("تکمیل شد", "success")
        msg = f"اسکن لیست عمومی با موفقیت به پایان رسید.\nکل رکوردهای موجود: {total}\nموارد جدید افزوده شده: {new_count}\nهشدارهای شباهت به برندهای شرکت: {alerts}"
        self.lbl_decl_status.setText(f"اسکن پایان یافت. {new_count} مورد جدید ثبت شد.")
        self._msg("information", "اتمام اسکن لیست عمومی", f"{msg}\n\nفایل جدول Word در مسیر زیر به‌روزرسانی گردید:\n{docx_path}")

    def on_decl_scan_failed(self, error_msg: str):
        logger.error(f"اسکن اظهارنامه‌ها با شکست مواجه شد: {error_msg}")
        self.btn_decl_new.setEnabled(True)
        self.btn_decl_full.setEnabled(True)
        self.btn_decl_stop.setEnabled(False)
        self._set_state("خطای اسکن", "error")
        self.lbl_decl_status.setText("اسکن متوقف شد.")
        self._msg("critical", "خطا در اسکن لیست عمومی", error_msg)

    def open_current_word(self):
        docx_path = os.path.abspath(WORD_OUTPUT_PATH)
        if os.path.exists(docx_path):
            try:
                if hasattr(os, "startfile"):
                    os.startfile(docx_path)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f"file://{docx_path}")
            except Exception as e:
                self._msg("warning", "خطا", f"باز کردن فایل Word ممکن نشد:\n{e}")
        else:
            self._msg("information", "فایلی نیست",
                      "هنوز فایل Word جدول برندها ساخته نشده است.\nلطفاً ابتدا یکی از اسکن‌های لیست عمومی را اجرا فرمایید.")


def run_app():
    # راه‌اندازی اولیه سیستم ثبت وقایع و لاگ‌ها
    setup_logging("DEBUG")
    logger.info("راه‌اندازی موتور نرم‌افزار سامانه پایش هوشمند علائم تجاری...")

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    try:
        if "Fusion" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("Fusion"))
    except Exception:
        pass
    window = TrademarkApp()
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

