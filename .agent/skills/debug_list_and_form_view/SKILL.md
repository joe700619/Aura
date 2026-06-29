---
name: debug_list_and_form_view
description: 如何對 list.html 和 form.html 進行除錯和修正，涵蓋常見症狀、診斷步驟與修正方法
---

# Debug: List & Form View

當 list.html 或 form.html 出現問題時，依據症狀查閱對應的診斷與修正步驟。

---

## 基礎架構提醒

| Template | 繼承自 | 對應 Skill |
|----------|--------|-----------|
| list.html | `components/list_view.html` | `standard_list_view` |
| form.html | `components/form_view.html` | `standard_form_view` |

> [!IMPORTANT]
> 修改前一定要先確認問題是在 **template**、**views.py**、**forms.py**、還是 **urls.py**。不要盲目修改 template。

---

## 📋 LIST VIEW 除錯

### 症狀 1：頁面空白 / 500 伺服器錯誤

**診斷步驟：**
1. 確認 Django 後端錯誤訊息（瀏覽器或 terminal）
2. 確認 View 是否繼承 `ListActionMixin`：
   ```python
   # views.py
   from core.mixins import ListActionMixin
   class MyListView(ListActionMixin, LoginRequiredMixin, ListView):
       ...
   ```
3. 確認 `template_name` 路徑正確，且檔案存在
4. 確認 `context_object_name` 與 template 內使用的變數名稱一致

---

### 症狀 2：全選/勾選 checkbox 無效

**診斷步驟：**
1. 開啟瀏覽器 Console，查看是否有 JSON parse error
2. 確認 `{% block content %}` 內有 `list-metadata` script：
   ```html
   {% block content %}
   <script id="list-metadata" type="application/json">
   [
       {% for obj in objects %}
       {
           "id": {{ obj.pk }},
           "category": "{{ obj.category|escapejs }}",
           "content": "{{ obj.name|escapejs }}"
       }{% if not forloop.last %},{% endif %}
       {% endfor %}
   ]
   </script>
   {{ block.super }}
   {% endblock %}
   ```
3. 確認 checkbox 使用 `x-model.number`（不是 `x-model`）：
   ```html
   <input type="checkbox" value="{{ obj.pk }}" x-model.number="selectedRows">
   ```
4. 確認所有字串欄位都有 `|escapejs` filter

**常見錯誤：**
- `{{ block.super }}` 漏寫 → 整個 base template 消失
- `x-model` 而非 `x-model.number` → ID 型別不符，無法比對

---

### 症狀 3：Email / Line 批次發送按鈕不出現

**診斷步驟：**
1. 確認 View 有繼承 `ListActionMixin`（這是顯示條件的來源）
2. 進入 Django Admin，確認已建立 `EmailTemplate` 或 `LineMessageTemplate`，且 `model_content_type` 指向正確 model
3. 確認 `{% block overlays %}` 有包含對應的 sidebar include：
   ```html
   {% block overlays %}
   {% include "components/export_modal.html" %}
   {% include "components/email_sidebar.html" %}
   {% include "components/line_sidebar.html" %}
   {% endblock %}
   ```

> [!WARNING]
> 不要把 sidebar include 放在 `{% block content %}` 內，會因為 `overflow:hidden` 造成 sidebar 被截斷。

---

### 症狀 4：搜尋 / Filter 無效

**診斷步驟：**
1. 確認 `list-metadata` 的 `content` 欄位包含所有需要搜尋的字串
2. 確認 filter button 的 `@click` 值與 `list-metadata` 的 `category` 值完全一致（大小寫敏感）：
   ```html
   <!-- category 值是 'ACTIVE'，filter 也要是 'ACTIVE' -->
   <button @click="filter = 'ACTIVE'">啟用中</button>
   ```
3. 確認 `x-show` 使用的是 `matches()` 函式：
   ```html
   <tr x-show="matches('{{ obj.category|escapejs }}', '{{ obj.name|escapejs }}')">
   ```

---

### 症狀 5：資料筆數多（超過 500 筆）時搜尋失效

