---
name: Standard Form View
description: Instructions for creating standard form views with proper widget configuration in forms.py and standardized toolbar
---

# Standard Form View Component

## Overview

The standard form view (`components/form_view.html`) provides a consistent user experience across all form pages with:
- **Standardized Toolbar**: Automatic buttons (Add, Copy, Delete, Cancel, Save, Action dropdown, Previous/Next, History Toggle)
- **Collapsible History Sidebar**: Shows related historical records
- **Three-section Layout**: Top block with 3 cards, bottom block for remarks, tabs section
- **Automatic Integration**: No need to define buttons manually, they're provided by the base template

---

## ⚠️ CRITICAL: Correct Approach for Field Styling

### ✅ CORRECT: Configure Widgets in forms.py

**All CSS styling should be configured in `forms.py`, NOT in templates.**

```python
# forms/employee.py
from django import forms
from ..models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'gender', 'id_number', 'email', 'hire_date', ...]
        
        # ✅ Configure widgets with Tailwind CSS classes HERE
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入員工姓名'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：employee@example.com'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
        }
```

**Then in template, simply use Django widgets:**

```django
{# templates/employee/form.html #}
{% block form_card_1 %}
<div class="space-y-4">
    <div class="flex items-center gap-2 border-b border-slate-100 pb-2 mb-2">
        <div class="w-1 h-4 bg-blue-600 rounded-full"></div>
        <h4 class="font-bold text-slate-800 text-sm">基本資料</h4>
    </div>
    
    {# Name Field #}
    <div>
        <label for="{{ form.name.id_for_label }}" class="block text-sm font-medium text-slate-700 mb-1">
            {{ form.name.label }} <span class="text-red-500">*</span>
        </label>
        {{ form.name }}  {# ← Widget with classes from forms.py #}
        {% if form.name.errors %}
        <p class="mt-1 text-sm text-red-600">{{ form.name.errors.0 }}</p>
        {% endif %}
    </div>
</div>
{% endblock %}
```

**Benefits:**
- ✅ CSS classes centralized in forms.py
- ✅ Django handles value binding, validation automatically
- ✅ Less error-prone (no template syntax issues)
- ✅ Easier to maintain and update styling
- ✅ Consistent across all forms

---

### ❌ WRONG: Manual HTML in Templates

**DO NOT write manual HTML inputs in templates:**

```django
{# ❌ DON'T DO THIS - Error-prone and hard to maintain #}
<input type="text" 
       name="{{ form.name.name }}" 
       value="{{ form.name.value|default:'' }}"
       class="w-full px-3 py-2 ..." />
```

**Problems with manual HTML:**
- Template syntax errors (`==` spacing issues, quote mismatches)
- Value binding breaks on validation errors
- No automatic error handling
- Hard to maintain
- Duplicated code across templates

---

## Standard Tailwind CSS Classes

### For All Input Fields

```python
'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
```

### Common Attributes

```python
widgets = {
    # Text Input
    'name': forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'placeholder': '請輸入姓名'
    }),
    
    # Select Dropdown
    'status': forms.Select(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
    }),
    
    # Email Input
    'email': forms.EmailInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'placeholder': '例：user@example.com'
    }),
    
    # Date Input
    'birth_date': forms.DateInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'type': 'date'
    }),
    
    # Textarea (single line)
    'address': forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'placeholder': '請輸入地址'
    }),
    
    # Textarea (multi-line) - if needed
    'notes': forms.Textarea(attrs={
        'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
        'rows': 3,
        'placeholder': '請輸入備註'
    }),
}
```

---

## Template Structure

### Required Template Extension

```django
{% extends 'components/form_view.html' %}
```

### Block Hierarchy

```
form_view.html
├── page_title (頁面標題)
├── toolbar_actions (工具列按鈕 - 通常不需要覆寫)
├── toolbar_nav (導航連結，如「回列表」)
├── form_top_block (預設3欄布局)
│   ├── form_card_1 (第一區塊)
│   ├── form_card_2 (第二區塊)
│   └── form_card_3 (第三區塊)
├── form_bottom_block (備註區)
├── form_tabs (tabs 區域)
│   ├── tabs_header
│   └── tabs_content
└── overlays (sidebars: document, email, line)
```

---

## Complete Example

### 1. Create Form in forms.py

```python
# modules/hr/forms/employee.py
from django import forms
from ..models import Employee

class EmployeeForm(forms.ModelForm):
    """員工表單"""
    
    class Meta:
        model = Employee
        fields = [
            'name', 'gender', 'id_number', 'line_id', 'extension',
            'phone', 'address', 'email',
            'employment_status', 'hire_date', 'resignation_date', 'team',
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '請輸入員工姓名'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：A123456789',
                'maxlength': '10'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': '例：employee@example.com'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm',
                'type': 'date'
            }),
            # ... other fields
        }
```

### 2. Create Template

