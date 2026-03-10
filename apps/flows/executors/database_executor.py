"""
Database Query executor: runs table data queries via the existing database service.
"""
from apps.databases.models import saved_connections_collection


def _get_saved_connection(connection_id: str, username: str):
    """Load a saved database connection config from MongoDB."""
    doc = saved_connections_collection.find_one({"id": connection_id, "username": username})
    if not doc:
        doc = saved_connections_collection.find_one({"id": connection_id})
    return doc


def execute(node_data: dict, inputs: dict, username: str) -> dict:
    connection_id = node_data.get('connectionId', '')
    table = node_data.get('table', '')
    filters = node_data.get('filters', [])
    columns = node_data.get('columns', [])

    if not connection_id:
        return {'status': 'failed', 'error': 'No database connection selected'}
    if not table:
        return {'status': 'failed', 'error': 'No table/collection specified'}

    saved = _get_saved_connection(connection_id, username)
    if not saved:
        return {'status': 'failed', 'error': f'Connection {connection_id!r} not found'}

    connection = saved.get('config', {})
    provider = connection.get('provider', '')

    try:
        from apps.databases.services import database_service

        # Convert node filters to the format expected by the database service
        db_filters = [
            {'column': f['field'], 'operator': f['operator'], 'value': f['value']}
            for f in filters if f.get('field')
        ]

        # Determine target from table name
        # Table may be "schema.table" for postgres
        parts = table.split('.')
        if provider == 'postgres' and len(parts) >= 2:
            target = {'database': connection.get('database', ''), 'schema': parts[0], 'table': parts[1]}
        elif provider == 'mongodb':
            target = {'database': connection.get('database', ''), 'collection': table}
        else:
            target = {'database': connection.get('database', ''), 'table': table}

        result = database_service.get_table_data_for_connection(
            connection=connection,
            target=target,
            page=1,
            page_size=100,
            filters=db_filters if db_filters else None,
        )

        if not result.get('success'):
            return {'status': 'failed', 'error': result.get('error', 'Query failed')}

        rows = result.get('rows', [])

        # Filter columns if specified
        if columns:
            rows = [{col: row.get(col) for col in columns if col in row} for row in rows]

        return {
            'status': 'success',
            'data': {
                'rows': rows,
                'columns': result.get('columns', columns or []),
                'total_count': result.get('totalCount', len(rows)),
            },
        }
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
