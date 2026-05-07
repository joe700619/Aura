---
name: create_standard_list_view
description: instructions for creating a standard list view using the shared component
---

# Create Standard List View

When the user asks to create a list view or table for a data model, use the `templates/components/list_view.html` base template. This ensures consistency across the application.

## Template Path
`templates/components/list_view.html`

## Standard Bulk Actions (Automatic)

The base template now includes **standard bulk action buttons** that appear automatically:

| Action | Visibility | Description |
|--------|-----------|-------------|
| **下載 Excel** | Always visible | Export selected rows to Excel |
| **寄出 Email** | Only if EmailTemplate exists in admin | Send bulk emails using templates |
| **傳送 Line** | Only if LineMessageTemplate exists in admin | Send bulk LINE messages using templates |

**IMPORTANT**: You do NOT need to define these buttons in child templates. They are provided by the base template and will work automatically when you use `ListActionMixin`.

## ListActionMixin (Required)

To enable standard bulk actions, your ListView MUST inherit from `ListActionMixin`:

```python
from core.mixins import ListActionMixin
from django.views.generic import ListView

class MyModelListView(ListActionMixin, ListView):
    model = MyModel
    template_name = 'myapp/list.html'
    context_object_name = 'objects'
```

**What it does:**
- Automatically adds `model_app_label`, `model_name`, and `model_class` to template context
- Enables the base template to check for available Email/Line templates
- Provides correct metadata for modal dispatches

## Standard Create Button (Automatic)

The base template now also provides a **standard Create button** that appears automatically when using `ListActionMixin`:

| Feature | Description |
|---------|-------------|
| **Auto URL** | Generates URL based on `{model_name}_create` pattern |
| **Custom Label** | Set via `create_button_label` attribute |
| **Default Label** | "新增資料" if not customized |
| **Position** | Top right, next to bulk action dropdown |

**Example:**
```python
class MyModelListView(ListActionMixin, ListView):
    model = MyModel
    create_button_label = '新增產品'  # Optional customization
```

If you don't set `create_button_label`, the button will show "新增資料".

## Usage Pattern

Create a new template file and extend the base component:

```html
{% extends 'components/list_view.html' %}

<!-- 1. Page & Header Info -->
{% block page_title %}Page Title{% endblock %}
{% block header_title %}Header Title{% endblock %}
{% block header_description %}Description{% endblock %}

<!-- 2. Custom Bulk Actions (OPTIONAL) -->
<!-- Only use this if you need ADDITIONAL actions beyond Excel/Email/Line -->
{% block custom_bulk_actions %}
<button type="button" @click="..." class="...">
    客戶專屬功能
</button>
{% endblock %}

<!-- 3. Primary Actions (Top Right) -->
{% block actions %}
    <a href="{% url 'model_create' %}" class="bg-blue-600 ...">新增資料</a>
{% endblock %}

<!-- 4. Data Initialization -->
{% block content %}
<script id="list-metadata" type="application/json">
[
    {% for obj in object_list %}
    {
        "id": {{ obj.pk }},
        "category": "{{ obj.category_field|escapejs }}",
        "content": "{{ obj.name|escapejs }}"
    }{% if not forloop.last %},{% endif %}
    {% endfor %}
]
</script>
{{ block.super }}
{% endblock %}

<!-- 5. Filters -->
{% block filters %}
    <button @click="filter = 'TYPE_A'" :class="filter === 'TYPE_A' ? 'bg-blue-600 text-white' : '...'">Type A</button>
    <button @click="filter = 'ALL'" :class="filter === 'ALL' ? 'bg-blue-600 text-white' : '...'">All</button>
{% endblock %}

<!-- 6. Table Headers -->
{% block table_headers %}
    <th>Name</th>
    <th>Status</th>
    <th>Actions</th>
{% endblock %}

<!-- 7. Table Rows -->
{% block table_rows %}
    {% for obj in object_list %}
    <tr x-show="matches('{{ obj.category|escapejs }}', '{{ obj.name|escapejs }}')" 
        :class="selectedRows.includes({{ obj.pk }}) ? 'bg-blue-50/30' : ''">
        <td class="px-6 py-4">
             <label class="...">
                <input type="checkbox" value="{{ obj.pk }}" x-model.number="selectedRows" class="sr-only">
                <!-- Custom checkbox UI -->
            </label>
        </td>
        <td>{{ obj.name }}</td>
        <td>{{ obj.status }}</td>
        <td>
            <a href="{% url 'model_update' obj.pk %}">Edit</a>
        </td>
    </tr>
    {% empty %}
    <tr><td colspan="...">No data found</td></tr>
    {% endfor %}
{% endblock %}

<!-- 8. Overlays (Sidebars/Modals) -->
{% block overlays %}
{% include "components/export_modal.html" %}
{% include "components/email_sidebar.html" %}
{% include "components/line_sidebar.html" %}
{% endblock %}
```

