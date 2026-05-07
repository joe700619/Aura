---
name: multi_file_attachment_carousel
description: 為 Django 表單新增多檔案附件輪播 UI（Alpine.js + Tailwind），支援上傳、預覽、刪除，模仿 DocumentDispatch 發文系統的附件模式
---

# Multi-File Attachment Carousel

為 Django 表單新增多檔案附件功能，採用輪播（Carousel）UI。
支援：多檔上傳、圖片預覽、PDF/文件圖示、刪除暫存或已儲存附件。

---

## 架構概覽

```
MyModel (主模型)
    ↓ FK
MyModelAttachment (附件模型)
    - file: FileField(upload_to='...')
    - uploaded_at: DateTimeField(auto_now_add=True)
    + filename @property
    + is_image @property
```

---

## Step 1: 建立附件模型

在 `models/my_model.py` 末尾加上附件 class：

```python
import os
from django.db import models
from core.models import BaseModel  # 或 models.Model

class MyModelAttachment(models.Model):
    parent = models.ForeignKey(
        MyModel, on_delete=models.CASCADE,
        related_name='attachments', verbose_name="主紀錄"
    )
    file = models.FileField(
        upload_to='app_name/my_model/%Y/%m/',
        verbose_name="附件"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    class Meta:
        verbose_name = "附件"
        verbose_name_plural = "附件"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.parent} - {os.path.basename(self.file.name)}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_image(self):
        return self.file.name.lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'png', 'gif', 'webp')
```

在 `models/__init__.py` 加入 import 與 `__all__`：

```python
from .my_model import MyModel, MyModelAttachment
__all__ = [..., 'MyModelAttachment']
```

建立並執行 migration：

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Step 2: 更新 views.py

### CreateView

```python
from django.db import transaction
from django.shortcuts import redirect
from ..models import MyModel, MyModelAttachment

class MyModelCreateView(LoginRequiredMixin, CreateView):
    model = MyModel
    form_class = MyModelForm
    template_name = 'app/my_model/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = []  # 新增時沒有附件
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            for f in self.request.FILES.getlist('new_attachments'):
                MyModelAttachment.objects.create(parent=self.object, file=f)
        messages.success(self.request, '新增成功。')
        return redirect('app:my_model_update', pk=self.object.pk)
```

### UpdateView

```python
class MyModelUpdateView(LoginRequiredMixin, UpdateView):
    model = MyModel
    form_class = MyModelForm
    template_name = 'app/my_model/form.html'

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()

            # 刪除被標記的附件
            deleted_ids_str = self.request.POST.get('deleted_attachment_ids', '')
            if deleted_ids_str:
                id_list = [i.strip() for i in deleted_ids_str.split(',') if i.strip().isdigit()]
                if id_list:
                    MyModelAttachment.objects.filter(
                        id__in=id_list, parent=self.object
                    ).delete()

            # 新增上傳的附件
            for f in self.request.FILES.getlist('new_attachments'):
                MyModelAttachment.objects.create(parent=self.object, file=f)

        messages.success(self.request, '更新成功。')
        return redirect('app:my_model_update', pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context['attachments'] = self.object.attachments.all()
        return context
```

---

## Step 3: form.html — Alpine.js 輪播 UI

在 `{% block form_card_2 %}` 或適合的 block 內放入以下完整片段。

> ⚠️ **重要**: `enctype="multipart/form-data"` 必須設定，否則檔案不會上傳。
> 加在 form.html 最上方：`{% block form_attributes %}enctype="multipart/form-data"{% endblock %}`

### 3a. JSON 資料嵌入（傳遞已儲存附件給 Alpine）

```html
<script id="my-model-attachment-data" type="application/json">
[
    {% for att in attachments %}
    { "id": "{{ att.id }}", "url": "{{ att.file.url|escapejs }}", "name": "{{ att.filename|escapejs }}", "isImage": {{ att.is_image|yesno:"true,false" }}, "isTemp": false, "time": "{{ att.uploaded_at|date:'Y-m-d H:i'|escapejs }}" }{% if not forloop.last %},{% endif %}
    {% endfor %}
]
</script>
```

### 3b. Alpine.js Component

