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

# Set your warehouse name as per your outlet_list
WAREHOUSE_NAME = "Warehouse1"  # Use the exact warehouse name from your system
returns_inventory = {}  # key: (warehouse, sku), value: {qty, unit_cost, reasons: [str]}




# Document stores
doc_counters = {"PO": 0, "TO": 0, "DO": 0, "GRN": 0, "TN": 0, "RN": 0}
documents = {"DO": [], "GRN": [], "TN": [], "RN": []}

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
        sku = item["sku"]
        qty = item["qty"]
        cost = item["unit_cost"]
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

        cost_history.append({
            "timestamp": date_override or datetime.datetime.now(),
            "type": "GRN",
            "sku": sku,
            "qty": qty,
            "unit_cost": cost,
            "total_cost": qty * cost,
            "outlet": outlet
        })

    # Create one GRN doc per PO, with all items
    doc_id = generate_doc_id("GRN")
    documents["GRN"].append({
        "timestamp": date_override or datetime.datetime.now(),
        "doc_id": doc_id,
        "ref": po["po_id"],
        "type": "GRN",
        "outlet": po["outlet"],
        "items": po["items"]
    })
    doc_storage[doc_id] = generate_pdf(doc_id, po["po_id"], po["outlet"], po["items"], "GRN")

    po["status"] = "Completed"


# TO flow
def submit_to(to):
    to["status"] = "Requesting"

def approve_to(to):
    to["status"] = "Processing"
    to["fulfilled_qty"] = 0
    to["received_qty"] = 0

def fulfill_to(to, fulfill_qty_dict, fulfill_date):
    do_items = []

    for item in to["items"]:
        sku = item["sku"]
        requested_qty = item["qty"]
        fulfill_qty = fulfill_qty_dict.get(sku, 0)
        source = to["source"]
        key = (source, sku)

        if fulfill_qty <= 0:
            continue

        if key not in inventory or inventory[key]["qty"] < fulfill_qty:
            to["status"] = "Error - Insufficient stock at source"
            continue

        # Deduct from source
        inventory[key]["qty"] -= fulfill_qty
        to["fulfilled_qty_dict"] = to.get("fulfilled_qty_dict", {})
        to["fulfilled_qty_dict"][sku] = to["fulfilled_qty_dict"].get(sku, 0) + fulfill_qty

        unit_cost = inventory[key]["unit_cost"]

        do_items.append({
            "sku": sku,
            "qty": fulfill_qty,
            "unit_cost": unit_cost,
            "total_cost": fulfill_qty * unit_cost
        })

    # Create one DO doc per TO fulfillment event, with all items
    if do_items:
        doc_id = generate_doc_id("DO")
        documents["DO"].append({
            "timestamp": fulfill_date or datetime.datetime.now(),
            "doc_id": doc_id,
            "ref": to["to_id"],
            "type": "DO",
            "outlet": to["source"],
            "items": do_items
        })
        doc_storage[doc_id] = generate_pdf(doc_id, to["to_id"], to["source"], do_items, "DO")

    to["status"] = "Receiving"



def receive_to(to, receive_qty_dict, date_override=None):
    tn_items = []

    for item in to["items"]:
        sku = item["sku"]
        requested_qty = item["qty"]
        receive_qty = receive_qty_dict.get(sku, 0)
        key = (to["destination"], sku)

        if receive_qty <= 0:
            continue

        if key not in inventory:
            inventory[key] = {"qty": 0, "unit_cost": 0}

        unit_cost = get_unit_cost((to["source"], sku))

        prev_qty = inventory[key]["qty"]
        prev_cost = inventory[key]["unit_cost"]
        new_qty = prev_qty + receive_qty
        new_cost = ((prev_qty * prev_cost) + (receive_qty * unit_cost)) / new_qty if new_qty else unit_cost
        inventory[key]["qty"] = new_qty
        inventory[key]["unit_cost"] = new_cost

        cost_history.append({
            "timestamp": date_override or datetime.datetime.now(),
            "type": "TN",
            "sku": sku,
            "qty": receive_qty,
            "unit_cost": unit_cost,
            "total_cost": receive_qty * unit_cost,
            "outlet": to["destination"]
        })

        to["received_qty_dict"] = to.get("received_qty_dict", {})
        to["received_qty_dict"][sku] = to["received_qty_dict"].get(sku, 0) + receive_qty

        tn_items.append({
            "sku": sku,
            "qty": receive_qty,
            "unit_cost": unit_cost,
            "total_cost": receive_qty * unit_cost
        })

    # Create one TN doc per TO receive event, with all items
    if tn_items:
        doc_id = generate_doc_id("TN")
        documents["TN"].append({
            "timestamp": date_override or datetime.datetime.now(),
            "doc_id": doc_id,
            "ref": to["to_id"],
            "type": "TN",
            "outlet": to["destination"],
            "items": tn_items
        })
        doc_storage[doc_id] = generate_pdf(doc_id, to["to_id"], to["destination"], tn_items, "TN")

    # After loop, check if all items are received
    all_received = True
    for item in to["items"]:
        sku = item["sku"]
        requested = item["qty"]
        received = to.get("received_qty_dict", {}).get(sku, 0)
        if received < requested:
            all_received = False
            break

    to["status"] = "Completed" if all_received else "Processing"