## Overlays & Sidebars

When using sidebars (like `email_sidebar.html`) or modals, place them in the `overlays` block to ensure proper rendering at page bottom, avoiding `overflow: hidden` restrictions.

**Base template support:** `list_view.html` includes `{% block overlays %}{% endblock %}`.

**Sidebar requirements:**
- Unique ID on root element (e.g., `id="email-sidebar"`)
- Inner `fixed` container with explicit `position: fixed` style
- Use Tailwind classes `fixed inset-y-0 right-0` for slide-out effect

## Delete Behavior

**Soft Delete**: All delete actions should perform a soft delete (mark as inactive/deleted). Records must be recoverable via Django Admin.

## Key Points

1. **Automatic Actions**: Excel, Email, and Line buttons are automatic - DO NOT redefine them
2. **ListActionMixin Required**: Always inherit from `ListActionMixin` in your ListView
3. **Visibility Logic**: Email and Line buttons only show if admin has configured templates
4. **Selected Rows**: Use `selectedRows` array for accessing selected item IDs
5. **Filtering Works**: `toggleAll()` only selects rows matching current filter + search

---

## ✅ Implementation Checklist

Use this checklist when creating a new list view to ensure all critical components are included:

### Required Blocks (MUST IMPLEMENT)
- [ ] `{% extends 'components/list_view.html' %}`
- [ ] `{% block page_title %}` - Browser tab title
- [ ] `{% block header_title %}` - Page header text
- [ ] `{% block header_description %}` - Subtitle/description
- [ ] `{% block content %}` - **MUST include list-metadata script**
- [ ] `{% block table_headers %}` - Table column headers
- [ ] `{% block table_rows %}` - Table data rows
- [ ] `{% block overlays %}` - Email/Line sidebars

### list-metadata Requirements
- [ ] Script tag with `id="list-metadata"`
- [ ] Valid JSON array format
- [ ] Each object has `id`, `category`, `content` fields
- [ ] Use `|escapejs` filter on all string fields
- [ ] Include `{{ block.super }}` after script

### Checkbox Binding
- [ ] Use `x-model.number="selectedRows"` (not just `x-model`)
- [ ] Value attribute: `value="{{ obj.pk }}"`
- [ ] Class binding for visual feedback

### View Class (views.py)
- [ ] Inherit from `ListActionMixin`
- [ ] Set `model` attribute
- [ ] Set `template_name` attribute
- [ ] Set `context_object_name` attribute
- [ ] (Optional) Set `create_button_label`

---

## ⚠️ Common Mistakes & Fixes

### 1. ❌ Forgot list-metadata → Select All doesn't work
**Symptom:** Clicking header checkbox doesn't select any rows

**Wrong:**
```html
{% block content %}
{{ block.super }}
{% endblock %}
```

**Correct:**
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

### 2. ❌ Checkbox without .number → Can't select rows
**Symptom:** Individual checkboxes don't work

**Wrong:**
```html
<input type="checkbox" value="{{ obj.pk }}" x-model="selectedRows">
```

**Correct:**
```html
<input type="checkbox" value="{{ obj.pk }}" x-model.number="selectedRows">
```

### 3. ❌ Wrong block name for overlays
**Symptom:** Email/Line options don't appear in dropdown, or page is blank

**Wrong:**
```html
{% block content %}
{% include "components/email_sidebar.html" %}
{% endblock %}
```

**Correct:**
```html
{% block overlays %}
{% include "components/email_sidebar.html" %}
{% include "components/line_sidebar.html" %}
{% endblock %}
```

### 4. ❌ Forgot escapejs filter → JSON parse error
**Symptom:** Console error, select all doesn't work

**Wrong:**
```json
"content": "{{ obj.name }}"
```

**Correct:**
```json
"content": "{{ obj.name|escapejs }}"
```

### 5. ❌ Not using ListActionMixin → Model metadata missing
**Symptom:** Email/Line buttons never appear, even with templates configured

**Wrong:**
```python
class MyListView(LoginRequiredMixin, ListView):
    model = MyModel
```

**Correct:**
```python
class MyListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = MyModel
```

---

## 📋 Complete Working Example

### Template: `myapp/templates/myapp/product_list.html`

