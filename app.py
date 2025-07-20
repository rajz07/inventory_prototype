import streamlit as st
import pandas as pd
import datetime
from utils import (
    inventory,
    sku_list,
    outlet_list,
    WAREHOUSE_NAME,
    returns_inventory,
    cost_history,
    process_stock_return,
    # ...any other function or variable you use in app.py
)



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
        outlet = st.selectbox("Outlet Name", [o for o in outlet_list if not o.startswith("Warehouse")])

        if "po_items" not in st.session_state:
            st.session_state["po_items"] = [{"sku": sku_list[0], "qty": 1, "unit_cost": item_master.get(sku_list[0], 1.00)}]

        def add_po_item():
            st.session_state.po_items.append({"sku": sku_list[0], "qty": 1, "unit_cost": item_master.get(sku_list[0], 1.00)})

        def remove_po_item():
            if len(st.session_state.po_items) > 1:
                st.session_state.po_items.pop()

        for idx, item in enumerate(st.session_state.po_items):
            col1, col2, col3 = st.columns([3,2,2])
            with col1:
                item["sku"] = st.selectbox(f"SKU #{idx+1}", sku_list, key=f"po_sku_{idx}")
            with col2:
                item["qty"] = st.number_input(f"Quantity #{idx+1}", min_value=1, step=1, key=f"po_qty_{idx}")
            with col3:
                item["unit_cost"] = st.number_input(f"Unit Cost #{idx+1}", min_value=0.01, value=item_master.get(item['sku'], 1.00), step=0.01, key=f"po_cost_{idx}")

        col_add, col_remove = st.columns(2)
        col_add.button("➕ Add Item", on_click=add_po_item, key="po_add_item")
        col_remove.button("➖ Remove Item", on_click=remove_po_item, key="po_remove_item")


        po_date = st.date_input("PO Creation Date (Optional)", value=None, key="po_date", disabled=False)

        if st.button("Create PO"):
            po_id = generate_po_id()
            created_at = datetime.datetime.combine(po_date, datetime.datetime.min.time()) if po_date else datetime.datetime.now()
            po = {
                "po_id": po_id,
                "outlet": outlet,
                "status": "Draft",
                "items": [item.copy() for item in st.session_state.po_items],
                "created_at": created_at
            }
            po_list.append(po)
            st.session_state.po_items = [{"sku": sku_list[0], "qty": 1, "unit_cost": item_master.get(sku_list[0], 1.00)}]
            st.success(f"PO {po_id} created.")
            st.rerun()


    with st.expander("Create TO"):
        source = st.selectbox("Source", outlet_list, key="to_src")
        destination = st.selectbox("Destination", outlet_list, key="to_dest")
        if source == destination:
            st.warning("Source and destination must be different.")

        if "to_items" not in st.session_state:
            st.session_state["to_items"] = [{"sku": sku_list[0], "qty": 1}]

        def add_to_item():
            st.session_state.to_items.append({"sku": sku_list[0], "qty": 1})

        def remove_to_item():
            if len(st.session_state.to_items) > 1:
                st.session_state.to_items.pop()

        for idx, item in enumerate(st.session_state.to_items):
            col1, col2 = st.columns([3,2])
            with col1:
                item["sku"] = st.selectbox(f"SKU #{idx+1}", sku_list, key=f"to_sku_{idx}")
            with col2:
                item["qty"] = st.number_input(f"Quantity #{idx+1}", min_value=1, step=1, key=f"to_qty_{idx}")

        col_add, col_remove = st.columns(2)
        col_add.button("➕ Add Item", on_click=add_to_item, key="to_add_item")
        col_remove.button("➖ Remove Item", on_click=remove_to_item, key="to_remove_item")


        to_date = st.date_input("TO Creation Date (Optional)", value=None, key="to_date", disabled=False)

        if st.button("Create TO") and source != destination:
            to_id = generate_to_id()
            created_at = datetime.datetime.combine(to_date, datetime.datetime.min.time()) if to_date else datetime.datetime.now()
            to = {
                "to_id": to_id,
                "source": source,
                "destination": destination,
                "status": "Draft",
                "items": [item.copy() for item in st.session_state.to_items],
                "created_at": created_at
            }
            to_list.append(to)
            st.session_state.to_items = [{"sku": sku_list[0], "qty": 1}]
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

            # Get fulfill_qty_dict from session state or create new
            if f"fulfill_qty_dict_{to['to_id']}" not in st.session_state:
                st.session_state[f"fulfill_qty_dict_{to['to_id']}"] = {item['sku']: 0 for item in to['items']}

            fulfill_qty_dict = st.session_state[f"fulfill_qty_dict_{to['to_id']}"]

            requested = {item["sku"]: item["qty"] for item in to["items"]}
            fulfilled = to.get("fulfilled_qty_dict", {item["sku"]: 0 for item in to["items"]})
            received = to.get("received_qty_dict", {item["sku"]: 0 for item in to["items"]})

            # Display item-wise status
            for item in to["items"]:
                sku = item["sku"]
                req = requested[sku]
                ful = fulfilled.get(sku, 0)
                rec = received.get(sku, 0)
                remaining = req - rec
                st.markdown(
                    f"<span style='font-size: 14px;'>"
                    f"🔢 <strong>{sku}</strong>: "
                    f"📦 <strong>Requested:</strong> {req} | "
                    f"✅ <strong>Fulfilled:</strong> {ful} | "
                    f"📥 <strong>Received:</strong> {rec} | "
                    f"🔄 <strong>Remaining:</strong> {remaining}"
                    f"</span>",
                    unsafe_allow_html=True
                )

                # Fulfill input for this SKU
                max_to_fulfill = req - ful
                fulfill_qty_dict[sku] = st.number_input(
                    f"Enter Fulfill Qty for {sku} in {to['to_id']}",
                    min_value=0,
                    max_value=max_to_fulfill,
                    value=0,
                    key=f"fulfill_qty_{to['to_id']}_{sku}"
                )

            fulfill_date = st.date_input(
                f"Fulfill Date for {to['to_id']} (Optional)",
                value=None,
                key=f"fulfill_date_{to['to_id']}_{idx}"
            )

            if st.button(f"Fulfill TO {to['to_id']}", key=f"fulfill_btn_{to['to_id']}"):
                fulfill_to(to, fulfill_qty_dict.copy(), fulfill_date)
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
            fulfill_dict = to.get("fulfilled_qty_dict", {item["sku"]: 0 for item in to["items"]})
            received_dict = to.get("received_qty_dict", {item["sku"]: 0 for item in to["items"]})

            # Check if there is anything left to receive for any SKU
            any_to_receive = False
            receive_qty_dict = {}
            for item in to["items"]:
                sku = item["sku"]
                fulfilled = fulfill_dict.get(sku, 0)
                received = received_dict.get(sku, 0)
                remaining = fulfilled - received

                if remaining > 0:
                    any_to_receive = True

            if not any_to_receive:
                st.success("✅ Awaiting Further Fulfillment")
                continue

            # Receive inputs per SKU
            for item in to["items"]:
                sku = item["sku"]
                fulfilled = fulfill_dict.get(sku, 0)
                received = received_dict.get(sku, 0)
                remaining = fulfilled - received

                st.markdown(
                    f"<span style='font-size: 14px;'>"
                    f"🔢 <strong>{sku}</strong>: "
                    f"✅ <strong>Fulfilled:</strong> {fulfilled} | "
                    f"📥 <strong>Received:</strong> {received} | "
                    f"🔄 <strong>To Receive:</strong> {remaining}"
                    f"</span>",
                    unsafe_allow_html=True
                )

                # Only allow positive to receive
                if remaining > 0:
                    receive_qty_dict[sku] = st.number_input(
                        f"Qty to receive for {sku} in {to['to_id']}",
                        min_value=0,
                        max_value=remaining,
                        value=0,
                        key=f"receive_qty_{to['to_id']}_{sku}"
                    )

            recv_date = st.date_input(
                f"Receive Date for {to['to_id']}",
                value=None,
                key=f"recv_to_date_{to['to_id']}"
            )

            if st.button(f"Receive TO {to['to_id']}", key=f"recv_to_{to['to_id']}"):
                # Only pass SKUs with qty > 0
                filtered_receive = {sku: qty for sku, qty in receive_qty_dict.items() if qty > 0}
                if filtered_receive:
                    receive_to(to, filtered_receive, recv_date)
                    # Status update happens inside receive_to
                    st.rerun()
                else:
                    st.warning("Enter at least one quantity to receive.")
                    
    st.subheader("🔄 Outlet Stock Return to Warehouse")

    # Only non-warehouse outlets
    pos_outlets = [o for o in outlet_list if not o.lower().startswith("warehouse")]
    return_outlet = st.selectbox("Select Outlet for Return", pos_outlets, key="ret_outlet")

    warehouse = WAREHOUSE_NAME  # define somewhere, match your system's warehouse name

    # Collect all SKUs for this outlet
    outlet_skus = [sku for (out, sku) in inventory if out == return_outlet]
    if not outlet_skus:
        st.info("No SKUs in this outlet.")
    else:
        st.markdown("**Enter quantities and reasons to return:**")
        return_items = []
        for sku in sorted(outlet_skus):
            key = (return_outlet, sku)
            bal = inventory.get(key, {}).get("qty", 0)
            unit_cost = inventory.get(key, {}).get("unit_cost", 1.0)
            col1, col2, col3 = st.columns([2, 2, 4])
            with col1:
                st.markdown(f"**{sku}**  \nBalance: {bal}")
            with col2:
                ret_qty = st.number_input(
                    f"Qty to return for {sku}", min_value=0, max_value=bal, value=0, step=1, key=f"ret_qty_{sku}"
                )
            with col3:
                reason = st.text_input(
                    f"Reason for {sku}", value="", key=f"ret_reason_{sku}"
                )
            if ret_qty > 0 and reason.strip():
                return_items.append({"sku": sku, "qty": ret_qty, "reason": reason})

        if st.button("Submit Return", key="submit_return_btn"):
            if return_items:
                process_stock_return(return_outlet, warehouse, return_items)
                st.success("Stock return submitted!")
                st.rerun()
            else:
                st.warning("Enter quantity and reason for at least one SKU to return.")


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

        outlet_filter = st.multiselect("Outlet Filter", df.get("outlet", df.get("from")).unique())
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
    st.subheader("🗳️ Outlet Stock Balance (Manual Adjust)")

    selected_outlet = st.selectbox(
        "Select Outlet/Warehouse to Adjust",
        outlet_list,
        key="manual_adjust_outlet"
    )

    # Collect all SKUs (union of all inventory for this outlet)
    existing = [
        (sku, values)
        for (outlet, sku), values in inventory.items()
        if outlet == selected_outlet
    ]

    sku_set = set([sku for sku, _ in existing] + sku_list)  # include all possible SKUs

    if not sku_set:
        st.info("No SKUs configured for this outlet yet.")
    else:
        st.write("Edit stock balances and unit cost, then save to update:")

        adjust_data = []
        for sku in sorted(sku_set):
            key = (selected_outlet, sku)
            qty = inventory.get(key, {}).get("qty", 0)
            cost = inventory.get(key, {}).get("unit_cost", 1.00)
            col1, col2, col3 = st.columns([1, 2, 2])
            with col1:
                st.markdown(f"**{sku}**")
            with col2:
                new_qty = st.number_input(
                    f"Qty_{selected_outlet}_{sku}",
                    min_value=0,
                    value=qty,
                    step=1,
                    key=f"adjust_qty_{selected_outlet}_{sku}"
                )
            with col3:
                new_cost = st.number_input(
                    f"UnitCost_{selected_outlet}_{sku}",
                    min_value=0.00,
                    value=cost,
                    step=0.01,
                    format="%.2f",
                    key=f"adjust_cost_{selected_outlet}_{sku}"
                )
            adjust_data.append((sku, new_qty, new_cost))

        if st.button("💾 Save Adjustments", key="save_adjustment_btn"):
            for sku, new_qty, new_cost in adjust_data:
                key = (selected_outlet, sku)
                inventory[key] = {"qty": new_qty, "unit_cost": new_cost}
            st.success(f"Stock balances for {selected_outlet} updated!")
            st.rerun()
            
        # Summary table of current stock for the selected outlet
        display_data = []
        for sku in sorted(sku_set):
            key = (selected_outlet, sku)
            qty = inventory.get(key, {}).get("qty", 0)
            cost = inventory.get(key, {}).get("unit_cost", 1.00)
            display_data.append({
                "SKU": sku,
                "Quantity": qty,
                "Unit Cost": f"RM {cost:.2f}",
                "Total Cost": f"RM {qty * cost:.2f}"
            })

        # Summary table of current stock for the selected outlet
        display_data = []
        for sku in sorted(sku_set):
            key = (selected_outlet, sku)
            qty = inventory.get(key, {}).get("qty", 0)
            cost = inventory.get(key, {}).get("unit_cost", 1.00)
            display_data.append({
                "SKU": sku,
                "Quantity": qty,
                "Unit Cost": f"RM {cost:.2f}",
                "Total Cost": f"RM {qty * cost:.2f}"
            })

        if display_data:
            st.markdown("**Items:**")
            st.table(display_data)
        else:
            st.info("No SKUs available for this outlet yet.")

        # --- Show Returns Inventory Table Only for Warehouse ---
        if selected_outlet == WAREHOUSE_NAME:
            st.subheader("Warehouse Returns Inventory")
            warehouse_returns = []
            for (wh, sku), val in returns_inventory.items():
                if wh == WAREHOUSE_NAME:
                    warehouse_returns.append({
                        "SKU": sku,
                        "Qty": val["qty"],
                        "Unit Cost": f"RM {val['unit_cost']:.2f}",
                        "Total Value": f"RM {val['qty'] * val['unit_cost']:.2f}",
                        "Reasons": ", ".join(val["reasons"])
                    })
            if warehouse_returns:
                st.table(warehouse_returns)
            else:
                st.info("No returned stock yet.")




