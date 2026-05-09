# Aura RUNBOOK — 維運手冊

> 上線後常見問題的排查 SOP。
> 規則：先看狀態 → 看 log → 重啟服務 → 再深入排查。

---

## 目錄

1. [日常檢查指令](#日常檢查指令)
2. [服務無法啟動](#服務無法啟動)
3. [使用者反映「網站很慢」](#使用者反映網站很慢)
4. [使用者反映「沒收到通知信」](#使用者反映沒收到通知信)
5. [使用者反映「列表頁顯示不對 / 缺項目」](#使用者反映列表頁顯示不對--缺項目)
6. [DB 連線爆炸](#db-連線爆炸)
7. [Celery worker 沒在跑](#celery-worker-沒在跑)
8. [Redis 掛了](#redis-掛了)
9. [緊急回滾](#緊急回滾)
10. [備份 / 還原](#備份--還原)
11. [監控接點](#監控接點)

---

## 日常檢查指令

```powershell
# 看所有 container 狀態
docker-compose ps

# 即時看 web 日誌
docker-compose logs -f web

# 進 web container shell
docker-compose exec web bash

# 進 Django shell
docker-compose exec web python manage.py shell

# 進 PostgreSQL
docker-compose exec db psql -U postgres -d aura_db
```

健康指標：6 個 service 全部 `Up`，db 與 redis `(healthy)`。

---

## 服務無法啟動

### 症狀
`docker-compose up -d` 後，某個 container 一直 restart。

### 排查順序
```powershell
docker-compose ps                       # 找出哪個服務 restart
docker-compose logs <service> --tail=80 # 看具體錯誤
```

### 常見原因
| log 訊息 | 對策 |
|---|---|
| `connection refused 5432` | DB 還沒 ready，等 30 秒；若仍失敗，檢查 `.env` 的 DB 設定 |
| `ModuleNotFoundError: No module named 'X'` | requirements.txt 漏裝，重 build：`docker-compose build --no-cache web` |
| `type "vector" does not exist` | pgvector extension 未啟用：`docker-compose exec db psql -U postgres -d aura_db -c "CREATE EXTENSION IF NOT EXISTS vector;"` |
| `port is already allocated` | 5432 / 6379 / 8000 / 80 被別的程序佔用，找出並關閉 |
| migration 失敗 | 看完整 traceback 找出哪支 migration，本機重現 |

---

## 使用者反映「網站很慢」

### 第一步：定位是哪一層慢

```powershell
# 量機器資源
docker stats --no-stream

# 看活動連線
docker-compose exec db psql -U postgres -d aura_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### 第二步：判斷症狀
| 症狀 | 可能原因 | 對策 |
|---|---|---|
| 全部頁面慢 | DB 連線爆 / web container 記憶體吃光 | 看下方「DB 連線爆炸」 |
| 特定頁面慢 | N+1 查詢 / 缺 index | 開 DEBUG=True 用 debug-toolbar 抓 SQL |
| 月結 / 報表卡 | 同步在 request thread 跑 | 確認 celery worker 有跑、task 有派出 |
| 突然全慢 | Redis 掛了 → cache miss | 看下方「Redis 掛了」 |

### 第三步：DB 慢查詢
```sql
-- 看當下最慢的查詢
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
ORDER BY duration DESC;

-- 殺掉卡住的查詢
SELECT pg_cancel_backend(pid);
```

如果有啟用 `pg_stat_statements`：
```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

---

## 使用者反映「沒收到通知信」

### 排查順序
1. **看 EmailLog**：到 admin → Notifications → Email Logs，找該使用者的紀錄
   - `status='sent'` → 已寄出，叫使用者看垃圾信
   - `status='pending'` → 還沒寄，往下看
   - `status='failed'` → 看 error_message 欄位

2. **看 celery worker 是否運作**：
   ```powershell
   docker-compose logs celery_worker --tail=30
   ```
   找有沒有 `core.send_email_log_async[xxx] succeeded` 字樣。

3. **沒看到 task 執行** → celery worker 掛了或 broker 連不上：
   ```powershell
   docker-compose restart celery_worker
   ```

4. **task 有跑但寄不出去** → SMTP 設定錯誤：
   - 進 admin → System Config → SystemParameter
   - 確認 `EMAIL_HOST`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD` 等參數
   - 用 `python manage.py shell` 手動測：
     ```python
     from django.core.mail import send_mail
     send_mail('test', 'body', None, ['你@gmail.com'], fail_silently=False)
     ```

---

## 使用者反映「列表頁顯示不對 / 缺項目」

### 可能原因
1. **Cache 還沒失效**（5 分鐘 TTL）
   - sidebar 缺選單：可能剛在 admin 加了 MenuItem，等 5 分鐘 / 重啟 web
   - 強制清：`docker-compose exec redis redis-cli FLUSHDB`
2. **Filter 查詢條件沒 reset**：使用者上次的 GET 參數還在 URL，叫他重新從 sidebar 進入
3. **權限問題**：使用者所屬 Group 設定不對 → 進 admin → Auth → Groups 看設定
4. **資料被軟刪除**：
   ```sql
   SELECT count(*) FROM <table> WHERE is_deleted = TRUE;
   ```

---

## DB 連線爆炸

### 症狀
- 大量請求 502 / 503
- web log 出現 `OperationalError: FATAL: too many connections`

### 排查
```sql
-- 看當前連線數
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
-- 看 max
SHOW max_connections;
```

### 對策
1. **臨時**：重啟 web 釋放連線：`docker-compose restart web`
2. **長期**：
   - 加 PostgreSQL `max_connections`（修 docker-compose / postgresql.conf）
   - 引入 pgbouncer（連線池）
   - 找出哪段程式碼漏關連線（grep `connection.cursor()` 沒用 with 包的地方）

---

## Celery worker 沒在跑

### 排查
```powershell
docker-compose ps celery_worker
docker-compose logs celery_worker --tail=50
```

### 對策
- 看到 `Connected to redis` 但 task 不跑：worker 卡死，重啟 `docker-compose restart celery_worker`
- 看到 `Connection refused redis:6379`：Redis 掛了
- worker 一直 OOM kill：增加 RAM 或降低 `--concurrency`（目前預設 16）

---

## Redis 掛了

### 影響範圍
- Cache 全部 miss → 一切回到打 DB（會慢但不會死）
- Celery 不能派 task → 寄信、月結卡住
- Session 仍在 DB（Django 預設）→ 登入不受影響

### 排查
```powershell
docker-compose exec redis redis-cli ping
# 應回 PONG
```

### 對策
```powershell
docker-compose restart redis
```

---

## 緊急回滾

### 程式碼回滾
```powershell
# 看最近 commit
git log --oneline -10

# 回到上一個 commit（保留改動到 working tree）
git reset --soft HEAD~1

# 完全回到上一個 commit（丟棄改動，慎用）
git reset --hard HEAD~1

# 重 build & 部署
docker-compose build web
docker-compose up -d
```

### Migration 回滾
```powershell
# 回到指定 migration（apply 之前的版本）
docker-compose exec web python manage.py migrate <app> <previous_migration_name>

# 例：回到 bookkeeping 0050
docker-compose exec web python manage.py migrate bookkeeping 0050
```

⚠️ Migration 回滾若涉及刪欄位 / 表，**會掉資料**。先 dump 備份。

---

## 備份 / 還原

### 備份
```powershell
docker-compose exec db pg_dump -U postgres -Fc aura_db > backups\aura_$(Get-Date -Format yyyyMMdd_HHmm).dump
```

### 還原（會清空現有資料）
```powershell
Get-Content backups\aura_xxxx.dump -Raw | docker-compose exec -T db pg_restore -U postgres -d aura_db --no-owner --clean --if-exists
```

⚠️ pg_dump 與 pg_restore 必須是同一 PostgreSQL 主版本。Aura 用 pg16。

---

## 監控接點

| 監控項目 | 接點 |
|---|---|
| Production error 即時通知 | Sentry（環境變數 `SENTRY_DSN`） |
| Uptime / 連線監控 | UptimeRobot（外部，免費版即可） |
| DB 慢查詢 | `pg_stat_statements`（需在 postgresql.conf 啟用） |
| 容器資源 | `docker stats` 或 Portainer |
| Log 查詢 | `docker-compose logs <service>` 或接 ELK / Loki |

### Sentry 啟用步驟
1. 註冊 https://sentry.io（個人方案免費）
2. 建立 Django 專案，拿 DSN
3. 編輯 `.env`：
   ```
   SENTRY_DSN=https://xxx@sentry.io/xxx
   SENTRY_ENVIRONMENT=production
   ```
4. 重啟 web 與 celery_worker
5. 故意觸發 error 確認 Sentry 收到

---

## 上線前檢查 SOP

```powershell
# 1. Production 設定檢查
docker-compose exec web python manage.py check --deploy --settings=config.settings_production

# 2. Migration 狀態
docker-compose exec web python manage.py showmigrations | grep "\[ \]"   # 找未 apply

# 3. 跑全測試
docker-compose exec web pytest

# 4. 壓測
docker-compose exec web python manage.py benchmark_queries

# 5. 備份當前資料
docker-compose exec db pg_dump -U postgres -Fc aura_db > backups\pre_release.dump
```

5 個都通過再上線。
