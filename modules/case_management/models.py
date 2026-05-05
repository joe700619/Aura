"""案件管理 (Case Management) 資料模型"""
import secrets

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Case(BaseModel):
    """案件 / 對外溝通專案主體"""

    class Category(models.TextChoices):
        CONSULT = 'consult', '諮詢'
        REQUEST_DOC = 'request_doc', '索取資料'
        FILING = 'filing', '申報作業'
        DISPUTE = 'dispute', '稅局查帳'
        OTHER = 'other', '其他'

    class Status(models.TextChoices):
        OPEN = 'open', '進行中'
        WAITING_CLIENT = 'waiting_client', '等待客戶回覆'
        WAITING_INTERNAL = 'waiting_internal', '等待內部處理'
        DONE = 'done', '已完成'
        ARCHIVED = 'archived', '封存'

    class Priority(models.TextChoices):
        LOW = 'low', '低'
        NORMAL = 'normal', '一般'
        HIGH = 'high', '高'
        URGENT = 'urgent', '緊急'

    class Source(models.TextChoices):
        INTERNAL = 'internal', '內部建立'
        CLIENT_PORTAL = 'client_portal', '客戶端發起'
        LINE_API = 'line_api', 'LINE 發起'
        EMAIL = 'email', 'Email 轉入'

    title = models.CharField(max_length=200, verbose_name="案件標題")
    summary = models.TextField(blank=True, verbose_name="案件摘要")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.CONSULT, verbose_name="類別")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, verbose_name="狀態")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL, verbose_name="優先度")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.INTERNAL, verbose_name="發起來源")

    client_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="關聯客戶類型"
    )
    client_object_id = models.PositiveIntegerField(null=True, blank=True)
    client = GenericForeignKey('client_content_type', 'client_object_id')

    external_contact_name = models.CharField(max_length=100, blank=True, verbose_name="外部聯絡人")
    external_contact_email = models.EmailField(blank=True, verbose_name="聯絡 Email")
    external_contact_phone = models.CharField(max_length=30, blank=True, verbose_name="聯絡電話")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='owned_cases', verbose_name="負責會計師"
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='collaborating_cases', verbose_name="協作人員"
    )

    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_cases', verbose_name="建立者"
    )
    created_by_external_email = models.EmailField(blank=True, verbose_name="建立者 Email")
    expected_completion_date = models.DateField(null=True, blank=True, verbose_name="期望完成日")

    needs_followup = models.BooleanField(default=False, verbose_name="是否需要追蹤")
    next_followup_date = models.DateField(null=True, blank=True, verbose_name="下次追蹤日")
    last_activity_at = models.DateTimeField(default=timezone.now, verbose_name="最後活動時間")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="結案時間")

    class Meta:
        verbose_name = "案件"
        verbose_name_plural = "案件"
        ordering = ['-last_activity_at']
        indexes = [
            models.Index(fields=['status', 'needs_followup']),
            models.Index(fields=['client_content_type', 'client_object_id']),
            models.Index(fields=['owner', 'status']),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    @property
    def open_task_count(self):
        return self.tasks.filter(is_done=False, is_hidden=False, is_deleted=False).count()


class CaseTask(BaseModel):
    """案件下的待辦項目"""

    class Assignee(models.TextChoices):
        INTERNAL = 'internal', '內部處理'
        EXTERNAL = 'external', '請客戶提供'

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='tasks', verbose_name="所屬案件")
    title = models.CharField(max_length=300, verbose_name="待辦項目")
    note = models.TextField(blank=True, verbose_name="備註")
    assignee_type = models.CharField(
        max_length=10, choices=Assignee.choices, default=Assignee.INTERNAL, verbose_name="責任歸屬"
    )
    due_date = models.DateField(null=True, blank=True, verbose_name="期限")

    is_done = models.BooleanField(default=False, verbose_name="是否完成")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完成時間")
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='completed_case_tasks'
    )
    is_hidden = models.BooleanField(default=False, verbose_name="從清單隱藏")
    order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        verbose_name = "案件待辦"
        verbose_name_plural = "案件待辦"
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def mark_done(self, user):
        self.is_done = True
        self.done_at = timezone.now()
        self.done_by = user
        self.save(update_fields=['is_done', 'done_at', 'done_by', 'updated_at'])