```html
<script>
function attachmentCarousel() {
    return {
        activeIndex: 0,
        fileList: [],
        deletedIds: [],
        init() {
            try {
                const el = document.getElementById('my-model-attachment-data');
                if (el) this.fileList = JSON.parse(el.textContent);
            } catch(e) { this.fileList = []; }
        },
        handleFileSelect(event) {
            const files = event.target.files;
            if (!files || !files.length) return;
            const startIndex = this.fileList.length;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const isImage = file.type.startsWith('image/');
                const now = new Date();
                const timeStr = now.getFullYear() + '-' +
                    String(now.getMonth()+1).padStart(2,'0') + '-' +
                    String(now.getDate()).padStart(2,'0') + ' ' +
                    String(now.getHours()).padStart(2,'0') + ':' +
                    String(now.getMinutes()).padStart(2,'0');
                this.fileList.push({
                    id: 'temp_' + Date.now() + '_' + i,
                    url: isImage ? URL.createObjectURL(file) : '',
                    name: file.name,
                    isImage: isImage,
                    isTemp: true,
                    time: timeStr + ' (暫存)'
                });
            }
            this.activeIndex = startIndex;
            // ⚠️ 不要加 event.target.value = '' — 這會清空 file input！
        },
        deleteActive() {
            const f = this.fileList[this.activeIndex];
            if (!f) return;
            if (f.isTemp) {
                // 從 file input 的 FileList 移除（DataTransfer API）
                const inp = this.$el.querySelector('input[type="file"]');
                if (inp && inp.files && typeof DataTransfer !== 'undefined') {
                    const dt = new DataTransfer();
                    for (let i = 0; i < inp.files.length; i++) {
                        if (inp.files[i].name !== f.name) dt.items.add(inp.files[i]);
                    }
                    inp.files = dt.files;
                }
            } else {
                // 已儲存的附件：標記 ID，POST 時由後端刪除
                this.deletedIds.push(String(f.id));
            }
            this.fileList.splice(this.activeIndex, 1);
            if (this.activeIndex >= this.fileList.length)
                this.activeIndex = Math.max(0, this.fileList.length - 1);
        }
    };
}
</script>
```

### 3c. HTML 結構

