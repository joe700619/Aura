# Code Review Checklist

> 任何 PR 提交前、合併前必須逐項檢查。

## 用途
避免常見的後端效能與架構問題，特別針對 Aura 專案踩過的坑。

## 檢查清單

### A. 查詢效能（最高優先）
- [ ] 新增 / 修改的 ListView 用 django-debug-toolbar 確認 SQL 數 < 15
- [ ] template 中 `{% for x in list %}` 內若用到 `x.related.xxx`，view 必須有 `select_related` 或 `prefetch_related`
- [ ] 沒有在迴圈內呼叫 `.filter()` `.count()` `.first()`
- [ ] 報表 / 重型查詢用 `.only()` 或 `.defer()` 限制欄位

### B. Index
- [ ] 新增的 FK 預設加 `db_index=True`（除非確定不會 filter）
- [ ] 新增「使用者會搜尋的欄位」加 `db_index=True`
- [ ] 兩個欄位常一起 filter 時，加 `Meta.indexes` 複合 index

### C. 跨 module 依賴
- [ ] 沒有出現 `from modules.xxx.models import YYY`（跨 module）
- [ ] 跨 module FK 用 string reference：`'app.Model'`
- [ ] 跨 module 取資料走 `core/services/`

### D. 架構規範
- [ ] 新 signal 集中在 `<module>/signals.py`，未散落在 model 檔案
- [ ] signal 用 `get_or_create`（idempotent），失敗 raise 不 try/except 吞錯
- [ ] signal 上方有 docstring 說明觸發時機與副作用
- [ ] ListView 有繼承 `core.mixins` 的 SearchMixin / FilterMixin
- [ ] FormView 有遵循 `standard_form_view` skill

### E. 安全
- [ ] 沒有 hardcode SECRET_KEY / 密碼 / API key
- [ ] 新設定加到 `.env.example`
- [ ] 使用者輸入有經過 form / serializer 驗證

### F. 非同步
- [ ] 寄信 / 產 PDF / 批次操作走 Celery，不阻塞 request

### G. Migration
- [ ] model 改動有產 migration 並 commit
- [ ] migration dependency 正確

### H. 前端一致性
- [ ] 表單樣式走 `standard_form_view`
- [ ] 列表樣式走 `standard_list_view`
- [ ] 沒有自創 UI 元件 / 自寫 alert

### I. HistoricalRecords
- [ ] 前端 template / view 沒有顯示 `.history.all()`（只在 admin 顯示）

## 發現問題時
立刻修正後再次跑 checklist，不要累積技術債。
