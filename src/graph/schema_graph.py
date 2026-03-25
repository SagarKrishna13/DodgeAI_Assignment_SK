NODE_CONFIG = [
    {"id": "customer", "label": "Customer", "group": "entity", "tables": ["business_partners", "business_partner_addresses", "customer_company_assignments", "customer_sales_area_assignments"]},
    {"id": "sales_order", "label": "Sales Order", "group": "document", "tables": ["sales_order_headers", "sales_order_items", "sales_order_schedule_lines"]},
    {"id": "outbound_delivery", "label": "Outbound Delivery", "group": "document", "tables": ["outbound_delivery_headers", "outbound_delivery_items"]},
    {"id": "billing_document", "label": "Billing Document", "group": "document", "tables": ["billing_document_headers", "billing_document_items", "billing_document_cancellations"]},
    {"id": "payment", "label": "Payment", "group": "financial", "tables": ["payments_accounts_receivable", "journal_entry_items_accounts_receivable"]},
    {"id": "product", "label": "Product", "group": "master_data", "tables": ["products", "product_descriptions", "product_plants", "product_storage_locations"]},
    {"id": "plant", "label": "Plant", "group": "master_data", "tables": ["plants"]}
]

EDGE_MAP = [
    {"from": "customer", "to": "sales_order", "label": "places_order"},
    {"from": "sales_order", "to": "product", "label": "contains_item"},
    {"from": "sales_order", "to": "outbound_delivery", "label": "fulfilled_by"},
    {"from": "outbound_delivery", "to": "plant", "label": "ships_from"},
    {"from": "outbound_delivery", "to": "billing_document", "label": "invoiced_as"},
    {"from": "billing_document", "to": "payment", "label": "paid_via"}
]

def build_schema_graph() -> dict:
    """Builds a knowledge graph from the database schema structure (lightweight, no data loading)."""
    # Exclude internal 'tables' property from the final frontend representation to keep it clean, if needed
    nodes = [{"id": n["id"], "label": n["label"], "group": n["group"]} for n in NODE_CONFIG]
    return {
        "nodes": nodes,
        "edges": EDGE_MAP
    }
