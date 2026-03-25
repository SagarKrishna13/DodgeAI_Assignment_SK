import os
import json
import pandas as pd
from pathlib import Path
from app.config import DATA_DIR
from app.db.connection import get_db_connection

def ingest_data():
    """Ingests data from JSONL files into the database on startup."""
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        print(f"Data directory '{DATA_DIR}' not found. Skipping ingestion.")
        return

    jsonl_files = list(data_path.rglob('*.jsonl'))

    if not jsonl_files:
        print(f"No JSONL files found in '{DATA_DIR}' or its subdirectories.")
        return

    conn = get_db_connection()
    tables_created = set()
    try:
        for file_path in jsonl_files:
            file_name = file_path.name
            # If the file is named 'part-...', use the parent directory as the table name
            if file_name.startswith('part-'):
                table_name = file_path.parent.name
            else:
                table_name = file_path.stem
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = [json.loads(line) for line in f if line.strip()]
                if not data:
                    print(f"Skipping empty file: {file_name}")
                    continue
                # Flatten nested JSON
                df = pd.json_normalize(data)
            except Exception as e:
                print(f"Error reading {file_name}: {e}")
                continue
                
            # Data cleaning: strip whitespace and replace spaces with underscores, handle dots from json_normalize
            df.columns = [str(col).strip().replace(' ', '_').replace('.', '_') for col in df.columns]
            
            for col in df.columns:
                if 'date' in col.lower() or 'time' in col.lower():
                    # Parse to datetime and convert to ISO 8601 strings
                    df[col] = pd.to_datetime(df[col], errors='coerce').apply(
                        lambda x: x.isoformat() if pd.notnull(x) else None
                    )
            
            # Replace table if it exists on the first file for this table, append for the rest
            table_mode = 'append' if table_name in tables_created else 'replace'
            
            df.to_sql(table_name, conn, if_exists=table_mode, index=False)
            tables_created.add(table_name)
            print(f"Ingested {file_name} into table '{table_name}' ({len(df)} rows loaded)")
    except Exception as e:
        print(f"Error during data ingestion: {e}")
    finally:
        conn.close()
