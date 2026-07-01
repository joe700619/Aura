# A 段實作文件：LINE 對話紀錄收進 ERP（LineEventLog）

> 狀態：**已實作（本機驗證通過，待部署 + 切換）**
> 目標：把官方 LINE 帳號的 inbound 事件（客戶提問 + 加入事件）從 Google Apps Script + Sheet 改收進 ERP，作為知識庫 B 段萃取的素材池，並順帶提供客戶頁的提問歷史 / userID·roomID 撈取。

---

## 1. 範圍

**做：**
- 收 **inbound** 事件：`message`（**只記文字 text**）、`join`（bot 被拉進群）、`follow`（個人加好友）
- 文字訊息存全文
- 對得到客戶就連 FK，對不到存 null（可回填）
- admin 列表可瀏覽，取代 Apps Script 的「確認有收到」用途

**不做（明確排除）：**
- **不記錄非文字訊息**（圖片/檔案/貼圖/位置…）—— 連 metadata 都不存，之後要擴建再說
- 不下載圖片/檔案本體（LINE 過期即無法回補，見 §8）
- 不收 outbound（你方回覆收不到，已確認；答案改由 B 段會計師補）
- 不抓 displayName / 大頭貼（B 段萃取用不到，且會增加 profile API 呼叫）
- 不碰 B 段萃取、bot

---

## 2. 已定設計決策

| # | 決策 | 理由 |
|---|---|---|
| 1 | 表名 `LineEventLog`，**不繼承 BaseModel** | 既有 `LineMessageLog` 是外送用，命名衝突；log 為 append-only，繼承 BaseModel 會被 HistoricalRecords 翻倍寫入 |
| 2 | `room_id` / `sender_user_id` 分兩欄 | 群組訊息同時有「哪個群」和「誰講的」；對齊 Customer 的 line_id / room_id |
| 3 | `sender_user_id` 允許空白 | 群組裡未加好友的成員，LINE 不給 userId |
| 4 | 去重鍵用 `webhook_event_id`（非 message.id） | join/follow 沒有 message.id；webhookEventId 所有事件都有、重送不變 |
| 5 | 對客戶邏輯按 source_type 分流 | user→比對 line_id；group/room→比對 room_id |
| 6 | 直接切換、不平行跑 | Apps Script 僅用於撈 ID + 確認收訊，ERP log 兩者都接得住 |

---

## 3. Model

新增於 `core/notifications/models.py`：

```python
class LineEventLog(models.Model):
    """LINE inbound 事件紀錄（append-only）。

    收 message / join / follow 三類事件，作為知識庫萃取素材與提問歷史。
    刻意不繼承 BaseModel：log 永不修改，不需要 HistoricalRecords / is_deleted。
    去重靠 webhook_event_id（LINE 重送時不變）。
    """
    EVENT_TYPES = (
        ('message', 'Message'),
        ('join', 'Join'),
        ('follow', 'Follow'),
    )

    webhook_event_id = models.CharField(max_length=64, unique=True, verbose_name='事件 ID')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, verbose_name='事件類型')
    sent_at = models.DateTimeField(db_index=True, verbose_name='發生時間')

    source_type = models.CharField(max_length=10, verbose_name='來源類型')      # user / group / room
    room_id = models.CharField(max_length=64, blank=True, db_index=True, verbose_name='RoomID')
    sender_user_id = models.CharField(max_length=64, blank=True, db_index=True, verbose_name='發話者 UserID')

    message_type = models.CharField(max_length=20, blank=True, verbose_name='訊息類型')  # 目前只寫 'text'；join/follow 空。欄位保留供未來擴建
    text = models.TextField(blank=True, verbose_name='文字內容')
    line_message_id = models.CharField(max_length=64, blank=True, verbose_name='訊息 ID')  # text 訊息填；保留供未來非文字擴建

    customer = models.ForeignKey(
        'basic_data.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, db_index=True, verbose_name='對應客戶',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'LINE 事件紀錄'
        verbose_name_plural = 'LINE 事件紀錄'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['room_id', 'sent_at']),
            models.Index(fields=['sender_user_id', 'sent_at']),
        ]

    def __str__(self):
        who = self.room_id or self.sender_user_id or '?'
        return f'[{self.event_type}] {who} @ {self.sent_at:%Y-%m-%d %H:%M}'
```

> 註：Customer.line_id / room_id 為 max_length=50，這裡用 64 足以容納並留餘裕（LINE ID 實際約 33 字元）。

> 註：A 段只寫「文字訊息 + join/follow 事件」。`message_type` / `line_message_id` 欄位保留但目前僅文字會用到——保留空欄位成本為零，未來要擴建收非文字時只改 `_log_event` 寫入邏輯、免 migration。

**Migration**：`python manage.py makemigrations notifications` 後 commit。純新增表，無資料遷移、無對既有表的相依風險。

---

## 4. Webhook 改動

檔案：`core/notifications/views.py` 的 `LineWebhookView.post`。

### 4.1 關鍵：現有迴圈會「吃掉」join/follow

目前迴圈第一行就是：

```python
for event in data.get('events', []):
    if event.get('type') != 'message':
        continue          # ← join / follow 在這裡就被丟掉
```

所以**記錄動作必須放在這行 filter 之前**，否則 join/follow 一筆都記不到。

### 4.2 改法（只加、不動既有指令邏輯）

