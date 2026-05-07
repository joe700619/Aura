---
description: Comprehensive guide to integrating the Standard Approval Workflow into any module, including troubleshooting common visibility and logic issues.
---

# Standard Approval Workflow Integration Guide

This guide details how to integrate the centralized approval workflow system into any Django app (e.g., HR, Purchase, Expense).

## 1. Model Integration

Add the following helper methods to your model (e.g., `Employee`, `PurchaseOrder`) to interact with the workflow system.

```python
from django.contrib.contenttypes.models import ContentType
from modules.workflow.models import ApprovalRequest

class MyModel(models.Model):
    # ... fields ...

    def get_approval_request(self):
        """
        Get the latest approval request regardless of status.
        CRITICAL: Do NOT filter by status='PENDING'. You must return
        APPROVED, REJECTED, and RETURNED requests so the UI can display
        the final state or history.
        """
        content_type = ContentType.objects.get_for_model(self)
        return ApprovalRequest.objects.filter(
            content_type=content_type,
            object_id=self.pk
        ).order_by('-request_date').first()

    def can_submit_for_approval(self):
        # Logic to check if a request can be submitted
        # e.g., no pending request exists
        req = self.get_approval_request()
        if req and req.status in ['PENDING']:
            return False
        return True

    def can_user_approve(self, user):
        req = self.get_approval_request()
        if not req:
            return False
        return req.can_user_approve(user)
```

## 2. View Integration

In your `UpdateView` or `DetailView`, ensure the approval request is added to the context.

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # 1. Get the request
    approval_request = self.object.get_approval_request()
    context['approval_request'] = approval_request
    
    # 2. Check permission for current user
    if approval_request:
        context['can_approve'] = self.object.can_user_approve(self.request.user)
    else:
        context['can_approve'] = False
        
    return context
```

## 3. Template Integration

### Form View (`form.html`)

You must verify the **Parent Template's Block Names**.
*   **Standard `form_view.html`** uses `{% block form_top_block %}`.
*   **DO NOT** use `{% block form_top %}` if the parent uses `_block`. Mismatched block names are the #1 cause of the progress bar not appearing.

```django
{% extends "components/form_view.html" %}

{# CRITICAL: Match the block name exactly! #}
{% block form_top_block %}
    {% if object %}
        {% include "components/approval/status.html" %}
    {% endif %}
    {{ block.super }}
{% endblock %}

{# Tabs for History #}
{% block form_tabs %}
    {# ... other tabs ... #}
    <button class="tab-btn" data-target="#approval-history">
        <i class="fas fa-history mr-2"></i>核准狀態
    </button>
{% endblock %}

{% block form_content %}
    {# ... form fields ... #}
    
    {# Approval History Content #}
    <div id="approval-history" class="tab-pane hidden">
        {% include "components/approval/history.html" %}
    </div>
{% endblock %}
```

---

## ⚠️ Troubleshooting & Common Pitfalls

### 1. Progress Bar Not Showing (進度條沒出現)

*   **Cause A: Block Name Mismatch**
    *   Check if you are using `{% block form_top %}` but the parent template defines `{% block form_top_block %}`.
    *   **Fix:** Rename your block to `form_top_block`.

*   **Cause B: Data Retrieval Logic**
    *   Check `get_approval_request()` in your `services.py` or model.
    *   **Fix:** Ensure it returns the request even if `status='APPROVED'`. If you filter `status='PENDING'`, the progress bar will vanish as soon as the workflow completes.

### 2. TemplateSyntaxError in `status.html`

*   **Cause:** Django template parser struggles with multi-line `{% if %}` tags or complex boolean logic with parentheses `()`.
*   **Fix:**
    *   **NEVER** use parentheses in Django `{% if %}` tags (e.g., `{% if (a and b) or c %}` is invalid).
    *   **Keep tags on one line.** Do not split `{% if ... %}` across multiple lines.
    *   **Use `{% with %}`** to shorten long variable names to help them fit on one line.
    
    *Bad:*
    ```django
    {% if approval_request.current_step and step.step_number <
          approval_request.current_step.step_number %}
    ```
    
    *Good:*
    ```django
    {% with cur=approval_request.current_step %}
    {% if cur and step.step_number < cur.step_number %}
    ...
    {% endif %}
    {% endwith %}
    ```

### 3. Invisible Progress Icons/Lines (CSS Issues)

*   **Cause:** Tailwind CSS classes (like `bg-green-500`, `w-10`, `h-10`) might not load or apply correctly in all contexts, especially if `include` is used dynamically.
*   **Fix:** Use **inline styles** with `!important` for critical visual elements (circles, lines).
    ```html
    <div style="background-color: #22c55e !important; width: 40px !important; height: 40px !important; ...">
       ✓
    </div>
    ```

### 4. Status Reset (退回後的狀態)

*   **Behavior:** When an approver clicks "Return" (`RETURNED` status):
    1.  The request status updates to `RETURNED`.
    2.  The "Progress Bar" should show the current state (often orange/red).
    3.  When the original applicant re-submits, the `submit_for_approval` service is called.
    4.  Logic should ideally **update the existing request** back to `PENDING` and reset the `current_step` to the first step, OR create a new request depending on audit requirements.
    *   *Current Implementation Default:* Updates existing request to track the lifecycle of *that specific submission attempt* unless configured otherwise.

### 5. Completed Status (最終核准)

*   **Behavior:** When the final approver approves:
    1.  Status becomes `APPROVED`.
    2.  `current_step` might be `None` or the last step.
    3.  **UI Logic:** The loop in `status.html` must explicitly handle `status == 'APPROVED'`.
    ```django
    {% if approval_request.status == 'APPROVED' %}
       <!-- Force Green Checkmark -->
    {% elif ... %}
    ```
