from src.db.connection import get_db_connection

def extract_schema_string() -> str:
    """Extracts and returns the database schema as a string."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema_lines = []
        for table in tables:
            table_name = table['name']
            schema_lines.append(f"TABLE {table_name}:")
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns = cursor.fetchall()
            for col in columns:
                schema_lines.append(f"  {col['name']} {col['type']}")
            schema_lines.append("")
        
        return "\n".join(schema_lines)
    finally:
        conn.close()
