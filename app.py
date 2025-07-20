import streamlit as st
import pandas as pd
import datetime
from utils import *

st.set_page_config(page_title="PO / TO Automation System", layout="wide")
st.title("📦 PO / TO Automation System")

# ---------------------------- SIDEBAR STATUS PANEL ----------------------------
st.sidebar.header("📋 PO / TO Status")

def render_status_sidebar(records, label):
    st.sidebar.markdown(f"**{label}**")
    for doc in records:
        doc_id = doc.get("po_id") or doc.get("to_id")
        status = doc["status"]
        outlet = doc.get("outlet", f"{doc.get('source')} ➜ {doc.get('destination')}")
        st.sidebar.markdown(f"- {doc_id} ({outlet})\n  - *{status}*")

render_status_sidebar(po_list, "📦 POs")
render_status_sidebar(to_list, "🚚 TOs")

if st.sidebar.button("🗑️ Clear All POs & TOs"):
    po_list.clear()
    to_list.clear()
    cost_history.clear()
    inventory.clear()
    for key in documents:
        documents[key].clear()
    st.sidebar.success("All records cleared.")
    st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📘 FeedMe", "📙 NetSuite", "📗 POS",
    "📊 Dashboard", "📅 Cost Summary",
    "🧾 Item Master", "📦 Stock Balance", "📒 Audit Log", "📁 Documents"
])

# ---------------------------- TAB 1: FeedMe ----------------------------
with tab1:
    st.header("📘 FeedMe: PO / TO Actions")

    with st.expander("Create PO"):
        col1, col2, col3 = st.columns(3)
        with col1:
            outlet = st.selectbox("Outlet Name", [o for o in outlet_list if not o.startswith("Warehouse")])
        with col2:
            sku = st.selectbox("Item SKU", sku_list, key="po_sku")
        with col3:
            qty = st.number_input("Quantity", min_value=1, step=1, key="po_qty")

        cost = st.number_input("Unit Cost (RM)", min_value=0.01, value=item_master.get(sku, 1.00), step=0.01, key="po_cost")
        po_date = st.date_input("PO Creation Date (Optional)", value=None, key="po_date", disabled=False)

        if st.button("Create PO"):
            po_id = generate_po_id()
            created_at = datetime.datetime.combine(po_date, datetime.datetime.min.time()) if po_date else datetime.datetime.now()
            po = {
                "po_id": po_id,
                "outlet": outlet,
                "status": "Draft",
                "items": [{"sku": sku, "qty": qty, "unit_cost": cost}],
                "created_at": created_at
            }
            po_list.append(po)
            st.success(f"PO {po_id} created.")
            st.rerun()

    with st.expander("Create TO"):
        col1, col2, col3 = st.columns(3)
        with col1:
            source = st.selectbox("Source", outlet_list, key="to_src")
        with col2:
            destination = st.selectbox("Destination", outlet_list, key="to_dest")
        with col3:
            if source == destination:
                st.warning("Source and destination must be different.")

        sku = st.selectbox("Item SKU", sku_list, key="to_sku")
        qty = st.number_input("Quantity", min_value=1, step=1, key="to_qty")
        to_date = st.date_input("TO Creation Date (Optional)", value=None, key="to_date", disabled=False)

        if st.button("Create TO") and source != destination:
            to_id = generate_to_id()
            created_at = datetime.datetime.combine(to_date, datetime.datetime.min.time()) if to_date else datetime.datetime.now()
            to = {
                "to_id": to_id,
                "source": source,
                "destination": destination,
                "status": "Draft",
                "items": [{"sku": sku, "qty": qty}],
                "created_at": created_at
            }
            to_list.append(to)
            st.success(f"TO {to_id} created.")
            st.rerun()

    st.subheader("POs in Draft")
    for po in po_list:
        if po["status"] == "Draft":
            st.write(f"{po['po_id']} ({po['outlet']})")
            if st.button(f"Submit PO {po['po_id']}", key=f"submit_po_{po['po_id']}"):
                submit_po(po)
                st.rerun()

    st.subheader("TOs in Draft")
    for to in to_list:
        if to["status"] == "Draft":
            st.write(f"{to['to_id']} ({to['source']} ➜ {to['destination']})")
            if st.button(f"Submit TO {to['to_id']}", key=f"submit_to_{to['to_id']}"):
                submit_to(to)
                st.rerun()

