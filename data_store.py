from models import PurchaseOrder, TransferOrder

# Simulate in-memory storage
POs = {}
TOs = {}

def create_po(po_id, outlet, items):
    POs[po_id] = PurchaseOrder(po_id, outlet, items)

def create_to(to_id, source, dest, items):
    TOs[to_id] = TransferOrder(to_id, source, dest, items)

def get_pos_by_status(status):
    return [po for po in POs.values() if po.status == status]

def get_tos_by_status(status):
    return [to for to in TOs.values() if to.status == status]