**根本原因：** 前端 Alpine.js 搜尋只能過濾**當前頁**的資料，分頁後其他頁的資料無法被搜尋到。

**修正：加入 `SearchMixin`（後端伺服器搜尋）**

**Step 1 — `views.py` 加 mixin：**
```python
from core.mixins import ListActionMixin, SearchMixin

class MyListView(ListActionMixin, SearchMixin, LoginRequiredMixin, ListView):
    model = MyModel
    search_fields = ['name', 'tax_id']          # 定義要搜尋的欄位（支援跨關聯，例如 'client__name'）
    paginate_by = 25                             # 建議同時設定分頁
```

**Step 2 — 確認 `list_view.html` 已具備（已內建，不需額外修改）：**
- 搜尋框是 `<form method="GET">` → 按 Enter 或停止輸入 500ms 後自動送出
- 分頁連結自動帶 `?q=` 參數，換頁不會清除搜尋條件

> [!NOTE]
> `SearchMixin` 定義在 `core/mixins.py`，對 TemplateView（非 ListView）需在 `get_context_data` 手動套 Q 過濾，參考 `progress_views.py` 的 `ProgressTrackerView`。

---

### 症狀 5：新增按鈕 URL 錯誤 (NoReverseMatch)

**診斷步驟：**
Base template 會自動根據 `{model_name}_create` 組成 URL。確認：
1. View 的 `model` 屬性設定正確
2. `urls.py` 中有對應名稱的 URL pattern（如 `employee_create`）

若想自訂新增按鈕，於 template 覆寫 `{% block actions %}`：
```html
{% block actions %}
<a href="{% url 'my_custom_create' %}" class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm">新增</a>
{% endblock %}
```

---

## 📋 FORM VIEW 除錯

### 症狀 1：儲存後資料未保存 (Form Invalid)

**診斷步驟：**
1. 在 template 的 `{% block form_card_1 %}` 最上方加入暫時的 error dump：
   ```html
   {% if form.errors %}
   <div class="bg-red-50 border border-red-300 rounded p-3 text-sm text-red-700">
       {{ form.errors }}
   </div>
   {% endif %}
   ```
2. 提交後觀察顯示的欄位錯誤
3. 確認 `forms.py` 的 `fields` 清單包含所有必填欄位
4. 確認 View 的 `form_class` 指向正確的 form class

---

### 症狀 1.5：按「儲存」完全沒反應（無 loading、無錯誤、頁面不動）

**根本原因：隱藏頁籤裡有「不可聚焦的無效欄位」，導致 `requestSubmit()` 靜默中止。**

toolbar 的儲存鈕執行的是 `document.getElementById('main-form').requestSubmit()`，
而 `requestSubmit()` 會先跑**瀏覽器原生欄位驗證**。只要表單裡有任何一個欄位「驗證不過」
**且當下無法被聚焦**（例如在 `x-show`/`display:none` 的隱藏頁籤、或 `name=''` 的純 UI 欄位），
瀏覽器無法提示該欄位，就會**靜默取消送出、什麼都不做**。

**診斷（決定性）：** 開 DevTools Console，按儲存，會看到：
```
An invalid form control with name='…' is not focusable. <input …>
```
Console 會直接指出是哪一個 `<input>`。

**常見肇因欄位：**
- 純 Alpine `x-model` 代理欄位（**沒有 `name`**，資料另存進 hidden 的 JSON 欄位），卻掛了 `min`/`max`/`step`/`required`
- 多頁籤表單中，藏在非 active 頁籤（`display:none`）裡、值不合 `min`/`max`/`step` 的 number/date 欄位

**修正原則：**
> **只作為 x-model 代理、沒有 `name`、又可能藏在隱藏頁籤裡的欄位，一律用 `type="text"`（要數字鍵盤就加 `inputmode="decimal"`），不要掛 `required`/`min`/`max`/`step`。**
> 這類欄位本來就不靠表單送出（而是序列化進 hidden 欄位交給後端），原生驗證對它沒有意義，卻會連累整張表單無法儲存。
> ⚠️ 只移除 `min`/`max`/`step` **還不夠**：`type="number"` 本身在「值無法解析成合法數字」時會進入 **badInput** 狀態，照樣是 invalid、照樣靜默擋掉送出。所以要直接改成 `type="text"`。

