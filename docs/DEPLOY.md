# Aura 部署 SOP（Railway + Cloudflare）

> 目標：把 Aura 部署到 Railway，網域 chixin.com.tw 走 Cloudflare。
> 預估首次部署 1-2 小時（含註冊帳號、設定 DNS）。

---

## 部署架構

```
使用者瀏覽器
     ↓ HTTPS（Cloudflare 端證書）
[Cloudflare]  ← chixin.com.tw 在此託管
     ↓ HTTPS（Railway 端證書）
[Railway Tokyo 機房]
  ├─ web（Django + gunicorn）
  ├─ celery_worker
  ├─ celery_beat
  ├─ Postgres（Railway managed）
  └─ Redis（Railway managed）
```

---

## 第一階段：Railway 帳號 + 上線（45 分鐘）

### 1.1 註冊 Railway
1. 開 https://railway.app
2. 用 **GitHub 帳號** 登入（之後會用同一個 GitHub 來連 repo）
3. 升級到 Hobby Plan：每月 $5 訂閱費（含 $5 免費 usage）

### 1.2 建立 Project
1. Dashboard → **New Project** → **Empty Project**
2. 命名 `aura-production`

### 1.3 加入 Postgres
1. Project 內 → **+ New** → **Database** → **PostgreSQL**
2. 等 30 秒部署完
3. 點進 Postgres → **Connect** tab → 複製 `DATABASE_URL`（之後給 web service 用）

> ⚠️ Railway 預設 Postgres 沒有 pgvector extension。
> 部署後要進 Railway 的 Postgres CLI（**Data** tab → **Query**）跑：
> ```sql
> CREATE EXTENSION IF NOT EXISTS vector;
> ```
> 否則 migration 會掛在 knowledge_base.0001（已測過）

### 1.4 加入 Redis
1. Project → **+ New** → **Database** → **Redis**
2. Redis 內 → **Connect** 複製 `REDIS_URL`

### 1.5 建立 web service
1. Project → **+ New** → **GitHub Repo**
2. 選 `Aura` repo（如果是 private repo 要先在 GitHub 設定授權）
3. 自動偵測到 `Dockerfile` + `railway.json`
4. **Variables** tab 設環境變數（從 `.env` 抄過來但**改值**）：

```
DJANGO_SETTINGS_MODULE=config.settings_production
SECRET_KEY=<重新產生一個新的 50 字元字串>
DEBUG=False
ALLOWED_HOSTS=chixin.com.tw,www.chixin.com.tw,.up.railway.app
CSRF_TRUSTED_ORIGINS=https://chixin.com.tw,https://www.chixin.com.tw

# 從 Postgres / Redis service 引用（${{Postgres.DATABASE_URL}} 是 Railway 語法）
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Email：等實際 SMTP 提供商（Mailgun / SendGrid / Gmail SMTP）設好再填
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Aura <noreply@chixin.com.tw>

# HTTPS 安全設定（production 必須）
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Sentry（等註冊好填）
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
```

5. Settings tab → **Networking** → 點 **Generate Domain** 取得 `xxx.up.railway.app` 暫時網址
6. 等部署完成（約 5-10 分鐘 build + deploy）
7. 訪問 `xxx.up.railway.app`，**預期會看到 login 頁**

> 第一次部署後，DB 是空的，需要建 superuser：
> Railway web service → **Settings** → **Custom Start Command** 改成：
> ```
> python manage.py createsuperuser --noinput --username admin --email you@example.com && python manage.py migrate ...
> ```
> 或進 Railway shell 手動跑（**Settings** → **Deploy** → **Shell**）。

### 1.6 建立 celery_worker service
1. Project → **+ New** → **GitHub Repo**（同一個 repo）
2. **Settings** → **Source** → 選同一個 repo
3. **Settings** → **Deploy** → **Custom Start Command**：
   ```
   celery -A config worker -l info
   ```
4. **Variables** tab：點右上 **Raw Editor** → 從 web service 複製貼上同一份環境變數

### 1.7 建立 celery_beat service
同上，但 Custom Start Command 改：
```
celery -A config beat -l info
```

### 1.8 驗收 staging 階段
- [ ] web 訪問 `xxx.up.railway.app/login/` → 200
- [ ] 登入 admin → 看 Dashboard 正常
- [ ] Celery worker log 看到 `ready.`
- [ ] 試寄一封通知信，看是否進 EmailLog（status=pending → sent）

---

## 第二階段：Cloudflare DNS（30 分鐘）

### 2.1 註冊 Cloudflare
1. https://cloudflare.com 註冊
2. **Add a Site** → 輸入 `chixin.com.tw`
3. 選 **Free plan**

### 2.2 改 nameserver
1. Cloudflare 會給你兩個 nameserver，例如：
   - `xxx.ns.cloudflare.com`
   - `yyy.ns.cloudflare.com`
2. 到買網域的地方（中華電信 / Gandi / Namecheap...）
3. 修改 chixin.com.tw 的 nameserver 為 Cloudflare 給的兩個
4. 等 DNS 生效（最快 5 分鐘，最慢 24 小時）

### 2.3 加 DNS records 指到 Railway
回到 Cloudflare Dashboard → DNS：

| Type | Name | Content | Proxy |
|---|---|---|---|
| CNAME | @ | xxx.up.railway.app | 🟠 Proxied |
| CNAME | www | xxx.up.railway.app | 🟠 Proxied |

