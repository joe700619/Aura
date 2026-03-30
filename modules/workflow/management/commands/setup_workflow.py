"""
Management command to setup default workflow template for employee onboarding
"""
from django.core.management.base import BaseCommand
from modules.workflow.models import WorkflowTemplate, WorkflowStep

class Command(BaseCommand):
    help = 'Setup default workflow template for employee onboarding'

    def handle(self, *args, **options):
        self.stdout.write('Setting up employee onboarding workflow...')

        # Create workflow template
        template, created = WorkflowTemplate.objects.get_or_create(
            code='employee_onboarding',
            defaults={
                'name': '員工入職核准',
                'description': '新員工入職時需要的核准流程',
                'is_active': True,
                'reminder_hours': 24,
                'max_reminders': 3
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created workflow template: {template.name}"))
        else:
            self.stdout.write(f"✓ Workflow template already exists: {template.name}")
        
        # Create Step 1: HR Manager
        step1, created = WorkflowStep.objects.get_or_create(
            template=template,
            step_number=1,
            defaults={
                'step_name': 'HR主管核准',
                'can_approve': True,
                'can_reject': True,
                'can_return': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created step 1: {step1.step_name}"))
        else:
            self.stdout.write(f"  ✓ Step 1 already exists: {step1.step_name}")
        
        # Create Step 2: General Manager
        step2, created = WorkflowStep.objects.get_or_create(
            template=template,
            step_number=2,  
            defaults={
                'step_name': '總經理核准',
                'can_approve': True,
                'can_reject': True,
                'can_return': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created step 2: {step2.step_name}"))
        else:
            self.stdout.write(f"  ✓ Step 2 already exists: {step2.step_name}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Workflow template setup complete!"))
        self.stdout.write(f"   Template: {template.name} ({template.code})")

        # ===== Leave Request Workflow =====
        self.stdout.write('\nSetting up leave request workflow...')

        leave_template, created = WorkflowTemplate.objects.get_or_create(
            code='leave_request',
            defaults={
                'name': '請假核准',
                'description': '員工請假時需要主管核准',
                'is_active': True,
                'reminder_hours': 24,
                'max_reminders': 3,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created workflow template: {leave_template.name}"))
        else:
            self.stdout.write(f"✓ Workflow template already exists: {leave_template.name}")

        # Step 1: 直屬主管核准 (動態從 employee.supervisor 取得)
        leave_step1, created = WorkflowStep.objects.get_or_create(
            template=leave_template,
            step_number=1,
            defaults={
                'step_name': '直屬主管核准',
                'approver_field': 'employee.supervisor',
                'can_approve': True,
                'can_reject': True,
                'can_return': True,
            }
        )

        if not created:
            # 更新既有的 step 改用動態欄位
            leave_step1.step_name = '直屬主管核准'
            leave_step1.approver_field = 'employee.supervisor'
            leave_step1.approver_user = None
            leave_step1.save()

        self.stdout.write(self.style.SUCCESS(f"\n✅ Leave request workflow setup complete!"))
        self.stdout.write(f"   Template: {leave_template.name} ({leave_template.code})")

        # ===== Overtime Record Workflow =====
        self.stdout.write('\nSetting up overtime record workflow...')

        ot_template, created = WorkflowTemplate.objects.get_or_create(
            code='overtime_record',
            defaults={
                'name': '加班核准',
                'description': '員工加班時需要主管核准',
                'is_active': True,
                'reminder_hours': 24,
                'max_reminders': 3,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created workflow template: {ot_template.name}"))
        else:
            self.stdout.write(f"✓ Workflow template already exists: {ot_template.name}")

        ot_step1, created = WorkflowStep.objects.get_or_create(
            template=ot_template,
            step_number=1,
            defaults={
                'step_name': '直屬主管核准',
                'approver_field': 'employee.supervisor',
                'can_approve': True,
                'can_reject': True,
                'can_return': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created step 1: {ot_step1.step_name}"))
        else:
            self.stdout.write(f"  ✓ Step 1 already exists: {ot_step1.step_name}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Overtime record workflow setup complete!"))
        self.stdout.write(f"   Template: {ot_template.name} ({ot_template.code})")

        # ===== Advance Payment Workflow =====
        self.stdout.write('\nSetting up advance payment workflow...')

        from django.contrib.auth.models import Group
        ap_group, _ = Group.objects.get_or_create(name='管理層')

        ap_template, created = WorkflowTemplate.objects.get_or_create(
            code='advance_payment_approval',
            defaults={
                'name': '代墊款核准',
                'description': '代墊款申請需要主管核准',
                'is_active': True,
                'reminder_hours': 24,
                'max_reminders': 3,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created workflow template: {ap_template.name}"))
        else:
            self.stdout.write(f"✓ Workflow template already exists: {ap_template.name}")

        ap_step1, created = WorkflowStep.objects.get_or_create(
            template=ap_template,
            step_number=1,
            defaults={
                'step_name': '主管核准',
                'approver_role': ap_group,
                'can_approve': True,
                'can_reject': True,
                'can_return': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created step 1: {ap_step1.step_name}"))
        else:
            self.stdout.write(f"  ✓ Step 1 already exists: {ap_step1.step_name}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Advance payment workflow setup complete!"))
        self.stdout.write(f"   Template: {ap_template.name} ({ap_template.code})")
        self.stdout.write(f"   Approver role: {ap_group.name} (請至 Django Admin 將相關人員加入此群組)")
