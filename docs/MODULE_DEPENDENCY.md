# Module 依賴規範

> 用途：避免新增 model / 新功能時造成跨 module 循環依賴、隱藏耦合。
> 適用對象：所有 PR 提交前必看；新增 model 時必看（搭配 `.agent/skills/add_new_model/`）。

---

## 1. 依賴分層

```
┌─────────────────────────────────────────────┐
│   入口層（向下依賴業務 module 是合理的）          │
│   • client_portal                           │
│   • public_site                             │
│   • blog                                    │
└────────────┬────────────────────────────────┘
             │ 可依賴
             ▼
┌─────────────────────────────────────────────┐
│   業務 module（彼此互不直接依賴 model）         │
│   • bookkeeping                             │
│   • case_management                         │
│   • internal_accounting                     │
│   • administrative                          │
│   • registration                            │
│   • payment                                 │
│   • hr                                      │
└────────────┬────────────────────────────────┘
             │ 可依賴
             ▼
┌─────────────────────────────────────────────┐
│   共用層                                     │
│   • basic_data（Customer/Contact/ServiceItem）│
│   • workflow（ApprovalRequest + services）    │
│   • system_config（MenuItem/SystemParameter） │
└────────────┬────────────────────────────────┘
             │ 可依賴
             ▼
┌─────────────────────────────────────────────┐
│   底層基礎建設                                │
│   • core（auth/audit/notifications/services）│
│   • shared                                   │
└─────────────────────────────────────────────┘
```

**規則：**
- 箭頭方向是允許的依賴方向
- 同層之間原則上**不直接依賴 model**
- 反向依賴（下層 → 上層）一律禁止

---

## 2. 跨 module 引用規則

### 2.1 Model 之間的 FK / GenericRelation

**一律使用 string reference**：

✅ 正確
```python
customer = models.ForeignKey('basic_data.Customer', on_delete=models.PROTECT)
approvals = GenericRelation('workflow.ApprovalRequest', related_query_name='client_assessment')
```

❌ 錯誤
```python
from modules.basic_data.models import Customer
customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
```

理由：避免循環 import、加快 Django 啟動、讓依賴關係只在 migration 看得到。

### 2.2 業務 module 之間取資料

**禁止**：直接 `from modules.X.models import Y` 然後操作 `Y.objects.filter(...)`

**建議**：透過 `core/services/` 或目標 module 的 `services.py` 提供函式

✅ 正確
```python
# bookkeeping 想取 hr.Employee 資料
from modules.hr.services.employee_service import get_active_employees
employees = get_active_employees()
```

❌ 錯誤
```python
from modules.hr.models import Employee
employees = Employee.objects.filter(is_active=True)
```

### 2.3 Service 函式可以跨 module 呼叫

`xxx.services` 是模組對外的 API。允許其他模組呼叫：

✅ 正確
```python
from modules.workflow.services import create_approval_request
from modules.internal_accounting.services import ReceivableTransferService
```

---

## 3. 既有依賴狀況（2026-05-07 盤點）

### 3.1 已合規的依賴
- 多處業務 module → `workflow.services`（service call）
- 多處業務 module → `basic_data.Customer`（共用基礎資料）
- `client_portal/views/*` → `bookkeeping.models.*`（入口層 → 業務層）

### 3.2 已修正
- `bookkeeping/models/bookkeeping_client.py`：FK to Customer 改 string ref
- `registration/models/client_assessment.py`：GenericRelation to ApprovalRequest 改 string
- `administrative/models/document_dispatch.py`、`document_receipt.py`、`irs_audit_notice.py`：FK to Customer 改 string

### 3.3 待後續批次處理（合併進批次 2 修復 N+1 時一起改）
- `case_management/views/api.py` 與 `case_management/forms.py` → `bookkeeping.BookkeepingClient`
- `bookkeeping/views/vat_views.py` → `internal_accounting.Receivable`
- `bookkeeping/views/bill_views.py` → `administrative.AdvancePaymentDetail`
- `bookkeeping/admin.py`、`bookkeeping/views/bookkeeping_client.py` → `hr.Employee`
- `internal_accounting/views/fee_apportion_report.py` → `hr.Employee`
- `bookkeeping/views/service_remuneration_tax_rate.py` → `client_portal.forms_remuneration`（**方向錯誤**，待重構）

---

## 4. PR 提交前檢查

```bash
# 找跨 module 直接 import model 的地方
grep -rn "^from modules\." modules/ \
  | grep -v "from modules\.\(self_module\)\." \
  | grep -v "services" \
  | grep -v "mixins"
```

加進 `.agent/skills/code_review_checklist/` 的「跨 module 依賴」段落。

---

## 5. 例外申請

如果有合理理由必須跨 module 直接 import model（極少情況），需要：
1. 在 PR 描述中說明理由
2. 在程式碼註解寫 `# CROSS-MODULE-IMPORT: <理由>`
3. 評估是否該把目標 model 上提到 `core/` 或 `basic_data/`
