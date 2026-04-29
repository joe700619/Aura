"""
Tax152 各類所得扣繳稅額繳款書產生器
===================================
使用原版 152.pdf 空白範本 + pypdf 套印

做法：
1. 用 reportlab 產生只含動態資料（文字+條碼）的透明 overlay PDF
2. 用 pypdf 將 overlay 疊印到 152.pdf 範本上
   → 靜態文字、框線、說明文字全由 152.pdf 提供，不需手動繪製

座標系統：
  jrxml: 原點在左上角，y 向下
  reportlab: 原點在左下角，y 向上
  轉換: pdf_y = page_height - jrxml_y
"""

import os
import datetime
import tempfile
from dataclasses import dataclass, field

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code39
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter


# ============================================================
# 頁面常數
# ============================================================
PAGE_W, PAGE_H = A4  # 595.27 x 841.89

DEFAULT_TEMPLATE_PDF = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tax152_assets", "152.pdf"
)

# ============================================================
# 所得類別對照
# ============================================================
INCOME_TYPE_MAP = {
    "152": "租賃", "153": "利息", "154": "權利金",
    "155": "股利或盈餘", "156": "執行業務報酬",
    "157": "競技競賽及機會中獎獎金", "158": "退職所得",
    "15B": "其他所得", "15U": "文物及藝術品財產交易所得",
}

# ============================================================
# 條碼核心邏輯（從 BarcodeFactory.java 反編譯移植）
# ============================================================
MONTH_CODE = "123456789ABC"
CHECK_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHECK_CODE_TABLE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def get_check_code(barcode1: str, barcode2: str, barcode3_temp: str) -> str:
    check_amt = 0
    for barcode in [barcode1, barcode2, barcode3_temp]:
        for c in barcode.upper():
            idx = CHECK_ALPHA.find(c)
            if idx > -1:
                check_amt += idx + 10
            else:
                check_amt += ord(c) - ord('0')
    return CHECK_CODE_TABLE[check_amt % 36]


def get_give_date(year: str, month: str, day: str) -> str:
    yy = f"{int(year):03d}"[1:]
    month_char = MONTH_CODE[int(month) - 1]
    dd = f"{int(day):02d}"
    return yy + month_char + dd


def roc_date_add(year, month, day, cal_type, unit):
    import calendar as cal_mod
    ad_year = int(year) + 1911
    m, d = int(month), int(day)
    dt = datetime.date(ad_year, m, d)
    if cal_type == "month":
        new_m = m + unit
        new_y = ad_year + (new_m - 1) // 12
        new_m = (new_m - 1) % 12 + 1
        max_d = cal_mod.monthrange(new_y, new_m)[1]
        return datetime.date(new_y, new_m, min(d, max_d))
    return dt + datetime.timedelta(days=unit)


def skip_holidays(dt, holidays=None):
    if holidays is None:
        holidays = set()
    while dt.weekday() >= 5 or dt in holidays:
        dt += datetime.timedelta(days=1)
    return dt


def to_roc_6(dt):
    roc = dt.year - 1911
    yy = str(roc)[-2:] if roc >= 100 else f"{roc:02d}"
    return f"{yy}{dt.month:02d}{dt.day:02d}"


def to_roc_date_str(dt):
    roc = dt.year - 1911
    return f"{roc:03d} 年 {dt.month:02d} 月 {dt.day:02d} 日"


# ============================================================
# 產生 Tax152 三段條碼
# ============================================================

@dataclass
class Tax152Input:
    city_id: str          # 縣市代碼 (1碼)
    unit_code: str        # 稅籍單位代碼 (4碼)
    company_no: str       # 統一編號 (8碼)
    tran_type: str        # 交易類型代碼 (如 "152","153",...)
    pw_amt: int           # 應扣繳稅額
    owner_cat: str = "0"  # "0"=本國人, "1"=外國人
    is_expired: bool = False
    is_media_file: bool = False
    give_year: str = ""   # 給付年 (民國)
    give_month: str = ""
    give_day: str = ""
    property23: str = "1" # "2"=適用(baseDay=10), 其他=9
    holidays: set = field(default_factory=set)

    # 以下為 PDF 欄位
    unit_name: str = ""          # 稽徵機關
    company_name: str = ""       # 扣繳單位名稱
    withholding_person: str = "" # 扣繳義務人
    withholding_address: str = ""
    withholding_phone: str = ""
    income_year: str = ""        # 所得所屬年度
    income_month: str = ""       # 所得所屬月份
    gross_income: int = 0        # 給付所得總額
    taxable_income: int = 0      # 應扣繳所得額
    is_auto_repay: bool = False  # 自動補扣繳