```html
{% extends 'components/list_view.html' %}

{% block page_title %}產品列表{% endblock %}
{% block header_title %}產品管理{% endblock %}
{% block header_description %}管理所有產品資料{% endblock %}

{% block content %}
<script id="list-metadata" type="application/json">
[
    {% for product in products %}
    {
        "id": {{ product.pk }},
        "category": "{{ product.category|escapejs }}",
        "content": "{{ product.name|escapejs }} {{ product.sku|default:''|escapejs }}"
    }{% if not forloop.last %},{% endif %}
    {% endfor %}
]
</script>
{{ block.super }}
{% endblock %}

{% block filters %}
<button @click="filter = 'ELECTRONICS'" 
    :class="filter === 'ELECTRONICS' ? 'bg-blue-600 text-white' : 'text-slate-600'"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors">電子產品</button>
<button @click="filter = 'FOOD'" 
    :class="filter === 'FOOD' ? 'bg-blue-600 text-white' : 'text-slate-600'"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors">食品</button>
<button @click="filter = 'ALL'" 
    :class="filter === 'ALL' ? 'bg-blue-600 text-white' : 'text-slate-600'"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors">全部</button>
{% endblock %}

{% block table_headers %}
<th scope="col" class="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">產品名稱</th>
<th scope="col" class="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">SKU</th>
<th scope="col" class="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">分類</th>
<th scope="col" class="px-4 py-4 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">操作</th>
{% endblock %}

{% block table_rows %}
{% for product in products %}
<tr class="hover:bg-slate-50 transition duration-150"
    x-show="matches('{{ product.category|escapejs }}', '{{ product.name|escapejs }} {{ product.sku|default:''|escapejs }}')"
    :class="selectedRows.includes({{ product.pk }}) ? 'bg-blue-50/30' : ''">
    <td class="px-6 py-4 whitespace-nowrap">
        <label class="relative flex cursor-pointer select-none items-center">
            <input type="checkbox" class="sr-only" value="{{ product.pk }}" x-model.number="selectedRows">
            <div :class="selectedRows.includes({{ product.pk }}) ? 'bg-blue-600 border-blue-600' : 'bg-white border-slate-300'"
                class="flex h-5 w-5 items-center justify-center rounded border transition-colors shadow-sm">
                <template x-if="selectedRows.includes({{ product.pk }})">
                    <svg class="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                    </svg>
                </template>
            </div>
        </label>
    </td>
    <td class="px-4 py-4">{{ product.name }}</td>
    <td class="px-4 py-4 text-slate-500">{{ product.sku|default:"-" }}</td>
    <td class="px-4 py-4">
        <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">{{ product.get_category_display }}</span>
    </td>
    <td class="px-4 py-4 text-center">
        <a href="{% url 'product_update' product.pk %}" class="text-blue-600 hover:text-blue-800">編輯</a>
    </td>
</tr>
{% empty %}
<tr><td colspan="5" class="px-6 py-8 text-center text-slate-500">目前沒有產品資料</td></tr>
{% endfor %}
{% endblock %}

{% block overlays %}
{% include "components/export_modal.html" %}
{% include "components/email_sidebar.html" %}
{% include "components/line_sidebar.html" %}
{% endblock %}
```

### View: `myapp/views.py`

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from core.mixins import ListActionMixin
from .models import Product

class ProductListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = Product
    template_name = 'myapp/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    create_button_label = '新增產品'
```

---

## 🔍 Troubleshooting Guide

### Issue: Email/Line buttons don't appear
**Check:**
1. Did you inherit from `ListActionMixin` in views.py?
2. Have you configured Email/LineMessageTemplate in Django Admin?
3. Is the template's `model_content_type` field set correctly?

### Issue: Select All doesn't work
**Check:**
1. Does `list-metadata` script exist in `{% block content %}`?
2. Is the JSON format valid? (Check browser console)
3. Did you include `{{ block.super }}` after the script?

### Issue: Checkboxes can't be selected
**Check:**
1. Are you using `x-model.number="selectedRows"` (with `.number`)?
2. Is the value attribute correct: `value="{{ obj.pk }}"`?

### Issue: Page is blank or overlays don't work
**Check:**
1. Are sidebars in `{% block overlays %}` (not `content` or `actions`)?
2. Did you include all three: export_modal, email_sidebar, line_sidebar?

### Issue: JSON parse error in console
**Check:**
1. Are you using `|escapejs` filter on all string fields?
2. Is the comma logic correct? `{% if not forloop.last %},{% endif %}`

---

## 📦 Template Scaffolds

For quick setup, use the template scaffolds in `templates/scaffolds/`:
- `list_view_template.html` - Complete list view template
- `list_view_views.py` - View class boilerplate

See the Implementation Plan artifact for details on using these scaffolds.
