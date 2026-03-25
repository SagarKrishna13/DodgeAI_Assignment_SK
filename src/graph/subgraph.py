from src.graph.schema_graph import NODE_CONFIG, EDGE_MAP


def fetch_subgraph(entity_ids: list) -> dict:
    """
    Fetches actual data rows from SQLite for the given arbitrary entity IDs.
    Each table query is wrapped individually so one failure never blocks others.
    """
    from src.db.connection import get_db_connection

    if not entity_ids:
        return {"nodes": [], "edges": []}

    conn = get_db_connection()
    nodes = {}
    edges = []

    def add_node(node_id, label, group, metadata=None):
        if not node_id:
            return
        nid = str(node_id)
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": label, "group": group, "metadata": metadata or {}}

    def add_edge(from_id, to_id, label=""):
        if not from_id or not to_id:
            return
        edges.append({"from": str(from_id), "to": str(to_id), "label": label})

    ph = ",".join("?" * len(entity_ids))
    ids = entity_ids

    # 1 — Sales Order Headers
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT salesOrder, soldToParty, totalNetAmount, creationDate "
            f"FROM sales_order_headers WHERE salesOrder IN ({ph}) OR soldToParty IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            so = r.get("salesOrder"); cust = r.get("soldToParty")
            add_node(so, f"Order {so}", "document", r)
            if cust:
                add_node(cust, f"Customer {cust}", "entity")
                add_edge(cust, so, "places_order")
    except Exception as e:
        print(f"[subgraph] sales_order_headers: {e}")

    # 2 — Billing Document Headers  (soldToParty + billingDocument live here)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT billingDocument, soldToParty, totalNetAmount, billingDocumentDate, accountingDocument "
            f"FROM billing_document_headers WHERE billingDocument IN ({ph}) OR soldToParty IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            inv = r.get("billingDocument"); cust = r.get("soldToParty")
            add_node(inv, f"Invoice {inv}", "financial", r)
            if cust:
                add_node(cust, f"Customer {cust}", "entity")
                add_edge(cust, inv, "billed_to")
    except Exception as e:
        print(f"[subgraph] billing_document_headers: {e}")

    # 3 — Billing Document Items  (referenceSdDocument lives here, not in headers)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT billingDocument, referenceSdDocument "
            f"FROM billing_document_items WHERE billingDocument IN ({ph}) OR referenceSdDocument IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            inv = r.get("billingDocument"); so_ref = r.get("referenceSdDocument")
            add_node(inv, f"Invoice {inv}", "financial", r)
            if so_ref:
                add_edge(so_ref, inv, "invoiced_as")
    except Exception as e:
        print(f"[subgraph] billing_document_items: {e}")

    # 4 — Outbound Delivery Items
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT deliveryDocument, referenceSdDocument, plant "
            f"FROM outbound_delivery_items WHERE deliveryDocument IN ({ph}) OR referenceSdDocument IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            dv = r.get("deliveryDocument"); so_ref = r.get("referenceSdDocument")
            add_node(dv, f"Delivery {dv}", "document", r)
            if so_ref:
                add_edge(so_ref, dv, "fulfilled_by")
    except Exception as e:
        print(f"[subgraph] outbound_delivery_items: {e}")

    # 5 — Journal Entries (AR)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT accountingDocument, referenceDocument, amountInTransactionCurrency "
            f"FROM journal_entry_items_accounts_receivable "
            f"WHERE accountingDocument IN ({ph}) OR referenceDocument IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            acc = r.get("accountingDocument"); ref = r.get("referenceDocument")
            add_node(acc, f"Journal {acc}", "financial", r)
            if ref:
                add_edge(ref, acc, "cleared_by")
    except Exception as e:
        print(f"[subgraph] journal_entry_items: {e}")

    # 6 — Payments
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT accountingDocument, clearingDate, amountInTransactionCurrency, customer "
            f"FROM payments_accounts_receivable WHERE accountingDocument IN ({ph}) OR customer IN ({ph})",
            ids + ids
        )
        for row in cursor.fetchall():
            r = dict(row)
            pay = r.get("accountingDocument"); cust = r.get("customer")
            add_node(pay, f"Payment {pay}", "financial", r)
            if cust:
                add_node(cust, f"Customer {cust}", "entity")
    except Exception as e:
        print(f"[subgraph] payments: {e}")

    conn.close()

    # Deduplicate edges
    seen = set()
    unique_edges = []
    for e in edges:
        sig = f"{e['from']}-{e['to']}-{e['label']}"
        if sig not in seen:
            seen.add(sig)
            unique_edges.append(e)

    return {"nodes": list(nodes.values()), "edges": unique_edges}
