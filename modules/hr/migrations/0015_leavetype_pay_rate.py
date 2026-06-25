from decimal import Decimal

from django.db import migrations, models


def set_pay_rate(apps, schema_editor):
    """依舊的 is_paid 推導 pay_rate：無薪→0.00、有薪→1.00（預設），並修正生理假為半薪。"""
    LeaveType = apps.get_model('hr', 'LeaveType')
    Historical = apps.get_model('hr', 'HistoricalLeaveType')

    LeaveType.objects.filter(is_paid=False).update(pay_rate=Decimal('0.00'))
    Historical.objects.filter(is_paid=False).update(pay_rate=Decimal('0.00'))

    # 生理假為半薪，舊資料 is_paid=True 會被帶成 1.00，這裡修正
    LeaveType.objects.filter(code='menstrual').update(pay_rate=Decimal('0.50'))
    Historical.objects.filter(code='menstrual').update(pay_rate=Decimal('0.50'))


def reverse_pay_rate(apps, schema_editor):
    """回滾：pay_rate=0 視為無薪，其餘視為有薪（半薪資訊會遺失）。"""
    LeaveType = apps.get_model('hr', 'LeaveType')
    Historical = apps.get_model('hr', 'HistoricalLeaveType')

    LeaveType.objects.filter(pay_rate=Decimal('0.00')).update(is_paid=False)
    Historical.objects.filter(pay_rate=Decimal('0.00')).update(is_paid=False)


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0014_remove_attendancerecord_unique_employee_date_attendance_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='leavetype',
            name='pay_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), help_text='1.00=全薪、0.50=半薪、0.00=無薪', max_digits=3, verbose_name='給薪比例'),
        ),
        migrations.AddField(
            model_name='historicalleavetype',
            name='pay_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), help_text='1.00=全薪、0.50=半薪、0.00=無薪', max_digits=3, verbose_name='給薪比例'),
        ),
        migrations.RunPython(set_pay_rate, reverse_pay_rate),
        migrations.RemoveField(
            model_name='leavetype',
            name='is_paid',
        ),
        migrations.RemoveField(
            model_name='historicalleavetype',
            name='is_paid',
        ),
    ]
