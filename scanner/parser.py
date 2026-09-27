"""
تجزیه‌گر HTML نتایج اظهارنامه‌های علائم تجاری
HTML Parser for SSAA Trademark Search Results
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://ipm.ssaa.ir/"

# تبدیل ارقام فارسی/عربی به انگلیسی
PERSIAN_DIGITS_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def to_english_digits(text: str) -> str:
    """تبدیل ارقام فارسی/عربی به انگلیسی."""
    if not text:
        return ""
    return str(text).translate(PERSIAN_DIGITS_TABLE)


def is_rejected_status(status: str) -> bool:
    """وضعیت پرونده رد شده یا ابطال شده است؟ (مبنای واحد برای همه ماژول‌ها)"""
    if not status:
        return False
    return ('رد شده' in status) or ('ابطال' in status)


def is_finally_registered(status: str) -> bool:
    """وضعیت پرونده «ثبت قطعی شده» است؟ — مبنای تب ACTIVE ONLY."""
    if not status:
        return False
    return 'ثبت قطعی شده' in status


def parse_classes(class_str: str) -> List[int]:
    """استخراج لیست شماره طبقات از رشته طبقه بندی بین المللی."""
    if not class_str:
        return []
    en_str = to_english_digits(class_str)
    result = set()

    # ۱. بررسی محدوده‌ها مانند ۱ تا ۵ یا ۱-۵ یا ۱ الی ۵
    for match in re.finditer(r'(\d+)\s*(?:-|تا|الی)\s*(\d+)', en_str):
        try:
            start_c, end_c = int(match.group(1)), int(match.group(2))
            if 1 <= start_c <= end_c <= 45:
                for c in range(start_c, end_c + 1):
                    result.add(c)
        except ValueError:
            pass

    # ۲. پیدا کردن همه اعداد مجزا (طبقات معتبر ۱ تا ۴۵ علائم تجاری)
    for n in re.findall(r'\d+', en_str):
        try:
            val = int(n)
            if 1 <= val <= 45:
                result.add(val)
        except ValueError:
            continue
    return sorted(result)


def parse_search_results(html_content: str) -> List[Dict[str, Any]]:
    """
    تجزیه محتوای HTML دریافتی از /serv/Issue-Trademark.Sabt
    و استخراج ساختاریافته فیلدهای هر اظهارنامه.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    records = []

    # هر نتیجه داخل یک تگ <a> حاوی h2 قرار دارد
    links = soup.find_all('a')
    for a in links:
        h2 = a.find('h2')
        if not h2:
            continue

        title = h2.get_text(strip=True)
        raw_href = a.get('href', '')
        detail_url = urljoin(BASE_URL, raw_href) if raw_href else ""

        # تصویر علامت
        img = a.find('img')
        image_url = ""
        if img and img.get('src'):
            image_url = urljoin(BASE_URL, img.get('src'))

        # استخراج متون span ها
        dec_date = ""
        dec_no = ""
        status = ""
        classes = []
        raw_classes_str = ""

        for span in a.find_all('span'):
            text = span.get_text(strip=True)
            if 'تاریخ اظهارنامه' in text:
                dec_date = text.split(':', 1)[-1].strip()
            elif 'شماره اظهارنامه' in text:
                dec_no = to_english_digits(text.split(':', 1)[-1].strip())
            elif 'وضعیت پرونده' in text:
                status = text.split(':', 1)[-1].strip()
            elif any(k in text for k in ('طبقه بندی', 'طبقه بندي', 'طبقات', 'طبقه', 'کلاس')):
                raw_classes_str = text.split(':', 1)[-1].strip() if ':' in text else text
                classes = parse_classes(raw_classes_str)

        is_rejected = is_rejected_status(status)
        is_active = is_finally_registered(status)
        has_class_5 = 5 in classes

        records.append({
            'title': title,
            'declaration_no': dec_no,
            'declaration_date': dec_date,
            'status': status,
            'is_rejected': is_rejected,
            'is_active': is_active,
            'classes': classes,
            'classes_str': raw_classes_str or ','.join(map(str, classes)),
            'has_class_5': has_class_5,
            'image_url': image_url,
            'detail_url': detail_url
        })

    return records


def parse_declaration_page(html: str) -> List[Dict[str, Any]]:
    """تجزیه HTML جدول اظهارنامه‌ها و استخراج ستون‌ها."""
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody", id="DataList")
    if not tbody:
        return []

    rows = []
    for tr in tbody.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 8:
            continue

        row_num = tds[0].get_text(strip=True)

        img_a = tds[1].find("a")
        image_url = img_a["href"].strip() if img_a and img_a.has_attr("href") else ""

        dec_a = tds[2].find("a")
        dec_no_display = dec_a.get_text(strip=True) if dec_a else tds[2].get_text(strip=True)
        detail_url = dec_a["href"].strip() if dec_a and dec_a.has_attr("href") else ""
        if detail_url.startswith("/"):
            detail_url = f"https://ipm.ssaa.ir{detail_url}"
        elif detail_url and not detail_url.startswith("http"):
            detail_url = f"https://ipm.ssaa.ir/{detail_url}"
        m = re.search(r"DecNo=(\d+)", detail_url)
        dec_no_id = m.group(1) if m else to_english_digits(dec_no_display).strip()

        title = tds[3].get_text(strip=True)
        office = tds[4].get_text(strip=True)

        owner_b = tds[5].find("b")
        percent = ""
        owner_name = ""
        if owner_b:
            percent_i = owner_b.find("i")
            percent = percent_i.get_text(strip=True) if percent_i else ""
            owner_name = owner_b.get_text(separator=" ", strip=True)
            if percent:
                owner_name = owner_name.replace(percent, "").strip()
        else:
            owner_name = tds[5].get_text(strip=True)

        date_text = tds[6].get_text(separator="|", strip=True)
        date_parts = [p for p in date_text.split("|") if p]
        reg_date = date_parts[0] if len(date_parts) > 0 else ""
        reg_time = date_parts[1] if len(date_parts) > 1 else ""

        status_span = tds[7].find("span")
        status = status_span.get_text(strip=True) if status_span else tds[7].get_text(strip=True)

        rows.append({
            "dec_no_id": dec_no_id,
            "row_num": row_num,
            "dec_no_display": dec_no_display,
            "declaration_no": dec_no_display,
            "title": title,
            "office": office,
            "owner_name": owner_name,
            "owner_percent": percent,
            "reg_date": reg_date,
            "declaration_date": reg_date,
            "reg_time": reg_time,
            "status": status,
            "image_url": image_url,
            "detail_url": detail_url,
            "is_rejected": 1 if is_rejected_status(status) else 0,
            "is_active": 1 if is_finally_registered(status) else 0,
            "classes": "",
            "has_class_5": 0,
        })
    return rows