> Proxy（橘色雲）= 流量走 Cloudflare CDN，提供 DDoS 防護、隱藏 origin IP、免費 SSL。

### 2.4 SSL/TLS 模式設 Full (strict)
Cloudflare → **SSL/TLS** → 模式選 **Full (strict)**
這樣是「使用者→Cloudflare→Railway」全程 HTTPS。

### 2.5 在 Railway 加 custom domain
1. Railway web service → **Settings** → **Networking** → **Custom Domain**
2. 輸入 `chixin.com.tw`
3. Railway 會給你一個 CNAME target（可能跟 `xxx.up.railway.app` 不同），更新 Cloudflare DNS
4. 同樣加 `www.chixin.com.tw`

### 2.6 驗收
- [ ] https://chixin.com.tw → 看到 login 頁，瀏覽器顯示綠色鎖頭
- [ ] http://chixin.com.tw → 自動 redirect 到 https
- [ ] https://www.chixin.com.tw → 也通

---

## 第三階段：上線前檢查（每次發版都跑）

```powershell
# 1. 跑全測試（在本機）
docker-compose exec web pytest

# 2. Production 設定檢查
docker-compose exec web python manage.py check --deploy --settings=config.settings_production

# 3. Migration 列表（確認無未 apply）
docker-compose exec web python manage.py showmigrations | Select-String "\[ \]"

# 4. 備份 Railway DB（每次發版前必做）
# Railway dashboard → Postgres → Backups → Create Backup
```

5 個檢查通過才能 push deploy。

---

## 第四階段：發版流程（routine deploy）

### 4.1 標準流程（git push 自動觸發）

```powershell
# 在 batch-1-architecture 分支做完所有變更
git checkout main
git merge batch-1-architecture
git push origin main
```

Railway 自動偵測 push 後：
1. Build 新 image（5-10 分鐘）
2. 跑 `migrate` + `collectstatic`
3. 啟動新 container
4. 健康檢查通過後切流量
5. 舊 container 收掉

> ⚠️ Migration 期間網站可能短暫 503（10-30 秒），影響很小。

### 4.2 出包緊急回滾
Railway dashboard → web service → **Deployments** → 找上一個成功的 deploy → **Redeploy**

或者 git revert + push：
```powershell
git revert HEAD
git push origin main
```

---

## 第五階段：故障演練（每季跑一次）

### 模擬 Redis 掛了
本機：
```powershell
docker-compose stop redis
# 訪問 http://localhost:8000，預期：cache 全 miss、celery 派不出 task，但**主流程仍可用**
docker-compose start redis
```

### 模擬 DB 掛了
```powershell
docker-compose stop db
# 訪問任一頁，預期：500 錯誤頁
docker-compose start db
```

### 模擬 Celery worker 掛了
```powershell
docker-compose stop celery_worker
# 觸發寄信 / 月結，task 進 broker 但不執行
# 啟動後會自動消化排隊的 task
docker-compose start celery_worker
```

---

## 第六階段：監控接點

| 項目 | 在哪看 |
|---|---|
| Railway 服務狀態 | Railway dashboard |
| Production error | Sentry（需要先註冊填 SENTRY_DSN） |
| 流量監控 | Cloudflare dashboard → Analytics |
| Uptime | UptimeRobot（外部監控，免費 50 個 endpoint） |
| DB 慢查詢 | Railway Postgres → Query → 開 pg_stat_statements |
| Log 即時看 | Railway service → **Logs** tab |

---

## 第七階段：成本控管

### 預估月費
| 服務 | 規格 | 月費（usage 估） |
|---|---|---|
| 訂閱 Hobby plan | base | $5 |
| Postgres | 1GB RAM | ~$5-10 |
| Redis | 256MB | ~$3-5 |
| Web service | 1GB RAM 跑 8 小時 active | ~$8-15 |
| Celery worker | 256MB 24x7 | ~$3-5 |
| Celery beat | 128MB 24x7 | ~$1-3 |
| **總計** | | **~$25-43** |

### 怎麼省錢
- Web service Auto-sleep（沒人用就停）→ 但會增加冷啟延遲，**不建議 production 開**
- Worker 規格降到最小 → 月結時會慢一點，但 OK
- 設 **Spending Limit**：Railway → Account → Usage → **Set Limit** $50（超過會收信通知）

---

## 常見問題

### Q1：第一次部署 migration 失敗
- 看 Railway log 有沒有 `type "vector" does not exist`
- → 進 Postgres CLI 跑 `CREATE EXTENSION vector`，redeploy

### Q2：`ALLOWED_HOSTS` 拒絕 Railway 預設網址
- 把 `.up.railway.app` 加進 `ALLOWED_HOSTS`（注意前面有點）

### Q3：Cloudflare 一直 Error 521
- Railway service 沒起來、或 SSL 模式設錯
- 改成 **Full (strict)** 而不是 Flexible

### Q4：static 檔案 404
- `python manage.py collectstatic` 沒跑，看 startCommand 是否正確
- whitenoise middleware 是否在最前面

### Q5：寄信失敗
- SMTP 設定錯（EMAIL_HOST 等）
- 進 admin → SystemParameter 改設定（會即時生效，不用重啟）
- 看 EmailLog 的 error_message