class BarcodeResult:
    def __init__(self, barcode1, barcode2, barcode3):
        self.barcode1 = barcode1
        self.barcode2 = barcode2
        self.barcode3 = barcode3


def generate_152_barcode(tax: Tax152Input) -> BarcodeResult:
    base_day = 10 if tax.property23 == "2" else 9

    barcode2 = tax.city_id + tax.unit_code + tax.company_no
    barcode2 += get_give_date(tax.give_year, tax.give_month, tax.give_day)
    barcode2 += "1" if tax.owner_cat == "0" else "2"

    if tax.owner_cat == "0":
        pay_deadline = roc_date_add(tax.give_year, tax.give_month, "10",
                                    "month", 1)
    else:
        pay_deadline = roc_date_add(tax.give_year, tax.give_month,
                                    tax.give_day, "day", base_day)

    # 限繳日期直接取次月10日，不順延假日

    cal_date_6 = to_roc_6(pay_deadline)
    barcode1 = cal_date_6 + ("6AF" if (tax.is_media_file or tax.is_expired)
                              else "6AE")

    tax_code = tax.tran_type[:3]
    expire_code = "4" if tax.is_expired else "3"
    pw_amt_str = f"{tax.pw_amt:010d}"

    barcode3_temp = tax_code + expire_code + pw_amt_str
    check_code = get_check_code(barcode1, barcode2, barcode3_temp)
    barcode3 = tax_code + expire_code + check_code + pw_amt_str

    tax._pay_deadline = pay_deadline
    tax._pay_start_date = datetime.date(
        int(tax.give_year) + 1911, int(tax.give_month), int(tax.give_day))

    return BarcodeResult(barcode1, barcode2, barcode3)


# ============================================================
# PDF 套印（使用 152.pdf 範本 + overlay）
# ============================================================

def jy(jrxml_y):
    return PAGE_H - jrxml_y


def setup_font():
    for fp in ["C:/Windows/Fonts/kaiu.ttf",
               "C:/Windows/Fonts/msjh.ttc",
               "C:/Windows/Fonts/mingliu.ttc"]:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("CJK", fp))
                return "CJK"
            except Exception:
                continue
    return "Helvetica"


def draw_text(c, font, size, x, y, w, h, text, align="left", v_align="middle"):
    c.setFont(font, size)
    if v_align == "middle":
        text_y = jy(y) - h / 2 - size * 0.3
    elif v_align == "top":
        text_y = jy(y) - size
    else:
        text_y = jy(y) - h + 2
    if align == "center":
        c.drawCentredString(x + w / 2, text_y, text)
    elif align == "right":
        c.drawRightString(x + w - 3, text_y, text)
    else:
        c.drawString(x + 2, text_y, text)


def draw_code39(c, x, y, h, data):
    BAR_WIDTH = 0.7
    bc_obj = code39.Standard39(
        data,
        barWidth=BAR_WIDTH,
        barHeight=h - 2,
        checksum=0,
        humanReadable=False,
    )
    bc_obj.drawOn(c, x, jy(y) - h + 1)
    return x


