# 通知範本完整對照表

記帳模組各通知功能所需的範本 code、可用變數，以及可直接套用的範例文案。

## 共用規則

- 建立範本時 **`code` 必須與下表完全一致**，且 **`is_active` 要打勾**。
  程式是用 `code=..., is_active=True` 查找，少一個就會報 `template not found or inactive`（見 [core/notifications/services.py](../core/notifications/services.py)）。
- Line 與 Email 使用**同一個 code**，但分別建立在「Line 訊息範本」與「Email 範本」。
- 內容使用 Django 模板語法 `{{ 變數 }}`。
- 客戶的 `notification_method` 決定走哪個管道：`line` 只發 Line、`email` 只發 Email、`both` 兩者都發。
  → 至少要建客戶會用到的那個管道的範本。
- Line 範本有 `text`（純文字）與 `flex`（卡片）兩種型態；`flex` 需填合法 JSON，否則 render 失敗。先用 `text` 最快。
- 金額目前為純數字（如 `12000`）。若需千分位顯示，需在範本加 filter 或在 service 的 context 預先格式化。

> 各範本的變數來源為對應 service 的 `build_*_context()`，路徑見每節標題。

## 單筆送 vs 批次送

通知有兩條送出路徑，請留意：

- **單筆送**（各明細頁的「發送繳稅通知」按鈕）：走該功能的 `build_*_context()`，變數最完整。
- **批次送**（進度頁的「批次 Line／Email 通知」）：走 core 通用的 `DocumentService._build_context()`。

兩條路徑的變數**已對齊**（見 [core/services/document.py](../core/services/document.py) 內 `TaxFilingPeriod` 分支），同一份範本兩邊都可用。唯一差異：

- **營業稅批次送的 `final_total` 不含「前期未收餘額」**（`outstanding_balance` 以 0 計，故 `final_total` ＝本期應納稅額）。前期未收只有在單筆送頁面手動「取得未收餘額」後才會帶入。批次大量發送時若需逐筆未收，請改用單筆送。

---

## ① 營業稅繳稅通知 `vat_payment_request`

- **觸發**：營業稅期別明細頁「發送繳稅通知」
- **來源**：[modules/bookkeeping/services/vat_notification.py](../modules/bookkeeping/services/vat_notification.py)

| 變數 | 內容 |
|---|---|
| `{{ client_name }}` | 客戶名稱 |
| `{{ year }}` | 年度（民國） |
| `{{ period_label }}` | 期別，例 `01-02月` |
| `{{ payable_tax }}` | 本期應納稅額 |
| `{{ outstanding_balance }}` | 前期未收餘額 |
| `{{ final_total }}` | 合計（應納＋未收） |
| `{{ tax_deadline }}` | 繳稅截止日 |
| `{{ payment_method }}` | 繳稅方式 |
| `{{ confirm_url }}` | 客戶確認連結 |

**Line（text）：**
```
【{{ client_name }}】營業稅繳款通知

{{ year }}年 {{ period_label }}
應納稅額：{{ payable_tax }} 元
前期未收：{{ outstanding_balance }} 元
應繳合計：{{ final_total }} 元

繳稅方式：{{ payment_method }}
繳款期限：{{ tax_deadline }}

請點選確認繳款：
{{ confirm_url }}
```

**Email — 主旨：**
```
{{ client_name }} {{ year }}年{{ period_label }}營業稅繳款通知
```

**Email — 內文（HTML）：**
```html
<p>{{ client_name }} 您好：</p>
<p>貴公司 {{ year }} 年 {{ period_label }} 營業稅繳款資訊如下：</p>
<ul>
  <li>本期應納稅額：{{ payable_tax }} 元</li>
  <li>前期未收餘額：{{ outstanding_balance }} 元</li>
  <li><strong>應繳合計：{{ final_total }} 元</strong></li>
  <li>繳稅方式：{{ payment_method }}</li>
  <li>繳款期限：{{ tax_deadline }}</li>
</ul>
<p><a href="{{ confirm_url }}">點此確認繳款</a></p>
```

---

## ② 暫繳通知 `provisional_tax_notification`

- **觸發**：暫繳明細頁「發送繳稅通知」
- **來源**：[modules/bookkeeping/services/provisional_tax_notification.py](../modules/bookkeeping/services/provisional_tax_notification.py)

| 變數 | 內容 |
|---|---|
| `{{ client_name }}` | 客戶名稱 |
| `{{ year }}` | 年度（民國） |
| `{{ provisional_amount }}` | 暫繳金額 |
| `{{ tax_deadline }}` | 繳稅截止日 |
| `{{ payment_method }}` | 繳稅方式 |

> ⚠️ 暫繳**沒有** `confirm_url` 變數，勿在此範本使用。

**Line（text）：**
```
【{{ client_name }}】暫繳稅款通知

{{ year }}年 營利事業所得稅暫繳
暫繳金額：{{ provisional_amount }} 元
繳稅方式：{{ payment_method }}
繳款期限：{{ tax_deadline }}

請於期限前完成繳納，謝謝。
```

