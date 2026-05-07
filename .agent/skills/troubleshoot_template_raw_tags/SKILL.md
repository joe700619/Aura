---
name: Troubleshoot Django Template Raw Tags
description: Guide to troubleshooting and fixing raw Django template tags `{{ ... }}` appearing in rendered HTML.
---

# Troubleshooting Raw Django Template Tags

When Django template tags (e.g., `{{ variable }}`) appear literally in the browser instead of being rendered, it usually indicates a parsing failure in the template engine. This often happens in complex HTML attributes or when using certain frontend frameworks.

## 症状 (Symptoms)

*   頁面顯示 `{{ object.field }}` 或 `{{ value|filter }}` 等原始代碼，而不是變數的值。
*   通常發生在 HTML 屬性（如 `data-` 或 `x-data`）中，或者緊接在這些屬性後的標籤內容中。
*   `TemplateSyntaxError` **不會** 被拋出，頁面能載入但顯示錯誤。

## 常見原因 (Common Causes)

### 1. 複雜的行內屬性 (Complex Inline Attributes)
Django 模板解析器在處理長行或包含多個 `{{ ... }}` 的 HTML 屬性時，可能會失敗，特別是當這些屬性跨越多行或與 JavaScript 表達式混合時。

**錯誤範例 (Bad):**
```html
<tr x-show="matches('{{ obj.status|escapejs }}', '{{ obj.name|escapejs }} {{ obj.desc|escapejs }}')"
    data-content="{{ obj.field1 }} {{ obj.field2 }}">
    ...
</tr>
```

### 2. 屬性值中的引號衝突 (Quote Conflicts)
在 HTML 屬性中使用雙引號包圍，而 Django 變數內部已包含未轉義的引號，會破壞 HTML 結構。

## 解決方案 (Solutions)

### 1. 格式化與分行 (Formatting & Newlines)
將複雜的屬性分行書寫，並確保每個屬性都在獨立的一行。這有助於 Django 解析器正確識別邊界。

**修正範例 (Fix):**
```html
<tr 
    class="hover:bg-slate-50"
    data-category="{{ obj.status|escapejs }}"
    data-content="{{ obj.name|escapejs }} {{ obj.desc|escapejs }}"
    x-show="matches($el.dataset.category, $el.dataset.content)">
    ...
</tr>
```

### 2. 使用 `escapejs` 過濾器 (Use escapejs)
當變數用於 JavaScript 上下文或 HTML 屬性中時，務必使用 `|escapejs` 過濾器，防止特殊字符（如引號、換行）破壞結構。

```django
data-name="{{ employee.name|escapejs }}"
```

### 3. 使用 Data Attributes 解耦 (Decouple with Data Attributes)
避免在 `x-show` 或 `x-data` 等複雜指令中直接嵌入 Django 變數。改為將變數放入標準的 `data-*` 屬性，再由 JavaScript 讀取。

**錯誤範例 (Bad):**
```html
<div x-data="{ name: '{{ user.name }}' }">
```

**修正範例 (Fix):**
```html
<div x-data="{ name: $el.dataset.name }" data-name="{{ user.name|escapejs }}">
```

## 檢核清單 (Checklist)

1.  **檢查屬性格式**：是否有多個 `{{ ... }}` 擠在同一行？嘗試分行。
2.  **檢查轉義**：所有注入到 JS 或 HTML 屬性的變數是否都加了 `|escapejs`？
3.  **簡化邏輯**：將複雜的 Django 邏輯移出 HTML 標籤，改用 `data-` 屬性傳遞值。
4.  **驗證 HTML 結構**：檢查是否有未閉合的引號或標籤。

---
**Version**: 1.0
**Context**: Created after observing parsing failures in `list.html` where multi-line `tr` tags with complex `data-` attributes caused downstream `td` content to render as raw text.
