"""
تولیدکننده گزارش‌های اکسل با استایل استاندارد و پشتیبانی کامل راست‌به‌چپ (RTL)
Excel Exporter with 3 sheets:
1. Matching, Active Brandings
2. Rejected
3. ALL SCRAPED RECORDS
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def export_scan_to_excel(
    scan_info: Dict[str, Any],
    alerts: List[Dict[str, Any]],
    all_class5: Optional[List[Dict[str, Any]]] = None,
    output_dir: str = "reports",
    rejected: Optional[List[Dict[str, Any]]] = None,
    all_records: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    تولید فایل اکسل سه برگه‌ای (هشدارهای شباهت فعال + پرونده‌های رد شده + کلیه اظهارنامه‌ها)
    """
    os.makedirs(output_dir, exist_ok=True)
    scan_date_str = str(scan_info.get('scan_date', 'unknown')).replace('/', '-').replace(':', '-')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"گزارش_اسکن_{scan_date_str}_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)

    wb = openpyxl.Workbook()

    # استایل‌ها
    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_font = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")

    high_risk_fill = PatternFill(start_color="FFD2D2", end_color="FFD2D2", fill_type="solid")
    high_risk_font = Font(name="Tahoma", size=10, bold=True, color="9C0006")

    med_risk_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    med_risk_font = Font(name="Tahoma", size=10, bold=True, color="9C6500")

    cell_font = Font(name="Tahoma", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # --- برگه ۱: Matching, Active Brandings ---
    ws_alerts = wb.active
    ws_alerts.title = "Matching, Active Brandings"
    ws_alerts.views.sheetView[0].rightToLeft = True

    headers_alerts = [
        "ردیف", "درصد شباهت", "سطح ریسک", "برند مرجع",
        "عنوان علامت متقاضی", "شماره اظهارنامه", "تاریخ اظهارنامه",
        "وضعیت پرونده", "طبقات بین‌المللی", "لینک پرونده در سامانه"
    ]

    ws_alerts.append(headers_alerts)
    for col_idx, _ in enumerate(headers_alerts, start=1):
        c = ws_alerts.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center_align

    for idx, item in enumerate(alerts or [], start=1):
        score = float(item.get('similarity_score', 0.0))
        risk = item.get('risk_level', 'low')
        risk_fa = "خطر بالا" if risk == 'high' else ("خطر متوسط" if risk == 'medium' else "عادی")

        row_data = [
            idx,
            f"{score:.1f}%",
            risk_fa,
            item.get('matched_brand', ''),
            item.get('title', ''),
            item.get('declaration_no', ''),
            item.get('declaration_date', ''),
            item.get('status', ''),
            item.get('classes', ''),
            item.get('detail_url', '')
        ]
        ws_alerts.append(row_data)
        row_num = ws_alerts.max_row

        for c_idx in range(1, len(row_data) + 1):
            cell = ws_alerts.cell(row=row_num, column=c_idx)
            cell.font = cell_font
            cell.border = thin_border
            cell.alignment = right_align if c_idx in [4, 5] else center_align

            if c_idx in [2, 3]:
                if risk == 'high':
                    cell.fill = high_risk_fill
                    cell.font = high_risk_font
                elif risk == 'medium':
                    cell.fill = med_risk_fill
                    cell.font = med_risk_font

            if c_idx == 10 and item.get('detail_url'):
                cell.hyperlink = item.get('detail_url')
                cell.font = Font(name="Tahoma", size=10, color="0000FF", underline="single")

    # --- برگه ۲: Rejected ---
    ws_rejected = wb.create_sheet(title="Rejected")
    ws_rejected.views.sheetView[0].rightToLeft = True

    headers_rejected = [
        "ردیف", "عنوان علامت", "شماره اظهارنامه", "تاریخ اظهارنامه",
        "وضعیت پرونده", "طبقات بین‌المللی", "لینک پرونده در سامانه"
    ]

    ws_rejected.append(headers_rejected)
    for col_idx, _ in enumerate(headers_rejected, start=1):
        c = ws_rejected.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center_align

    # اگر لیست rejected اختصاصی داده نشده بود، از رکوردهای رد شده استخراج کن
    records_to_check = all_records or all_class5 or []
    rej_list = rejected if rejected is not None else [r for r in records_to_check if r.get('is_rejected')]

    for idx, item in enumerate(rej_list, start=1):
        row_data = [
            idx,
            item.get('title', ''),
            item.get('declaration_no', ''),
            item.get('declaration_date', ''),
            item.get('status', 'رد شده'),
            item.get('classes', ''),
            item.get('detail_url', '')
        ]
        ws_rejected.append(row_data)
        row_num = ws_rejected.max_row

        for c_idx in range(1, len(row_data) + 1):
            cell = ws_rejected.cell(row=row_num, column=c_idx)
            cell.font = cell_font
            cell.border = thin_border
            cell.alignment = right_align if c_idx == 2 else center_align

            if c_idx == 7 and item.get('detail_url'):
                cell.hyperlink = item.get('detail_url')
                cell.font = Font(name="Tahoma", size=10, color="0000FF", underline="single")

    # --- برگه ۳: ALL SCRAPED RECORDS ---
    ws_all = wb.create_sheet(title="ALL SCRAPED RECORDS")
    ws_all.views.sheetView[0].rightToLeft = True

    headers_all = [
        "ردیف", "عنوان علامت", "شماره اظهارنامه", "تاریخ اظهارنامه",
        "وضعیت پرونده", "وضعیت رد", "طبقات بین‌المللی", "لینک پرونده در سامانه"
    ]

    ws_all.append(headers_all)
    for col_idx, _ in enumerate(headers_all, start=1):
        c = ws_all.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center_align

    all_list = all_records or all_class5 or []
    for idx, item in enumerate(all_list, start=1):
        is_rej = item.get('is_rejected')
        rej_fa = "رد شده" if is_rej else "فعال"

        row_data = [
            idx,
            item.get('title', ''),
            item.get('declaration_no', ''),
            item.get('declaration_date', ''),
            item.get('status', ''),
            rej_fa,
            item.get('classes', ''),
            item.get('detail_url', '')
        ]
        ws_all.append(row_data)
        row_num = ws_all.max_row

        for c_idx in range(1, len(row_data) + 1):
            cell = ws_all.cell(row=row_num, column=c_idx)
            cell.font = cell_font
            cell.border = thin_border
            cell.alignment = right_align if c_idx == 2 else center_align

            if c_idx == 8 and item.get('detail_url'):
                cell.hyperlink = item.get('detail_url')
                cell.font = Font(name="Tahoma", size=10, color="0000FF", underline="single")

    # تنظیم خودکار عرض ستون‌ها
    for ws in [ws_alerts, ws_rejected, ws_all]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(filepath)
    return filepath
