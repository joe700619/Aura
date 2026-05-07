# 新增 Model 標準流程

> 用途：避免新增 model 造成跨 module 影響、缺 index、忘記 history、未來查詢卡頓。

## 步驟

### 1. 確認位置
問自己：
- 這個 model 屬於哪個業務領域？放對應 module 的 `models.py` 或 `models/` 子目錄
- 會被多個 module 用到嗎？→ 放 `core/` 或 `basic_data/`
- 是純粹的 lookup 表（國家、幣別等）→ `basic_data/` 或 `system_config/`

### 2. 繼承 BaseModel
```python
from core.models import BaseModel

class MyModel(BaseModel):  # 自動帶 created_at / updated_at / HistoricalRecords
    ...
```
**例外**：高頻寫入的 log 類 model 可考慮不繼承（避免 history 暴增），但要明確說明理由。

### 3. FK 與依賴規則
- **同 module FK**：可以 `from .other import OtherModel` 然後 `ForeignKey(OtherModel)`
- **跨 module FK**：**一律用 string reference**
  ```python
  customer = models.ForeignKey('basic_data.Customer', on_delete=models.PROTECT)
  ```
- **依賴方向**：業務 module → core / basic_data / shared（不可反向、不可平行）

### 4. Index 規範（強制）
```python
class MyModel(BaseModel):
    name = models.CharField(max_length=100, db_index=True)        # 會搜尋 → 加
    status = models.CharField(max_length=20, db_index=True)        # 狀態欄位 → 加
    customer = models.ForeignKey('basic_data.Customer', ...)       # FK 預設加 db_index
    period = models.DateField()                                    # 沒 filter 不必加

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'period']),  # 常一起 filter 加複合
            models.Index(fields=['status', '-created_at']),
        ]
        ordering = ['-created_at']
```

### 5. on_delete 選擇
- 業務上不可刪的關聯：`PROTECT`（如客戶之於帳單）
- 主檔刪則子檔跟著刪：`CASCADE`（如訂單之於訂單明細）
- 主檔刪則設 NULL：`SET_NULL`（要 `null=True`）
- **預設用 PROTECT**，避免誤刪連動

### 6. on_delete 與 Migration
- 跑 `python manage.py makemigrations`
- 確認 migration 檔案 commit
- 跨 module FK 的 migration `dependencies` 要列對

### 7. Admin 註冊
```python
from simple_history.admin import SimpleHistoryAdmin

@admin.register(MyModel)
class MyModelAdmin(SimpleHistoryAdmin):  # 用這個才會顯示 history
    list_display = (...)
    search_fields = (...)
    list_filter = (...)
```

### 8. 自我檢查
- [ ] 跨 module FK 有用 string reference？
- [ ] 會搜尋 / 會 filter 的欄位都加了 db_index？
- [ ] 常一起 filter 的欄位有複合 index？
- [ ] 繼承了 BaseModel？
- [ ] on_delete 選對了？
- [ ] migration 產出且能正常 apply？
- [ ] admin 用 SimpleHistoryAdmin？
- [ ] 沒有掛 signal？

### 9. 完成後
- 更新 `docs/MODULE_DEPENDENCY.md`（如果新增了跨 module 依賴）
- 跑 `python manage.py check` 確認無警告

## 常見錯誤
1. **直接 import 跨 module model** → 未來會 circular import
2. **忘記加 index** → 上線後資料一多就卡
3. **on_delete=CASCADE 用太爽** → 一刪客戶連帶刪幾千筆帳單
4. **掛 signal 做副作用** → 未來除錯災難
