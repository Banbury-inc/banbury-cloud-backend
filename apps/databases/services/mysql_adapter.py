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


def _get_primary_key_columns(cursor, database_name: str, table_name: str) -> list[str]:
    cursor.execute(
        """
        SELECT kcu.COLUMN_NAME
        FROM information_schema.TABLE_CONSTRAINTS tc
        JOIN information_schema.KEY_COLUMN_USAGE kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
            AND tc.TABLE_SCHEMA = %s
            AND tc.TABLE_NAME = %s
        ORDER BY kcu.ORDINAL_POSITION
        """,
        (database_name, table_name),
    )
    return [row["COLUMN_NAME"] for row in cursor.fetchall()]


def _build_where_clause(filters: list[dict]) -> tuple[str, list]:
    if not filters:
        return "", []

    parts = []
    params = []

    operator_map = {
        "=": "=",
        "!=": "<>",
        ">": ">",
        "<": "<",
        ">=": ">=",
        "<=": "<=",
    }

    for f in filters:
        col = _quote_identifier(f["column"])
        op = f["operator"]
        val = f["value"]

        if op == "contains":
            parts.append(f"{col} LIKE %s")
            params.append(f"%{val}%")
        else:
            sql_op = operator_map[op]
            parts.append(f"{col} {sql_op} %s")
            params.append(val)

    return "WHERE " + " AND ".join(parts), params


def get_table_data(connection: dict[str, Any], target: dict[str, Any], page: int, page_size: int, order_by=None, filters=None):
    database_name = target["database"]
    table_name = target["table"]
    offset = (page - 1) * page_size

    db_connection, tunnel, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            table_ref = f"{_quote_identifier(database_name)}.{_quote_identifier(table_name)}"

            where_clause, where_params = _build_where_clause(filters or [])

            order_clause = ""
            if order_by:
                direction = "ASC" if order_by["direction"] == "asc" else "DESC"
                order_clause = f"ORDER BY {_quote_identifier(order_by['column'])} {direction}"

            cursor.execute(
                f"SELECT COUNT(*) AS total_count FROM {table_ref} {where_clause}",
                where_params,
            )
            total_count = int(cursor.fetchone()["total_count"])

            cursor.execute(
                f"SELECT * FROM {table_ref} {where_clause} {order_clause} LIMIT %s OFFSET %s",
                (*where_params, page_size, offset),
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

            primary_key_columns = _get_primary_key_columns(cursor, database_name, table_name)

            return {
                "success": True,
                "columns": columns,
                "rows": serialized_rows,
                "page": page,
                "pageSize": page_size,
                "totalCount": total_count,
                "primaryKeyColumns": primary_key_columns,
            }
    except Exception:
        return {"success": False, "error": "Failed to query MySQL table"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()


def update_rows(connection: dict[str, Any], target: dict[str, Any], updates: list[dict]):
    database_name = target["database"]
    table_name = target["table"]
    table_ref = f"{_quote_identifier(database_name)}.{_quote_identifier(table_name)}"

    db_connection, tunnel, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            for update in updates:
                primary_key = update.get("primaryKey", {})
                changes = update.get("changes", {})
                if not primary_key or not changes:
                    continue
                set_clause = ", ".join([f"{_quote_identifier(col)} = %s" for col in changes])
                where_clause = " AND ".join([f"{_quote_identifier(col)} = %s" for col in primary_key])
                values = list(changes.values()) + list(primary_key.values())
                cursor.execute(f"UPDATE {table_ref} SET {set_clause} WHERE {where_clause}", values)
        db_connection.commit()
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Failed to update MySQL rows"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()


def insert_rows(connection: dict[str, Any], target: dict[str, Any], rows: list[dict]):
    database_name = target["database"]
    table_name = target["table"]
    table_ref = f"{_quote_identifier(database_name)}.{_quote_identifier(table_name)}"

    db_connection, tunnel, error_message = _connect(connection, database_name)
    if error_message:
        return {"success": False, "error": error_message}

    try:
        with db_connection.cursor() as cursor:
            for row in rows:
                if not row:
                    continue
                columns = list(row.keys())
                col_clause = ", ".join([_quote_identifier(col) for col in columns])
                val_clause = ", ".join(["%s"] * len(columns))
                values = [row[col] for col in columns]
                cursor.execute(f"INSERT INTO {table_ref} ({col_clause}) VALUES ({val_clause})", values)
        db_connection.commit()
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Failed to insert rows into MySQL table"}
    finally:
        db_connection.close()
        if tunnel:
            tunnel.stop()
