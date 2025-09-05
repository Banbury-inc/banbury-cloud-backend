from django.core.management.base import BaseCommand
from apps.tasks.taskstudio_views import process_due_tasks_internal


class Command(BaseCommand):
    help = 'Process due TaskStudio tasks (scheduled <= now) and run AI on descriptions.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=25, help='Max tasks to process')

    def handle(self, *args, **options):
        limit = options.get('limit') or 25
        processed = process_due_tasks_internal(limit=limit)
        self.stdout.write(self.style.SUCCESS(f'Processed {len(processed)} tasks'))

