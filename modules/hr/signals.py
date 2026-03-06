"""
HR Module Signals

Employee post_save: 自動計算並給予特休/病假
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='hr.Employee')
def auto_grant_leave_on_employee_save(sender, instance, created, **kwargs):
    """
    員工建立或更新時，自動計算並給予當前年資對應的特休和病假。

    只在以下條件觸發：
    - 員工是在職狀態
    - 員工有到職日期
    """
    if not instance.is_active or instance.employment_status != 'ACTIVE':
        return

    if not instance.hire_date:
        return

    try:
        from .services.leave_calculator import grant_leave_for_employee
        results = grant_leave_for_employee(instance)
        for r in results:
            if r['action'] == 'created':
                logger.info(
                    f"Auto-granted {r['leave_type']} for {r['employee']}: "
                    f"{r['days']}天 ({r['period']})"
                )
    except Exception as e:
        logger.error(f"Error auto-granting leave for {instance.name}: {e}")
