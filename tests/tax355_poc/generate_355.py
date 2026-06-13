"""
Tax355 暫繳繳款書 PDF 套印 — PoC
=================================
作法與正式的 tax152_service 相同：
  1. reportlab 產生「只含動態資料（文字＋條碼）」的透明 overlay
  2. pypdf 疊印到空白範本 assets/355.pdf 上
     → 框線、標籤、說明文字全由 355.pdf 提供

座標系：jrxml / 355.pdf / PyMuPDF 皆 595×842、左上原點；reportlab 左下原點，
       故 pdf_y = PAGE_H - y（jy()）。

文字欄位座標來源：用 PyMuPDF 抽出 355.pdf 既有標籤的精確 bbox，
把「值」貼到標籤後方或填入「自__年__月__日」的空格中央
（355.pdf 已印標籤，overlay 只填值，不重畫標籤）。
條碼座標取自 ETW144W3.jrxml（範本無對應靜態物）。

僅供 tests/ 驗證，輸入皆模擬資料，未接正式流程、不連資料庫。
"""

import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code39
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

from tests.tax355_poc.barcode355 import Tax355Input, generate_355_barcode

PAGE_W, PAGE_H = A4
TEMPLATE_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "355.pdf")

_CJK_FONT_CANDIDATES = [
    "C:/Windows/Fonts/kaiu.ttf",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/mingliu.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
]


def _setup_font():
    for fp in _CJK_FONT_CANDIDATES:
        if os.path.exists(fp):
            try:
                if fp.lower().endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont("CJK", fp, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont("CJK", fp))
                return "CJK"
            except Exception:
                continue
    return "Helvetica"


def _jy(y):
    return PAGE_H - y


def _text(c, font, size, x, y0, text, align="left"):
    """以範本標籤的 bbox 上緣 y0 對齊畫字（baseline ≈ jy(y0) - size*0.85）。"""
    c.setFont(font, size)
    ty = _jy(y0) - size * 0.85
    if align == "center":
        c.drawCentredString(x, ty, text)
    elif align == "right":
        c.drawRightString(x, ty, text)
    else:
        c.drawString(x, ty, text)


def _code39(c, x, y, w, h, data):
    """Code39，moduleWidth 0.7；不加自身檢查碼（已由 generate_355_barcode 編入）。"""
    bc = code39.Standard39(data, barWidth=0.7, barHeight=h,
                           checksum=0, humanReadable=False)
    bc.drawOn(c, x, _jy(y) - h)


# ── 三聯公司資料區：每個標籤的 bbox 上緣 y 與「值起始 x」（取自 355.pdf）──
#   收據聯 base、證明聯 base 兩組
_COMPANY_BLOCKS = [
    # (名稱y, 統編y, 姓名y, 負責統編y, 地址y)
    (89.5, 101.5, 113.5, 125.5, 137.5),   # 收據聯
    (402.4, 414.4, 426.4, 438.4, 450.4),  # 證明聯
]
# 值起始 x（標籤 x1 + 小間距）
_X_NAME, _X_NO, _X_PEOPLE, _X_PNO, _X_ADDR = 102, 122, 172, 192, 102

# ── 法定繳納期間「自__年__月__日起 / 至__年__月__日止」空格中央 x ──
#   收據聯 / 證明聯共用 x，y 不同
_DATE_X = {"year": 462.5, "mm": 498.5, "dd": 531.5}
_DATE_ROWS = [
    (114.6, 131.7),  # 收據聯 (起, 止)
    (427.6, 444.6),  # 證明聯
]
# ── 收據/證明聯金額欄（本稅 / 應繳金額合計）值列 y 與右對齊 x ──
_AMT_ROWS = [176.0, 489.0]  # 收據聯、證明聯（值欄 171–190 / 484–503 的垂直中央）
_X_AMT_TAX, _X_AMT_TOTAL = 185, 410


