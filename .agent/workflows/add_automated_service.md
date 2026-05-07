---
description: 如何新增自動化關連服務表單 (依報價單觸發)
---

本文件說明如何根據您在「報價單」中選擇的服務項目，自動建立相關的子服務表單。

### 步驟 1: 在 ServiceItem 增加標籤 (如果尚未建立)
編輯 `modules/basic_data/models/service_item.py`，新增一個 BooleanField 作為該服務是否需自動化的標籤。
```python
is_new_service_check = models.BooleanField(_('是否需執行新服務'), default=False)
```
並執行 `makemigrations` 與 `migrate`。

### 步驟 2: 更新搜尋 partial 樣板
編輯 `modules/basic_data/templates/basic_data/partials/service_item_search_results.html`，在 `selectItem` 函數中把新標籤傳遞給前端。
```html
is_new_service_check: {{ item.is_new_service_check|yesno:'true,false' }}
```

### 步驟 3: 更新報價單元件
編輯 `templates/components/quotation_table.html`，更新 `addRow` 與 `updateRow` 函數，確保新標籤會儲存到 JSON 中。

### 步驟 4: 撰寫自動化邏輯 (Signals)
編輯 `modules/registration/signals.py`，在 `auto_create_related_services` 中檢查 `quotation_data`。
```python
should_trigger = any(
    isinstance(item, dict) and item.get('is_new_service_check') is True 
    for item in instance.quotation_data
)
if should_trigger:
    # 建立對應表單邏輯...
```

### 步驟 5: 更新 View 與 Checklist 顯示
要在「登記進度表」看到狀態，需編輯 `modules/registration/views/progress.py` 的 `ProgressUpdateView` 並在 `checklist` 中加入新项。
最後在 `progress/form.html` 的「工作清單」表格中增加對應的顯示列。

### 驗證
1. 在服務項目管理中，將某項目勾選「新服務」。
2. 在登記進度表的報價單中選取該項目並儲存。
3. 確認子表單已自動建立，且 Checklist 狀態正確。
