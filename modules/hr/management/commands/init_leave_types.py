from django.core.management.base import BaseCommand
from modules.hr.services.leave_calculator import _ensure_leave_types
from modules.hr.models import LeaveType


class Command(BaseCommand):
    help = '初始化台灣勞基法標準假別（LeaveType）'

    def handle(self, *args, **options):
        _ensure_leave_types()
        types = LeaveType.objects.order_by('sort_order')
        self.stdout.write(self.style.SUCCESS(f'共 {types.count()} 種假別：'))
        for t in types:
            paid = '有薪' if t.is_paid else '無薪'
            limit = f'上限 {int(t.max_hours_per_year)}h' if t.max_hours_per_year else '無上限'
            self.stdout.write(f'  [{t.sort_order:2d}] {t.code:<15} {t.name:<8} {paid}  {limit}')
