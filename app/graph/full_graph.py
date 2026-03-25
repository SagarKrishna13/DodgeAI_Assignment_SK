from app.db.connection import get_db_connection

def build_full_graph(limit_per_table: int = 150) -> dict:
    """
    Builds a large, interconnected graph of actual O2C data instances.
    Includes Headers, Items, Products (Materials), Plants, and Customers
    to satisfy deep relationship modeling requirements.
    """
    nodes = {}
    edges = []

    def add_node(node_id, label, group, metadata=None):
        if not node_id: return
        node_id_str = str(node_id)
        if node_id_str not in nodes:
            nodes[node_id_str] = {
                "id": node_id_str,
                "label": label,
                "group": group,
                "metadata": metadata or {}
            }

    def add_edge(from_id, to_id, label=""):
        if not from_id or not to_id: return
        from_str, to_str = str(from_id), str(to_id)
        if from_str in nodes and to_str in nodes:
            edges.append({"from": from_str, "to": to_str, "label": label})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Sales Orders & Customers
        cursor.execute(f"SELECT * FROM sales_order_headers LIMIT {limit_per_table}")
        for row in cursor.fetchall():
            r = dict(row)
            add_node(r.get('salesOrder'), f"Order {r.get('salesOrder')}", "document", r)
            if r.get('soldToParty'):
                add_node(r.get('soldToParty'), f"Customer {r.get('soldToParty')}", "entity", {"type": "Customer", "id": r.get('soldToParty')})
                add_edge(r.get('soldToParty'), r.get('salesOrder'), "places_order")

        # 2. Sales Order Items & Products
        cursor.execute(f"SELECT * FROM sales_order_items LIMIT {limit_per_table * 3}")
        for row in cursor.fetchall():
            r = dict(row)
            item_id = f"{r.get('salesOrder')}-{r.get('salesOrderItem')}"
            add_node(item_id, f"SO Item {r.get('salesOrderItem')}", "document_item", r)
            add_edge(r.get('salesOrder'), item_id, "has_item")
            
            if r.get('product'):
                add_node(r.get('product'), f"Product {r.get('product')}", "master_data", {"type": "Material", "id": r.get('product')})
                add_edge(item_id, r.get('product'), "requests_material")
            if r.get('plant'):
                add_node(r.get('plant'), f"Plant {r.get('plant')}", "entity", {"type": "Plant", "id": r.get('plant')})
                add_edge(item_id, r.get('plant'), "sourced_from")

        # 3. Outbound Deliveries & Delivery Items
        cursor.execute(f"""
            SELECT h.deliveryDocument, i.deliveryDocumentItem, i.referenceSdDocument, i.plant, i.product
            FROM outbound_delivery_headers h
            JOIN outbound_delivery_items i ON h.deliveryDocument = i.deliveryDocument
            LIMIT {limit_per_table * 2}
        """)
        for row in cursor.fetchall():
            r = dict(row)
            dv_id = r.get('deliveryDocument')
            add_node(dv_id, f"Delivery {dv_id}", "document", r)
            
            # Map Delivery to Plant
            if r.get('plant'):
                add_node(r.get('plant'), f"Plant {r.get('plant')}", "entity", {"id": r.get('plant')})
                add_edge(dv_id, r.get('plant'), "ships_from")
                
            # Map Delivery to Order
            if r.get('referenceSdDocument'):
                add_edge(dv_id, r.get('referenceSdDocument'), "fulfills_order")

        # 4. Billing Documents
        cursor.execute(f"""
            SELECT h.billingDocument, i.referenceSdDocument
            FROM billing_document_headers h
            JOIN billing_document_items i ON h.billingDocument = i.billingDocument
            LIMIT {limit_per_table * 2}
        """)
        for row in cursor.fetchall():
            r = dict(row)
            inv_id = r.get('billingDocument')
            add_node(inv_id, f"Invoice {inv_id}", "financial", r)
            if r.get('referenceSdDocument'):
                add_edge(inv_id, r.get('referenceSdDocument'), "invoiced_for")

        conn.close()
    except Exception as e:
        print(f"Error building full graph: {e}")

    # Deduplicate edges
    unique_edges = []
    seen = set()
    for e in edges:
        sig = f"{e['from']}-{e['to']}-{e['label']}"
        if sig not in seen:
            seen.add(sig)
            unique_edges.append(e)

    return {"nodes": list(nodes.values()), "edges": unique_edges}