```django
{# modules/hr/templates/employee/form.html #}
{% extends 'components/form_view.html' %}

{% block page_title %}
{% if object %}編輯員工 - {{ object.name }}{% else %}新增員工{% endif %}
{% endblock %}

{% block toolbar_nav %}
{{ block.super }}
<a href="{% url 'employee_list' %}"
    class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-md text-sm font-bold border border-slate-300">回列表</a>
{% endblock %}

{% block form_card_1 %}
<div class="space-y-4">
    {# Section Header #}
    <div class="flex items-center gap-2 border-b border-slate-100 pb-2 mb-2">
        <div class="w-1 h-4 bg-blue-600 rounded-full"></div>
        <h4 class="font-bold text-slate-800 text-sm">基本資料</h4>
    </div>
    
    {# Name Field #}
    <div>
        <label for="{{ form.name.id_for_label }}" class="block text-sm font-medium text-slate-700 mb-1">
            {{ form.name.label }} <span class="text-red-500">*</span>
        </label>
        {{ form.name }}
        {% if form.name.errors %}
        <p class="mt-1 text-sm text-red-600">{{ form.name.errors.0 }}</p>
        {% endif %}
    </div>
    
    {# Gender Field #}
    <div>
        <label for="{{ form.gender.id_for_label }}" class="block text-sm font-medium text-slate-700 mb-1">
            {{ form.gender.label }} <span class="text-red-500">*</span>
        </label>
        {{ form.gender }}
        {% if form.gender.errors %}
        <p class="mt-1 text-sm text-red-600">{{ form.gender.errors.0 }}</p>
        {% endif %}
    </div>
    
    {# More fields... #}
</div>
{% endblock %}

{% block form_card_2 %}
<div class="space-y-4">
    <div class="flex items-center gap-2 border-b border-slate-100 pb-2 mb-2">
        <div class="w-1 h-4 bg-green-600 rounded-full"></div>
        <h4 class="font-bold text-slate-800 text-sm">聯絡資訊</h4>
    </div>
    {# Fields... #}
</div>
{% endblock %}

{% block form_card_3 %}
<div class="space-y-4">
    <div class="flex items-center gap-2 border-b border-slate-100 pb-2 mb-2">
        <div class="w-1 h-4 bg-purple-600 rounded-full"></div>
        <h4 class="font-bold text-slate-800 text-sm">其他資訊</h4>
    </div>
    {# Fields... #}
</div>
{% endblock %}

{% block form_bottom_block %}
<div class="space-y-4">
    <div class="flex items-center gap-2 border-b border-slate-100 pb-2 mb-2">
        <div class="w-1 h-4 bg-slate-500 rounded-full"></div>
        <h4 class="font-bold text-slate-800 text-sm">備註</h4>
    </div>
    <div>
        <textarea name="notes" rows="3"
            class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="其他補充說明">{{ object.notes|default:'' }}</textarea>
    </div>
</div>
{% endblock %}

{% block form_tabs %}
{# Optional tabs section #}
{% endblock %}

{% block overlays %}
{% include "components/document_sidebar.html" %}
{% include "components/email_sidebar.html" %}
{% include "components/line_sidebar.html" %}
{% endblock %}
```

### 3. Create Views

```python
# modules/hr/views/employee.py
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from core.mixins import CopyMixin, PrevNextMixin
from ..models import Employee
from ..forms import EmployeeForm

class EmployeeCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/form.html'
    success_url = reverse_lazy('employee_list')

class EmployeeUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/form.html'
    success_url = reverse_lazy('employee_list')
    prev_next_order_field = 'employee_number'
```

---

## Field Rendering Pattern

### Standard Field Template

```django
<div>
    <label for="{{ form.field_name.id_for_label }}" class="block text-sm font-medium text-slate-700 mb-1">
        {{ form.field_name.label }}
        {% if form.field_name.field.required %}<span class="text-red-500">*</span>{% endif %}
    </label>
    {{ form.field_name }}
    {% if form.field_name.errors %}
    <p class="mt-1 text-sm text-red-600">{{ form.field_name.errors.0 }}</p>
    {% endif %}
</div>
```

### Readonly Field (Edit Mode Only)

```django
{% if object %}
<div>
    <label class="block text-sm font-medium text-slate-700 mb-1">員工編號</label>
    <input type="text" value="{{ object.employee_number }}" readonly
           class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-md text-slate-600 cursor-not-allowed text-sm" />
    <p class="mt-1 text-xs text-slate-500">系統自動產生</p>
</div>
{% endif %}
```

---

## Common Mistakes

### 1. ❌ Using Bootstrap Classes
```python
# WRONG - This project uses Tailwind, not Bootstrap
'class': 'form-control'
```
```python
# CORRECT
'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm'
```

### 2. ❌ Manual HTML in Template
```django
{# WRONG - Error-prone #}
<input type="text" name="{{ form.name.name }}" value="{{ form.name.value|default:'' }}" />
```
```django
{# CORRECT - Use widget #}
{{ form.name }}
```

### 3. ❌ Missing Widget Configuration
```python
# WRONG - No styling
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'email']
```
```python
# CORRECT - Configure widgets
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': '...'}),
            'email': forms.EmailInput(attrs={'class': '...'}),
        }
```

### 4. ❌ Forgetting Date Type
```python
# WRONG - Browser shows text input
'hire_date': forms.DateInput(attrs={'class': '...'})
```
```python
# CORRECT - Shows date picker
'hire_date': forms.DateInput(attrs={'class': '...', 'type': 'date'})
```

---

## Checklist

- [ ] Create Form in `forms.py` with **all widgets configured**
- [ ] Use **Tailwind classes** (not Bootstrap `form-control`)
- [ ] Extend `components/form_view.html` in template  
- [ ] Set `page_title` block
- [ ] Use `{{ form.field }}` in template (NOT manual HTML)
- [ ] Include label with red asterisk for required fields
- [ ] Add section headers with colored dots
- [ ] Implement `form_bottom_block` for remarks
- [ ] Add `toolbar_nav` with "回列表" link
- [ ] Include overlays block for sidebars
- [ ] Configure views with mixins (CopyMixin, PrevNextMixin)

---

## Reference Files

- **Base Template**: `templates/components/form_view.html`
- **Example Form**: `modules/hr/forms/employee.py`
- **Example Template**: `modules/hr/templates/employee/form.html`
- **Mixins**: `core/mixins.py`
