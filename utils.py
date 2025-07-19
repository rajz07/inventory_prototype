import datetime
import base64
from io import BytesIO
from reportlab.pdfgen import canvas

# Data stores
po_list = []
to_list = []
cost_history = []
inventory = {}
item_master = {}
sku_list = ["MILK2002", "BREAD1001"]
outlet_list = ["OutletA", "OutletB", "Warehouse1", "Warehouse2"]

# Document stores
doc_counters = {"PO": 0, "TO": 0, "DO": 0, "GRN": 0, "TN": 0}
documents = {"DO": [], "GRN": [], "TN": []}
doc_storage = {}

# ID generators
def generate_po_id():
    doc_counters["PO"] += 1
    return f"PO{doc_counters['PO']}"

def generate_to_id():
    doc_counters["TO"] += 1
    return f"TO{doc_counters['TO']}"

def generate_doc_id(doc_type):
    doc_counters[doc_type] += 1
    return f"{doc_type}{doc_counters[doc_type]}"

# SKU management
def add_sku(sku, cost):
    sku_list.append(sku)
    item_master[sku] = cost

# PO flow
def submit_po(po):
    po["status"] = "Requesting"

def approve_po(po):
    po["status"] = "Receiving"

def receive_po(po, date_override=None):
    for item in po["items"]:
        sku, qty, cost = item["sku"], item["qty"], item["unit_cost"]
        outlet = po["outlet"]
        key = (outlet, sku)

        if key not in inventory:
            inventory[key] = {"qty": 0, "unit_cost": 0}

        prev_qty = inventory[key]["qty"]
        prev_cost = inventory[key]["unit_cost"]
        new_qty = prev_qty + qty
        new_cost = ((prev_qty * prev_cost) + (qty * cost)) / new_qty if new_qty else cost
        inventory[key]["qty"] = new_qty
        inventory[key]["unit_cost"] = new_cost

        # Log cost history
        cost_history.append({
            "timestamp": date_override or datetime.datetime.now(),
            "type": "GRN",
            "sku": sku,
            "qty": qty,
            "unit_cost": cost,
            "total_cost": qty * cost,
            "outlet": outlet
        })

        # GRN doc
        doc_id = generate_doc_id("GRN")
        documents["GRN"].append({
            "timestamp": date_override or datetime.datetime.now(),
            "doc_id": doc_id,
            "ref": po["po_id"],
            "type": "GRN",
            "outlet": outlet,
            "sku": sku,
            "qty": qty,
            "unit_cost": cost,
            "total_cost": qty * cost
        })
        doc_storage[doc_id] = generate_pdf(doc_id, po["po_id"], outlet, sku, qty, cost, "GRN")

    po["status"] = "Completed"

# TO flow
def submit_to(to):
    to["status"] = "Requesting"

def approve_to(to):
    to["status"] = "Processing"

def fulfill_to(to):
    item = to["items"][0]
    sku, qty = item["sku"], item["qty"]
    source = to["source"]
    key = (source, sku)

    if key not in inventory or inventory[key]["qty"] < qty:
        to["status"] = "Error - Insufficient stock at source"
        return

    # Deduct from source
    inventory[key]["qty"] -= qty

    # Log DO
    doc_id = generate_doc_id("DO")
    documents["DO"].append({
        "timestamp": datetime.datetime.now(),
        "doc_id": doc_id,
        "ref": to["to_id"],
        "type": "DO",
        "outlet": source,
        "sku": sku,
        "qty": qty,
        "unit_cost": inventory[key]["unit_cost"],
        "total_cost": qty * inventory[key]["unit_cost"]
    })
    doc_storage[doc_id] = generate_pdf(doc_id, to["to_id"], source, sku, qty, inventory[key]["unit_cost"], "DO")

    to["status"] = "Receiving"
    to["received_qty"] = 0

def receive_to(to, qty, date_override=None):
    item = to["items"][0]
    sku = item["sku"]
    unit_cost = get_unit_cost((to["source"], sku))
    key = (to["destination"], sku)

    if key not in inventory:
        inventory[key] = {"qty": 0, "unit_cost": 0}

    # WAVG
    prev_qty = inventory[key]["qty"]
    prev_cost = inventory[key]["unit_cost"]
    new_qty = prev_qty + qty
    new_cost = ((prev_qty * prev_cost) + (qty * unit_cost)) / new_qty if new_qty else unit_cost
    inventory[key]["qty"] = new_qty
    inventory[key]["unit_cost"] = new_cost

    # Cost history
    cost_history.append({
        "timestamp": date_override or datetime.datetime.now(),
        "type": "TN",
        "sku": sku,
        "qty": qty,
        "unit_cost": unit_cost,
        "total_cost": qty * unit_cost,
        "outlet": to["destination"]
    })

    # TN doc
    doc_id = generate_doc_id("TN")
    documents["TN"].append({
        "timestamp": date_override or datetime.datetime.now(),
        "doc_id": doc_id,
        "ref": to["to_id"],
        "type": "TN",
        "outlet": to["destination"],
        "sku": sku,
        "qty": qty,
        "unit_cost": unit_cost,
        "total_cost": qty * unit_cost
    })
    doc_storage[doc_id] = generate_pdf(doc_id, to["to_id"], to["destination"], sku, qty, unit_cost, "TN")

    # Status tracking
    to["received_qty"] = to.get("received_qty", 0) + qty
    total = item["qty"]
    to["status"] = "Completed" if to["received_qty"] >= total else "Processing"

# Cost helper
def get_unit_cost(key):
    return inventory.get(key, {}).get("unit_cost", 1.0)

# PDF generation
def generate_pdf(doc_id, ref, outlet, sku, qty, unit_cost, doc_type):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, f"{doc_type} DOCUMENT")
    p.drawString(100, 780, f"Document ID: {doc_id}")
    p.drawString(100, 760, f"Reference: {ref}")
    p.drawString(100, 740, f"Outlet: {outlet}")
    p.drawString(100, 720, f"SKU: {sku}")
    p.drawString(100, 700, f"Quantity: {qty}")
    p.drawString(100, 680, f"Unit Cost: RM {unit_cost:.2f}")
    p.drawString(100, 660, f"Total Cost: RM {qty * unit_cost:.2f}")
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf).decode("utf-8")