# Cost helper
def get_unit_cost(key):
    return inventory.get(key, {}).get("unit_cost", 1.0)

# PDF generation
def generate_pdf(doc_id, ref, outlet, items, doc_type):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"{doc_type} DOCUMENT")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Document ID: {doc_id}")
    p.drawString(100, 765, f"Reference: {ref}")
    p.drawString(100, 750, f"Outlet: {outlet}")

    y = 720
    p.setFont("Helvetica-Bold", 11)
    p.drawString(100, y, "SKU")
    p.drawString(220, y, "Qty")
    p.drawString(300, y, "Unit Cost")
    p.drawString(400, y, "Total Cost")
    y -= 18
    p.setFont("Helvetica", 11)

    for item in items:
        sku = item['sku']
        qty = item['qty']
        unit_cost = item.get('unit_cost', 0)
        total_cost = qty * unit_cost
        p.drawString(100, y, str(sku))
        p.drawString(220, y, str(qty))
        p.drawString(300, y, f"RM {unit_cost:.2f}")
        p.drawString(400, y, f"RM {total_cost:.2f}")
        if item.get("reason"):
            p.drawString(500, y, f"{item['reason']}")
        y -= 16
        if y < 50:  # Start new page if needed
            p.showPage()
            y = 800
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf).decode("utf-8")


def process_stock_return(outlet, warehouse, return_items, date_override=None):
    rn_items = []
    for item in return_items:
        sku = item["sku"]
        qty = item["qty"]
        reason = item["reason"]
        key_outlet = (outlet, sku)
        key_warehouse = (warehouse, sku)

        # Deduct from outlet inventory
        if key_outlet in inventory:
            prev_qty = inventory[key_outlet]["qty"]
            prev_cost = inventory[key_outlet]["unit_cost"]
            new_qty = max(prev_qty - qty, 0)
            inventory[key_outlet]["qty"] = new_qty
        else:
            prev_cost = 1.0  # fallback if missing

        # Add to returns bucket in warehouse
        if key_warehouse not in returns_inventory:
            returns_inventory[key_warehouse] = {"qty": 0, "unit_cost": prev_cost, "reasons": []}
        returns_inventory[key_warehouse]["qty"] += qty
        returns_inventory[key_warehouse]["unit_cost"] = prev_cost  # keep last known cost
        returns_inventory[key_warehouse]["reasons"].append(reason)

        # --- AUDIT LOG ENTRY (add here) ---
        cost_history.append({
            "timestamp": date_override or datetime.datetime.now(),
            "type": "RETURN",
            "sku": sku,
            "qty": qty,
            "unit_cost": prev_cost,
            "total_cost": qty * prev_cost,
            "from": outlet,
            "to": warehouse,
            "reason": reason
        })
        # --- END AUDIT LOG ENTRY ---

        rn_items.append({
            "sku": sku,
            "qty": qty,
            "unit_cost": prev_cost,
            "reason": reason
        })

    # Generate one RN document for this return
    doc_id = generate_doc_id("RN")
    documents["RN"].append({
        "timestamp": date_override or datetime.datetime.now(),
        "doc_id": doc_id,
        "ref": f"{outlet}_to_{warehouse}",
        "type": "RN",
        "outlet": outlet,
        "warehouse": warehouse,
        "items": rn_items
    })
    doc_storage[doc_id] = generate_pdf(doc_id, f"{outlet}_to_{warehouse}", warehouse, rn_items, "RN")

