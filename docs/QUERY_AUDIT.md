# 查詢效能盤點 (Query Audit)

> 用途：批次 2 上線前的列表頁/報表頁 SQL 查詢數量盤點。
> 目標：每個列表頁 SQL 數 < 15、頁面 < 500ms（空 DB）。
> 工具：django-debug-toolbar（DEBUG=True 時自動載入）。
> 啟動日期：2026-05-08

---

## 如何使用 debug-toolbar

1. 確認 `.env` 中 `DEBUG=True`
2. 用瀏覽器訪問 http://localhost:8000 並登入
3. 右上角會出現深色側邊欄
4. 點 **SQL** 看：
   - **總查詢數**（重點）
   - **重複查詢**（重點，N+1 警告）
   - **總時間**
5. 點任一 SQL 看「called from / template」追蹤觸發位置

---

## 衡量標準

| SQL 數 | 評估 |
|---|---|
| ≤ 15 | ✅ 健康 |
| 16-30 | 🟡 可接受，但有改善空間 |
| 31-50 | 🟠 應排程修復（典型 N+1） |
| > 50 | 🔴 嚴重，列入優先修復 |

---

## 盤點結果

### Dashboard (`/dashboard/`)
| 指標 | 數值 | 備註 |
|---|---|---|
| SQL 數 | _待測_ | |
| 總時間 | _待測_ ms | |
| 重複查詢 | _待測_ | |
| 結論 | ⏳ | |

### 基本資料 - 客戶列表 (`/basic-data/customers/`)
| 指標 | 數值 | 備註 |
|---|---|---|
| SQL 數 | _待測_ | |

### 基本資料 - 聯絡人 (`/basic-data/contacts/`)
| 指標 | 數值 | 備註 |
|---|---|---|

### 基本資料 - 服務項目 (`/basic-data/service-items/`)
| 指標 | 數值 | 備註 |
|---|---|---|

### 行政管理 - 收文系統 (`/administrative/document-receipts/`)

### 行政管理 - 發文系統 (`/administrative/document-dispatches/`)

### 行政管理 - 國稅局查帳通知 (`/administrative/irs-audit-notices/`)

### 行政管理 - 代墊款申請 (`/administrative/advance-payments/`)

### 記帳 - 客戶基本資料 (`/bookkeeping/clients/`)

### 記帳 - 統購發票 (`/bookkeeping/group-invoice-report/`)

### 記帳 - 7-11便利袋 (`/bookkeeping/convenience-bags/`)

### 記帳 - 營業稅申報 (`/bookkeeping/business-tax/`)

### 記帳 - 營所稅申報 (`/bookkeeping/income-tax/`)

### 記帳 - 商工登記 (`/bookkeeping/business-registrations/`)

### 記帳 - 各業別稅率標準 (`/bookkeeping/industry-tax-rates/`)

### 記帳 - 記帳進度表 (`/bookkeeping/progress/`)

### 記帳 - 客戶帳單 (`/bookkeeping/bills/`)

### 登記 - 進度表 (`/registration/progress/`)

### 登記 - 客戶評估表 (`/registration/client-assessments/`)

### 登記 - 案件評估表 (`/registration/case-assessments/`)

### 登記 - 股東名簿 (`/registration/shareholder-registers/`)

### 案件管理 (`/cases/internal/`)

### 內部會計 - 傳票作業 (`/accounting/vouchers/`)

### 內部會計 - 應收帳款 (`/accounting/receivables/`)

### 內部會計 - 收款管理 (`/accounting/collections/`)

### 內部會計 - 損益表 (`/accounting/reports/income-statement/`)

### 內部會計 - 資產負債表 (`/accounting/reports/balance-sheet/`)

### 內部會計 - 總分類帳 (`/accounting/reports/general-ledger/`)

### 內部會計 - 日記帳 (`/accounting/reports/journal/`)

### 內部會計 - 科目管理 (`/accounting/accounts/`)

### 內部會計 - 財產目錄 (`/accounting/fixed-assets/`)

### 人力資源 - 員工資料 (`/hr/employees/`)

### 人力資源 - 出勤紀錄 (`/hr/attendance/`)

### 人力資源 - 請假管理 (`/hr/leave-requests/`)

### 人力資源 - 薪資單 (`/hr/payroll/`)

### 知識庫 (`/knowledge/`)

---

## 優先處理清單（待 audit 完成後填入）

| # | 頁面 | SQL 數 | 主因 | 修復方案 |
|---|---|---|---|---|
| 1 | _待填_ | | | |

---

## Index 補強候選清單（從 audit 推導）

| 欄位 | 表 | 加 index 理由 | 狀態 |
|---|---|---|---|
| _待填_ | | | |
