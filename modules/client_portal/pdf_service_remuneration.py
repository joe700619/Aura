"""
勞務報酬單 PDF 產生器（使用 ReportLab Platypus）
"""
import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)


# ============================================================
# 字型注冊（一次性）
# ============================================================
_FONT_NAME = 'CJK'
_FONT_REGISTERED = False


def _ensure_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return _FONT_NAME
    for path in ['C:/Windows/Fonts/kaiu.ttf',
                 'C:/Windows/Fonts/msjh.ttc',
                 'C:/Windows/Fonts/mingliu.ttc']:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(_FONT_NAME, path))
                _FONT_REGISTERED = True
                return _FONT_NAME
            except Exception:
                continue
    return 'Helvetica'


# ============================================================
# 工具函式
# ============================================================
def _roc_date(d) -> str:
    if not d:
        return ''
    return f"{d.year - 1911}年{d.month}月{d.day}日"


def _cb(checked: bool) -> str:
    """checkbox 字元"""
    return '■' if checked else '□'


def _fmt_int(n) -> str:
    if n is None:
        return ''
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n == 0:
        return ''
    return f"{n:,}"


# ============================================================
# 主函式
# ============================================================
def generate_service_remuneration_pdf(obj) -> bytes:
    font = _ensure_font()

    # ---- styles ----
    base_style = ParagraphStyle(
        name='base', fontName=font, fontSize=9, leading=12,
    )
    title_style = ParagraphStyle(
        name='title', fontName=font, fontSize=18, leading=22,
        alignment=1,  # center
    )
    pay_date_style = ParagraphStyle(
        name='paydate', fontName=font, fontSize=10, leading=14,
        alignment=1,
    )
    note_title_style = ParagraphStyle(
        name='note_title', fontName=font, fontSize=8.5, leading=12,
        textColor=colors.HexColor('#1414cc'),
    )
    note_body_style = ParagraphStyle(
        name='note_body', fontName=font, fontSize=8, leading=11,
    )
    sig_style = ParagraphStyle(
        name='sig', fontName=font, fontSize=9.5, leading=13,
    )
    label_style = ParagraphStyle(
        name='label', fontName=font, fontSize=9, leading=12,
        alignment=1,
    )

    is_local = obj.nationality == 'local'
    is_gte_183 = obj.nationality == 'foreign_gte_183'
    is_lt_183 = obj.nationality == 'foreign_lt_183'

    cat = obj.income_category
    is_9a = cat == '9A'
    is_9b = cat == '9B'
    is_50 = cat == '50'
    is_92 = cat == '92'
    is_51 = cat == '51'

    # ---- elements ----
    elements = []

    # ① 標題
    elements.append(Paragraph(
        '<u>　<b>勞　務　報　酬　單</b>　</u>', title_style,
    ))
    elements.append(Spacer(1, 4))

    # 支付日期
    filing_label = _roc_date(obj.filing_date) or '______年______月______日'
    elements.append(Paragraph(f'支付日期：{filing_label}', pay_date_style))
    elements.append(Spacer(1, 6))

    # ② 領款人基本資料
    nat_line = (
        f"<b>領款人基本資料：</b>　　"
        f"{_cb(is_local)} 本國籍　　"
        f"{_cb(is_gte_183)} 外國籍（在台<b>滿</b>183天）　　"
        f"{_cb(is_lt_183)} 外國籍（在台<b>未滿</b>183天）"
    )
    basic_data = [
        [Paragraph(nat_line, base_style)],
        [
            Paragraph('姓名：', base_style),
            Paragraph(obj.recipient_name or '', base_style),
            Paragraph('身分證字號：', base_style),
            Paragraph(obj.id_number or '', base_style),
        ],
        [
            Paragraph('連絡電話：', base_style),
            Paragraph(obj.phone or '', base_style),
            Paragraph('居留證/護照No.', base_style),
            Paragraph('', base_style),
        ],
        [
            Paragraph('戶籍地址：', base_style),
            Paragraph(obj.residence_address or '', base_style),
        ],
    ]
    basic_table = Table(
        basic_data,
        colWidths=[22*mm, 60*mm, 28*mm, 72*mm],
        rowHeights=[None, None, None, None],
    )
    basic_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('SPAN', (0, 0), (3, 0)),
        ('SPAN', (1, 3), (3, 3)),
        ('BACKGROUND', (0, 1), (0, 3), colors.HexColor('#f0f0f0')),
        ('BACKGROUND', (2, 1), (2, 2), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(basic_table)
    elements.append(Spacer(1, 4))

    # ③ 勞務內容
    content_table = Table(
        [[
            Paragraph('勞務內容<br/>（請概述）', label_style),
            Paragraph(obj.service_content or '', base_style),
        ]],
        colWidths=[22*mm, 160*mm],
        rowHeights=[18*mm],
    )
    content_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('VALIGN', (1, 0), (1, 0), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(content_table)
    elements.append(Spacer(1, 4))

    # ④ 所得類別
    income_line = (
        f"{_cb(is_9a)} 執行業務 9A　　"
        f"{_cb(is_9b)} 稿費 9B　　"
        f"{_cb(is_50)} 兼職薪資 50　　"
        f"{_cb(is_92)} 其他所得 92　　"
        f"{_cb(is_51)} 租賃所得 51"
    )
    income_table = Table(
        [[
            Paragraph('所得類別', label_style),
            Paragraph(income_line, base_style),
        ]],
        colWidths=[22*mm, 160*mm],
    )
    income_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(income_table)
    elements.append(Spacer(1, 4))

    # ⑤ 注1, 注2
    note1_lines = [
        Paragraph('承攬或接案者（非僱傭關係），勾選9A或9B', note_title_style),
        Paragraph(
            '注1：<b><font color="#1414cc">9A執行業務者：</font></b>'
            '係指律師、會計師、建築師、技師、醫師、藥師、助產士、醫事檢驗師、'
            '藝術師、不動產估價師、物理治療師、職業治療師、營養師、心理師、'
            '地政士、記帳士、<b>經紀人</b>、代書人、<b>演講人</b>、引水人、'
            '節目製作人、商標代理人、專利代理人、仲裁人及「<b>其他</b>」'
            '以技藝自力營生者。',
            note_body_style,
        ),
        Paragraph(
            '注2：<b>9B稿費：</b>個人稿費、版稅、樂譜、作曲、演講費、稿資的統稱。',
            note_body_style,
        ),
    ]
    note1_table = Table([[note1_lines]], colWidths=[182*mm])
    note1_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(note1_table)
    elements.append(Spacer(1, 4))

    # ⑥ 注3, 注4
    note2_lines = [
        Paragraph('薪資關係，勾選薪資(50)：', note_title_style),
        Paragraph(
            '注3：<b>已投保勞健保之員工免填</b>勞務報酬單。',
            note_body_style,
        ),
        Paragraph(
            '注4：未投保健保之員工，若公司已成立健保單位且未加保其他受僱員工，'
            '公司須繳約<b>2.11%二代健保</b>。',
            note_body_style,
        ),
    ]
    note2_table = Table([[note2_lines]], colWidths=[182*mm])
    note2_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(note2_table)
    elements.append(Spacer(1, 4))

    # ⑦ 領款金額表
    amt_header_style = ParagraphStyle(
        name='amt_header', fontName=font, fontSize=8.5, leading=11,
        alignment=1,
    )
    amt_sub_style = ParagraphStyle(
        name='amt_sub', fontName=font, fontSize=7.5, leading=10,
        alignment=1, textColor=colors.HexColor('#666666'),
    )
    amt_val_style = ParagraphStyle(
        name='amt_val', fontName=font, fontSize=10, leading=14,
        alignment=2,  # right
    )
    amt_label_style = ParagraphStyle(
        name='amt_label', fontName=font, fontSize=9, leading=12,
        alignment=1,
    )

    wh_50 = _fmt_int(obj.withholding_tax) if is_50 else ''
    wh_other = _fmt_int(obj.withholding_tax) if not is_50 else ''
    supp = _fmt_int(obj.supplementary_premium)

    amt_data = [
        [
            Paragraph('領款金額', amt_label_style),
            Paragraph('支領金額', amt_header_style),
            [Paragraph('兼職薪資扣繳5%', amt_header_style),
             Paragraph('（起扣額 90,501）', amt_sub_style)],
            [Paragraph('執行業務扣繳10%', amt_header_style),
             Paragraph('（起扣額 20,001）', amt_sub_style)],
            [Paragraph('二代健保扣費2.11%', amt_header_style),
             Paragraph('（起扣額 20,000）', amt_sub_style)],
            Paragraph('實領金額', amt_header_style),
        ],
        [
            '',
            Paragraph(_fmt_int(obj.amount), amt_val_style),
            Paragraph(wh_50, amt_val_style),
            Paragraph(wh_other, amt_val_style),
            Paragraph(supp, amt_val_style),
            Paragraph(_fmt_int(obj.actual_payment), amt_val_style),
        ],
    ]
    amt_table = Table(
        amt_data,
        colWidths=[22*mm, 32*mm, 32*mm, 32*mm, 32*mm, 32*mm],
        rowHeights=[16*mm, 11*mm],
    )
    amt_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (1, 0), (-1, 0), colors.HexColor('#e0e0e0')),
        ('SPAN', (0, 0), (0, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(amt_table)
    elements.append(Spacer(1, 4))

    # ⑧ 簽章列
    confirm_text = ''
    if obj.confirmed_at:
        confirm_text = f'已於 {_roc_date(obj.confirmed_at.date())} 確認'

    sig_table = Table(
        [[
            Paragraph('上述資料經本人確認無誤。', sig_style),
            Paragraph(
                f'所得人：<u>　{confirm_text}　　　　</u>'
                f'　<font color="#cc0000">（簽章）</font>',
                sig_style,
            ),
        ]],
        colWidths=[80*mm, 102*mm],
    )
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.6, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 3))

    # 提示
    note_style = ParagraphStyle(
        name='small_note', fontName=font, fontSize=8.5, leading=11,
        alignment=1, textColor=colors.HexColor('#333333'),
    )
    elements.append(Paragraph(
        '請附身分證影本（外籍人士請檢附居留證/護照影本）', note_style,
    ))
    elements.append(Spacer(1, 4))

    # ⑨ 身分證黏貼區
    id_title_style = ParagraphStyle(
        name='id_title', fontName=font, fontSize=10, leading=14,
        alignment=1,
    )
    id_label_style = ParagraphStyle(
        name='id_label', fontName=font, fontSize=10, leading=14,
        alignment=1,
    )

    def _id_cell(label, image_field):
        cell = [Paragraph(label, id_label_style), Spacer(1, 3)]
        if image_field:
            try:
                img = Image(image_field.path, width=70*mm, height=40*mm,
                            kind='proportional')
                cell.append(img)
            except Exception:
                cell.append(Paragraph('（無法載入圖片）', base_style))
        else:
            cell.append(Paragraph('黏貼於此',
                ParagraphStyle(name='paste', fontName=font, fontSize=9,
                               alignment=1, textColor=colors.HexColor('#aaaaaa'))))
        return cell

    id_section = Table(
        [
            [Paragraph('<b>身分證（居留證/護照）影本黏貼處</b>', id_title_style)],
            [[
                Table([[
                    _id_cell('正面', obj.id_front_image),
                    _id_cell('反面', obj.id_back_image),
                ]],
                colWidths=[91*mm, 91*mm],
                rowHeights=[50*mm],
                style=TableStyle([
                    ('LINEAFTER', (0, 0), (0, 0), 0.4, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                ]))
            ]],
        ],
        colWidths=[182*mm],
    )
    id_section.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('LINEBELOW', (0, 0), (0, 0), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(id_section)

    # ---- build PDF ----
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=12*mm, bottomMargin=12*mm,
        title='勞務報酬單',
    )
    doc.build(elements)
    buf.seek(0)
    return buf.read()