def generate_355_pdf(data: dict) -> bytes:
    font = _setup_font()

    tax = Tax355Input(
        agency_code=data["agency_code"],
        company_no=data["company_no"],
        pw_amt=data["pw_amt"],
        b_yy=data["pay_year"],
        tran_type=data.get("tran_type", "355"),
        holidays=data.get("holidays", set()),
    )
    bc1, bc2, bc3 = generate_355_barcode(tax)
    amt_str = f"{int(data['pw_amt']):,}"
    yr, smm, sdd = data["pay_year"], int(data["start_mm"]), int(data["start_dd"])
    emm, edd = int(data["end_mm"]), int(data["end_dd"])

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # ── 三聯標題：稽徵機關（dynamic，範本無）──
    for yy in (30, 351, 548):
        _text(c, font, 15, 264, yy, data["unit_name"], "center")

    # ── 收據聯 / 證明聯：公司資料 + 期間 + 金額 ──
    for (ny, noy, py, pnoy, ay), (r_s, r_e), amt_y in zip(
            _COMPANY_BLOCKS, _DATE_ROWS, _AMT_ROWS):
        _text(c, font, 10, _X_NAME, ny, data["company_name"])
        _text(c, font, 10, _X_NO, noy, data["company_no"])
        _text(c, font, 10, _X_PEOPLE, py, data["people_name"])
        _text(c, font, 10, _X_PNO, pnoy, data["people_no"])
        _text(c, font, 9, _X_ADDR, ay, data["company_addr"])
        # 期間空格（年/月/日 分開填入中央）
        _text(c, font, 10, _DATE_X["year"], r_s, yr, "center")
        _text(c, font, 10, _DATE_X["mm"], r_s, f"{smm:02d}", "center")
        _text(c, font, 10, _DATE_X["dd"], r_s, f"{sdd:02d}", "center")
        _text(c, font, 10, _DATE_X["year"], r_e, yr, "center")
        _text(c, font, 10, _DATE_X["mm"], r_e, f"{emm:02d}", "center")
        _text(c, font, 10, _DATE_X["dd"], r_e, f"{edd:02d}", "center")
        # 金額
        _text(c, font, 10, _X_AMT_TAX, amt_y, amt_str, "right")
        _text(c, font, 10, _X_AMT_TOTAL, amt_y, amt_str, "right")

    # ── 收款機構留存聯（底部）──
    # 條碼三段（jrxml 座標）+ 可讀文字
    _code39(c, 50, 659, 230, 26, bc1)
    _text(c, "Courier", 9, 66, 692, bc1)
    _code39(c, 50, 709, 230, 26, bc2)
    _text(c, "Courier", 9, 66, 742, bc2)
    _code39(c, 50, 759, 230, 26, bc3)
    _text(c, "Courier", 9, 66, 792, bc3)
    # 右側明細值欄（稅目 355 範本已印，不重畫）
    _text(c, font, 10, 365, 617.5, data["company_name"])          # 營利事業名稱
    _text(c, font, 11, 400, 646.9, data["pay_year"], "center")    # 所屬年度
    _text(c, font, 10, 435, 704.5, amt_str, "right")              # 應繳金額合計
    _text(c, font, 9, 462, 594.0, data["phone"])                  # 納稅義務人電話
    # 法定繳納期間空格（底部留存聯）
    _text(c, font, 9, 385, 732.4, yr, "center")
    _text(c, font, 9, 410, 732.4, f"{smm:02d}", "center")
    _text(c, font, 9, 435, 732.4, f"{sdd:02d}", "center")
    _text(c, font, 9, 482, 732.4, yr, "center")
    _text(c, font, 9, 507, 732.4, f"{emm:02d}", "center")
    _text(c, font, 9, 532, 732.4, f"{edd:02d}", "center")

    c.save()
    buf.seek(0)

    # ── pypdf 疊印 ──
    template = PdfReader(TEMPLATE_PDF)
    overlay = PdfReader(buf)
    page = template.pages[0]
    if "/Annots" in page:
        del page["/Annots"]
    page.merge_page(overlay.pages[0])

    writer = PdfWriter()
    writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()
