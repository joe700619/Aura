# Aura 上線前強化計畫（Pre-Launch Hardening Plan）

> **建立日期**：2026-05-07
> **目標**：在內部上線前，把已知高風險問題排除，建立可長期穩定運作、可擴充的系統。
> **進度追蹤**：每完成一個批次，在對應段落打勾並寫日期。

---

## 🎯 總體原則

1. **批次推進**：一次只做一個批次，做完驗收才進下一批
2. **本機 = 線上**：所有開發在 Docker 環境進行，避免「本機過、線上爆」
3. **可逆原則**：每個改動都走 PR + 可 rollback
4. **規範先行**：每個批次完成後，更新 `CLAUDE.md` 與 `.agent/skills/`，避免未來重蹈覆轍

---

## 📦 批次 0：環境統一化 + 規範建立（2-3 天）

> 把開發環境完全對齊 production，並建立未來開發的規範地基。

### 0A. Docker 環境完整化
- [ ] 擴充 `docker-compose.yml`，加入 services：
  - `redis`（cache + celery broker）
  - `web`（Django + gunicorn，**不用 runserver**）
  - `celery_worker`
  - `celery_beat`
  - `nginx`（反向代理 + 提供靜態檔）
- [ ] 建立 `Dockerfile`（web container 用）
- [ ] 建立 `.env.example` 範本
- [ ] 確認 `docker-compose up` 可一鍵起整套環境
- [ ] 寫 `docs/LOCAL_DEV.md` 說明本機如何開發

### 0B. 環境變數與安全設定
- [ ] 安裝 `python-decouple` 或 `django-environ`
- [ ] `SECRET_KEY` / DB 密碼 / EMAIL 設定全改成從 `.env` 讀取
- [ ] `DEBUG`、`ALLOWED_HOSTS` 環境化
- [ ] 建立 `config/settings_staging.py`、`config/settings_production.py`
- [ ] 加入 `SECURE_*` 系列設定（HSTS、SSL redirect、Secure Cookies）
- [ ] `python manage.py check --deploy` 無高危警告

### 0C. 建立規範文件
- [ ] `CLAUDE.md` 已建立（架構規則、寫程式規範）
- [ ] `.agent/skills/code_review_checklist/` 已建立
- [ ] `.agent/skills/add_new_model/` 已建立
- [ ] 既有 skill 補強：`standard_list_view`、`standard_form_view` 加入「必須繼承 Mixin」「必須加 select_related」等強制規則

### 0D. 安全網
- [ ] `requirements-dev.txt` 建立（debug-toolbar、pytest-django、factory-boy、django-extensions、django-silk）
- [ ] DB 完整備份並驗證可還原
- [ ] Git 開 `pre-launch-hardening` 分支

**驗收**：`docker-compose up` 起整套環境，能在 staging 設定下訪問首頁，CLAUDE.md + 兩個新 skill 已在 repo 中。

---

## 📦 批次 1：架構隱憂修正（2 天）

> 解決「未來新增 model 會彼此影響」的根本問題。

### 1A. 跨 module 依賴審查
- [ ] 全專案 grep `from modules\.` 的 import，列出跨 module 直接 import 的清單
- [ ] 把所有跨 module FK 改成 string reference（`'app.Model'`）
- [ ] 把跨 module 的 model 直接 import 改成走 `core/services/` 提供的 function
- [ ] 寫成 `docs/MODULE_DEPENDENCY.md`，畫出允許的依賴方向（單向，不可循環）

### 1B. Signal 清理
- [ ] grep 全專案的 `@receiver` / `signals.connect`
- [ ] 評估每個 signal：能改成顯式 service call 的就改
- [ ] 必要保留的 signal 加文件說明
- [ ] 在 CLAUDE.md 寫明「新功能禁用 signal」規則

### 1C. Mixin 使用稽查
- [ ] 列出所有 ListView / FormView / DetailView，標註是否使用 core mixin
- [ ] 沒用 mixin 的列表做改造計畫（不一定全改，但要列出例外清單）

**驗收**：`MODULE_DEPENDENCY.md` 完成，沒有 circular import，signal 數量減少。