**Email — 主旨：**
```
{{ client_name }} {{ year }}年暫繳稅款通知
```

**Email — 內文（HTML）：**
```html
<p>{{ client_name }} 您好：</p>
<p>貴公司 {{ year }} 年營利事業所得稅暫繳資訊如下：</p>
<ul>
  <li>暫繳金額：{{ provisional_amount }} 元</li>
  <li>繳稅方式：{{ payment_method }}</li>
  <li>繳款期限：{{ tax_deadline }}</li>
</ul>
```

---

## ③ 扣繳通知 `withholding_tax_notification`

- **觸發**：扣繳明細頁「發送繳稅通知」
- **來源**：[modules/bookkeeping/services/withholding_tax_notification.py](../modules/bookkeeping/services/withholding_tax_notification.py)

| 變數 | 內容 |
|---|---|
| `{{ client_name }}` | 客戶名稱 |
| `{{ year }}` | 年度（民國） |
| `{{ payable_tax }}` | 應納（扣繳）稅額 |
| `{{ tax_deadline }}` | 繳稅截止日 |
| `{{ payment_method }}` | 繳稅方式 |

**Line（text）：**
```
【{{ client_name }}】扣繳稅款通知

{{ year }}年 扣繳稅款
應納稅額：{{ payable_tax }} 元
繳稅方式：{{ payment_method }}
繳款期限：{{ tax_deadline }}

請於期限前完成繳納，謝謝。
```

**Email — 主旨：**
```
{{ client_name }} {{ year }}年扣繳稅款通知
```

**Email — 內文（HTML）：**
```html
<p>{{ client_name }} 您好：</p>
<p>貴公司 {{ year }} 年扣繳稅款資訊如下：</p>
<ul>
  <li>應納稅額：{{ payable_tax }} 元</li>
  <li>繳稅方式：{{ payment_method }}</li>
  <li>繳款期限：{{ tax_deadline }}</li>
</ul>
```

---

## ④ 勞務報酬繳費提醒 `service_remuneration_payment_reminder`

- **觸發**：每月 1 號自動排程（客戶需開啟「啟用勞務報酬繳費提醒」）
- **來源**：[modules/bookkeeping/services/service_remuneration_notification.py](../modules/bookkeeping/services/service_remuneration_notification.py)

| 變數 | 內容 |
|---|---|
| `{{ client_name }}` | 客戶名稱 |
| `{{ target_year }}` | 支付年度 |
| `{{ target_month }}` | 支付月份 |
| `{{ deadline }}` | 繳款期限（次月 10 日） |
| `{{ count }}` | 待繳筆數 |
| `{{ total_withholding_tax }}` | 扣繳稅款合計 |
| `{{ total_supplementary_premium }}` | 補充保費合計 |
| `{{ total_payable }}` | 應繳總計 |
| `{{ items }}` | 明細清單（需 `{% for %}` 迴圈） |

`items` 每筆欄位：`recipient_name`（受款人）、`amount`（給付金額）、`withholding_tax`（扣繳稅）、`supplementary_premium`（補充保費）、`category`（所得類別）、`filing_date`（申報日）。

**Line（text）：**
```
【{{ client_name }}】勞務報酬繳費提醒

{{ target_year }}年{{ target_month }}月 共 {{ count }} 筆待繳：
{% for item in items %}・{{ item.recipient_name }}（{{ item.category }}）扣繳 {{ item.withholding_tax }} / 補充保費 {{ item.supplementary_premium }}
{% endfor %}
扣繳稅款合計：{{ total_withholding_tax }} 元
補充保費合計：{{ total_supplementary_premium }} 元
應繳總計：{{ total_payable }} 元

繳款期限：{{ deadline }}
```

**Email — 主旨：**
```
{{ client_name }} {{ target_year }}年{{ target_month }}月勞務報酬繳費提醒
```

**Email — 內文（HTML）：**
```html
<p>{{ client_name }} 您好：</p>
<p>{{ target_year }} 年 {{ target_month }} 月共有 {{ count }} 筆勞務報酬待繳：</p>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>受款人</th><th>類別</th><th>給付金額</th><th>扣繳稅款</th><th>補充保費</th></tr>
  {% for item in items %}
  <tr>
    <td>{{ item.recipient_name }}</td><td>{{ item.category }}</td>
    <td>{{ item.amount }}</td><td>{{ item.withholding_tax }}</td><td>{{ item.supplementary_premium }}</td>
  </tr>
  {% endfor %}
</table>
<p>扣繳稅款合計：{{ total_withholding_tax }} 元<br>
補充保費合計：{{ total_supplementary_premium }} 元<br>
<strong>應繳總計：{{ total_payable }} 元</strong><br>
繳款期限：{{ deadline }}</p>
```

---

## 建立優先順序

1. 先建 `vat_payment_request`（依客戶實際使用的管道建 Line 或 Email）→ 可立即驗證。
2. 其餘三個於對應功能上線前再建即可。
