"""
Django management command to check MongoDB connection health and status.
"""

from django.core.management.base import BaseCommand
from core.mongodb_manager import mongodb_manager


class Command(BaseCommand):
    """Django command to check MongoDB connection health."""
    
    help = 'Check MongoDB connection health and display connection information'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--close',
            action='store_true',
            help='Close MongoDB connection after health check'
        )
        
        parser.add_argument(
            '--info',
            action='store_true',
            help='Display detailed connection information'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write(
            self.style.SUCCESS('Checking MongoDB connection health...')
        )
        
        # Perform health check
        is_healthy = mongodb_manager.health_check()
        
        if is_healthy:
            self.stdout.write(
                self.style.SUCCESS('✓ MongoDB connection is healthy')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ MongoDB connection is unhealthy')
            )
            return
        
        # Display connection info if requested
        if options['info']:
            self.stdout.write('\nConnection Information:')
            info = mongodb_manager.get_connection_info()
            
            for key, value in info.items():
                self.stdout.write(f"  {key}: {value}")
        
        # Close connection if requested
        if options['close']:
            self.stdout.write('\nClosing MongoDB connection...')
            mongodb_manager.close_connection()
            self.stdout.write(
                self.style.SUCCESS('✓ MongoDB connection closed')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\nMongoDB health check completed')
        )
