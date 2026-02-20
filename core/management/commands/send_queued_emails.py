from django.core.management.base import BaseCommand
from django.utils import timezone
from core.notifications.models import EmailLog
from core.notifications.services import EmailService

class Command(BaseCommand):
    help = 'Sends queued emails that are scheduled to be sent.'

    """
    DEPLOYMENT INSTRUCTIONS:
    To run this command periodically (e.g., every 5 minutes):

    1. Windows (Task Scheduler):
       - Create a Basic Task.
       - Trigger: "Daily" -> "Repeat task every 5 minutes" for a duration of "Indefinitely".
       - Action: "Start a program".
       - Program/script: `path\to\your\venv\Scripts\python.exe`
       - Add arguments: `path\to\your\project\manage.py send_queued_emails`
       - Start in: `path\to\your\project\`

    2. Linux (Crontab):
       - Run `crontab -e`
       - Add line: `* * * * * /path/to/venv/bin/python /path/to/project/manage.py send_queued_emails` (runs every minute and checks queue)
    """

    def handle(self, *args, **options):
        now = timezone.now()
        # Find emails that are scheduled and due
        pending_emails = EmailLog.objects.filter(
            status='scheduled',
            scheduled_at__lte=now
        )
        
        count = pending_emails.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No queued emails to send.'))
            return

        self.stdout.write(f"Found {count} queued emails. Sending...")
        
        for log in pending_emails:
            self.stdout.write(f"Sending email ID {log.id} to {log.recipient}...")
            # Mark as pending to avoid double processing if script runs concurrently (basic lock)
            log.status = 'pending'
            log.save(update_fields=['status'])
            
            success = EmailService._send_from_log(log)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully sent email ID {log.id}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to send email ID {log.id}"))
