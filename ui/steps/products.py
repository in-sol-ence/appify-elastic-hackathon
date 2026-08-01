import streamlit as st

from models.enums import PurchaseStatus, SelectionStatus, VerificationStatus
from models.project import ProductSelection, new_id
from ui.shared import blocking_ui_error, editor_records, enum_values, get_wizard, set_step_errors


NONE = "— No role —"


def render() -> None:
    project = get_wizard().current_project
    st.subheader("Specific product selections")
    st.write("Add zero or more candidate products to a role. Roles can remain product-agnostic.")
    with st.expander("Component role versus specific product"):
        st.write("“Onboard computer” is a role. “NVIDIA Jetson Orin Nano” is a specific product that may fill it. Keeping them separate makes alternatives and compatibility explicit.")
    roles = {item.id: item.role_name for item in project.component_roles}
    role_ids = {name: item_id for item_id, name in roles.items()}
    role_options = [NONE, *role_ids]
    rows = [{
        "ID": item.id, "Component role": roles.get(item.component_role_id, NONE),
        "Manufacturer": item.manufacturer, "Product name": item.product_name, "Model": item.model,
        "Manufacturer part number": item.manufacturer_part_number, "Quantity": item.quantity,
        "Expected unit price": item.expected_unit_price, "Supplier name": item.supplier_name, "Supplier URL": item.supplier_url,
        "Manufacturer URL": item.manufacturer_url, "Hardware revision": item.hardware_revision,
        "Firmware version": item.firmware_version, "Selection status": item.selection_status.value,
        "Purchase status": item.purchase_status.value, "Verification status": item.verification_status.value,
        "Primary product": item.primary_product, "Alternatives allowed": item.alternatives_allowed,
        "Notes": item.notes,
    } for item in project.products]
    edited = st.data_editor(
        rows, num_rows="dynamic", hide_index=True, width="stretch", key="products_editor",
        column_config={
            "ID": st.column_config.TextColumn(disabled=True),
            "Component role": st.column_config.SelectboxColumn(options=role_options, required=True),
            "Quantity": st.column_config.NumberColumn(min_value=1, step=1),
            "Expected unit price": st.column_config.NumberColumn(min_value=0.0, format="$%.2f"),
            "Supplier URL": st.column_config.LinkColumn(), "Manufacturer URL": st.column_config.LinkColumn(),
            "Selection status": st.column_config.SelectboxColumn(options=enum_values(SelectionStatus)),
            "Purchase status": st.column_config.SelectboxColumn(options=enum_values(PurchaseStatus)),
            "Verification status": st.column_config.SelectboxColumn(options=enum_values(VerificationStatus)),
            "Primary product": st.column_config.CheckboxColumn(),
            "Alternatives allowed": st.column_config.CheckboxColumn(),
        },
    )
    try:
        parsed = []
        for row in editor_records(edited):
            if not str(row.get("Product name") or "").strip():
                continue
            parsed.append(ProductSelection(
                id=str(row.get("ID") or new_id()),
                component_role_id=role_ids.get(str(row.get("Component role") or NONE), ""),
                manufacturer=str(row.get("Manufacturer") or ""), product_name=str(row["Product name"]).strip(),
                model=str(row.get("Model") or ""), manufacturer_part_number=str(row.get("Manufacturer part number") or ""),
                quantity=int(row.get("Quantity") or 1), expected_unit_price=float(row.get("Expected unit price") or 0),
                supplier_name=str(row.get("Supplier name") or ""), supplier_url=str(row.get("Supplier URL") or ""), manufacturer_url=str(row.get("Manufacturer URL") or ""),
                hardware_revision=str(row.get("Hardware revision") or ""), firmware_version=str(row.get("Firmware version") or ""),
                selection_status=SelectionStatus(str(row.get("Selection status") or SelectionStatus.CANDIDATE.value)),
                purchase_status=PurchaseStatus(str(row.get("Purchase status") or PurchaseStatus.NOT_PLANNED.value)),
                verification_status=VerificationStatus(str(row.get("Verification status") or VerificationStatus.UNVERIFIED.value)),
                primary_product=bool(row.get("Primary product", False)), alternatives_allowed=bool(row.get("Alternatives allowed", True)),
                notes=str(row.get("Notes") or ""),
            ))
        project.products = parsed
        set_step_errors([])
    except Exception as error:
        set_step_errors([blocking_ui_error("invalid_product_row", f"Fix the product table: {error}")])
        st.error(f"Fix the product table: {error}")
    st.caption("Only one product per component role may be primary. Selected but unverified products will generate a review warning.")
