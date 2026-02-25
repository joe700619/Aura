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
