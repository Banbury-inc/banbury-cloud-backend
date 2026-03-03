from typing import Any

from .serializers import serialize_value
from .ssh_tunnel import create_ssh_tunnel

SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys"}
MAX_DATABASES = 20
MAX_TABLES_PER_DATABASE = 500


def _quote_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def _connect(connection: dict[str, Any], database_override: str | None = None):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError:
        return None, None, "MySQL driver is not installed"

    target_database = database_override or connection.get("database")
    tunnel, tunnel_error = create_ssh_tunnel(connection)
    if tunnel_error:
        return None, None, tunnel_error

    host = connection["host"]
    port = connection["port"]
    if tunnel:
        host = "127.0.0.1"
        port = tunnel.local_bind_port

    try:
        db_connection = pymysql.connect(
            host=host,
            port=port,
            user=connection["username"],
            password=connection["password"],
            database=target_database,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
            cursorclass=DictCursor,
        )
        return db_connection, tunnel, None
    except Exception:
        if tunnel:
            tunnel.stop()
        return None, None, "Unable to connect to MySQL"


def test_connection(connection: dict[str, Any]):
    db_connection, tunnel, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok_value")
            cursor.fetchone()
        return {"success": True}
    except Exception:
        return {"success": False, "error": "MySQL test query failed"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()


def get_tree(connection: dict[str, Any]):
    db_connection, tunnel, error_message = _connect(connection)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        if connection.get("database"):
            databases = [connection["database"]]
        else:
            with db_connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                databases = []
                for row in cursor.fetchall():
                    db_name = next(iter(row.values()))
                    if db_name not in SYSTEM_DATABASES:
                        databases.append(db_name)
                databases = databases[:MAX_DATABASES]
    except Exception:
        return {"success": False, "error": "Failed to list MySQL databases"}
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
            "id": f"mysql-db-{database_name}",
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
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    LIMIT %s
                    """,
                    (database_name, MAX_TABLES_PER_DATABASE),
                )
                database_node["children"] = [
                    {
                        "id": f"mysql-table-{database_name}-{row['table_name']}",
                        "label": row["table_name"],
                        "nodeType": "table",
                        "database": database_name,
                        "table": row["table_name"],
                        "hasChildren": False,
                    }
                    for row in cursor.fetchall()
                ]
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
    table_name = target["table"]
    offset = (page - 1) * page_size

    db_connection, tunnel, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            table_ref = f"{_quote_identifier(database_name)}.{_quote_identifier(table_name)}"
            cursor.execute(f"SELECT COUNT(*) AS total_count FROM {table_ref}")
            total_count = int(cursor.fetchone()["total_count"])

            cursor.execute(
                f"SELECT * FROM {table_ref} LIMIT %s OFFSET %s",
                (page_size, offset),
            )
            rows = cursor.fetchall()

            columns = []
            if rows:
                columns = list(rows[0].keys())
            elif cursor.description:
                columns = [description[0] for description in cursor.description]

            serialized_rows = []
            for row in rows:
                serialized_rows.append({key: serialize_value(value) for key, value in row.items()})

            return {
                "success": True,
                "columns": columns,
                "rows": serialized_rows,
                "page": page,
                "pageSize": page_size,
                "totalCount": total_count,
            }
    except Exception:
        return {"success": False, "error": "Failed to query MySQL table"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()
