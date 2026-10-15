"""
مدیریت پایگاه داده محلی SQLite برای ذخیره تاریخچه اسکن‌ها و برندها
SQLite Database Manager for Scans, Declarations, and Watchlist
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from scanner import BASE_DIR, DATA_DIR

DB_FILE = os.path.join(DATA_DIR, 'scans.db')


def _init_schema_on_conn(conn: sqlite3.Connection):
    """ایجاد جداول و داده‌های پیش‌فرض روی اتصال فعال."""
    cursor = conn.cursor()

    # مخزن جاری و مرجع برنامه؛ JSON فقط برای مهاجرت نسخه‌های قدیمی است.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS record_store (
            bucket TEXT NOT NULL,
            record_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (bucket, record_key)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT NOT NULL
        )
    ''')

    # ۱. جدول برندهای تحت حفاظت شرکت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_fa TEXT NOT NULL,
            name_en TEXT,
            classes TEXT DEFAULT '5',
            created_at TEXT
        )
    ''')

    # ۲. جدول تاریخچه اسکن‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT NOT NULL,
            search_params TEXT,
            total_records INTEGER DEFAULT 0,
            class5_count INTEGER DEFAULT 0,
            alerts_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')

    # ۳. جدول اظهارنامه‌های استخراج‌شده
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS declarations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            title TEXT,
            declaration_no TEXT,
            declaration_date TEXT,
            status TEXT,
            is_rejected INTEGER,
            is_active INTEGER DEFAULT 0,
            classes TEXT,
            has_class_5 INTEGER,
            image_url TEXT,
            detail_url TEXT,
            matched_brand TEXT,
            similarity_score REAL,
            risk_level TEXT,
            FOREIGN KEY(scan_id) REFERENCES scans(id)
        )
    ''')

    # مهاجرت ستون is_active برای دیتابیس‌های قدیمی
    cursor.execute("PRAGMA table_info(declarations)")
    decl_columns = {row[1] for row in cursor.fetchall()}
    if 'is_active' not in decl_columns:
        cursor.execute('ALTER TABLE declarations ADD COLUMN is_active INTEGER DEFAULT 0')

    # مهاجرت فیلدهای جدید جدول حالت ۱ (نام فارسی/لاتین، شماره ثبت، تاریخ تمدید، لینک گواهی)
    for col, ddl in (
        ('title_fa', 'ALTER TABLE declarations ADD COLUMN title_fa TEXT DEFAULT ""'),
        ('title_en', 'ALTER TABLE declarations ADD COLUMN title_en TEXT DEFAULT ""'),
        ('register_no', 'ALTER TABLE declarations ADD COLUMN register_no TEXT DEFAULT ""'),
        ('renewal_date', 'ALTER TABLE declarations ADD COLUMN renewal_date TEXT DEFAULT ""'),
        ('certificate_url', 'ALTER TABLE declarations ADD COLUMN certificate_url TEXT DEFAULT ""'),
    ):
        if col not in decl_columns:
            cursor.execute(ddl)

    # ۴. جدول تاریخچه جستجوها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            params_json TEXT,
            created_at TEXT
        )
    ''')

    # ایجاد ایندکس جهت جستجوی سریع در تاریخچه
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dec_scan ON declarations(scan_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dec_no ON declarations(declaration_no)')

    # افزودن برند پیش‌فرض اگر جدول خالی است
    cursor.execute('SELECT COUNT(*) FROM watchlist')
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO watchlist (name_fa, name_en, classes, created_at) VALUES (?, ?, ?, ?)',
            ('متاسنت', 'Metacent', '5', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
    conn.commit()


class ClosingConnection(sqlite3.Connection):
    """اتصال SQLite که در پایان بلوک with به صورت خودکار بسته می‌شود."""
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    is_new = not os.path.exists(db_path) or os.path.getsize(db_path) == 0
    conn = sqlite3.connect(db_path, factory=ClosingConnection)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    if is_new:
        _init_schema_on_conn(conn)
    return conn


def init_db(db_path: str = DB_FILE):
    """ایجاد جداول و داده‌های پیش‌فرض در صورت عدم وجود."""
    with get_connection(db_path) as conn:
        _init_schema_on_conn(conn)


# --- توابع مدیریت برندهای تحت حفاظت (Watchlist) ---

def get_watchlist(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name_fa, name_en, classes, created_at FROM watchlist ORDER BY id DESC')
        return [dict(row) for row in cursor.fetchall()]


def add_watchlist_item(name_fa: str, name_en: str = "", classes: str = "5", db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO watchlist (name_fa, name_en, classes, created_at) VALUES (?, ?, ?, ?)',
            (name_fa.strip(), name_en.strip(), classes.strip() or '5', now)
        )
        conn.commit()
        return cursor.lastrowid


def delete_watchlist_item(item_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM watchlist WHERE id = ?', (item_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- توابع مدیریت اسکن‌ها و ذخیره رکوردها ---

def create_scan_session(
    scan_date: str,
    search_params: Dict[str, Any],
    total_records: int = 0,
    class5_count: int = 0,
    alerts_count: int = 0,
    db_path: str = DB_FILE
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO scans (scan_date, search_params, total_records, class5_count, alerts_count, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (scan_date, json.dumps(search_params, ensure_ascii=False),
             total_records, class5_count, alerts_count, now)
        )
        conn.commit()
        return cursor.lastrowid


def save_declarations_batch(scan_id: int, declarations: List[Dict[str, Any]], db_path: str = DB_FILE):
    if not declarations:
        return
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # اطمینان از وجود ستون‌های جدید حتی اگر init روی دیتابیس قدیمی اجرا نشده باشد
        cursor.execute("PRAGMA table_info(declarations)")
        _cols = {row[1] for row in cursor.fetchall()}
        for _col, _ddl in (
            ('title_fa', 'ALTER TABLE declarations ADD COLUMN title_fa TEXT DEFAULT ""'),
            ('title_en', 'ALTER TABLE declarations ADD COLUMN title_en TEXT DEFAULT ""'),
            ('register_no', 'ALTER TABLE declarations ADD COLUMN register_no TEXT DEFAULT ""'),
            ('renewal_date', 'ALTER TABLE declarations ADD COLUMN renewal_date TEXT DEFAULT ""'),
            ('certificate_url', 'ALTER TABLE declarations ADD COLUMN certificate_url TEXT DEFAULT ""'),
        ):
            if _col not in _cols:
                try:
                    cursor.execute(_ddl)
                except Exception:
                    pass
        rows = []
        for d in declarations:
            classes_str = ','.join(map(str, d.get('classes', []))) if isinstance(d.get('classes'), list) else str(d.get('classes_str', ''))
            rows.append((
                scan_id,
                d.get('title', ''),
                d.get('title_fa', '') or d.get('title', ''),
                d.get('title_en', ''),
                d.get('declaration_no', ''),
                d.get('register_no', ''),
                d.get('declaration_date', ''),
                d.get('renewal_date', ''),
                d.get('certificate_url', ''),
                d.get('status', ''),
                1 if d.get('is_rejected') else 0,
                1 if d.get('is_active') else 0,
                classes_str,
                1 if d.get('has_class_5') else 0,
                d.get('image_url', ''),
                d.get('detail_url', ''),
                d.get('matched_brand', ''),
                float(d.get('similarity_score', 0.0)),
                d.get('risk_level', 'low')
            ))
        cursor.executemany('''
            INSERT INTO declarations (
                scan_id, title, title_fa, title_en, declaration_no, register_no,
                declaration_date, renewal_date, certificate_url,
                status, is_rejected,
                is_active, classes, has_class_5, image_url, detail_url,
                matched_brand, similarity_score, risk_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rows)
        conn.commit()


def update_scan_stats(scan_id: int, total: int, class5_count: int, alerts_count: int, db_path: str = DB_FILE):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE scans SET total_records = ?, class5_count = ?, alerts_count = ? WHERE id = ?',
            (total, class5_count, alerts_count, scan_id)
        )
        conn.commit()


def get_all_scans(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, scan_date, search_params, total_records, class5_count, alerts_count, created_at
            FROM scans ORDER BY id DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_scan_declarations(scan_id: int, filter_type: str = 'all', db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """
    دریافت رکوردهای یک نوبت اسکن:
    - 'active': موارد نهایی‌شده (ثبت قطعی شده)
    - 'alerts': موارد فعال با ریسک شباهت بالا یا متوسط (غیر رد شده)
    - 'class5': موارد دارای طبقه ۵
    - 'rejected': موارد رد شده
    - 'all': کلیه رکوردها
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM declarations WHERE scan_id = ?'
        params = [scan_id]

        if filter_type == 'active':
            query += " AND is_active = 1 ORDER BY id DESC"
        elif filter_type == 'alerts':
            query += " AND is_rejected = 0 AND risk_level IN ('high', 'medium') ORDER BY similarity_score DESC"
        elif filter_type == 'class5':
            query += " AND has_class_5 = 1 ORDER BY is_rejected ASC, id DESC"
        elif filter_type == 'rejected':
            query += " AND is_rejected = 1 ORDER BY id DESC"
        else:
            query += " ORDER BY id DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# --- تاریخچه جستجوها (Search Queries History) ---

def save_search_history(title: str, params: Dict[str, Any], db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO search_history (title, params_json, created_at) VALUES (?, ?, ?)',
            (title.strip() or 'جستجو', json.dumps(params, ensure_ascii=False), now)
        )
        conn.commit()
        return cursor.lastrowid


def get_search_history(limit: int = 50, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, title, params_json, created_at FROM search_history ORDER BY id DESC LIMIT ?',
            (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item['params'] = json.loads(item['params_json'])
            except Exception:
                item['params'] = {}
            results.append(item)
        return results