實例：`components/cost_sharing_table.html` 的「比例(%)」欄位先因 `step/min/max` 卡死，移除後正式站仍卡——因為 `type="number"` 的 badInput（本機資料乾淨沒事、正式站某筆 ratio 值觸發）。最終改 `type="text" inputmode="decimal"` 才根治。

> [!WARNING]
> 這是「本機正常、正式環境不能存檔」的典型陷阱：同一份 template，差別只在**資料**。本機那筆數字乾淨、正式站那筆觸發 badInput，於是只有正式站靜默卡死。看到「本機好、線上壞」別只懷疑部署/快取，先用 Console 看是不是資料讓某欄位 invalid。

> [!NOTE]
> 若真的需要限制範圍，改用 JS（`@input` 內 clamp）或後端驗證，不要用會阻擋 submit 的原生 HTML 驗證。

---

### 症狀 2：欄位沒有樣式（輸入框很小或沒有邊框）

**原因：** `forms.py` 的 widget 未設定 Tailwind class。

**修正（在 forms.py 設定，不要在 template 寫 HTML）：**
```python
widgets = {
    'name': forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'placeholder': '請輸入名稱'
    }),
    'status': forms.Select(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
    }),
    'date_field': forms.DateInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'type': 'date'  # ← 必須加，否則不會顯示日期選擇器
    }),
}
```

> [!CAUTION]
> 不要在 template 手動寫 `<input type="text" name="..." value="...">` — 這種方式在 validation error 時不會保留使用者輸入值，而且容易出錯。

---

### 症狀 3：日期欄位顯示文字輸入框而非日期選擇器

**修正：** `forms.py` 的 `DateInput` 必須加 `'type': 'date'`：
```python
'date_field': forms.DateInput(attrs={
    'class': '...',
    'type': 'date'  # ← 這行不能省略
})
```

---

### 症狀 4：工具列按鈕（儲存/刪除/複製）不出現

**診斷步驟：**
1. 確認 template 有 `{% extends 'components/form_view.html' %}`
2. 確認 View 有繼承對應的 Mixin：

| 功能 | Mixin | Import |
|------|-------|--------|
| 複製記錄 | `CopyMixin` | `from core.mixins import CopyMixin` |
| 上一筆/下一筆 | `PrevNextMixin` | `from core.mixins import PrevNextMixin` |
| 自動傳票 | 見 auto_posting_voucher skill | — |

---

### 症狀 5：上一筆/下一筆導航錯誤

**診斷步驟：**
確認 UpdateView 有設定 `prev_next_order_field`：
```python
class MyUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = MyModel
    prev_next_order_field = 'created_at'  # ← 依哪個欄位排序導航
```

---

### 症狀 6：Sidebar (文件/Email/Line) 被截斷或不出現

**修正：** 確認 sidebars 放在 `{% block overlays %}`，而非 `{% block content %}`：
```html
{% block overlays %}
{% include "components/document_sidebar.html" %}
{% include "components/email_sidebar.html" %}
{% include "components/line_sidebar.html" %}
{% endblock %}
```

---

### 症狀 7：Template 中出現 `{{ }}` 字面字串（未被解析）

**請參考 skill：** `troubleshoot_template_raw_tags`

常見原因：Alpine.js 的 `x-data` 內有雙大括號，與 Django template 語法衝突。

---

### 症狀 7.5：彈窗 / 遮罩一打開「整個畫面變成不透明灰色」（背景沒有半透明）

**根本原因：用了 Tailwind v3 的 `bg-opacity-*` / `*-opacity-*`，但本專案編出來的是 Tailwind v4，這些 utility 已被移除 → 透明度靜默失效，遮罩變成純色蓋滿全畫面。**

本專案 `theme/static/css/dist/styles.css` 是 **Tailwind v4**。v4 已**移除** `bg-opacity-*`、`text-opacity-*`、`border-opacity-*`、`ring-opacity-*` 這些獨立的透明度 utility，改用「斜線語法」表達透明度。

