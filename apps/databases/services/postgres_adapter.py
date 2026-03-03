from typing import Any

from .serializers import serialize_value
from .ssh_tunnel import create_ssh_tunnel

MAX_DATABASES = 20
MAX_TABLES_PER_SCHEMA = 500


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _connect(connection: dict[str, Any], database_override: str | None = None):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return None, None, "Postgres driver is not installed"

    target_database = database_override or connection.get("database") or "postgres"
    tunnel, tunnel_error = create_ssh_tunnel(connection)
    if tunnel_error:
        return None, None, tunnel_error

    host = connection["host"]
    port = connection["port"]
    if tunnel:
        host = "127.0.0.1"
        port = tunnel.local_bind_port

    try:
        db_connection = psycopg.connect(
            host=host,
            port=port,
            user=connection["username"],
            password=connection["password"],
            dbname=target_database,
            connect_timeout=5,
            options="-c statement_timeout=10000",
            row_factory=dict_row,
        )
        return db_connection, tunnel, None
    except Exception:
        if tunnel:
            tunnel.stop()
        return None, None, "Unable to connect to Postgres"


def test_connection(connection: dict[str, Any]):
    db_connection, tunnel, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Postgres test query failed"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()


def get_tree(connection: dict[str, Any]):
    db_connection, tunnel, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        databases = []
        if connection.get("database"):
            databases = [connection["database"]]
        else:
            with db_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT datname
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                    LIMIT %s
                    """,
                    (MAX_DATABASES,),
                )
                databases = [row["datname"] for row in cursor.fetchall()]
    except Exception:
        return {"success": False, "error": "Failed to list Postgres databases"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()

    tree = []
    for database_name in databases:
        child_connection, child_tunnel, child_error = _connect(connection, database_name)
        if child_error:
            continue

        database_node = {
            "id": f"postgres-db-{database_name}",
            "label": database_name,
            "nodeType": "database",
            "database": database_name,
            "hasChildren": True,
            "children": [],
        }

        try:
            with child_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schema_name
                    """
                )
                schemas = [row["schema_name"] for row in cursor.fetchall()]

                for schema_name in schemas:
                    schema_node = {
                        "id": f"postgres-schema-{database_name}-{schema_name}",
                        "label": schema_name,
                        "nodeType": "schema",
                        "database": database_name,
                        "schema": schema_name,
                        "hasChildren": True,
                        "children": [],
                    }

                    cursor.execute(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                          AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                        LIMIT %s
                        """,
                        (schema_name, MAX_TABLES_PER_SCHEMA),
                    )
                    table_names = [row["table_name"] for row in cursor.fetchall()]
                    schema_node["children"] = [
                        {
                            "id": f"postgres-table-{database_name}-{schema_name}-{table_name}",
                            "label": table_name,
                            "nodeType": "table",
                            "database": database_name,
                            "schema": schema_name,
                            "table": table_name,
                            "hasChildren": False,
                        }
                        for table_name in table_names
                    ]
                    database_node["children"].append(schema_node)
        except Exception:
            pass
        finally:
            child_connection.close()
            if child_tunnel:
                child_tunnel.stop()

        tree.append(database_node)

    return {"success": True, "tree": tree}


def get_table_data(connection: dict[str, Any], target: dict[str, Any], page: int, page_size: int):
    database_name = target["database"]
    schema_name = target.get("schema") or "public"
    table_name = target["table"]
    offset = (page - 1) * page_size

    db_connection, tunnel, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            table_ref = ".".join([
                _quote_identifier(schema_name),
                _quote_identifier(table_name),
            ])

            cursor.execute(f"SELECT COUNT(*) AS total_count FROM {table_ref}")
            total_count = int(cursor.fetchone()["total_count"])

            cursor.execute(
                f"SELECT * FROM {table_ref} LIMIT %s OFFSET %s",
                (page_size, offset),
            )
            rows = cursor.fetchall()
            columns = []
            if cursor.description:
                columns = [description.name for description in cursor.description]

            serialized_rows = []
            for row in rows:
                serialized_row = {}
                for column_name in columns:
                    serialized_row[column_name] = serialize_value(row.get(column_name))
                serialized_rows.append(serialized_row)

            return {
                "success": True,
                "columns": columns,
                "rows": serialized_rows,
                "page": page,
                "pageSize": page_size,
                "totalCount": total_count,
            }
    except Exception:
        return {"success": False, "error": "Failed to query Postgres table"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()
