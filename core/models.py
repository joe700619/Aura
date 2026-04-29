from .auth.models import User
from django.db import models
from django.contrib.contenttypes.models import ContentType
from simple_history.models import HistoricalRecords

class BaseModel(models.Model):
    """
    全域基礎模型 (Base Model)
    所有需要軟刪除與歷史紀錄的 Model 都應該繼承此類別。
    """
    is_deleted = models.BooleanField(default=False, verbose_name="是否刪除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    # 讓繼承此 Model 的子類別自動擁有歷史紀錄
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True
class DocumentTemplate(models.Model):
    name = models.CharField(max_length=255, verbose_name="模板名稱")
    description = models.TextField(blank=True, verbose_name="描述")
    file = models.FileField(upload_to='document_templates/', verbose_name="模板檔案")
    
    # Optional connection to a specific model to filter templates
    model_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="適用模型"
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    class Meta:
        verbose_name = "文件模板"
        verbose_name_plural = "文件模板"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name


class ScheduledJob(models.Model):
    """集中管理的排程任務。

    目前由外部排程器（Windows 工作排程器 / Linux cron）呼叫對應的
    management command 觸發；本表用於記錄任務清單、狀態及執行歷史，
    將來可由 admin 統一管理（啟用/停用、查看上次執行結果）。
    """
    class Status(models.TextChoices):
        NEVER = 'never', '尚未執行'
        SUCCESS = 'success', '成功'
        ERROR = 'error', '失敗'

    name = models.CharField('任務名稱', max_length=100, unique=True)
    command = models.CharField(
        '管理指令', max_length=100,
        help_text='Django management command 名稱（例如：send_remuneration_reminders）',
    )
    description = models.TextField('說明', blank=True)
    cron_schedule = models.CharField(
        'Cron 表達式', max_length=100, blank=True,
        help_text='例如：0 9 1 * *（每月1號 09:00）— 雲端遷移時使用',
    )
    enabled = models.BooleanField('啟用', default=True)
    last_run_at = models.DateTimeField('上次執行時間', null=True, blank=True)
    last_status = models.CharField(
        '上次狀態', max_length=10,
        choices=Status.choices, default=Status.NEVER,
    )
    last_message = models.TextField('上次執行訊息', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '排程任務'
        verbose_name_plural = '排程任務'
        ordering = ['name']

    def __str__(self):
        return self.name

    def record_run(self, success: bool, message: str = ''):
        """由 management command 執行完畢時呼叫，更新狀態。"""
        from django.utils import timezone
        self.last_run_at = timezone.now()
        self.last_status = self.Status.SUCCESS if success else self.Status.ERROR
        self.last_message = message[:5000]
        self.save(update_fields=['last_run_at', 'last_status', 'last_message', 'updated_at'])