**錯誤寫法（v3，v4 編不出來 → 失效）：**
```html
<div class="fixed inset-0 bg-gray-500 bg-opacity-75"></div>
<!-- bg-gray-500 生效=純灰、bg-opacity-75 是空 class → 整片不透明灰 -->
```

**正確寫法（v4 斜線透明度）：**
```html
<div class="fixed inset-0 bg-gray-500/75"></div>
<!-- 或對齊專案既有彈窗 modal_select.html / document_modal.html 的 bg-slate-900/60 -->
```

**診斷（決定性）：** 直接 grep 編譯後 CSS 確認該 class 根本沒被編出來：
```bash
grep -c "bg-opacity-75" theme/static/css/dist/styles.css   # → 0 代表這個 class 不存在
```

> [!WARNING]
> 這屬於「Tailwind 新/改的 class 靜默失效」家族雷：class 名稱沒報錯、頁面也不會壞，只是樣式默默不套用。新刻彈窗/遮罩時，透明度一律用 `顏色/數字`（如 `bg-slate-900/60`），**禁止再用 `bg-opacity-*` 等 v3 寫法**。實例：股東名簿「董監事名單」Tab 的搜尋彈窗 `shareholder_search_modal.html`，遮罩用 `bg-opacity-75` 導致一開彈窗整頁變不透明灰。

---

### 症狀 7.6：彈窗「看得到卻點不到 / 一點就關 / 內容被遮罩蓋住」

**根本原因：遮罩（`position:fixed`）疊在面板（`position:static`）之上 —— 面板少了 `relative`。**

CSS 疊放規則：**同一個 stacking context 裡，定位元素（`fixed`/`absolute`/`relative`）會畫在非定位元素（`static`）之上**。常見的錯誤結構是「遮罩與面板互為**兄弟**」：

```html
<div class="flex ...">
    <div class="fixed inset-0 bg-slate-900/60" @click="open=false"></div>  <!-- 遮罩：fixed=定位 -->
    <div class="inline-block bg-white ...">  <!-- 面板：static，沒有 relative → 被遮罩蓋住 -->
```

面板雖然 DOM 在後面，但因為它是 `static`、遮罩是 `fixed`，遮罩照樣畫在面板上面。結果：

- 遮罩不透明 → 面板被整片蓋住（看起來像「整頁變色、沒跳出內容」）。
- 遮罩半透明 → 面板**看得到**（自動 focus 還能打字），但**點擊全被上層遮罩吃掉** → 點按鈕沒反應、或點一下就觸發遮罩的 `@click` 關閉彈窗。

**修正：給面板加 `relative z-10`**（讓它變定位元素並疊上去）：
```html
<div class="relative z-10 inline-block bg-white ...">
```
或改成「面板是遮罩的**子元素**」的結構（子元素天生畫在父層之上，如 `modal_select.html` / `document_modal.html`）。

> [!WARNING]
> 這雷的迷惑點：彈窗「明明有開、也看得到」，所以會誤判成 JS／事件／選擇器問題，一路往那邊修都修不好。判斷口訣：**「看得到卻點不到」八成是 stacking，先檢查面板有沒有 `relative z-10`、遮罩是不是 `fixed` 的兄弟。** 實例：`shareholder_search_modal.html` 面板缺 `relative`，點搜尋結果一律點到遮罩，事件從未觸發。

---

### 症狀 8：表單儲存後跳轉離開 (希望停留在表單繼續編輯)

**修正：**
若希望表單儲存後（新增或修改）停留在同一個物件的編輯頁面，需在 CreateView / UpdateView 覆寫 `get_success_url`：

```python
from django.urls import reverse_lazy
from django.contrib import messages

# CreateView 或 UpdateView
def get_success_url(self):
    messages.success(self.request, "儲存成功！")
    return reverse_lazy('your_app:your_model_update', kwargs={'pk': self.object.pk})
```

---

### 症狀 9：紀錄被永久刪除 (希望能做「軟性刪除」並保留於資料庫)

