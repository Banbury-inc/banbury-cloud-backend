from django.core.management.base import BaseCommand
from apps.meeting_agent.models import initialize_meeting_platforms


class Command(BaseCommand):
    help = 'Set up default meeting platforms in MongoDB (following existing patterns)'
    
    def handle(self, *args, **options):
        try:
            initialize_meeting_platforms()
            self.stdout.write(
                self.style.SUCCESS('Successfully set up meeting platforms in MongoDB')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to set up meeting platforms: {str(e)}')
            )