# ---------------------------- TAB 2: NetSuite ----------------------------
with tab2:
    st.header("📙 NetSuite: Approval & Fulfillment")

    st.subheader("POs for Approval")
    for po in po_list:
        if po["status"] == "Requesting":
            approve_date = st.date_input(f"Approve Date for {po['po_id']} (Optional)", value=None, key=f"apv_po_{po['po_id']}")
            st.write(f"{po['po_id']} - {po['outlet']}")
            if st.button(f"Approve PO {po['po_id']}", key=f"approve_po_{po['po_id']}"):
                po["created_at"] = datetime.datetime.combine(approve_date, datetime.datetime.min.time()) if approve_date else datetime.datetime.now()
                approve_po(po)
                st.rerun()

    st.subheader("TOs for Approval")
    for to in to_list:
        if to["status"] == "Requesting":
            approve_date = st.date_input(f"Approve Date for {to['to_id']} (Optional)", value=None, key=f"apv_to_{to['to_id']}")
            st.write(f"{to['to_id']} - {to['source']} ➜ {to['destination']}")
            if st.button(f"Approve TO {to['to_id']}", key=f"approve_to_{to['to_id']}"):
                to["created_at"] = datetime.datetime.combine(approve_date, datetime.datetime.min.time()) if approve_date else datetime.datetime.now()
                approve_to(to)
                st.rerun()

    for idx, to in enumerate(to_list):
        if to["status"] == "Processing":
            st.write(f"**{to['to_id']} - {to['source']} ➜ {to['destination']}**")

            item = to["items"][0]
            requested_qty = item["qty"]
            received_qty = to.get("received_qty", 0)
            fulfilled_qty = to.get("fulfilled_qty", 0)

            actual_remaining = requested_qty - received_qty
            if actual_remaining <= 0:
                st.write("✅ Fully Fulfilled and Received")
                continue

            # Display summary line
            st.markdown(
                f"<span style='font-size: 14px;'>"
                f"📦 <strong>Requested:</strong> {requested_qty} | "
                f"✅ <strong>Fulfilled:</strong> {fulfilled_qty} | "
                f"🔄 <strong>Remaining:</strong> {actual_remaining}"
                f"</span>",
                unsafe_allow_html=True
            )

            fulfill_qty = st.number_input(
                f"Enter Fulfill Qty for {to['to_id']}",
                min_value=1,
                max_value=actual_remaining,
                value=actual_remaining,
                key=f"fulfill_qty_{to['to_id']}"
            )

            fulfill_date = st.date_input(
                f"Fulfill Date for {to['to_id']} (Optional)",
                value=None,
                key=f"fulfill_date_{to['to_id']}_{idx}"
            )

            if st.button(f"Fulfill TO {to['to_id']}", key=f"fulfill_btn_{to['to_id']}"):
                fulfill_to(to, fulfill_qty, fulfill_date)
                st.rerun()




