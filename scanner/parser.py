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
    """تبدیل اعداد فارسی و عربی به ارقام انگلیسی."""
    if not text:
        return ""
    return str(text).translate(PERSIAN_DIGITS_TABLE)


def parse_classes(class_str: str) -> List[int]:
    """استخراج لیست شماره طبقات از رشته طبقه بندی بین المللی."""
    if not class_str:
        return []
    en_str = to_english_digits(class_str)
    # پیدا کردن همه دنباله‌های عددی
    nums = re.findall(r'\d+', en_str)
    result = []
    for n in nums:
        try:
            val = int(n)
            if val not in result:
                result.append(val)
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
            elif 'طبقه بندی' in text:
                raw_classes_str = text.split(':', 1)[-1].strip()
                classes = parse_classes(raw_classes_str)

        is_rejected = 'رد شده' in status
        has_class_5 = 5 in classes

        records.append({
            'title': title,
            'declaration_no': dec_no,
            'declaration_date': dec_date,
            'status': status,
            'is_rejected': is_rejected,
            'classes': classes,
            'classes_str': raw_classes_str or ','.join(map(str, classes)),
            'has_class_5': has_class_5,
            'image_url': image_url,
            'detail_url': detail_url
        })

    return records