**診斷步驟：**
1. 確認 Model 有繼承 `core.models.BaseModel`（會自動獲得 `is_deleted` 欄位）。
2. 確認 DeleteView 有繼承 `core.mixins.SoftDeleteMixin`（而不是普通的 DeleteView）：
   ```python
   from core.mixins import SoftDeleteMixin
   class MyModelDeleteView(SoftDeleteMixin, DeleteView):
       model = MyModel
       # ...
   ```
3. 確認 ListView 的 `get_queryset` 有過濾掉已刪除項目：
   ```python
   def get_queryset(self):
       qs = super().get_queryset()
       if hasattr(self.model, 'is_deleted'):
           qs = qs.filter(is_deleted=False)
       return qs
   ```

---

### 症狀 11：Toolbar 缺少「回列表」按鈕

**修正：** 在 template 覆寫 `{% block toolbar_nav %}`，並保留 `{{ block.super }}`：
```html
{% block toolbar_nav %}
{{ block.super }}
<a href="{% url 'app:model_list' %}"
    class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-md text-sm font-bold border border-slate-300">回列表</a>
{% endblock %}
```

> [!CAUTION]
> `{{ block.super }}` 不能省略，否則會覆蓋掉 base template 原有的儲存/刪除等按鈕。

---

### 症狀 12：Form 存檔後跳回列表，而非留在表單

**原因：** View 直接設定 `success_url = reverse_lazy('..._list')`。

**修正：** CreateView 和 UpdateView 都改用 `get_success_url()` 導回自身的 update URL：
```python
# ❌ 錯誤
success_url = reverse_lazy('app:model_list')

# ✅ 正確：新增後導到 update，修改後留在同一頁
def get_success_url(self):
    messages.success(self.request, "儲存成功！")
    return reverse_lazy('app:model_update', kwargs={'pk': self.object.pk})
```

> [!NOTE]
> CreateView 和 UpdateView 都需要覆寫，新增完成後才會同樣停在表單，而非跳回列表。

---

### 症狀 10：找不到變更紀錄或右側側邊欄無紀錄 (History Logs)

**診斷步驟：**
1. 確認 Model 有繼承 `core.models.BaseModel`（會自動整合 `simple_history`），**或**直接在 Model 加上 `HistoricalRecords()`：
   ```python
   # 方法 A：繼承 BaseModel（同時獲得 is_deleted / created_at / updated_at）
   from core.models import BaseModel
   class MyModel(BaseModel):
       ...

   # 方法 B：只加 HistoricalRecords（不需要軟刪除等欄位時）
   from simple_history.models import HistoricalRecords
   class MyModel(models.Model):
       ...
       history = HistoricalRecords()
   ```
   加完之後必須執行 `makemigrations` + `migrate`，否則 DB 不會建立 historical table。

2. 前端介面：確認頁面 extends `components/form_view.html`。按鈕「顯示紀錄」預設會出現在表單右上角。

3. 後端 View：在 UpdateView 的 `get_context_data` 中，確認有查詢並回傳 `history` 變數：
   ```python
   def get_context_data(self, **kwargs):
       context = super().get_context_data(**kwargs)
       if self.object and hasattr(self.object, 'history'):
           history_list = []
           for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
               history_list.append({
                   'history_user': record.history_user,
                   'history_date': record.history_date,
                   'history_type': record.history_type,
                   'history_change_reason': record.history_change_reason or "資料變更",
               })
           context['history'] = history_list
       return context
   ```

> [!NOTE]
> Migration 之前已存在的資料不會有歷史紀錄，只有 migration 之後的新增/修改才會被追蹤，這是正常現象。

---

### 症狀 14：分頁無效，筆數超過 paginate_by 仍顯示全部 / 「每頁顯示」下拉無作用

**根本原因 A：`paginate_by` 設定太大**

若 `paginate_by = 20` 而資料只有 15 筆，全部在第一頁，分頁不會觸發。
請依實際需求調低 `paginate_by`（建議預設 10）：
```python
class MyListView(ListActionMixin, LoginRequiredMixin, ListView):
    paginate_by = 10
```

**根本原因 B：前端「每頁顯示」下拉未連接後端**