# ---------------------------- TAB 3: POS ----------------------------
with tab3:
    st.header("📗 POS System: Receiving")

    st.subheader("POs in Receiving")
    for po in po_list:
        if po["status"] == "Receiving":
            st.write(f"{po['po_id']} - {po['outlet']}")
            recv_date = st.date_input(f"Receive Date for {po['po_id']}", value=None, key=f"recv_po_date_{po['po_id']}")
            if st.button(f"Receive PO {po['po_id']}", key=f"recv_po_{po['po_id']}"):
                receive_po(po, recv_date)
                st.rerun()

    st.subheader("TOs in Receiving")
    for to in to_list:
        if to["status"] == "Receiving":
            st.write(f"{to['to_id']} - {to['destination']}")
            item = to["items"][0]
            sku = item["sku"]
            requested_qty = item["qty"]
            fulfilled_qty = to.get("fulfilled_qty", 0)
            received_qty = to.get("received_qty", 0)

            remaining_to_receive = fulfilled_qty - received_qty

            if remaining_to_receive <= 0:
                st.write("✅ Awaiting Further Fulfillment")
                continue

            qty_key = f"receive_qty_{to['to_id']}"
            receive_qty = st.number_input(
                f"Qty to receive for {to['to_id']}",
                min_value=1,
                max_value=remaining_to_receive,
                value=remaining_to_receive,
                key=qty_key
            )
            recv_date = st.date_input(
                f"Receive Date for {to['to_id']}",
                value=None,
                key=f"recv_to_date_{to['to_id']}"
            )

            if st.button(f"Receive TO {to['to_id']}", key=f"recv_to_{to['to_id']}"):
                receive_to(to, receive_qty, recv_date)

                # 🔁 After receive, if still not fully received vs requested, fallback to Processing
                total_received = to.get("received_qty", 0)
                if total_received < requested_qty:
                    to["status"] = "Processing"
                else:
                    to["status"] = "Completed"

                st.rerun()

# ---------------------------- TAB 4: Dashboard ----------------------------
with tab4:
    st.header("📊 PO / TO Dashboard")

    def show_status(records, label):
        with st.expander(f"{label}"):
            if not records:
                st.write("No records.")
            for doc in records:
                doc_id = doc.get("po_id") or doc.get("to_id")
                status = doc.get("status", "")
                color = {
                    "Draft": "gray", "Requesting": "orange", "Processing": "blue",
                    "Receiving": "purple", "Completed": "green",
                    "Error - Insufficient stock at source": "red"
                }.get(status, "black")
                st.markdown(
                    f"""<div style='padding:4px 0'>
                        <strong>{doc_id}</strong> ➜ {doc.get('outlet', doc.get('destination'))}
                        <span style='background-color:{color};color:white;padding:2px 8px;border-radius:8px;margin-left:10px'>
                            {status}
                        </span>
                    </div>""",
                    unsafe_allow_html=True
                )

                for item in doc["items"]:
                    st.markdown(f"- {item['sku']} x{item['qty']}")

                # Show progress for TOs
                if "to_id" in doc:
                    fulfilled = doc.get("fulfilled_qty", 0)
                    received = doc.get("received_qty", 0)
                    total = doc["items"][0]["qty"]
                    st.markdown(f"- ✅ Fulfilled: {fulfilled} / {total} | 📦 Received: {received} / {total}")

                st.markdown(f"- 🕒 {doc['created_at'].strftime('%b %d %H:%M')}")

    show_status([p for p in po_list], "📦 All POs")
    show_status([t for t in to_list], "🚚 All TOs")


# ---------------------------- TAB 5: Cost Summary ----------------------------
with tab5:
    st.header("📅 PO / TO Cost Summary")
    df = pd.DataFrame(cost_history)

    if df.empty:
        st.info("No cost data yet.")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()

        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", min_date)
        end_date = col2.date_input("End Date", max_date)

        outlet_filter = st.multiselect("Outlet Filter", df["outlet"].unique())
        sku_filter = st.multiselect("SKU Filter", df["sku"].unique())

        mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
        if outlet_filter:
            mask &= df["outlet"].isin(outlet_filter)
        if sku_filter:
            mask &= df["sku"].isin(sku_filter)

        filtered = df[mask]

        if filtered.empty:
            st.warning("No matching records.")
        else:
            grouped = filtered.groupby(["outlet", "sku"]).agg({
                "qty": "sum",
                "total_cost": "sum"
            }).reset_index()
            grouped["avg_unit_cost"] = (grouped["total_cost"] / grouped["qty"]).round(2)

            st.dataframe(grouped.rename(columns={
                "outlet": "Outlet",
                "sku": "SKU",
                "qty": "Total Qty",
                "total_cost": "Total Cost",
                "avg_unit_cost": "Avg Unit Cost"
            }))

