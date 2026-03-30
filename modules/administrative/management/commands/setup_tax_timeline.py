from django.core.management.base import BaseCommand
from modules.administrative.models.tax_timeline import TaxTemplate, TaxTaskInstance
from django.utils import timezone
from datetime import date
import random

class Command(BaseCommand):
    help = '為儀表板生成年度行事曆的測試用任務檔案 (營業稅與營所稅)'

    def handle(self, *args, **options):
        self.stdout.write("開始清理舊有行事曆範本與資料...")
        TaxTaskInstance.objects.all().delete()
        TaxTemplate.objects.all().delete()

        current_year = date.today().year

        self.stdout.write("建立營業稅範本...")
        vat_template = TaxTemplate.objects.create(
            name="營業稅申報",
            is_recurring=True,
            recurring_months="1, 3, 5, 7, 9, 11",
            deadline_day=15,
            description="單數月15日前完成營業稅申報",
            source_type=TaxTemplate.SourceChoices.BUSINESS_TAX
        )

        self.stdout.write("建立營所稅範本...")
        income_tax_template = TaxTemplate.objects.create(
            name="營利事業所得稅結算申報",
            is_recurring=True,
            recurring_months="5",
            deadline_day=31,
            description="每年5月底前完成",
            source_type=TaxTemplate.SourceChoices.MANUAL
        )
        
        self.stdout.write("建立各類所得扣繳憑單申報範本...")
        withholding_tax_template = TaxTemplate.objects.create(
            name="各類所得扣繳暨免扣繳憑單申報",
            is_recurring=True,
            recurring_months="1",
            deadline_day=31,
            description="每年1月底前完成扣繳憑單申報",
            source_type=TaxTemplate.SourceChoices.MANUAL
        )

        templates_to_generate = [vat_template, income_tax_template, withholding_tax_template]

        self.stdout.write(f"正在為 {current_year} 年產出全部任務實例...")
        instances_created = 0

        for tmpl in templates_to_generate:
            months = [int(m.strip()) for m in tmpl.recurring_months.split(',')]
            
            for m in months:
                # Calculate deadline logic exactly per month (using try-except for max days)
                import calendar
                max_days = calendar.monthrange(current_year, m)[1]
                deadline_day = min(tmpl.deadline_day, max_days)
                deadline_date = date(current_year, m, deadline_day)

                task_title = f"{current_year}年 {m}月 {tmpl.name}"
                
                # Mock progress data
                total_clients = random.randint(120, 200)
                
                # if the month is past, assume fully completed. If this month, partially complete.
                if m < date.today().month:
                    completed_clients = total_clients
                    is_completed = True
                elif m == date.today().month:
                    # In current month, it might be heavily worked on, or mostly done if close to deadline
                    completed_clients = random.randint(int(total_clients * 0.2), int(total_clients * 0.9))
                    is_completed = False
                else:
                    completed_clients = 0
                    is_completed = False
                    
                # To demonstrate 'has_alert', if last month isn't finished:
                if m == date.today().month - 1 and date.today().day > tmpl.deadline_day:
                     completed_clients = int(total_clients * 0.95) # missed a few clients
                     is_completed = False
                
                # Add mock remarks
                mock_remarks = ""
                if m == date.today().month:
                    mock_remarks = f"本月申報重點：請確實核對進項發票。\n總客戶數:{total_clients}，請各組盡快回報進度。"
                elif not is_completed:
                    mock_remarks = "部分案件因客戶缺件尚未完工，已請業務聯繫補件。"
                
                TaxTaskInstance.objects.create(
                    template=tmpl,
                    year=current_year,
                    month=m,
                    title=task_title,
                    deadline=deadline_date,
                    total_clients=total_clients,
                    completed_clients=completed_clients,
                    is_completed=is_completed,
                    remarks=mock_remarks
                )
                instances_created += 1

        self.stdout.write(self.style.SUCCESS(f"成功完成! 總共建立了 {instances_created} 筆任務實例。請刷新 Dashboard 查看效果。"))
