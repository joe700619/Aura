---
description: 如何新增記帳模組的「專家系統診斷規則」
---

# 專家系統規則擴充指引

本文件說明當資深會計提出新的查帳 Know-how (例如「交際費佔營收比重過高」)，開發者該如何將其轉換為系統的自動檢查規則。Aura 系統已經具備了完善的動態載入引擎，因此新增規則**完全不需要修改核心引擎程式碼或資料庫**，只需撰寫單一 Python 檔案即可。

## 新增規則的標準流程 (SOP)

### 步驟 1：建立規則類別檔案
請在 `modules/bookkeeping/rules/` 目錄下建立一個新的 `.py` 檔案（或將同性質的規則寫在現有檔案中，例如稅務相關寫在 `tax_rules.py`，營收相關寫在 `revenue_rules.py`）。

### 步驟 2：繼承 BaseRule 並設定屬性
建立一個 Class 並且繼承 `BaseRule`。您必須設定以下四個類別屬性：

```python
from bookkeeping.rules.base import BaseRule
from bookkeeping.models import TaxFilingPeriod # 依需要載入

class HighEntertainmentExpenseRule(BaseRule):
    # 1. 唯一識別碼 (全大寫英數底線，請確保與其他規則不同)
    code = "EXP_ENTERTAINMENT_RATIO_HIGH"
    
    # 2. 顯示在畫面上的前端名稱
    name = "交際費佔營收比重過高"
    
    # 3. 規則詳細說明 (讓系統使用者看懂)
    description = "檢查申報的交際費用是否超過營業收入的一定比例"
    
    # 4. 系統預設閾值 (浮點數，客戶可於前端覆寫此值)
    default_threshold = 0.10  # 預設 10%
```

### 步驟 3：實作 evaluate 方法 (核心商業邏輯)
這是最重要的步驟，您必須實作 `@classmethod` 的 `evaluate` 方法。這個方法會在使用者點擊「執行專家診斷」時，由 `ExpertEngine` 傳入當前的客戶與期別物件。

```python
    @classmethod
    def evaluate(cls, client, period, current_threshold):
        """
        :param client: BookkeepingClient 單一客戶實例
        :param period: BookkeepingPeriod 觸發檢查的期別實例
        :param current_threshold: float 已經過系統判斷後的生效閾值 (可能是預設值或客戶專屬覆寫值)
        :return: (bool 是否觸發警報, 實際觸發的數值/比率等供留存紀錄)
        """
        
        # --- 撰寫您的查詢邏輯 ---
        # 範例：從關聯的稅務申報紀錄或會計項目中撈出銷售額與交際費
        sales = period.sales_amount or 0
        
        # (這裡只是示範，實際情況請引用正確的 model 與欄位)
        entertainment_expense = ... 
        
        # 防呆機制 (分母不可為零等)
        if sales == 0:
            return False, 0.0
            
        ratio = entertainment_expense / sales
        
        # --- 判斷是否超過閾值 ---
        if ratio > current_threshold:
            # 第一個回傳值 True 代表「異常、要發出警報」
            # 第二個回傳值是給前端畫面與資料庫留存的實際數值 (可將小數轉為百分比)
            return True, round(ratio * 100, 2)
            
        # 若無異常，回傳 False 
        return False, round(ratio * 100, 2)
```

### 步驟 4：開發與測試注意事項

1. **動態載入**：只要該類別繼承了 `BaseRule` 且有 `code` 屬性，`rules/__init__.py` 的掃描機制就會**自動將此規則註冊到全系統**。
2. **防錯處理**：請務必在 `evaluate` 方法內做好**防錯處理**（如 `None` 值判斷、除以零防護、過往資料不存在等）。若該客戶缺少所需檢測的資料，請一律回傳 `False, 0.0`，不要讓系統丟出 Exception。
3. **相對路徑引用**：在規則檔案內引用其他模組 (如 Models) 時，如果是在同一個 `modules.bookkeeping` 應用下，請**盡量使用上層相對路徑** (例如 `from ..models import TaxFilingPeriod`)，避免載入順序造成的 `ModuleNotFoundError` 循環依賴問題。

### 完成！
一旦程式碼存檔啟動後，這個新規則將會自動出現於所有客戶在「記帳進度表 - 客戶年度明細表」內的**「專家系統與稽核參數」**設定面板中。系統生效後，當執行專家診斷時也會一併涵蓋此項檢查。
