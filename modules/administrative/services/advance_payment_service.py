from django.utils import timezone

# 代墊類型 → 借方科目代碼對應表 (與前端 paymentTypeMap 一致)
PAYMENT_TYPE_ACCOUNT_MAP = {
    'POSTAGE':               ('613202', '郵資及快遞'),
    'GROUP_INVOICE':         ('613203', '發票費用'),
    'TAX':                   ('1141',   '代墊稅款及保費'),
    'SUPPLEMENTARY_PREMIUM': ('1141',   '代墊稅款及保費'),
    'GOV_FEE':               ('1142',   '代墊政府規費'),
    'RETAIL_INVOICE':        ('613203', '發票費用'),
    'SEAL':                  ('613204', '印章費用'),
}
FALLBACK_DEBIT_CODE = '6132'
CREDIT_ACCOUNT_CODE = '111401'  # 國泰世華


def generate_voucher_for_advance_payment(advance_payment, user):
    """
    為「代墊款」產生傳票。
    借方：依代墊類型對應的費用/資產科目（每筆明細一行）
    貸方：111401 國泰世華（一筆合計）
    """
    from modules.internal_accounting.models import Voucher, VoucherDetail, Account

    details = advance_payment.details.filter(amount__gt=0)
    if not details.exists():
        raise ValueError("沒有任何金額大於0的明細，無法產生傳票")

    total_amount = sum(d.amount for d in details)

    # 取得貸方科目
    try:
        credit_account = Account.objects.get(code=CREDIT_ACCOUNT_CODE)
    except Account.DoesNotExist:
        raise ValueError(f"找不到貸方科目 {CREDIT_ACCOUNT_CODE}，請先建立該會計科目")

    # 建立傳票主檔
    today_str = timezone.now().strftime('%Y%m%d')
    count = Voucher.objects.filter(date=timezone.now().date()).count() + 1
    voucher_no = f'VOU-{today_str}-{count:03d}'

    voucher = Voucher.objects.create(
        voucher_no=voucher_no,
        date=timezone.now().date(),
        description=f"代墊款拋轉：{advance_payment.advance_no}",
        status=Voucher.Status.DRAFT,
        source=Voucher.Source.SYSTEM,
        created_by=user
    )

    # 針對每一筆明細建立借方分錄
    for detail in details:
        code, _name = PAYMENT_TYPE_ACCOUNT_MAP.get(detail.payment_type, (FALLBACK_DEBIT_CODE, '代墊費用'))
        try:
            debit_account = Account.objects.get(code=code)
        except Account.DoesNotExist:
            try:
                debit_account = Account.objects.get(code=FALLBACK_DEBIT_CODE)
            except Account.DoesNotExist:
                raise ValueError(f"找不到借方科目 {code}（及備援科目 {FALLBACK_DEBIT_CODE}），請先建立該會計科目")

        VoucherDetail.objects.create(
            voucher=voucher,
            account=debit_account,
            debit=detail.amount,
            credit=0,
            remark=f"{detail.reason or ''}{' (' + detail.unified_business_no + ')' if detail.unified_business_no else ''}"
        )

    # 建立一筆貸方分錄（總計）
    VoucherDetail.objects.create(
        voucher=voucher,
        account=credit_account,
        debit=0,
        credit=total_amount,
        remark=f"代墊款拋轉 {advance_payment.advance_no}"
    )

    return voucher