class CaseReply(BaseModel):
    """案件下的雙方對話紀錄"""

    class AuthorType(models.TextChoices):
        INTERNAL = 'internal', '內部'
        EXTERNAL = 'external', '客戶'
        SYSTEM = 'system', '系統'

    class Channel(models.TextChoices):
        WEB = 'web', '網頁'
        PORTAL = 'portal', '客戶端 Portal'
        LINE = 'line', 'LINE'
        EMAIL = 'email', 'Email 回覆'
        SYSTEM = 'system', '系統'

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='replies', verbose_name="所屬案件")
    author_type = models.CharField(max_length=10, choices=AuthorType.choices, verbose_name="發言方")
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="內部發言者"
    )
    author_display_name = models.CharField(max_length=100, blank=True, verbose_name="顯示名稱")
    content = models.TextField(verbose_name="內容")
    is_system_log = models.BooleanField(default=False)
    external_channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.WEB, verbose_name="回覆來源通道"
    )

    class Meta:
        verbose_name = "案件回覆"
        verbose_name_plural = "案件回覆"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_author_type_display()}: {self.content[:30]}"


class CaseAttachment(BaseModel):
    """案件附件"""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='attachments', verbose_name="所屬案件")
    reply = models.ForeignKey(
        CaseReply, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attachments', verbose_name="關聯回覆"
    )
    file = models.FileField(upload_to='case_attachments/%Y/%m/', verbose_name="檔案")
    original_filename = models.CharField(max_length=255, verbose_name="原始檔名")
    size_bytes = models.PositiveBigIntegerField(default=0)

    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_by_external_name = models.CharField(max_length=100, blank=True)

    supersedes = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='superseded_by', verbose_name="取代的舊版檔案"
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "案件附件"
        verbose_name_plural = "案件附件"
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename


class CaseAccessToken(BaseModel):
    """供外部使用者免登入存取單一案件的 magic link token"""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='access_tokens', verbose_name="案件")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(verbose_name="授權對象 Email")

    expires_at = models.DateTimeField(verbose_name="過期時間")
    revoked_at = models.DateTimeField(null=True, blank=True)

    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "案件存取 Token"
        verbose_name_plural = "案件存取 Token"

    @classmethod
    def issue(cls, case, email, created_by=None, valid_days=30):
        return cls.objects.create(
            case=case,
            email=email,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timezone.timedelta(days=valid_days),
            created_by=created_by,
        )

    @property
    def is_valid(self):
        if self.revoked_at:
            return False
        return timezone.now() < self.expires_at

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.use_count += 1
        self.save(update_fields=['last_used_at', 'use_count', 'updated_at'])


class CaseNotificationPreference(BaseModel):
    """每位使用者可自訂哪些事件要收 Email / 站內通知"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='case_notification_pref', verbose_name="使用者"
    )

    email_on_new_case = models.BooleanField(default=True, verbose_name="新案件時 Email")
    email_on_new_reply = models.BooleanField(default=True, verbose_name="新回覆時 Email")
    email_on_status_change = models.BooleanField(default=True, verbose_name="狀態變更時 Email")
    email_on_followup_due = models.BooleanField(default=True, verbose_name="追蹤日到期時 Email")

    inapp_on_new_case = models.BooleanField(default=True)
    inapp_on_new_reply = models.BooleanField(default=True)
    inapp_on_status_change = models.BooleanField(default=True)

    digest_window_minutes = models.PositiveIntegerField(
        default=5, verbose_name="批次合併視窗（分鐘）",
        help_text="此分鐘內的多則通知合併為一封 Email；設為 0 則即時寄送"
    )

    class Meta:
        verbose_name = "案件通知偏好"
        verbose_name_plural = "案件通知偏好"


class CaseNotificationLog(BaseModel):
    """通知寄送紀錄"""

    class Event(models.TextChoices):
        NEW_CASE = 'new_case', '新案件'
        NEW_REPLY = 'new_reply', '新回覆'
        STATUS_CHANGE = 'status_change', '狀態變更'
        FOLLOWUP_DUE = 'followup_due', '追蹤日到期'

    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        INAPP = 'inapp', '站內通知'

    class Status(models.TextChoices):
        QUEUED = 'queued', '已排入'
        SENT = 'sent', '已送出'
        FAILED = 'failed', '失敗'
        SKIPPED = 'skipped', '依偏好略過'

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notification_logs')
    event = models.CharField(max_length=20, choices=Event.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    recipient_email = models.EmailField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "案件通知紀錄"
        verbose_name_plural = "案件通知紀錄"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['case', '-created_at'])]


class CaseTaskTemplate(BaseModel):
    """客戶自訂的案件清單範本

    當客戶從 Portal 建立案件，且類別符合此範本時，會自動將項目帶入該案件的 CaseTask。
    """

    bookkeeping_client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='case_task_templates',
        verbose_name="所屬客戶",
    )
    category = models.CharField(
        max_length=20, choices=Case.Category.choices, verbose_name="案件類別"
    )
    title = models.CharField(max_length=300, verbose_name="清單項目")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="排序")

    class Meta:
        verbose_name = "案件清單範本"
        verbose_name_plural = "案件清單範本"
        ordering = ['category', 'order', 'created_at']
        indexes = [models.Index(fields=['bookkeeping_client', 'category'])]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