`list_view.html` 的下拉選單必須透過 `?per_page=` 參數觸發頁面重載，並由 `ListActionMixin.get_paginate_by()` 讀取。

確認 `core/mixins.py` 的 `ListActionMixin` 有下列方法：
```python
_ALLOWED_PAGE_SIZES = {10, 25, 50}

def get_paginate_by(self, queryset):
    per_page = self.request.GET.get('per_page')
    if per_page and per_page.isdigit() and int(per_page) in self._ALLOWED_PAGE_SIZES:
        return int(per_page)
    return super().get_paginate_by(queryset)

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    ...
    context['current_per_page'] = self.get_paginate_by(self.get_queryset())
    return context
```

確認 `list_view.html` 的 select 有 `onchange` 觸發跳轉：
```html
<select onchange="window.location.href='?per_page='+this.value">
    <option value="10" {% if current_per_page == 10 %}selected{% endif %}>10</option>
    <option value="25" {% if current_per_page == 25 %}selected{% endif %}>25</option>
    <option value="50" {% if current_per_page == 50 %}selected{% endif %}>50</option>
</select>
```

**根本原因 C：翻頁連結未帶 `per_page` 參數**

分頁連結需附帶 `&per_page=` 否則翻頁後會重置回預設值：
```html
<a href="?page={{ page_obj.next_page_number }}{% if current_per_page %}&per_page={{ current_per_page }}{% endif %}">下一頁</a>
```

**根本原因 D：`pagination_info` 未使用分頁變數**

各 list.html 若有覆寫 `{% block pagination_info %}`，應使用分頁感知的寫法：
```html
{% block pagination_info %}
{% if is_paginated %}
顯示第 {{ page_obj.start_index }} 到 {{ page_obj.end_index }} 筆，共 {{ paginator.count }} 筆資料
{% else %}
顯示第 1 到 {{ object_list|length }} 筆，共 {{ object_list|length }} 筆資料
{% endif %}
{% endblock %}
```

> [!NOTE]
> `list_view.html` 的 client-side 搜尋（Alpine.js `allItems`）是從當前頁的 `list-metadata` 讀取，
> 分頁後搜尋範圍僅為當前頁資料，這是已知限制。

---

### 症狀 13：軟性刪除無效（資料被永久刪除），即使已使用 SoftDeleteMixin

**根本原因：Django 4.0+ Breaking Change**

Django 4.0 以後，`DeleteView.post()` 不再呼叫 `delete()` 方法，而是改呼叫 `form_valid()`。
因此若 `SoftDeleteMixin` 覆寫的是 `delete()`，在 Django 4.0+ 中完全不會被執行，導致走回預設的 `super().delete()` 永久刪除。

**確認方式：**
```python
# ❌ Django 4.0+ 不再呼叫此方法
class SoftDeleteMixin:
    def delete(self, request, *args, **kwargs):
        self.object.is_deleted = True
        ...
```

**修正：** 覆寫 `form_valid()` 而非 `delete()`：
```python
# ✅ 正確寫法（適用 Django 4.0+）
from django.http import HttpResponseRedirect
from django.contrib import messages

class SoftDeleteMixin:
    def form_valid(self, _form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        if hasattr(self.object, 'is_deleted'):
            self.object.is_deleted = True
            self.object.save(update_fields=['is_deleted', 'updated_at'])
            messages.success(self.request, f"「{self.object}」已成功刪除（移至資源回收桶）。")
        else:
            messages.warning(self.request, f"「{self.object}」已永久刪除。")
            self.object.delete()
        return HttpResponseRedirect(success_url)
```

> [!IMPORTANT]
> 此修正必須在 `core/mixins.py` 的 `SoftDeleteMixin` 統一修改，不是在各個 View 個別修改。修改完後，所有繼承 `SoftDeleteMixin` 的 DeleteView 都會一起生效。

**檢查清單：**
1. `core/mixins.py` 的 `SoftDeleteMixin` 覆寫的是 `form_valid()`（不是 `delete()`）
2. DeleteView 已繼承 `SoftDeleteMixin`（且放在繼承順序的第一位）
3. Model 有 `is_deleted` 欄位（繼承 `BaseModel` 即可）

