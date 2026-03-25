import sqlparse
import re

# Blocklist of dangerous SQL keywords
BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "REPLACE", "MERGE", "EXEC", "EXECUTE",
    "CREATE", "GRANT", "REVOKE", "ATTACH", "DETACH"
}

# Regex: matches any blocked keyword as a standalone word (case-insensitive)
BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE
)


def is_safe_sql(sql: str) -> bool:
    """
    Validates an SQL string for safety and correctness.
    Returns True if the SQL is safe to execute, False otherwise.
    """
    if not sql or not sql.strip():
        return False

    # 1. Reject if it contains any blocked keywords
    if BLOCKED_PATTERN.search(sql):
        return False

    # 2. Parse with sqlparse
    statements = sqlparse.parse(sql.strip())

    # 3. Only allow a SINGLE statement
    if len(statements) != 1:
        return False

    statement = statements[0]

    # 4. Reject empty or unrecognized statements
    if not statement.tokens:
        return False

    # 5. Must be a SELECT statement
    if statement.get_type() != "SELECT":
        return False

    return True


# backward-compatible alias
validate_sql = is_safe_sql


def enforce_limit(sql: str, limit: int = 500) -> str:
    """Ensure the query has a LIMIT clause to prevent massive data extraction.
    Returns the (possibly modified) SQL string.
    """
    cleaned = sql.strip().rstrip(";")
    if not re.search(r"\bLIMIT\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {limit}"
    return cleaned
