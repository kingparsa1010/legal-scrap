"""
موتور شباهت‌سنجی علائم تجاری (فارسی و انگلیسی)
Similarity & Phonetic Matching Engine for Trademarks
"""
import re
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz

# واژگان عمومی حقوقی و شرکتی جهت حذف از مقایسه عنوان
CORPORATE_STOPWORDS = {
    'شرکت', 'تولیدی', 'بازرگانی', 'سهامی', 'خاص', 'عام', 'با مسئولیت محدود',
    'گروه', 'صنعتی', 'داروسازی', 'دارویی', 'صنایع', 'صادرات', 'واردات',
    'پخش', 'توسعه', 'تجارت', 'بین المللی', 'موسسه', 'تعاونی', 'نوین',
    'company', 'co', 'ltd', 'inc', 'corp', 'pharma', 'pharmaceutical', 'group'
}

# نگاشت حروف هم‌صدا در زبان فارسی (Phonetic Equivalence)
PERSIAN_PHONETIC_MAP = {
    'ث': 'س', 'ص': 'س',
    'ط': 'ت',
    'ذ': 'ز', 'ض': 'ز', 'ظ': 'ز',
    'ح': 'ه',
    'غ': 'ق',
    'ع': '',
    'ء': '', 'ئ': 'ی', 'ؤ': 'و',
    'آ': 'ا', 'أ': 'ا', 'إ': 'ا',
}


def normalize_persian(text: str) -> str:
    """نرمال‌سازی پیشرفته متن فارسی و عربی."""
    if not text:
        return ""
    
    t = str(text).strip()
    
    # استانداردسازی حروف عربی/فارسی
    t = t.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    
    # حذف اعراب و تنوین (Harakat)
    t = re.sub(r'[\u064B-\u065F\u0670]', '', t)
    
    # حذف نیم‌فاصله‌ها و علائم نگارشی اضافی
    t = t.replace('\u200c', ' ')
    t = re.sub(r'[^\w\s]', ' ', t)
    
    # حذف فاصله‌های تکراری
    t = re.sub(r'\s+', ' ', t).strip()
    return t.lower()


def remove_stopwords(text: str) -> str:
    """حذف کلمات عمومی اداری/شرکتی جهت تمرکز بر هسته برند."""
    words = text.split()
    filtered = [w for w in words if w not in CORPORATE_STOPWORDS]
    return ' '.join(filtered) if filtered else text


def to_phonetic_persian(text: str) -> str:
    """تبدیل متن به شکل آوایی با جایگزینی حروف هم‌صدا."""
    norm = normalize_persian(text)
    phonetic_chars = []
    for ch in norm:
        phonetic_chars.append(PERSIAN_PHONETIC_MAP.get(ch, ch))
    res = ''.join(phonetic_chars)
    # حذف حروف تکراری پشت سر هم (مانند تت -> ت)
    res = re.sub(r'(.)\1+', r'\1', res)
    return res.strip()


def normalize_english(text: str) -> str:
    """نرمال‌سازی متن انگلیسی و نگاشت آوایی ساده (مانند C و S)."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    # نگاشت صوتی ساده: ph -> f, ce/ci/cy -> se/si/sy
    t = re.sub(r'ph', 'f', t)
    t = re.sub(r'c([eiy])', r's\1', t)
    t = re.sub(r'c', 'k', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


class TrademarkSimilarityEngine:
    """
    موتور ارزیابی میزان شباهت و تشخیص ریسک نقض علامت تجاری
    """

    def __init__(self, high_threshold: float = 80.0, medium_threshold: float = 65.0):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def calculate_similarity(self, candidate_name: str, target_name: str) -> float:
        """
        محاسبه درصد شباهت ترکیبی بین یک نام کاندید و نام هدف.
        شامل تطابق لغوی، تطابق کلمات، و تطابق آوایی.
        """
        if not candidate_name or not target_name:
            return 0.0

        # ۱. نرمال‌سازی پایه‌ای
        cand_norm = normalize_persian(candidate_name)
        targ_norm = normalize_persian(target_name)

        if cand_norm == targ_norm:
            return 100.0

        # حذف کلمات توقف شرکتی
        cand_clean = remove_stopwords(cand_norm)
        targ_clean = remove_stopwords(targ_norm)

        # اگر عین کلمه هدف داخل نام کاندید باشد
        if targ_clean in cand_clean or targ_norm in cand_norm:
            # کلمه هدف دقیقاً در عنوان وجود دارد
            return 95.0

        # ۲. مقایسه فازی مستقیم
        ratio_direct = fuzz.ratio(cand_clean, targ_clean)
        token_sort = fuzz.token_sort_ratio(cand_clean, targ_clean)
        partial = fuzz.partial_ratio(cand_clean, targ_clean)

        # ۳. مقایسه آوایی (حروف هم‌صدا مانند ث/س/ص)
        cand_phone = to_phonetic_persian(cand_clean)
        targ_phone = to_phonetic_persian(targ_clean)
        ratio_phone = fuzz.ratio(cand_phone, targ_phone)
        partial_phone = fuzz.partial_ratio(cand_phone, targ_phone)

        # ۴. مقایسه انگلیسی در صورت وجود حروف لاتین
        ratio_en = 0.0
        if re.search(r'[a-zA-Z]', candidate_name) and re.search(r'[a-zA-Z]', target_name):
            cand_en = normalize_english(candidate_name)
            targ_en = normalize_english(target_name)
            ratio_en = max(fuzz.ratio(cand_en, targ_en), fuzz.token_sort_ratio(cand_en, targ_en))

        # ترکیب وزن‌دار هوشمند
        lexical_score = max(ratio_direct, token_sort, partial * 0.9)
        phonetic_score = max(ratio_phone, partial_phone * 0.9)

        final_score = max(
            lexical_score * 0.6 + phonetic_score * 0.4,
            phonetic_score,
            ratio_en
        )

        return round(min(100.0, float(final_score)), 1)

    def evaluate_against_watchlist(
        self, candidate_name: str, watchlist: List[Dict]
    ) -> Tuple[float, str, str]:
        """
        مقایسه نام با کل لیست برندهای تحت حفاظت شرکت.
        خروجی: (بیشترین درصد شباهت, نام برند منطبق, سطح ریسک)
        """
        max_score = 0.0
        best_brand = ""

        for item in watchlist:
            name_fa = item.get('name_fa', '')
            name_en = item.get('name_en', '')

            # مقایسه با نام فارسی
            if name_fa:
                s_fa = self.calculate_similarity(candidate_name, name_fa)
                if s_fa > max_score:
                    max_score = s_fa
                    best_brand = name_fa

            # مقایسه با نام انگلیسی
            if name_en:
                s_en = self.calculate_similarity(candidate_name, name_en)
                if s_en > max_score:
                    max_score = s_en
                    best_brand = name_en

        if max_score >= self.high_threshold:
            risk = 'high'
        elif max_score >= self.medium_threshold:
            risk = 'medium'
        else:
            risk = 'low'

        return max_score, best_brand, risk


def get_similarity_label(risk: str) -> str:
    """تبدیل سطح ارزیابی به برچسب فارسی شباهت."""
    if risk == 'high':
        return "شباهت بالا"
    elif risk == 'medium':
        return "شباهت متوسط"
    return "عادی"