---

### 症狀 15：快速篩選只過濾當前頁，換頁後篩選消失

**根本原因：** `@click="filter='XXX'"` + `x-show="matches(...)"` 只操作當頁已渲染的 `<tr>`，分頁後其他頁不受影響。

> [!IMPORTANT]
> **規範：只要 view 設定了 `paginate_by`，快速篩選一律用後端模式（`FilterMixin`），不使用 Alpine.js 前端篩選。**

---

**修正：使用 `FilterMixin`（已在 `core/mixins.py` 定義）**

**Step 1 — `views.py` 加 `FilterMixin`，定義 `filter_choices`：**

```python
from core.mixins import FilterMixin, ListActionMixin, SearchMixin

# DB 欄位篩選（最常見）
class MyListView(FilterMixin, ListActionMixin, SearchMixin, LoginRequiredMixin, ListView):
    model = MyModel
    paginate_by = 25
    filter_choices = {
        'DRAFT':  {'status': 'DRAFT'},
        'POSTED': {'status': 'POSTED'},
    }

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
```

```python
# Python property 篩選（status 由計算得出，非 DB 欄位）
class MyListView(FilterMixin, ListActionMixin, SearchMixin, LoginRequiredMixin, ListView):
    filter_property = 'status'   # model property 名稱
    filter_choices = {
        '未收款':  {},
        '部分收款': {},
        '已結清':  {},
    }
```

`FilterMixin` 自動提供 context：
- `current_filter` — 目前選中的 filter 值（預設 `'ALL'`）
- `filter_counts` — dict，如 `{'ALL': 100, 'DRAFT': 30, 'POSTED': 70}`

**Step 2 — `list.html` 的 `{% block filters %}` 改成 `<a href>` 連結：**
```html
{% block filters %}
<a href="?filter=ALL{% if q %}&q={{ q }}{% endif %}{% if current_per_page %}&per_page={{ current_per_page }}{% endif %}"
   class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors
          {% if current_filter == 'ALL' %}bg-blue-600 text-white{% else %}text-slate-600 hover:bg-slate-100{% endif %}">
   全部 ({{ filter_counts.ALL }})</a>
<a href="?filter=DRAFT{% if q %}&q={{ q }}{% endif %}{% if current_per_page %}&per_page={{ current_per_page }}{% endif %}"
   class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors
          {% if current_filter == 'DRAFT' %}bg-blue-600 text-white{% else %}text-slate-600 hover:bg-slate-100{% endif %}">
   草稿 ({{ filter_counts.DRAFT }})</a>
{% endblock %}
```

**Step 3 — `list.html` 的 `<tr>` 移除 `x-show="matches(...)"`：**
```html
{# ❌ 移除 #}
x-show="matches('{{ item.status }}', '{{ item.name|escapejs }}')"
```

> [!NOTE]
> `list_view.html` 分頁連結已內建 `&filter={{ current_filter }}`，換頁自動保留篩選狀態。

> [!WARNING]
> `FilterMixin` 必須放在 MRO 最前面：`FilterMixin, ListActionMixin, SearchMixin, LoginRequiredMixin, ListView`

---

## 🔍 通用診斷流程

當不確定問題來源時，按以下順序排查：

```
1. 確認 URL 是否正確 (urls.py → NoReverseMatch?)
       ↓
2. 確認 View 是否正確 (views.py → TemplateDoesNotExist? ContextMissing?)
       ↓
3. 確認 Form 是否正確 (forms.py → ValidationError? Missing fields?)
       ↓
4. 確認 Template 是否正確 (html → Syntax error? Missing block?)
       ↓
5. 確認前端 JS (Browser console → Alpine error? JSON parse error?)
```

---

## 🔗 相關 Skills

- **新增 list view** → `standard_list_view` skill
- **新增 form view** → `standard_form_view` skill
- **自動產生傳票** → `auto_posting_voucher` skill
- **{{ }} 出現在頁面** → `troubleshoot_template_raw_tags` skill
