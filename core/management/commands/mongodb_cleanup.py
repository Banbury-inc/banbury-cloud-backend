"""
Django management command to clean up MongoDB connections (Atlas-compatible).
"""

from django.core.management.base import BaseCommand
from core.mongodb_manager import mongodb_manager
import time
import gc


class Command(BaseCommand):
    """Django command to clean up MongoDB connections for Atlas."""
    
    help = 'Clean up MongoDB connections (compatible with MongoDB Atlas)'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--force-cleanup',
            action='store_true',
            help='Force cleanup of all application connections'
        )
        
        parser.add_argument(
            '--restart-pool',
            action='store_true',
            help='Restart the connection pool'
        )
        
        parser.add_argument(
            '--test-new-connection',
            action='store_true',
            help='Test creating a new connection after cleanup'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write(
            self.style.SUCCESS('MongoDB Connection Cleanup Tool (Atlas Compatible)')
        )
        self.stdout.write('=' * 60)
        
        # Always do basic cleanup
        self.basic_cleanup()
        
        if options['force_cleanup']:
            self.force_cleanup()
        
        if options['restart_pool']:
            self.restart_connection_pool()
        
        if options['test_new_connection']:
            self.test_new_connection()
        
        # Provide guidance
        self.provide_guidance()
    
    def basic_cleanup(self):
        """Perform basic connection cleanup."""
        self.stdout.write('\n🧹 Performing basic connection cleanup...')
        
        try:
            # Close the managed connection pool
            mongodb_manager.close_connection()
            self.stdout.write('✓ Closed managed connection pool')
            
            # Force garbage collection
            gc.collect()
            self.stdout.write('✓ Forced garbage collection')
            
            # Wait a moment for connections to close
            time.sleep(2)
            self.stdout.write('✓ Waited for connection cleanup')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during basic cleanup: {e}')
            )
    
    def force_cleanup(self):
        """Force cleanup all possible connection references."""
        self.stdout.write('\n💪 Performing force cleanup...')
        
        try:
            # Import and close any global connections from the old files
            self.cleanup_old_connections()
            
            # Multiple garbage collection cycles
            for i in range(3):
                gc.collect()
                time.sleep(1)
            self.stdout.write('✓ Multiple garbage collection cycles completed')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during force cleanup: {e}')
            )
    
    def cleanup_old_connections(self):
        """Try to cleanup connections from old code patterns."""
        self.stdout.write('🔍 Looking for old connection patterns...')
        
        # Try to import and close old global connections
        try:
            # Check if there are any lingering global MongoClient instances
            import sys
            
            # Look for pymongo clients in loaded modules
            pymongo_clients = []
            for module_name, module in sys.modules.items():
                if hasattr(module, '__dict__'):
                    for attr_name, attr_value in module.__dict__.items():
                        if hasattr(attr_value, '__class__'):
                            class_name = attr_value.__class__.__name__
                            if 'MongoClient' in class_name:
                                pymongo_clients.append((module_name, attr_name, attr_value))
            
            # Close any found clients
            for module_name, attr_name, client in pymongo_clients:
                try:
                    if hasattr(client, 'close'):
                        client.close()
                        self.stdout.write(f'✓ Closed client in {module_name}.{attr_name}')
                except Exception as e:
                    self.stdout.write(f'⚠️  Could not close {module_name}.{attr_name}: {e}')
            
            if not pymongo_clients:
                self.stdout.write('✓ No old MongoClient instances found in modules')
                
        except Exception as e:
            self.stdout.write(f'⚠️  Error checking for old connections: {e}')
    
    def restart_connection_pool(self):
        """Restart the connection pool completely."""
        self.stdout.write('\n🔄 Restarting connection pool...')
        
        try:
            # Close existing connection
            mongodb_manager.close_connection()
            
            # Force reset the singleton
            if hasattr(mongodb_manager, '_client'):
                mongodb_manager._client = None
            if hasattr(mongodb_manager, '_db'):
                mongodb_manager._db = None
            
            # Wait
            time.sleep(3)
            
            # Test new connection
            client = mongodb_manager.get_client()
            db = mongodb_manager.get_database()
            
            # Test operation
            collections = db.list_collection_names()
            self.stdout.write(f'✓ New connection pool started ({len(collections)} collections found)')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error restarting connection pool: {e}')
            )
    
    def test_new_connection(self):
        """Test creating a new connection."""
        self.stdout.write('\n🧪 Testing new connection...')
        
        try:
            # Get a fresh connection
            users_collection = mongodb_manager.get_collection('users')
            user_count = users_collection.count_documents({})
            
            conversations_collection = mongodb_manager.get_collection('conversations')
            conv_count = conversations_collection.count_documents({})
            
            self.stdout.write(f'✓ Successfully connected')
            self.stdout.write(f'  - Users: {user_count}')
            self.stdout.write(f'  - Conversations: {conv_count}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error testing new connection: {e}')
            )
    
    def provide_guidance(self):
        """Provide guidance for dealing with high connection counts."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📋 GUIDANCE FOR HIGH CONNECTION COUNTS'))
        self.stdout.write('=' * 60)
        
        self.stdout.write("""
The 189 connections you see in MongoDB Atlas could be from:

1. 🔄 OLD APPLICATION INSTANCES
   - Stop any running Django development servers
   - Check for background processes: ps aux | grep python
   - Kill old processes: pkill -f "manage.py runserver"

2. 🌐 OTHER APPLICATIONS/ENVIRONMENTS
   - Production servers
   - Other development environments
   - CI/CD pipelines
   - Other team members' instances

3. ⏰ CONNECTION TIMEOUT
   - Atlas connections may take time to close
   - Wait 5-10 minutes and check again
   - Connections should auto-close after idle timeout

4. 🚀 RESTART YOUR APPLICATION
   - Restart your Django development server
   - This ensures you're using the new connection manager

RECOMMENDED ACTIONS:
""")
        
        self.stdout.write(self.style.WARNING("""
1. Run: pkill -f "manage.py runserver"
2. Run: python manage.py mongodb_cleanup --force-cleanup --restart-pool
3. Wait 5 minutes
4. Start your server: python manage.py runserver
5. Check Atlas dashboard again
"""))
        
        self.stdout.write('\n✨ The new connection manager prevents future connection leaks!')