def _create_overlay(tax: Tax152Input, bc: BarcodeResult, overlay_path: str):
    font = setup_font()
    c = canvas.Canvas(overlay_path, pagesize=A4)

    income_code = tax.tran_type[:3]
    income_name = INCOME_TYPE_MAP.get(income_code, income_code)
    pay_start_str = to_roc_date_str(tax._pay_start_date)
    pay_end_str = to_roc_date_str(tax._pay_deadline)
    auto_mark = "■" if tax.is_auto_repay else "□"
    wh_amt_str = f"{tax.pw_amt:,.0f}"
    gross_str = f"{tax.gross_income:,.0f}" if tax.gross_income else ""
    taxable_str = f"{tax.taxable_income:,.0f}" if tax.taxable_income else ""

    now = datetime.datetime.now()
    c.setFont(font, 7)
    c.drawRightString(417 + 152, jy(0) - 10, "第1頁共1頁")
    c.drawRightString(417 + 152, jy(0) - 20,
                      f"列印日期：{now.strftime('%Y年%m月%d日  %H時%M分%S秒')}")

    # 收據聯（上半部）
    draw_text(c, font, 14, 103, 29, 340, 20, tax.unit_name, "center")
    draw_text(c, font, 10, 101, 79, 261, 20, tax.company_name)
    draw_text(c, font, 9, 445, 79, 119, 13, tax.withholding_phone)
    draw_text(c, font, 9, 445, 93, 119, 13, pay_start_str)
    draw_text(c, font, 9, 445, 106, 119, 14, pay_end_str)
    draw_text(c, font, 10, 101, 110, 261, 14, tax.company_no)
    draw_text(c, font, 10, 101, 128, 261, 20, tax.withholding_person)
    draw_text(c, font, 9, 101, 149, 261, 15, tax.withholding_address)
    draw_text(c, font, 10, 28, 203, 146, 20,
              f"{income_code} {income_name}", "center")
    draw_text(c, font, 9, 174, 203, 74, 20,
              f"{tax.income_year}年{tax.income_month}月", "center")
    draw_text(c, font, 10, 248, 203, 94, 20, gross_str, "right")
    draw_text(c, font, 10, 342, 203, 94, 20, taxable_str, "right")
    draw_text(c, font, 10, 174, 223, 262, 20, wh_amt_str, "right")
    draw_text(c, font, 7, 68, 270, 48, 27, f"{auto_mark}自動補扣繳")

    # 收款機構留存聯（下半部）
    draw_text(c, font, 14, 103, 550, 340, 20, tax.unit_name, "center")
    draw_text(c, font, 8, 364, 592, 201, 18,
              f"扣繳義務人聯絡電話：{tax.withholding_phone}")

    draw_code39(c, 50, 639, 28, bc.barcode1)
    c.setFont("Courier", 9)
    c.drawString(66, jy(667) - 9, bc.barcode1)

    draw_code39(c, 50, 689, 28, bc.barcode2)
    c.setFont("Courier", 9)
    c.drawString(66, jy(717) - 9, bc.barcode2)

    draw_code39(c, 50, 739, 28, bc.barcode3)
    c.setFont("Courier", 9)
    c.drawString(66, jy(767) - 9, bc.barcode3)

    draw_text(c, font, 8, 353, 609, 93, 39, tax.withholding_person, "center")
    draw_text(c, font, 10, 353, 648, 93, 14, income_code, "center")
    draw_text(c, font, 10, 353, 662, 93, 26, wh_amt_str, "right")
    draw_text(c, font, 8, 306, 718, 140, 15, f"{auto_mark}自動補扣繳")

    pay_end_parts = pay_end_str.replace("年", " 年 ").replace(
        "月", " 月 ").replace("日", " 日")
    draw_text(c, font, 10, 306, 733, 264, 17,
              f"限繳日期：{pay_end_parts}")

    c.save()


def generate_pdf(tax: Tax152Input, bc: BarcodeResult, output_path: str,
                 template_pdf: str = None):
    if template_pdf is None:
        template_pdf = DEFAULT_TEMPLATE_PDF

    if not os.path.exists(template_pdf):
        raise FileNotFoundError(f"找不到範本 PDF: {template_pdf}")

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        overlay_path = tmp.name

    try:
        _create_overlay(tax, bc, overlay_path)

        template = PdfReader(template_pdf)
        overlay = PdfReader(overlay_path)

        page = template.pages[0]
        # 移除 Annotations（白色遮蓋方塊可能以 Annotation 形式存在，
        # 不移除會蓋在 overlay 之上）
        if "/Annots" in page:
            del page["/Annots"]
        page.merge_page(overlay.pages[0])

        writer = PdfWriter()
        writer.add_page(page)

        with open(output_path, 'wb') as f:
            writer.write(f)
    finally:
        if os.path.exists(overlay_path):
            os.unlink(overlay_path)

    return output_path


def generate_pdf_bytes(tax: Tax152Input, template_pdf: str = None) -> bytes:
    """產生 PDF 並直接回傳 bytes（供 HTTP response 使用）"""
    bc = generate_152_barcode(tax)

    if template_pdf is None:
        template_pdf = DEFAULT_TEMPLATE_PDF

    if not os.path.exists(template_pdf):
        raise FileNotFoundError(f"找不到範本 PDF: {template_pdf}")

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        overlay_path = tmp.name

    try:
        _create_overlay(tax, bc, overlay_path)

        template = PdfReader(template_pdf)
        overlay = PdfReader(overlay_path)

        page = template.pages[0]
        if "/Annots" in page:
            del page["/Annots"]
        page.merge_page(overlay.pages[0])

        writer = PdfWriter()
        writer.add_page(page)

        import io
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    finally:
        if os.path.exists(overlay_path):
            os.unlink(overlay_path)