# ---------------------------- TAB 6: Item Master ----------------------------
with tab6:
    st.header("🧾 Item Master - SKU Unit Costs")

    st.subheader("📌 Existing Items")
    for sku in sku_list:
        item_master[sku] = st.number_input(f"{sku} Unit Cost", value=item_master.get(sku, 1.00), key=f"cost_{sku}")

    st.markdown("---")
    st.subheader("➕ Add New SKU")
    col1, col2 = st.columns(2)
    with col1:
        new_sku = st.text_input("New SKU Code")
    with col2:
        new_cost = st.number_input("New SKU Unit Cost", min_value=0.01, value=1.00, step=0.01)

    if st.button("Add SKU"):
        if new_sku.strip() == "":
            st.warning("SKU cannot be empty.")
        elif new_sku in sku_list:
            st.info("SKU already exists.")
        else:
            add_sku(new_sku.strip(), new_cost)
            st.success(f"SKU {new_sku} added with cost RM {new_cost:.2f}.")

# ---------------------------- TAB 7: Stock Balance ----------------------------
with tab7:
    st.header("📦 Outlet Stock Balance")

    if not inventory:
        st.info("No inventory records yet.")
    else:
        stock_df = []
        for (outlet, sku), data in inventory.items():
            stock_df.append({
                "Outlet": outlet,
                "SKU": sku,
                "Quantity": data["qty"],
                "Unit Cost (WAVG)": round(data["unit_cost"], 2),
                "Total Value": round(data["qty"] * data["unit_cost"], 2)
            })

        df = pd.DataFrame(stock_df)
        df = df.sort_values(by=["Outlet", "SKU"])
        st.dataframe(df, use_container_width=True)

# ---------------------------- TAB 8: Audit Log ----------------------------

with tab8:
 
    st.header("📒 Detailed Cost Audit Log")

    if not cost_history:
        st.info("No audit data available.")
    else:
        df = pd.DataFrame(cost_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp", ascending=False)

        outlets = df["outlet"].unique()
        for outlet in outlets:
            outlet_data = df[df["outlet"] == outlet]
            with st.expander(f"{outlet}", expanded=False):
                display_df = outlet_data[["timestamp", "type", "sku", "qty", "unit_cost", "total_cost"]].copy()
                display_df.columns = ["Timestamp", "Type", "SKU", "Quantity", "Unit Cost", "Total Cost"]
                display_df["Unit Cost"] = display_df["Unit Cost"].apply(lambda x: f"RM {x:.2f}")
                display_df["Total Cost"] = display_df["Total Cost"].apply(lambda x: f"RM {x:.2f}")
                st.dataframe(display_df, use_container_width=True)


# ---------------------------- TAB 9: Document Viewer ----------------------------
with tab9: 

    st.header("📄 DO / GRN / TN Documents")

    for doc_type in ["GRN", "DO", "TN"]:
        st.subheader(f"{doc_type} Records")
        for doc in documents[doc_type]:
            with st.expander(f"{doc['doc_id']} - {doc['ref']}"):
                st.write(f"Timestamp: {doc['timestamp']}")
                st.write(f"Ref: {doc['ref']}")
                st.write(f"Outlet: {doc['outlet']}")
                st.write(f"SKU: {doc['sku']}")
                st.write(f"Quantity: {doc['qty']}")
                st.write(f"Unit Cost: RM {doc['unit_cost']:.2f}")
                st.write(f"Total Cost: RM {doc['total_cost']:.2f}")

                # Embed PDF
                pdf_base64 = doc_storage.get(doc["doc_id"])
                if pdf_base64:
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="700" height="400" type="application/pdf"></iframe>',
                        unsafe_allow_html=True
                    )
