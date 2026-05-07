# 本機開發環境（Docker）

> 目標：本機開發環境 = 線上環境，避免「本機過、線上爆」。

## 第一次啟動

### 1. 安裝 Docker Desktop
- Windows：[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- 確認 WSL2 已啟用

### 2. 建立 .env
```powershell
Copy-Item .env.example .env
```
然後編輯 `.env`：
- `SECRET_KEY` 重新產生（避免使用預設值）：
  ```powershell
  docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
- `DB_PASSWORD` 改一個安全的密碼
- `DEBUG=True`（本機開發用）

### 3. 啟動所有服務
```powershell
docker-compose up -d
```

第一次會下載 image + build，約 5-10 分鐘。

### 4. 確認服務啟動
```powershell
docker-compose ps
```
應該看到 db / redis / web / celery_worker / celery_beat / nginx 全部 running。

### 5. 建立超級使用者
```powershell
docker-compose exec web python manage.py createsuperuser
```

### 6. 訪問
- 直接：http://localhost:8000
- 經 nginx：http://localhost

---

## 日常開發

### 看 log
```powershell
docker-compose logs -f web           # web 服務 log
docker-compose logs -f celery_worker # celery log
docker-compose logs -f               # 全部
```

### 進 container shell
```powershell
docker-compose exec web bash
docker-compose exec web python manage.py shell
```

### 跑 migration
```powershell
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### 重啟單一服務
```powershell
docker-compose restart web
```

### 完整重 build（改了 Dockerfile 或 requirements）
```powershell
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 從舊 DB 還原資料

```powershell
docker-compose exec -T db pg_restore -U postgres -d aura_db < aura_backup.dump
```

---

## 切換 Settings

| 用途 | 設定值 | 啟動方式 |
|---|---|---|
| 本機開發 | `config.settings` | `DJANGO_SETTINGS_MODULE=config.settings`（預設） |
| Staging（壓測） | `config.settings_staging` | 編輯 `.env` 加 `DJANGO_SETTINGS_MODULE=config.settings_staging` |
| Production | `config.settings_production` | 部署環境另外設定 |

---

## 排錯

### `DB_PASSWORD must be set`
→ 沒建立 `.env` 或裡面沒設密碼

### web container 起不來，log 顯示連不到 DB
→ DB 還沒 ready，web 會自動等。如果一直失敗：
```powershell
docker-compose logs db
```

### static 檔案 404
→ 跑：
```powershell
docker-compose exec web python manage.py collectstatic --noinput
```

### 想完全重來
```powershell
docker-compose down -v   # -v 會刪 volume（DB 資料會清空！）
```

---

## 注意事項

- **不要在本機跑 `python manage.py runserver`**：環境差異會踩坑
- 改 model / requirements 要 rebuild
- 媒體檔放 `media/` volume，container 重啟不會掉
- `.env` 永遠不要 commit
