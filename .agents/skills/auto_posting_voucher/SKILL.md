---
name: Auto-Posting to Voucher
description: Instructions for implementing the automatic voucher generation (自動產生傳票) feature in any Django module.
---

# Auto-Posting to Voucher (自動產生傳票機制)

這份文件記錄了如何將「打勾確認後自動產生過帳傳票 (Voucher)」的機制，完美移植到其他 Django 模組（如：應付帳款 Payable、其他收支等）的標準實作流程。

## 系統架構概念
這個功能橫跨了前後端三個主要部分：
1. **Frontend Modal (AlpineJS)**: 負責在使用者點擊「過帳」前，即時抓取畫面資料（如：未收款餘額、各項收據/發票金額），動態產生傳票分錄預覽，並確保借貸平衡才允許送出。
2. **Frontend Form Submission**: 透過隱藏或已禁用的 `is_posted` Checkbox 來與 Django Form 互動。為避免被瀏覽器擋下，前端會透過 JS 強制勾選並呼叫原生的 `HTMLFormElement.prototype.submit.call(form)`，精準指定 `id="main-form"` 送出。
3. **Backend Form Validation (Django Views)**: 透過 `form.initial.get('is_posted')` 與 `form.cleaned_data.get('is_posted')` 比較，確保是真的一次「由 False 轉為 True」的狀態改變，然後在 `form_valid` 攔截，執行傳票生成功效。

## 實作步驟指南

### 步驟 1：後端 Django 視圖 (UpdateView) 的攔截設定
在處理表單的 `UpdateView` 中，覆寫 `form_valid` 函式，確保能接住前端送上來的狀態變更，並呼叫對應的生成邏輯。

```python
from django.db import transaction
from django.contrib import messages
from django.utils import timezone # 傳票日期務必需要 timezone

def form_valid(self, form):
    # 1. 偵測狀態變化 (必須從初始的 False 變成前端送來的 True)
    was_posted = form.initial.get('is_posted', False)
    is_posted_now = form.cleaned_data.get('is_posted', False)
    is_newly_posted = (not was_posted) and is_posted_now

    response = super().form_valid(form)

    # 2. 只有在此次真正被勾選過帳時，才產生傳票
    if is_newly_posted:
        try:
            with transaction.atomic():
                # 呼叫你為此模組撰寫的傳票生成腳本
                voucher = generate_voucher_for_module(self.object, self.request.user)
                if voucher:
                    messages.success(self.request, f"狀態已更新，並成功產生傳票：{voucher.voucher_no}")
                else:
                    messages.warning(self.request, "已過帳，但無金額可產生傳票分錄。")
        except ValueError as e:
            # 防呆：如果邏輯判斷(如金額不平)拋出例外，必須將 is_posted 退回 False
            self.object.is_posted = False
            self.object.save(update_fields=['is_posted'])
            messages.error(self.request, f"產生傳票失敗：{str(e)}。已取消過帳狀態。")
        except Exception as e:
            self.object.is_posted = False
            self.object.save(update_fields=['is_posted'])
            messages.error(self.request, f"產生傳票時發生系統錯誤：{str(e)}")
    else:
        # 其他一般的更新儲存提示
        if is_posted_now:
            messages.success(self.request, "資料已更新，狀態維持過帳 (未拋轉新傳票)")
        else:
            messages.success(self.request, "資料已更新 (未過帳)")
            
    return response
```

### 步驟 2：後端傳票生成邏輯 (Service Function)
你需要實作一個如 `generate_voucher_for_module` 的函式，概念與 `receivable.py` 中的相同：
1. **檢查餘額**：如應收帳款若還有未收款，應拋出 `ValueError("尚有未收款項，無法過帳")`。
2. **準備傳票 (Voucher)**：建立主表，填入時間 (`timezone.now().date()`)、製單人 (`user`)。
3. **生成分錄 (VoucherDetail)**：根據該模組的收款或付款明細，分別生成 `debit` (藉方) 與 `credit` (貸方) 的明細資料。
4. **驗證平衡**：在全部存入前，統計藉貸雙方總額是否相等。若不相符，透過 `raise ValueError("分錄借貸不平")` 阻擋（此例外會被 `form_valid` 捕捉並還原過帳狀態）。

### 步驟 3：前端傳票預覽 Modal (AlpineJS)
前端必須準備一個預覽 Modal，給使用者在正式送出前確認。參考 `voucher_preview_modal.html` 的核心重點：

1. **防呆驗證**：在開啟前驗證欄位（例如未收款是否歸零 `hasOutstandingBalance`），如果不為 0 則不允許點擊「確定」。
2. **精準抓取表單與核取方塊**：
   因為 HTML 渲染與 Tailwind / AlpineJS 的屬性衝突，**絕對不要在 Alpine 的 `x-data` 內使用雙引號 `""` 包含 Javascript 字串**，一律使用單引號 `''`。

```javascript
/* === 前端自動送出邏輯的防呆重點 === */
confirmPost() {
    // 1. 擋下不平的借貸
    if (!this.isBalanced) { alert('借貸不平！'); return; }

    // 2. 嚴格鎖定勾選框（即便被設為 readonly 或是隱藏）
    const postedCheckbox = document.querySelector('input[name=\'is_posted\'][type=\'checkbox\']');
    if (postedCheckbox) {
        postedCheckbox.checked = true;
    } else {
        alert('找不到過帳勾選框'); return;
    }
    
    // 3. 嚴格鎖定送出對象 (避免抓到例如 Navbar 上的 Logout form)
    let form = document.getElementById('main-form');
    if (!form) {
         // fallback 策略：找一個必定在此表單內的專屬欄位
         const anyField = document.querySelector('input[name=\'specific_field_name\']');
         if (anyField && anyField.form) form = anyField.form;
    }

    if (form) {
        // 4. 強制送出表單，規避瀏覽器的 event listener 攔截
        setTimeout(() => { HTMLFormElement.prototype.submit.call(form); }, 100);
    }
}
```

### 步驟 4：開發時常見的地雷與解法 (Troubleshooting)
- **`NameError: name 'timezone' is not defined`**: 在 `views.py` 或 `services.py` 處理日期時，務必確保檔案頂部有 `from django.utils import timezone`。
- **前端 `isOpen is not defined` 或無法執行操作**: 檢查 `x-data="{...}"` 中是否有出現未轉義的雙引號 `"..."` 把 HTML 屬性截斷了。
- **前端 `Unexpected Token }` 錯誤**: 當你在 `x-data` 中使用雙斜線 `//` 單行註解時，若被 HTML 壓縮工具移除換行，會變成整段程式碼被註解掉。**因此在 `x-data` 中務必使用 `/* ... */` 區塊註解。**
- **Django Form 沒有收到 True**: 如果前端設定了 `disabled` 屬性，瀏覽器在 submit 時會忽略它！請確認在 HTML 模板中 `is_posted` 這個 checkbox 或相關屬性是可以正常跟隨 Form 遞交的 (可給 `pointer-events-none` 或 hidden input 替代)。
