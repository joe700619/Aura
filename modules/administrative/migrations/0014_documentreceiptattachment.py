from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administrative', '0013_basemodel_documentreceipt'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentReceiptAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='document_receipts/%Y/%m/', verbose_name='附件')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='administrative.documentreceipt', verbose_name='收文紀錄')),
            ],
            options={
                'verbose_name': '收文附件',
                'verbose_name_plural': '收文附件',
                'ordering': ['uploaded_at'],
            },
        ),
    ]
