"""
Tax355（營利事業所得稅暫繳稅額繳款書）三段條碼產生器 — PoC
=================================================================
從國稅局 pbc-1.0.jar 的 BarcodeFactory.get355Barcode() 反編譯移植。

驗證基準（真實樣本 Report_355.pdf，115 年度、應繳 30,000）：
    barcode1 = 1509306AE
    barcode2 = E100085120097159011
    barcode3 = 3554O0000030000

⚠️ 這是 PoC，僅供 tests/ 內驗證，未接任何正式流程、不連資料庫。
   一切輸入皆為模擬資料。

未附帶的部分（已知缺口）
------------------------
原程式的「均日展延」會去查 Holiday_WRR 假日表（含週末＋國定假日，依轄區）
往後順延限繳日。那張表沒有隨 jar 附帶，這裡改成可注入的 `holidays` 集合，
預設為空 → 正好重現上面樣本（115/09/30 當年未順延）。
真正上線時，遇到「9/30 落在假日要展延」的年度，需補上該轄區假日表再對拍驗證。
"""

import datetime
from dataclasses import dataclass, field


# ============================================================
# 檢查碼（與 tax152 共用，BarcodeFactory.getCheckCode 一字不差）
# ============================================================
_CHECK_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CHECK_CODE_TABLE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def get_check_code(*barcodes: str) -> str:
    """三段（barcode1, barcode2, barcode3_temp）算出 1 碼檢查碼。

    規則：A-Z → (index+10)，數字 → 該數字值；總和 % 36 對照 36 進位表。
    """
    amt = 0
    for barcode in barcodes:
        for c in barcode.upper():
            idx = _CHECK_ALPHA.find(c)
            amt += (idx + 10) if idx > -1 else (ord(c) - ord("0"))
    return _CHECK_CODE_TABLE[amt % 36]


# ============================================================
# 限繳日期計算（BarcodeFactory.calDate, calType=DATE, checkType=1）
# ============================================================
def _skip_holidays(d: datetime.date, holidays: set) -> datetime.date:
    """checkHoliday(checkType=1)：日期落在假日表內就往後一天，直到非假日。

    原程式假日表 Holiday_WRR 含週末＋國定假日；這裡用注入的集合表示。
    預設空集合代表「不順延」。
    """
    while d in holidays:
        d += datetime.timedelta(days=1)
    return d


def _cal_date(year_roc: str, month: str, day: str, add_days: int,
              holidays: set, two_digit_year: bool = True) -> str:
    """民國日期 + add_days，再跳過假日，輸出 (YY|YYY)MMDD。

    對應 BarcodeFactory.calDate(year, month, day, 5, add_days, yearNums, 1)：
      - calType=5 (Calendar.DATE) → 加 add_days 天
      - checkType=1 → 只做假日往後順延
      - yearNums=2 → 年取末 2 碼（barcode1 用）；=3 → 補滿 3 碼
    """
    d = datetime.date(int(year_roc) + 1911, int(month), int(day))
    d += datetime.timedelta(days=add_days)
    d = _skip_holidays(d, holidays)
    roc = d.year - 1911
    yy = f"{roc:03d}"
    yy = yy[-2:] if two_digit_year else yy
    return f"{yy}{d.month:02d}{d.day:02d}"


# ============================================================
# 輸入資料（模擬用 dataclass）
# ============================================================
@dataclass
class Tax355Input:
    """產 355 條碼所需欄位。欄位名沿用反編譯後的 Tax355 pojo 語意。"""
    agency_code: str       # 縣市別+稅籍單位（barcode2 前綴，= cityId+deptId，如 "E1000"）
    company_no: str        # 營利事業統一編號（8 碼）
    pw_amt: int            # 應繳金額
    b_yy: str              # 所屬年度（民國，如 "115"）
    tran_type: str = "355"  # 稅目
    expire_check: str = "0"  # "0"=正常期間, "1"=逾期自填日期
    barcode_day: int = 0     # 均日展延天數（正常期間，來自 ETWT434.barcodeDay）
    holidays: set = field(default_factory=set)  # 順延用假日集合（含週末），預設空

    # 逾期（expire_check="1"）才用到的自填起訖日（民國）
    sp_yy: str = ""
    sp_mm: str = ""
    sp_dd: str = ""
    ep_yy: str = ""
    ep_mm: str = ""
    ep_dd: str = ""


# ============================================================
# 主函式：產三段條碼
# ============================================================
def generate_355_barcode(t: Tax355Input):
    """回傳 (barcode1, barcode2, barcode3)。

    忠實移植 BarcodeFactory.get355Barcode(tax355, barcodeDay)。
    """
    check_type = int(t.expire_check)
    pw_amt = f"{int(t.pw_amt):010d}"

    # ---- barcode2 前段：縣市+稅籍+統編 ----
    barcode2 = t.agency_code + t.company_no
    # ---- barcode3 前段：稅目前 3 碼 ----
    barcode3 = t.tran_type[:3]

    # ---- 限繳日期 → barcode1 ----
    if check_type == 0:
        if t.b_yy == "108":
            # 108 年度特例：自 10/01 起算（原程式 hardcode）
            cal_date = _cal_date(t.b_yy, "10", "01", 0, t.holidays)
        else:
            # 正常：9/30 + 均日展延天數，再跳假日
            cal_date = _cal_date(t.b_yy, "9", "30", t.barcode_day, t.holidays)
    else:
        # 逾期：用使用者自填的截止日
        cal_date = _cal_date(t.ep_yy, t.ep_mm, t.ep_dd, 0, t.holidays)

    cal_date_6 = cal_date[-6:]  # StrUtils.right(calDate, 6)
    barcode1 = cal_date_6 + "6AE"  # 355 固定 6AE（無媒體申報變體）

    # ---- barcode2 後段：年月 + 固定碼 ----
    if check_type == 0:
        d_yy = f"{int(t.b_yy):03d}"
        d_mm = "9"                       # 正常期間月份固定 9（%1d of 9）
        barcode2 += d_yy[-2:] + d_mm + "011"
    else:
        d_yy = f"{int(t.sp_yy):03d}"
        d_mm = format(int(t.sp_mm), "X")  # 逾期月份取 16 進位大寫
        barcode2 += d_yy[-2:] + d_mm + "012"

    # ---- barcode3：稅目+固定碼4 + 檢查碼 + 金額 ----
    barcode3 += "4"  # 355 結尾固定 4
    barcode3_temp = barcode3 + pw_amt
    check_code = get_check_code(barcode1, barcode2, barcode3_temp)
    barcode3 = barcode3 + check_code + pw_amt

    return barcode1, barcode2, barcode3