---

## 📦 批次 2：資料層體檢與 Index 補強（3 天）

### 2A. 查詢盤點（半天）
- [ ] 安裝 django-debug-toolbar
- [ ] 登入跑過所有主要列表頁、報表頁，記錄到 `docs/QUERY_AUDIT.md`：
  - 頁面網址 / SQL 數 / 總時間 / 最慢的 query
- [ ] 用 django-extensions 的 `graph_models` 畫 ER 圖

### 2B. Index 補強（1 天）
- [ ] 為所有「使用者搜尋欄位」加 `db_index=True`：tax_id、name、phone、email
- [ ] 為所有「狀態欄位」加 `db_index=True`：status、stage、is_active
- [ ] 為「常一起 filter 的兩個欄位」加 `Meta.indexes` 複合 index
- [ ] 全部寫成 migration，逐 module apply
- [ ] **目標**：`Meta.indexes` 比例從 3.3% 提升到 50%+

### 2C. N+1 修復（1 天）
- [ ] [bill_views.py:46-80](modules/bookkeeping/views/bill_views.py#L46-L80) 加 prefetch
- [ ] [progress_views.py:72](modules/bookkeeping/views/progress_views.py#L72) 改 annotate
- [ ] [inquiry.py:59](modules/case_management/views/inquiry.py#L59) 加 status index 並用 annotate
- [ ] 從 QUERY_AUDIT 結果挑 SQL 數 > 20 的頁面逐一修復

### 2D. 強制查詢規範
- [ ] CLAUDE.md 加「凡 ListView 必檢查 select_related/prefetch_related」
- [ ] `standard_list_view` skill 加 N+1 範例與反例

**驗收**：每個主要列表頁 SQL 查詢數 < 15、頁面回應 < 500ms（空 DB）。

---

## 📦 批次 3：壓力測試 — 模擬上萬筆資料（2-3 天）

> 你最在意的「資料量大會不會爆」的實證驗證。

### 3A. 假資料生成器（1 天）
- [ ] 用 factory-boy 為核心 model 寫 factories
- [ ] 寫 `python manage.py seed_stress_data` 命令，可一鍵灌：
  - Customer × 5,000
  - Case × 20,000
  - Inquiry × 10,000
  - ClientBill × 50,000
  - BookkeepingPeriod × 12,000
  - 自動帶出 history 約 100,000+ 筆
- [ ] 在 staging DB 跑一次

### 3B. 實測（1 天）
- [ ] 量測每個列表頁的載入時間
- [ ] 量測搜尋功能反應時間（含跨 join 搜尋）
- [ ] 量測批次操作（月結、產報表）時間
- [ ] 用 django-silk 抓所有 > 1 秒的 query
- [ ] 結果寫入 `docs/STRESS_TEST_RESULT.md`

### 3C. 針對性優化（半天）
- [ ] 慢查詢加 index / 改 query / 加 `.only()` `.defer()`
- [ ] 重型報表改分頁或匯出 CSV
- [ ] 確認 history table 規模（評估清理策略，移到批次 4C 處理）

**驗收**：5 萬筆資料下，所有列表頁 < 1 秒，搜尋 < 500ms。

---

## 📦 批次 4：可擴充性補強（3 天）

### 4A. Cache 引入（1 天）
- [ ] Redis 已在批次 0 dockerize
- [ ] 設定 Django CACHES 走 Redis
- [ ] 為「不常變」的資料加 cache：服務項目、選單、系統設定、使用者權限（5 分鐘）
- [ ] 用 `cached_property` 包裝重型 model property

### 4B. Celery 引入（1.5 天）
- [ ] Celery worker / beat 已在批次 0 dockerize
- [ ] 把以下改為非同步：
  - 寄信（通知、報表寄送）
  - 產 PDF / Excel 報表
  - 月結批次
- [ ] 前端加「處理中」狀態提示

### 4C. HistoricalRecords 處理（半天）
> 採用「保留 history、僅 admin 顯示、定期清理」策略
- [ ] 確認所有 admin.py 用 `SimpleHistoryAdmin`
- [ ] 全專案 grep 前端 template / view 是否引用 `.history.all()`，若有則移除
- [ ] 寫 celery beat 排程：每月清理超過 1 年的 history（用 simple_history 的 `clean_old_history` command）
- [ ] 可選：對某些超高頻寫入的 model（如 log 類）評估是否關閉 HistoricalRecords

### 4D. 媒體與靜態檔（半天 → 上線前**必處理**）

> 🔴 **使用者重要備註（2026-05-09）**：
> 1. 客戶上傳資料種類多：**申報書、對話紀錄、公司章程**等供客戶下載
> 2. 時間久後檔案會大量累積，**需要集中管理**（不能散在各 server 本地 volume）
> 3. **冷熱分層**：2 年前的資料較少存取，慢一點沒關係 → 適合走分層儲存
>
> 設計建議：
> - 走 **S3-compatible**（雲端 AWS S3 / Cloudflare R2 / 自建 MinIO 都可）
> - 用 `django-storages` + `boto3` 接 backend
> - 熱資料（< 2 年）放 **Standard tier**（即時存取）
> - 冷資料（> 2 年）走 **Glacier / Infrequent Access tier**（成本低 80%）
> - 用 lifecycle policy 自動轉移（不用寫 cron）
> - 媒體檔 URL 用 **presigned URL** 簽署（避免直接公開）
> - 備份策略：S3 啟用 versioning + cross-region replication

**待做事項：**
- [ ] 評估 S3 vs MinIO（依預算與資料量）
- [ ] 實作 `MediaStorage` 子類別、設定 `DEFAULT_FILE_STORAGE`
- [ ] 寫資料遷移指令把現有 `media/` 上傳到 bucket
- [ ] 設定 lifecycle rule：upload date > 2 年 → Infrequent Access
- [ ] 設定 versioning + 7 天 soft-delete（防誤刪）
- [ ] 文件下載走 presigned URL，TTL 5-10 分鐘
- [ ] 靜態檔走 whitenoise + nginx（上線前部署設定）

**驗收**：寄信不卡 request、月結背景跑、Redis cache 命中率 > 50%、history 有清理排程。

---

## 📦 批次 5：測試與監控（持續，至少 4 天起步）

### 5A. 核心測試（3 天）
不追求覆蓋率，先針對「金流」「法務」相關功能：
- [ ] bookkeeping 帳單計算
- [ ] internal_accounting 傳票借貸平衡
- [ ] case_management 狀態轉換
- [ ] core/auth 權限檢查
- [ ] 目標：50-80 個 test case，pytest-django 跑通

### 5B. 監控（1 天）
- [ ] 接 Sentry 抓 production error
- [ ] 接 UptimeRobot uptime 監控
- [ ] PostgreSQL 開 `pg_stat_statements`
- [ ] 寫 `docs/RUNBOOK.md`：常見問題排查 SOP

---

## 📦 批次 6：上線演練（1 天）

- [ ] 在 staging 完整跑「上線流程」：備份 → migrate → collectstatic → 重啟
- [ ] 寫 `docs/DEPLOY.md` SOP
- [ ] 模擬「DB 掛了」「Redis 掛了」「Celery 掛了」三種情境，驗證 degrade
- [ ] 演練還原備份

---

## 🗓️ 總時程

| 批次 | 工時 | 累計 |
|---|---|---|
| 0. 環境統一化 + 規範 | 2-3 天 | 3 天 |
| 1. 架構隱憂修正 | 2 天 | 5 天 |
| 2. 資料層 + Index | 3 天 | 8 天 |
| 3. 壓力測試 | 2-3 天 | 11 天 |
| 4. 可擴充性 | 3 天 | 14 天 |
| 5. 測試監控 | 4 天 | 18 天 |
| 6. 上線演練 | 1 天 | 19 天 |

**總計：約 3-4 週純工作日**（一個人開發 + 卡關緩衝，建議抓 1.5-2 個月）

---

## 📌 進度紀錄區

> 每個批次完成後在這裡記錄：日期、實際工時、發現的新問題、需要追加的 TODO
