from datetime import datetime, timedelta

class PurchaseOrder:
    def __init__(self, po_id, outlet, items):
        self.po_id = po_id
        self.outlet = outlet
        self.items = items  # list of {"sku": ..., "qty": ...}
        self.status = "Draft"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class TransferOrder:
    def __init__(self, to_id, source, destination, items):
        self.to_id = to_id
        self.source = source
        self.destination = destination
        self.items = items
        self.status = "Draft"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.received = []
