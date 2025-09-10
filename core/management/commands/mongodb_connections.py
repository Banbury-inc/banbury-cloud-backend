"""
Django management command to analyze and manage MongoDB connections.
"""

from django.core.management.base import BaseCommand
from core.mongodb_manager import mongodb_manager


class Command(BaseCommand):
    """Django command to analyze and manage MongoDB connections."""
    
    help = 'Analyze and manage MongoDB connections'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--list',
            action='store_true',
            help='List current connections and operations'
        )
        
        parser.add_argument(
            '--kill-idle',
            action='store_true',
            help='Kill idle connections (connections idle for more than 30 seconds)'
        )
        
        parser.add_argument(
            '--force-close',
            action='store_true',
            help='Force close all application connections'
        )
        
        parser.add_argument(
            '--idle-timeout',
            type=int,
            default=30,
            help='Timeout in seconds for considering a connection idle (default: 30)'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write(
            self.style.SUCCESS('Analyzing MongoDB connections...')
        )
        
        # Get current connection information
        connection_info = self.get_connection_info()
        
        if options['list'] or not any([options['kill_idle'], options['force_close']]):
            self.list_connections(connection_info)
        
        if options['kill_idle']:
            self.kill_idle_connections(options['idle_timeout'])
        
        if options['force_close']:
            self.force_close_connections()
    
    def get_connection_info(self):
        """Get MongoDB connection information."""
        try:
            client = mongodb_manager.get_client()
            admin_db = client.admin
            
            # Get server status
            server_status = admin_db.command("serverStatus")
            connections = server_status.get('connections', {})
            
            # Get current operations
            current_ops = admin_db.command("currentOp")
            operations = current_ops.get('inprog', [])
            
            return {
                'server_status': server_status,
                'connections': connections,
                'operations': operations
            }
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting connection info: {e}')
            )
            return None
    
    def list_connections(self, info):
        """List current connections and operations."""
        if not info:
            return
        
        connections = info['connections']
        operations = info['operations']
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('MongoDB Connection Information'))
        self.stdout.write('=' * 60)
        
        # Connection summary
        current = connections.get('current', 'Unknown')
        available = connections.get('available', 'Unknown')
        total_created = connections.get('totalCreated', 'Unknown')
        
        self.stdout.write(f"Current connections: {current}")
        self.stdout.write(f"Available connections: {available}")
        self.stdout.write(f"Total created: {total_created}")
        
        # Highlight high connection count
        if isinstance(current, int) and current > 50:
            self.stdout.write(
                self.style.WARNING(f"⚠️  High connection count: {current}")
            )
            self.stdout.write(
                self.style.WARNING("This may indicate connection leaks from old code.")
            )
        
        # Active operations summary
        self.stdout.write(f"\nActive operations: {len(operations)}")
        
        # Show details of some operations
        if operations:
            self.stdout.write('\nSample active operations:')
            for i, op in enumerate(operations[:5]):
                self.stdout.write(f"\nOperation {i+1}:")
                self.stdout.write(f"  OpID: {op.get('opid', 'Unknown')}")
                self.stdout.write(f"  Type: {op.get('op', 'Unknown')}")
                self.stdout.write(f"  Client: {op.get('client', 'Unknown')}")
                self.stdout.write(f"  Duration: {op.get('secs_running', 'Unknown')} seconds")
                self.stdout.write(f"  Active: {op.get('active', 'Unknown')}")
            
            if len(operations) > 5:
                self.stdout.write(f"\n... and {len(operations) - 5} more operations")
    
    def kill_idle_connections(self, idle_timeout):
        """Kill idle connections."""
        self.stdout.write(
            self.style.WARNING(f'\nKilling connections idle for more than {idle_timeout} seconds...')
        )
        
        try:
            client = mongodb_manager.get_client()
            admin_db = client.admin
            
            # Get current operations
            current_ops = admin_db.command("currentOp")
            operations = current_ops.get('inprog', [])
            
            killed_count = 0
            for op in operations:
                # Look for idle connections
                if (op.get('active', True) == False and 
                    op.get('secs_running', 0) > idle_timeout):
                    
                    try:
                        opid = op.get('opid')
                        if opid:
                            result = admin_db.command("killOp", op=opid)
                            if result.get('ok') == 1:
                                self.stdout.write(f"✓ Killed operation {opid}")
                                killed_count += 1
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f"✗ Failed to kill operation {opid}")
                                )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error killing operation {opid}: {e}")
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f"Killed {killed_count} idle connections")
            )
            
            # Show updated connection count
            updated_info = self.get_connection_info()
            if updated_info:
                current = updated_info['connections'].get('current', 'Unknown')
                self.stdout.write(f"Current connections after cleanup: {current}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error killing idle connections: {e}')
            )
    
    def force_close_connections(self):
        """Force close all application connections."""
        self.stdout.write(
            self.style.WARNING('\nForce closing all application connections...')
        )
        
        try:
            # Close our managed connection
            mongodb_manager.close_connection()
            self.stdout.write("✓ Closed managed connection pool")
            
            # Force garbage collection
            import gc
            gc.collect()
            self.stdout.write("✓ Forced garbage collection")
            
            self.stdout.write(
                self.style.SUCCESS("Application connections closed successfully")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error force closing connections: {e}')
            )
