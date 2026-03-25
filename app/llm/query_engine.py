import re
from groq import Groq
from app.config import GROQ_API_KEY, MODEL, MAX_TOKENS
from app.llm.prompt import build_system_prompt, generate_sql_prompt
from app.guardrails.sql_validator import is_safe_sql, enforce_limit
from app.db.schema import extract_schema_string
from app.db.connection import get_db_connection

# Regex patterns for SQL extraction
SQL_TAG_RE = re.compile(r"<sql>(.*?)</sql>", re.DOTALL | re.IGNORECASE)


def _extract_sql(text: str) -> str | None:
    """Extract SQL from <sql>...</sql> tags, with markdown fence fallback."""
    match = SQL_TAG_RE.search(text)
    if match:
        return match.group(1).strip()
    # Fallback: clean markdown fences
    sql = text.strip()
    for prefix in ("```sql", "```"):
        if sql.startswith(prefix):
            sql = sql[len(prefix):]
            break
    if sql.endswith("```"):
        sql = sql[:-3]
    # Only treat it as SQL if it looks like a SELECT statement
    cleaned = sql.strip()
    if cleaned.upper().startswith("SELECT"):
        return cleaned
    return None


# Columns that contain actual graph node IDs (not amounts/dates/text)
_ENTITY_ID_COLUMNS = {
    'salesOrder', 'deliveryDocument', 'billingDocument',
    'accountingDocument', 'businessPartner', 'soldToParty',
    'referenceDocument', 'referenceSdDocument', 'plant', 'product',
    'salesOrderItem', 'deliveryDocumentItem', 'billingDocumentItem',
}

def _extract_entity_ids(text: str, rows: list) -> list:
    """
    Extracts ONLY real entity ID values from SQL result rows.
    Filters by known O2C key column names to avoid emitting amounts, dates, or text.
    """
    ids = set()
    for row in rows:
        for col, val in row.items():
            if col in _ENTITY_ID_COLUMNS and val:
                ids.add(str(val))
    return list(ids)


def query_groq(question: str, history: list) -> dict:
    """
    Full query engine pipeline:
      1. Build messages with system prompt + conversation history
      2. Call Groq LLM to generate SQL inside <sql> tags
      3. Extract and validate SQL
      4. Execute SQL against SQLite
      5. Second LLM call to produce a human-readable answer
      6. Extract entity IDs for graph highlighting
    Returns: { "answer", "sql", "rows", "highlighted_ids" }
    """
    client = Groq(api_key=GROQ_API_KEY)
    schema = extract_schema_string()
    system_prompt = build_system_prompt(schema)
    user_prompt = generate_sql_prompt(question, schema)

    # ── Step 1: Build message list ────────────────────────────────────────────
    # Keep the last 6 history messages for context (3 turns)
    recent_history = history[-6:] if len(history) > 6 else history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_history)
    messages.append({"role": "user", "content": user_prompt})

    # ── Step 2: First LLM call – SQL generation ───────────────────────────────
    try:
        sql_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.0
        )
        raw_sql_output = sql_response.choices[0].message.content.strip()
    except Exception as e:
        return {"answer": f"LLM error during SQL generation: {e}", "sql": None, "rows": [], "highlighted_ids": []}

    # ── Step 3: Extract SQL ───────────────────────────────────────────────────
    sql = _extract_sql(raw_sql_output)
    if not sql:
        # The LLM likely returned a domain-rejection message or plain text
        return {"answer": raw_sql_output, "sql": None, "rows": [], "highlighted_ids": []}

    # ── Step 4: Validate SQL (guardrails) ────────────────────────────────────
    if not is_safe_sql(sql):
        return {
            "answer": "The generated query was rejected by the safety guardrail. Only SELECT queries are permitted.",
            "sql": sql,
            "rows": [],
            "highlighted_ids": []
        }

    # ── Step 5: Execute SQL ───────────────────────────────────────────────────
    # Auto-enforce LIMIT 50 if not present
    sql = enforce_limit(sql)
    rows = []
    db_error = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        db_error = str(e)

    if db_error:
        return {
            "answer": f"SQL execution error: {db_error}",
            "sql": sql,
            "rows": [],
            "highlighted_ids": []
        }

    # ── Step 6: Second LLM call – human-readable answer ──────────────────────
    summary_prompt = (
        f"The user asked: \"{question}\"\n\n"
        f"The following SQL was executed:\n{sql}\n\n"
        f"The query returned {len(rows)} row(s). Here is a sample (up to 10):\n"
        f"{rows[:10]}\n\n"
        "Please provide a concise, human-readable answer based on these results. "
        "Do not repeat the SQL. Do not include any code blocks."
    )
    try:
        summary_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful SAP O2C data analyst. Summarize query results in plain English."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.3
        )
        answer = summary_response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Results returned {len(rows)} row(s). (Summary generation failed: {e})"

    # ── Step 7: Extract entity IDs for graph highlighting ────────────────────
    highlighted_ids = _extract_entity_ids(answer + " " + sql, rows)

    return {
        "answer": answer,
        "sql": sql,
        "rows": rows,
        "highlighted_ids": highlighted_ids
    }
