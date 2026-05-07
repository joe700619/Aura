# CLAUDE.md — Aura 專案開發指引

> 這份文件提供給 Claude（與所有協作者）作為開發本專案時的強制規範。
> 修改本檔需要審慎評估，因為會影響後續所有開發行為。

---

## 1. 專案脈絡

- **性質**：內部使用的會計事務所管理系統（Django 5.1.5 + PostgreSQL + Wagtail）
- **階段**：上線前強化中（見 [PRE_LAUNCH_PLAN.md](PRE_LAUNCH_PLAN.md)）
- **使用者背景**：開發者主要前端背景，後端經驗較少 → 解釋時優先給「為什麼」與類比
- **規模目標**：穩定支撐 5,000 客戶 / 50,000 帳單 / 數年資料量

---

## 2. 必讀文件

接到任何任務前，先確認是否需要讀以下文件：

| 任務類型 | 必讀 |
|---|---|
| 新增 model | `.agent/skills/add_new_model/` |
| 新增 list view | `.agent/skills/standard_list_view/` |
| 新增 form view | `.agent/skills/standard_form_view/` |
| debug list/form view | `.agent/skills/debug_list_and_form_view/`（**強制**，不可手動推斷） |
| 新增模組 | `.agent/skills/debug_new_module/` |
| 任何 PR 前 | `.agent/skills/code_review_checklist/` |
| 跨 module 依賴 | `docs/MODULE_DEPENDENCY.md` |

---

## 3. 架構鐵則（違反需明確徵詢使用者）

### 3.1 跨 module 依賴
- **跨 module FK 一律用 string reference**：`ForeignKey('basic_data.Customer')`，禁止 `from modules.basic_data.models import Customer`
- **跨 module 取資料走 service**：A module 要 B module 的資料，透過 `core/services/` 提供的 function，禁止直接 import B 的 model 操作
- **依賴方向單向**：業務 module（bookkeeping、case_management 等）可依賴 `core` / `basic_data` / `shared`，但不可互相依賴

### 3.2 Signal 禁用
- **新功能禁用 `@receiver` / `post_save` signal**
- 必要的副作用（例如建立關聯資料）改用顯式 service function call
- 既有 signal 在批次 1 會逐步清理

### 3.3 Mixin 強制使用
- 新 ListView 必須繼承 `core.mixins.SearchMixin` + `FilterMixin` + `ListActionMixin`
- 新 FormView 必須繼承 `core.mixins` 對應 mixin
- 不繼承的話搜尋 UI 與行為會不一致 → 已踩過坑

### 3.4 HistoricalRecords 使用原則
- 保留 `BaseModel` 的 `HistoricalRecords()`（已內建）
- **前端 view / template 禁止顯示 `.history.all()`**，歷史紀錄只在 admin 顯示
- admin 用 `simple_history.admin.SimpleHistoryAdmin`

---

## 4. 後端寫程式規範

### 4.1 查詢效能（最重要，曾踩過坑）
- **任何 ListView 都要檢查 N+1**：在 template 中用到 `obj.related.xxx` 的，view 必須有 `select_related` / `prefetch_related`
- **任何 FK 欄位**預設加 `db_index=True`（除非確定不會 filter）
- **任何使用者會搜尋的欄位**（name、tax_id、phone、email、status）必須加 `db_index`
- **常一起 filter 的兩個欄位**用 `Meta.indexes` 加複合 index
- 寫完 view 用 django-debug-toolbar 確認 SQL 數 < 15

### 4.2 Migration
- 每次改 model 都要產 migration 並 commit
- 不在已 apply 的 migration 上修改，要修就新增一個
- 跨 module 的 migration dependency 寫清楚

### 4.3 環境變數
- **禁止 hardcode**：SECRET_KEY、DB 密碼、API key、email 認證等一律從 `.env` 讀
- 新增設定時同步更新 `.env.example`

### 4.4 非同步任務
- 使用者不需要等結果的事（寄信、產 PDF、批次計算）一律走 Celery
- 禁止在 request thread 中做 > 1 秒的工作

---

## 5. 前端 / Template 規範

### 5.1 樣式一致性
- 表單一律走 `standard_form_view` skill 的範本
- 列表一律走 `standard_list_view` skill 的範本
- 不要為單一頁面手刻 CSS / 自創 UI 元件

### 5.2 訊息 / 確認框
- 用 `core/templatetags/` 內既有的元件，不要自己 alert()

---

## 6. 與使用者協作的方式

### 6.1 解釋風格
- 使用者前端背景強、後端經驗少 → 解釋後端概念時用前端類比
- 重要決策提供 2-3 個方案 + 各自 trade-off，由使用者決定
- 不要直接「先做了再說」

### 6.2 改動規模
- 大規模改動先講計畫、由使用者同意
- 修一個 bug 不要順手重構周邊程式
- 不要新增「以防萬一」的錯誤處理或抽象

### 6.3 報告產出
- 改完 code 後簡短說明：改了什麼、為什麼、要注意什麼
- 不要重複貼整段 diff，使用者自己會看

---

## 7. Debug 流程

任何「列表頁壞了」「表單壞了」的情境，**必須先執行對應 skill**：
- list / form view 問題 → `.agent/skills/debug_list_and_form_view/`
- 新模組問題 → `.agent/skills/debug_new_module/`

不可以直接憑經驗猜。已經因此踩過坑。

---

## 8. 開發環境

- 本機開發走 Docker（`docker-compose up`），環境與線上一致
- 不在本機跑 `python manage.py runserver`
- staging 設定：`config/settings_staging.py`
- production 設定：`config/settings_production.py`

---

## 9. 文件維護

完成一個批次後，更新：
1. `PRE_LAUNCH_PLAN.md` 的進度勾選與紀錄
2. 對應的 `.agent/skills/` 內容（如果學到新規則）
3. 本檔的「架構鐵則」（如果新增規範）
