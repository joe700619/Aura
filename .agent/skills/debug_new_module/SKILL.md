---
name: debug_new_module
description: 新增模組後的完整檢查清單，涵蓋 views、templates、forms、urls、models 常見遺漏項目
---

# Debug: New Module Checklist

新增或修改模組後，依序逐一核對以下清單。

---

## ✅ Views (`views.py`)

### CreateView
- [ ] **沒有** `success_url = reverse_lazy('..._list')` — 改用 `get_success_url()` 導回 update 頁
  ```python
  def get_success_url(self):
      return reverse_lazy('app:model_update', kwargs={'pk': self.object.pk})
  ```

### UpdateView
- [ ] **沒有** `success_url = reverse_lazy('..._list')` — 同上改用 `get_success_url()`
- [ ] `get_context_data` 有傳入 `history` 給 template（讓右側變更紀錄 sidebar 正常顯示）：
  ```python
  if hasattr(self.object, 'history'):
      history_list = []
      for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
          history_list.append({
              'history_user': record.history_user,
              'history_date': record.history_date,
              'history_type': record.history_type,
              'history_change_reason': record.history_change_reason or '資料變更',
          })
      context['history'] = history_list
  ```

### ListView
- [ ] `get_context_data` 有設定 `context['model_name']` 和 `context['model_app_label']`（Excel 下載需要）

---

## ✅ Templates

### `form.html`
- [ ] 有 `{% block form_attributes %}enctype="multipart/form-data"{% endblock %}` — 凡有 `FileField` 或 `ImageField` 必須加
- [ ] 使用正確的 block 覆寫，不要使用不存在的 block 名稱（`form_content` 不存在！）

  **`form_view.html` 提供的可覆寫 blocks：**
  | Block | 用途 |
  |-------|------|
  | `form_attributes` | form tag 的屬性（enctype 等） |
  | `form_top_block` | 三欄卡片區域 |
  | `form_card_1` / `_2` / `_3` | 三個欄位卡片 |
  | `form_bottom_block` | 備註等底部區域 |
  | `form_tabs` | Tab 區塊 |
  | `toolbar_nav` | 工具列右側（上一筆/下一筆/回列表） |
  | `toolbar_actions` | 工具列左側（新增/複製/刪除/儲存） |
  | `extra_js` | 額外 JS |

### `list.html`
- [ ] 有 `{% block overlays %}{% include "components/export_modal.html" %}{% endblock %}` — Excel 下載按鈕需要

### `confirm_delete.html`
- [ ] **繼承 `base.html`**，不是 `form_view.html`
- [ ] 使用 `{% block content %}`，不是 `{% block form_content %}`（此 block 不存在！）

---

## ✅ Forms (`forms.py`)

- [ ] 所有 `DateField` widget 有設 `'type': 'date'`，否則不顯示日期選擇器
- [ ] 所有 `DateTimeField` widget 有設 `'type': 'datetime-local'`
- [ ] FileInput / ImageField 不套一般 Tailwind class（要用 `file:` prefix 的 class）

---

## ✅ Models (`models.py`)

- [ ] `upload_to` 使用統一格式：`{app}/{model}/{YYYY}/{MM}/`
  例：`'administrative/irs_audit_notices/%Y/%m/'`
- [ ] 若有 `FileField` / `ImageField`，確認 `settings.py` 有設定：
  ```python
  MEDIA_ROOT = BASE_DIR / 'media'
  MEDIA_URL = '/media/'
  ```

---

## ✅ URLs (`urls.py`)

- [ ] Approval 相關 URL name 格式為 `{modelname}_submit_approval`（modelname 為小寫無底線，如 `irsauditnotice`）
- [ ] 確認所有 View 都有對應的 URL pattern

---

## ✅ 常見錯誤對照表

| 症狀 | 根因 | 修正 |
|------|------|------|
| 儲存按鈕卡圈圈無法再按 | `form_view.html` 的 `@click` 在 HTML5 驗證失敗時仍設了 `globalSubmitting = true` | `@click` 只呼叫 `requestSubmit()`，`globalSubmitting = true` 只在 `@submit` 設定 |
| 附件上傳沒有作用 | form 缺少 `enctype="multipart/form-data"` | 加 `{% block form_attributes %}enctype="multipart/form-data"{% endblock %}` |
| 刪除確認頁面空白/亂碼 | `confirm_delete.html` 繼承 `form_view.html` 並用了不存在的 `{% block form_content %}` | 改繼承 `base.html`，用 `{% block content %}` |
| Excel 下載按鈕無作用 | `list.html` 缺少 export modal | 加 `{% block overlays %}{% include "components/export_modal.html" %}{% endblock %}` |
| 儲存後跳回列表 | View 設了 `success_url = reverse_lazy('..._list')` | 改用 `get_success_url()` 回 update 頁 |
| 右側紀錄 sidebar 永遠空白 | UpdateView 未傳 `history` 到 context | 在 `get_context_data` 查詢 `self.object.history` 並放入 context |
| 日期欄位顯示文字輸入框 | `DateInput` widget 缺少 `'type': 'date'` | 在 `forms.py` 的 widget attrs 加 `'type': 'date'` |