```python
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone

for event in data.get('events', []):
    etype = event.get('type')

    # ── A 段：記錄 inbound 事件（message / join / follow）──
    if etype in ('message', 'join', 'follow'):
        try:
            with transaction.atomic():          # savepoint：記錄失敗不污染外層交易、不影響打卡
                self._log_event(event)
        except Exception:
            logger.exception('LineEventLog 寫入失敗')

    # ── 以下為既有指令處理，完全不動 ──
    if etype != 'message':
        continue
    if event.get('message', {}).get('type') != 'text':
        continue
    # ...（綁定 / 打卡，原樣保留）
```

**為什麼要 `with transaction.atomic()` 包起來**：專案開了 `ATOMIC_REQUESTS=True`，整個 request 是一個交易。若 `_log_event` 直接拋例外被 try 接住，PostgreSQL 的交易會進入 aborted 狀態，**後面的打卡/綁定 query 全部會跟著失敗**。用 `transaction.atomic()` 建立 savepoint，記錄失敗只 rollback 這一小段，主流程不受影響。

### 4.3 `_log_event` 實作

```python
def _log_event(self, event):
    source = event.get('source', {})
    source_type = source.get('type', '')
    room_id = source.get('groupId') or source.get('roomId') or ''
    sender_user_id = source.get('userId', '')

    webhook_event_id = event.get('webhookEventId', '')
    if not webhook_event_id:
        return  # 理論上不會發生；沒有去重鍵就不記，避免空字串互撞

    ts = event.get('timestamp')  # 毫秒 epoch
    sent_at = (
        datetime.fromtimestamp(ts / 1000, tz=dt_timezone.utc)
        if ts else timezone.now()
    )

    message_type = text = line_message_id = ''
    if event.get('type') == 'message':
        msg = event.get('message', {})
        message_type = msg.get('type', '')
        # A 段只收文字；非文字訊息（圖片/檔案/貼圖…）直接略過、不建 log
        if message_type != 'text':
            return
        line_message_id = msg.get('id', '')
        text = msg.get('text', '')

    # 對應客戶：群組/聊天室用 room_id，個人用 user_id
    from modules.basic_data.models import Customer
    customer = None
    if source_type in ('group', 'room') and room_id:
        customer = Customer.objects.filter(room_id=room_id).first()
    elif sender_user_id:
        customer = Customer.objects.filter(line_id=sender_user_id).first()

    from .models import LineEventLog
    LineEventLog.objects.get_or_create(
        webhook_event_id=webhook_event_id,
        defaults={
            'event_type': event.get('type', ''),
            'sent_at': sent_at,
            'source_type': source_type,
            'room_id': room_id,
            'sender_user_id': sender_user_id,
            'message_type': message_type,
            'text': text,
            'line_message_id': line_message_id,
            'customer': customer,
        },
    )
```

用 `get_or_create` 而非 `create`：LINE 重送同一事件時靠 `webhook_event_id` 冪等，不會重複（與專案 signal 的 idempotent 原則一致）。

---

## 5. Admin

`core/notifications/admin.py` 新增（取代 Apps Script 的「確認有收到」監看）：

```python
@admin.register(LineEventLog)
class LineEventLogAdmin(admin.ModelAdmin):
    list_display = ('sent_at', 'event_type', 'source_type', 'customer',
                    'message_type', 'text', 'room_id', 'sender_user_id')
    list_filter = ('event_type', 'source_type', 'message_type', 'sent_at')
    search_fields = ('text', 'room_id', 'sender_user_id', 'line_message_id')
    readonly_fields = [f.name for f in LineEventLog._meta.fields]  # 全唯讀，log 不該手改
    date_hierarchy = 'sent_at'
```

---

## 6. 切換步驟（直接切，不平行）

1. 上 model + migration + webhook 改動 + admin。
2. 部署後，在 LINE 官方帳號隨意傳一則測試訊息 → 進 admin 看 `LineEventLog` 有沒有新增。
3. 確認群組訊息（room_id 有值）、個人訊息（sender_user_id 有值）、加好友（follow）、拉進群（join）都進得來。
4. 確認無誤後，**停掉 Google Apps Script 的觸發器**，Sheet 保留存查即可。

> 風險點：切換瞬間若新 code 有 bug，訊息會默默掉。緩解：(1) 部署後立刻用步驟 2-3 驗證；(2) `webhook_event_id` 冪等，重送不重複；(3) 記錄失敗已用 savepoint 隔離，不會連帶打掛打卡/綁定。

---

## 7. 驗證方式（不寫測試檔，跑過即可）

- 部署後直接用真實 LINE 帳號發訊息 / 加好友 / 拉進群，看 admin 列表。
- 或本機 Docker 用一支臨時 shell 餵假 event 進 `_log_event` 確認落庫與客戶對應正確，驗完即丟。

---

## 8. 後續（不在本段）

- B 段：批次 LLM 從 `LineEventLog.text` 萃取候選 Q&A → KnowledgeEntry(is_verified=False) → 會計師審核補答案。
- 圖片/檔案本體保存：**LINE 只在收到後短時間內保留本體，過期即無法再下載，無法事後回補**。若未來要保存，唯一做法是「收到當下就背景下載存 R2」（下載 + 上傳會拖垮 webhook，須走背景，不可同步）。屆時要一併補上「記錄非文字訊息」這段（A 段目前完全不記非文字）。
- ~~follow 事件可接「自動歡迎 + 引導綁定」回覆~~ → **已納入本段**：follow 時自動回覆歡迎 + LIFF 綁定連結（與「綁定」指令共用文案）。
