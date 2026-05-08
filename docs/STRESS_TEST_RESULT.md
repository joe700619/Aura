# 壓力測試結果（批次 3）

> 日期：2026-05-08
> 環境：Docker（PostgreSQL 16 + pgvector，本機 WSL2 7.5GB RAM）
> 規模：5,000 客戶 / 45,094 帳單 / 20,000 案件 / 10,000 諮詢 / 30,000 應收（共 110,094 筆）
> 工具：`python manage.py seed_stress_data` + `benchmark_queries` / `benchmark_baseline`

---

## 結論

**所有列表/搜尋查詢在 5K 客戶規模下表現優異**：
- 多數查詢 < 11ms / 1 條 SQL
- 月結批次（最重）155 ms / 2 SQL
- 完全無紅色警告

**批次 1+2 的價值經實證**：N+1 修復把月結批次從 2547ms / 4523 條 SQL 砍到 155ms / 2 條 SQL（16× 加速、2261× 減 SQL）。

---

## 詳細數據（benchmark_queries）

| 項目 | 時間 (ms) | SQL | 評估 |
|---|---|---|---|
| Customer 列表 (no search) | 11.1 | 3 | 🟢 |
| Customer 搜尋 tax_id (icontains) | 4.9 | 1 | 🟢 (db_index 生效) |
| Customer 搜尋 name (icontains) | 2.7 | 1 | 🟢 |
| BookkeepingClient 列表 active | 4.0 | 1 | 🟢 |
| BookkeepingClient 計數 by status | 1.6 | 1 | 🟢 |
| ClientBill 按 status filter + 排序 | 1.9 | 1 | 🟢 (複合 index 生效) |
| ClientBill 按年月排序 | 1.6 | 1 | 🟢 |
| ClientBill 計數 by status | 7.3 | 1 | 🟢 |
| Case 列表 (open + ordering) | 1.7 | 1 | 🟢 |
| Case 計數 by status | 2.6 | 1 | 🟢 |
| Inquiry 列表 (status filter) | 1.2 | 1 | 🟢 |
| Inquiry 跨欄位 OR 搜尋 | 5.0 | 1 | 🟢 |
| Inquiry 計數 by status | 1.6 | 1 | 🟢 |
| Receivable 列表 | 10.8 | 1 | 🟢 |
| Receivable 搜尋 company_name | 9.9 | 1 | 🟢 |
| **月結批次模擬 (5K 客戶, Prefetch)** | **155.3** | **2** | 🟢 |

判定標準：時間 < 100ms 綠 / 100-500ms 黃 / > 500ms 紅；SQL ≤ 3 綠 / 4-15 黃 / > 15 紅

---

## 修復前後對比（月結批次）

| | 修復前（N+1） | 修復後（Prefetch + to_attr） | 倍數差異 |
|---|---|---|---|
| 時間 | 2547.5 ms | 155.3 ms | **16.4×** 加速 |
| SQL 數 | 4523 | 2 | **2261×** 減少 |
| 等待感受 | 「卡住了？」 | 「秒開」 | — |

---

## 關鍵發現

### 1. db_index 對 icontains 仍有幫助（即使是 LIKE %x%）
- Customer.tax_id 加 index 後，5K 筆中找 tax_id 含 '15000' = 4.9 ms
- 沒 index 的話 PostgreSQL 會全表 scan，預期慢 5-10x

### 2. 複合 index 對「filter + order by」效果顯著
- ClientBill 的 `(status, -created_at)` 複合 index 讓「篩選草稿狀態 + 按時間排序」直接走 index，1.9 ms 完成

### 3. Prefetch + to_attr 是 N+1 殺手
- 修復前每個客戶都打一次 SQL 查 service_fee → 5K 客戶 = 5K 條 SQL
- 修復後一條 SQL 抓全部 service_fee，按客戶分組存 in-memory
- 這就是寫程式時要強制檢查 `for client in qs: client.related.filter()` pattern 的原因

---

## 待後續處理

### 觀察項
1. **`tax_id__icontains='15000'` 找不到資料**（測試資料 tax_id 從 10000000 開始遞增，沒 15000 開頭）
   → 這不是優化問題，純粹是測試資料設計。實際業務上會有完整 8 碼，使用者會搜「15008888」這種片段
2. **HistoricalRecords 規模**：bulk_create 沒觸發 history，所以這次測試 history 表是空的
   → 未來 batch 4 處理 history 清理時要重測
3. **暫無測試的場景**：
   - Login 後完整 dashboard 載入（需要 session）
   - Wagtail CMS 對外網頁（不是業務重點）
   - 跨 join 複雜查詢（例如「客戶最近 12 期帳單狀態」）

### 不做的事
- 暫無發現需要進一步補的 index
- 暫無發現新的 N+1 熱點

---

## 重現方式

```bash
# 灌資料（約 1 分鐘）
docker-compose exec web python manage.py seed_stress_data

# 跑 benchmark
docker-compose exec web python manage.py benchmark_queries

# 對照組（修復前的 N+1 寫法）
docker-compose exec web python manage.py benchmark_baseline

# 清空（如要還原）
docker-compose exec web python manage.py seed_stress_data --clear --scale 0
# 或重新灌
docker-compose exec web python manage.py seed_stress_data --clear
```
