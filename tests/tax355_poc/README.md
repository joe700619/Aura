# Tax355 暫繳繳款書 — Proof of Concept

> ⚠️ 這是 **PoC / 概念驗證**，只放在 `tests/` 底下。
> 未接任何正式流程、不連資料庫、不註冊選單、不加 migration。
> 所有輸入皆為**模擬資料**（取自真實樣本 `Report_355.pdf` 可見資訊）。

## 這是什麼

驗證「能不能用跟現有扣繳繳款書（tax152）一樣的作法，產出 355 營利事業所得稅
暫繳稅額繳款書」。核心邏輯從國稅局 `pbc-1.0.jar` 反編譯移植：

| 來源（國稅局程式） | 移植到 |
|---|---|
| `BarcodeFactory.get355Barcode()` | `barcode355.py` |
| `BarcodeFactory.getCheckCode()`（與 152 共用） | `barcode355.py` |
| `templates/355.pdf`（空白範本） | `assets/355.pdf` |
| `templates/jasperreports/ETW144W3.jrxml`（版面座標） | `generate_355.py` |
| `PdfAction6`（355 → 欄位對應） | `generate_355.py` |

## 檔案

- `barcode355.py` — 三段條碼產生器（**已對真實樣本驗證**）
- `generate_355.py` — 套印 PDF（reportlab overlay + pypdf，疊到 355.pdf）
- `verify_355.py` — 自我驗證：模擬資料跑出的條碼 == 樣本條碼
- `assets/355.pdf` — 國稅局空白範本（複製，未修改）

## 怎麼跑（手動）

```bash
# 只驗條碼
python -m tests.tax355_poc.verify_355

# 連同輸出套印 PDF 到 tests/tax355_poc/out/ 供肉眼檢查
python -m tests.tax355_poc.verify_355 --pdf
```

## 驗證基準

真實樣本（115 年度、應繳 30,000）三段條碼：

```
barcode1 = 1509306AE              限繳日 115/09/30 + 6AE
barcode2 = E100085120097159011    高雄稅籍 + 統編 + 年月 + 011
barcode3 = 3554O0000030000        稅目355 + 4 + 檢查碼O + 金額
```

檢查碼 `O` 已用移植後的演算法重算確認一致。

## 已知缺口（上線前要補）

1. **均日展延假日表**：原程式 `checkHoliday` 會查 `Holiday_WRR` 表（含週末＋
   國定假日）把限繳日往後順延。該表未隨 jar 附帶。本 PoC 用可注入的
   `holidays` 集合代替，預設空集合 → 正好重現「115/09/30 未順延」的樣本。
   遇到「9/30 落在假日要展延」的年度時，barcode1 日期會變，需補該轄區假日表再驗。
2. **文字欄位位置**：355.pdf 已印好所有靜態標籤，overlay 只填值。條碼與底部
   留存聯明細值欄座標精確；三聯的公司資料/期間日期為**初版位置**，需渲染後
   做一次視覺微調（與當年 152 相同流程）。
3. **資料來源對接**：正式接線時，`agency_code`（稅籍轄區）、負責人姓名/統編等
   需從客戶主檔取得；現有 `ProvisionalTax` model 只有暫繳金額/截止日。
4. **逾期（expire_check="1"）路徑**：已依反編譯實作，但尚無逾期樣本可對拍。