```html
<div x-data="attachmentCarousel()" x-init="init()">
    <!-- 隱藏欄位：傳遞要刪除的附件 ID -->
    <input type="hidden" name="deleted_attachment_ids" :value="deletedIds.join(',')">

    <!-- 上傳按鈕 -->
    <label class="cursor-pointer inline-flex items-center px-4 py-2 bg-indigo-50 text-indigo-700 font-semibold text-sm rounded-md border border-indigo-200 hover:bg-indigo-100 transition-colors">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
        </svg>
        選擇檔案...
        <input type="file" name="new_attachments" multiple
               accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.odt,.ods"
               class="hidden" @change="handleFileSelect($event)">
    </label>

    <!-- 有附件時顯示輪播 -->
    <template x-if="fileList.length > 0">
        <div class="mt-3 flex flex-col">

            <!-- ⚠️ 控制列必須在 overflow-hidden 容器「外面」，否則按鈕會被裁切 -->
            <div class="flex items-center justify-between bg-white border border-b-0 border-slate-200 rounded-t-lg px-3 py-2">
                <div class="flex items-center gap-2 min-w-0">
                    <span x-show="fileList.length > 1"
                          class="text-xs text-slate-400 font-mono shrink-0"
                          x-text="(activeIndex + 1) + ' / ' + fileList.length"></span>
                    <span class="text-xs text-slate-600 font-medium truncate"
                          x-text="fileList[activeIndex] ? fileList[activeIndex].name : ''"></span>
                    <span x-show="fileList[activeIndex] && fileList[activeIndex].isTemp"
                          class="text-xs text-amber-500 font-semibold shrink-0">(暫存)</span>
                </div>
                <div class="flex items-center gap-2 shrink-0 ml-2">
                    <template x-if="fileList[activeIndex] && !fileList[activeIndex].isTemp">
                        <a :href="fileList[activeIndex].url" target="_blank" download
                           class="text-xs text-indigo-600 hover:text-indigo-800 font-semibold border border-indigo-200 rounded px-2 py-1 bg-indigo-50 hover:bg-indigo-100 transition-colors">下載</a>
                    </template>
                    <button type="button"
                            @click="if(confirm('確定要移除此附件嗎？')) deleteActive()"
                            class="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-700 font-semibold border border-red-200 rounded px-2 py-1 bg-red-50 hover:bg-red-100 transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                        移除
                    </button>
                </div>
            </div>

            <!-- 主顯示區：overflow-hidden，prev/next 箭頭在此內部 -->
            <div class="relative w-full bg-slate-100 rounded-b-lg overflow-hidden border border-slate-200 shadow-inner" style="min-height:260px;">
                <template x-for="(f, index) in fileList" :key="f.id">
                    <div x-show="activeIndex === index"
                         class="w-full flex items-center justify-center"
                         style="min-height:260px;"
                         x-transition.opacity.duration.200ms>
                        <template x-if="f.isImage">
                            <img :src="f.url" class="max-w-full max-h-64 object-contain" alt="">
                        </template>
                        <template x-if="!f.isImage">
                            <div class="flex flex-col items-center justify-center gap-3 py-10 px-6">
                                <svg class="w-14 h-14 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                                </svg>
                                <span class="text-sm font-semibold text-slate-700 text-center break-all" x-text="f.name"></span>
                            </div>
                        </template>
                    </div>
                </template>

                <!-- Prev / Next 箭頭 -->
                <button type="button" x-show="fileList.length > 1"
                        @click="activeIndex = activeIndex === 0 ? fileList.length - 1 : activeIndex - 1"
                        class="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-1.5 rounded-full">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                    </svg>
                </button>
                <button type="button" x-show="fileList.length > 1"
                        @click="activeIndex = activeIndex === fileList.length - 1 ? 0 : activeIndex + 1"
                        class="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-1.5 rounded-full">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                </button>
            </div>

            <!-- 縮圖列 -->
            <div class="flex gap-2 mt-2 overflow-x-auto pb-1 snap-x">
                <template x-for="(f, index) in fileList" :key="f.id">
                    <button type="button" @click="activeIndex = index"
                            :class="activeIndex === index ? 'ring-2 ring-indigo-500 scale-105' : 'opacity-60 hover:opacity-100 border-slate-300'"
                            class="relative w-14 h-14 shrink-0 rounded overflow-hidden border transition-all snap-start bg-slate-200 flex items-center justify-center">
                        <template x-if="f.isImage">
                            <img :src="f.url" class="object-cover w-full h-full" alt="">
                        </template>
                        <template x-if="!f.isImage">
                            <svg class="w-7 h-7 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                            </svg>
                        </template>
                    </button>
                </template>
            </div>
        </div>
    </template>

    <!-- 空狀態 -->
    <template x-if="fileList.length === 0">
        <div class="mt-3 w-full flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 py-10 px-4">
            <svg class="w-10 h-10 text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
            </svg>
            <p class="text-sm text-slate-400">尚未上傳附件</p>
        </div>
    </template>
</div>
```

---

## 常見錯誤對照表

| 症狀 | 根因 | 修正 |
|------|------|------|
| 上傳後存檔，附件消失 | `handleFileSelect` 裡有 `event.target.value = ''` 清空了 file input | 移除那一行 |
| 刪除按鈕看不到 | 刪除按鈕在 `overflow-hidden` 容器內用 `absolute` 定位，被其他元素遮蓋 | 將控制列移到 `overflow-hidden` 容器**外面** |
| 刪除暫存附件後，存檔還是出現 | `deleteActive()` 只從 `fileList` 移除，沒有從 file input 移除 | 加入 `DataTransfer` API 邏輯同步移除 file input 中的檔案 |
| 存檔後附件沒有出現 | form 缺少 `enctype="multipart/form-data"` | 加 `{% block form_attributes %}enctype="multipart/form-data"{% endblock %}` |
| 已儲存附件刪除沒有效果 | `deleted_attachment_ids` hidden field 未建立，或後端未處理 | 確認 hidden field 存在，且 view 的 `form_valid` 有讀取 `deleted_attachment_ids` 並執行 `.delete()` |
| Alpine component 函式名稱衝突 | 同一頁有多個 carousel，都用同一個函式名稱 | 每個 carousel 使用不同的函式名稱（如 `receiptFileViewer`、`dispatchFileViewer`） |
