# Generated for adding 非公司組織 organization type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0047_caseassessment_beneficial_owner_declaration_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equitytransaction',
            name='organization_type',
            field=models.CharField(choices=[('LTD', '有限公司'), ('CORP', '股份有限公司'), ('NON_CORP', '非公司組織')], max_length=10, verbose_name='組織種類'),
        ),
        migrations.AlterField(
            model_name='historicalequitytransaction',
            name='organization_type',
            field=models.CharField(choices=[('LTD', '有限公司'), ('CORP', '股份有限公司'), ('NON_CORP', '非公司組織')], max_length=10, verbose_name='組織種類'),
        ),
    ]
