"""
Tax355 PoC 自我驗證
====================
用「真實樣本 Report_355.pdf」上看得到的資料當模擬輸入，
驗證移植出來的三段條碼 == 樣本上的條碼。

執行（手動，不自動跑）：
    python -m tests.tax355_poc.verify_355

可選：加上 --pdf 會把套印 PDF 寫到 tests/tax355_poc/out/ 供肉眼檢查。
全部輸入皆為模擬資料，不連資料庫、不接正式流程。
"""

import os
import sys

from tests.tax355_poc.barcode355 import Tax355Input, generate_355_barcode

# ── 模擬輸入（取自樣本 Report_355.pdf 可見資訊；負責人統編為樣本上的遮罩值）──
SAMPLE = {
    "unit_name":    "財政部高雄國稅局",
    "company_name": "益兆原環球科技有限公司",
    "company_no":   "85120097",
    "people_name":  "宗佳瑜",
    "people_no":    "B22366****",
    "company_addr": "高雄市三民區寶安里九如一路502號6樓之1",
    "phone":        "042375-8628",
    "pay_year":     "115",
    "tran_type":    "355",
    "pw_amt":       30000,
    "agency_code":  "E1000",   # = cityId+deptId（高雄）；樣本 barcode2 前綴
    "start_mm": "9", "start_dd": "1",
    "end_mm": "9", "end_dd": "30",
    "holidays": set(),          # 115/09/30 當年未順延
}

# ── 樣本上實際印出的三段條碼（基準答案）──
EXPECTED = {
    "barcode1": "1509306AE",
    "barcode2": "E100085120097159011",
    "barcode3": "3554O0000030000",
}


def run_barcode_check() -> bool:
    tax = Tax355Input(
        agency_code=SAMPLE["agency_code"],
        company_no=SAMPLE["company_no"],
        pw_amt=SAMPLE["pw_amt"],
        b_yy=SAMPLE["pay_year"],
        tran_type=SAMPLE["tran_type"],
        holidays=SAMPLE["holidays"],
    )
    b1, b2, b3 = generate_355_barcode(tax)
    got = {"barcode1": b1, "barcode2": b2, "barcode3": b3}

    print("=== 條碼比對（移植結果 vs 真實樣本）===")
    ok = True
    for key in ("barcode1", "barcode2", "barcode3"):
        match = got[key] == EXPECTED[key]
        ok = ok and match
        mark = "✓" if match else "✗ 不符"
        print(f"  {key}: {got[key]:<22} {mark}")
        if not match:
            print(f"          樣本應為: {EXPECTED[key]}")
    print("結果：", "全部通過 ✓" if ok else "有不符 ✗")
    return ok


def write_pdf():
    from tests.tax355_poc.generate_355 import generate_355_pdf
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "tax355_poc.pdf")
    with open(path, "wb") as f:
        f.write(generate_355_pdf(SAMPLE))
    print(f"已輸出套印 PDF：{path}")


if __name__ == "__main__":
    ok = run_barcode_check()
    if "--pdf" in sys.argv:
        write_pdf()
    sys.exit(0 if ok else 1)
