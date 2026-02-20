from .auth.models import User
from django.db import models
from django.contrib.contenttypes.models import ContentType

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
