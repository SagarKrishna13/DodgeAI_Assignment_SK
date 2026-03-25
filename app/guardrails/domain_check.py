def check_domain_relevance(query: str) -> bool:
    """Ensures the question asked is relevant to the dataset domain (Order-to-Cash)."""
    # Simple keyword-based domain check
    domain_keywords = [
        "order", "sales", "customer", "billing", "payment", "delivery", 
        "product", "plant", "journal", "invoice", "revenue", "cash"
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in domain_keywords)
