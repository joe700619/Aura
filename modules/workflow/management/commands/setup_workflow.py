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
