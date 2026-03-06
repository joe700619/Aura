"""
未打卡通知 Management Command

每天早上執行，檢查前一個工作日沒有打卡的員工，發送 Email 通知。

用法:
    python manage.py notify_missing_attendance
    python manage.py notify_missing_attendance --date 2026-03-03
    python manage.py notify_missing_attendance --dry-run
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from modules.hr.models import Employee, AttendanceRecord, WorkCalendar


class Command(BaseCommand):
    help = '檢查前一工作日未打卡的員工並發送 Email 通知'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='檢查特定日期 (格式: YYYY-MM-DD)。預設為前一工作日。',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示名單，不實際發送通知',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['date']:
            check_date = date.fromisoformat(options['date'])
        else:
            # 找到前一個工作日
            check_date = timezone.localdate() - timedelta(days=1)
            # 往前找到工作日
            for _ in range(7):  # 最多往前找 7 天
                if WorkCalendar.is_workday(check_date):
                    break
                check_date -= timedelta(days=1)

        self.stdout.write(f'檢查日期: {check_date}\n')

        if not WorkCalendar.is_workday(check_date):
            self.stdout.write(self.style.WARNING(f'{check_date} 不是工作日，跳過。'))
            return

        # 取得所有在職員工
        active_employees = Employee.objects.filter(
            employment_status='ACTIVE', is_active=True
        )

        # 找出沒打卡的員工
        missing = []
        for emp in active_employees:
            has_record = AttendanceRecord.objects.filter(
                employee=emp,
                date=check_date,
                clock_in__isnull=False,
                is_deleted=False,
            ).exists()
            if not has_record:
                missing.append(emp)

        if not missing:
            self.stdout.write(self.style.SUCCESS('✅ 所有員工都有打卡紀錄。'))
            return

        self.stdout.write(self.style.WARNING(f'⚠️ {len(missing)} 位員工未打卡:\n'))
        for emp in missing:
            self.stdout.write(f'  - {emp.employee_number} {emp.name} ({emp.email or "無Email"})')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n(DRY RUN 模式，未實際發送通知)'))
            return

        # 發送通知
        sent_count = 0
        for emp in missing:
            if not emp.email:
                self.stdout.write(f'  ⚠️ {emp.name} 沒有 Email，跳過')
                continue
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject=f'[Aura HR] 未打卡提醒 - {check_date}',
                    message=(
                        f'{emp.name} 您好，\n\n'
                        f'系統偵測到您在 {check_date} 沒有打卡紀錄。\n'
                        f'如有需要，請登入系統進行補卡。\n\n'
                        f'Aura ERP 人資系統'
                    ),
                    from_email=None,  # 使用 DEFAULT_FROM_EMAIL
                    recipient_list=[emp.email],
                    fail_silently=True,
                )
                sent_count += 1
                self.stdout.write(f'  ✉️ 已發送通知給 {emp.name} ({emp.email})')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ 發送失敗 {emp.name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n完成！已發送 {sent_count} 封通知。'))