with tab8:
    st.header("📒 Detailed Cost Audit Log")

    if not cost_history:
        st.info("No audit data available.")
    else:
        df = pd.DataFrame(cost_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp", ascending=False)

        # If you want to group by outlet (source), otherwise just show all
        if "outlet" in df.columns:
            outlets = df["outlet"].unique()
            for outlet in outlets:
                outlet_data = df[df["outlet"] == outlet]
                with st.expander(f"{outlet}", expanded=False):
                    # Add missing columns safely
                    for col in ["from", "to", "reason"]:
                        if col not in outlet_data.columns:
                            outlet_data[col] = ""
                    display_df = outlet_data[["timestamp", "type", "sku", "qty", "unit_cost", "total_cost", "from", "to", "reason"]].copy()
                    display_df.columns = ["Timestamp", "Type", "SKU", "Quantity", "Unit Cost", "Total Cost", "From", "To", "Reason"]
                    display_df["Unit Cost"] = display_df["Unit Cost"].apply(lambda x: f"RM {x:.2f}")
                    display_df["Total Cost"] = display_df["Total Cost"].apply(lambda x: f"RM {x:.2f}")
                    st.dataframe(display_df, use_container_width=True)
        else:
            # fallback if no "outlet" field
            st.dataframe(df)



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
                st.write("Items:")
                st.table([{
                    "SKU": item["sku"],
                    "Quantity": item["qty"],
                    "Unit Cost": f"RM {item.get('unit_cost', 0):.2f}",
                    "Total Cost": f"RM {item.get('qty', 0) * item.get('unit_cost', 0):.2f}"
                } for item in doc.get("items", [])])

                pdf_base64 = doc_storage.get(doc["doc_id"])
                if pdf_base64:
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="700" height="400" type="application/pdf"></iframe>',
                        unsafe_allow_html=True
                    )
                    
                    
    for doc_type in ["GRN", "DO", "TN", "RN"]:
        st.subheader(f"{doc_type} Records")
        for doc in documents.get(doc_type, []):
            with st.expander(f"{doc['doc_id']} - {doc['ref']}"):
                st.write(f"Timestamp: {doc['timestamp']}")
                st.write(f"Outlet: {doc.get('outlet', '')}")
                st.write(f"Warehouse: {doc.get('warehouse', '')}")
                st.write("Items:")
                st.table([{
                    "SKU": item["sku"],
                    "Quantity": item["qty"],
                    "Unit Cost": f"RM {item.get('unit_cost', 0):.2f}",
                    "Reason": item.get("reason", "")
                } for item in doc.get("items", [])])
                pdf_base64 = doc_storage.get(doc["doc_id"])
                if pdf_base64:
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="700" height="400" type="application/pdf"></iframe>',
                        unsafe_allow_html=True
                    )

