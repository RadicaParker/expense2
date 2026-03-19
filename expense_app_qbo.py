# expense_app_qbo.py
# Expense Claim Web App — SaaS Martech Edition
# QBO Bills CSV export with Class (Amoeba) tracking
# Run: streamlit run expense_app_qbo.py

import streamlit as st
import pandas as pd
import uuid
from datetime import date, datetime
import io

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Expense Claims",
    page_icon="🧾",
    layout="wide",
)

# ──────────────────────────────────────────────
# MASTER DATA
# ──────────────────────────────────────────────
AMOEBAS = [
    "Sales - Enterprise",
    "Sales - SMB",
    "Marketing - Growth",
    "Marketing - Brand",
    "Customer Success",
    "Product & Engineering",
    "Finance & Operations",
    "People & Culture",
]

AMOEBA_MANAGERS = {
    "Sales - Enterprise":    "Alice Ng",
    "Sales - SMB":           "Alice Ng",
    "Marketing - Growth":    "Brian Chan",
    "Marketing - Brand":     "Brian Chan",
    "Customer Success":      "Carol Lam",
    "Product & Engineering": "David Wu",
    "Finance & Operations":  "Eva Cheung",
    "People & Culture":      "Eva Cheung",
}

QBO_ACCOUNTS = [
    "Advertising & Marketing",
    "Bank Charges & Fees",
    "Entertainment",
    "IT & Software Subscriptions",
    "Meals & Entertainment",
    "Office Supplies & Equipment",
    "Professional Services",
    "Travel - Airfare",
    "Travel - Accommodation",
    "Travel - Ground Transport",
    "Training & Development",
    "Utilities",
    "Other Operating Expenses",
]

ROLES = ["Employee", "Manager", "Finance"]

STATUS_COLOURS = {
    "Pending":  "🟡",
    "Approved": "🟢",
    "Rejected": "🔴",
}

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
if "claims" not in st.session_state:
    st.session_state.claims = []
if "attachments" not in st.session_state:
    st.session_state.attachments = {}


def generate_claim_id():
    return "EXP-" + str(uuid.uuid4())[:8].upper()


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("🧾 Expense Claims")
    st.divider()
    role = st.selectbox("Login as Role", ROLES)
    if role == "Employee":
        user_name   = st.text_input("Your Name", value="New Employee")
        user_amoeba = st.selectbox("Your Amoeba (Department)", AMOEBAS)
    elif role == "Manager":
        manager_name    = st.selectbox("Manager Name", sorted(set(AMOEBA_MANAGERS.values())))
        managed_amoebas = [a for a, m in AMOEBA_MANAGERS.items() if m == manager_name]
    else:
        user_name = "Finance Team"
    st.divider()
    st.caption("Internal Finance Tool — SaaS Martech")


# ──────────────────────────────────────────────
# EMPLOYEE VIEW
# ──────────────────────────────────────────────
if role == "Employee":
    st.header("📋 Submit Expense Claim")

    with st.form("claim_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            expense_date = st.date_input("Expense Date", value=date.today())
            amount       = st.number_input("Amount (HKD)", min_value=0.01, step=0.01, format="%.2f")
            category     = st.selectbox("Category (QBO Account)", QBO_ACCOUNTS)
        with col2:
            description = st.text_area(
                "Description / Business Purpose",
                placeholder="e.g. Client dinner with Acme Corp — Q2 renewal discussion",
                height=120,
            )
            receipt = st.file_uploader(
                "Attach Receipt (PDF / PNG / JPG)",
                type=["pdf", "png", "jpg", "jpeg"],
            )

        st.info(
            "This claim will be routed to **"
            + AMOEBA_MANAGERS[user_amoeba]
            + "** for approval under **"
            + user_amoeba
            + "**."
        )
        submitted = st.form_submit_button("🚀 Submit Claim", use_container_width=True)

        if submitted:
            if not description.strip():
                st.error("Please add a description before submitting.")
            else:
                claim_id = generate_claim_id()
                claim = {
                    "claim_id":      claim_id,
                    "submitter":     user_name,
                    "amoeba":        user_amoeba,
                    "manager":       AMOEBA_MANAGERS[user_amoeba],
                    "expense_date":  str(expense_date),
                    "amount":        round(amount, 2),
                    "category":      category,
                    "description":   description.strip(),
                    "has_receipt":   receipt is not None,
                    "status":        "Pending",
                    "submitted_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reviewed_at":   "",
                    "reviewer_note": "",
                }
                st.session_state.claims.append(claim)
                if receipt:
                    st.session_state.attachments[claim_id] = {
                        "name":  receipt.name,
                        "bytes": receipt.read(),
                        "type":  receipt.type,
                    }
                st.success(
                    "Claim **" + claim_id + "** submitted! "
                    "Pending approval from " + AMOEBA_MANAGERS[user_amoeba] + "."
                )

    st.divider()
    st.subheader("📂 My Claims")
    my_claims = [c for c in st.session_state.claims if c["submitter"] == user_name]

    if not my_claims:
        st.info("No claims submitted yet.")
    else:
        for c in reversed(my_claims):
            badge = STATUS_COLOURS.get(c["status"], "⚪")
            with st.expander(
                badge + " " + c["claim_id"] + " | HKD "
                + str(c["amount"]) + " | " + c["category"]
                + " | " + c["expense_date"]
            ):
                st.write("**Amoeba (Class):** " + c["amoeba"])
                st.write("**Description:** " + c["description"])
                st.write("**Status:** " + c["status"])
                if c["reviewer_note"]:
                    st.write("**Manager Note:** " + c["reviewer_note"])
                if c["has_receipt"] and c["claim_id"] in st.session_state.attachments:
                    att = st.session_state.attachments[c["claim_id"]]
                    st.download_button(
                        label="⬇️ Download Receipt (" + att["name"] + ")",
                        data=att["bytes"],
                        file_name=att["name"],
                        mime=att["type"],
                        key="dl_emp_" + c["claim_id"],
                    )


# ──────────────────────────────────────────────
# MANAGER VIEW
# ──────────────────────────────────────────────
elif role == "Manager":
    st.header("✅ Approval Queue — " + manager_name)
    st.caption("Managing Amoebas: " + ", ".join(managed_amoebas))

    pending  = [c for c in st.session_state.claims if c["manager"] == manager_name and c["status"] == "Pending"]
    reviewed = [c for c in st.session_state.claims if c["manager"] == manager_name and c["status"] != "Pending"]

    tab1, tab2 = st.tabs(["⏳ Pending (" + str(len(pending)) + ")", "📋 Reviewed (" + str(len(reviewed)) + ")"])

    with tab1:
        if not pending:
            st.success("No pending claims. All clear! 🎉")
        for c in pending:
            with st.expander(
                "🟡 " + c["claim_id"] + " | " + c["submitter"]
                + " | HKD " + str(c["amount"]) + " | " + c["amoeba"]
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Submitter:** " + c["submitter"])
                    st.write("**Amoeba (Class):** " + c["amoeba"])
                    st.write("**Expense Date:** " + c["expense_date"])
                    st.write("**Amount:** HKD " + str(c["amount"]))
                with col2:
                    st.write("**Category:** " + c["category"])
                    st.write("**Submitted:** " + c["submitted_at"])
                    st.write("**Receipt:** " + ("Yes ✅" if c["has_receipt"] else "No ❌"))
                st.write("**Description:** " + c["description"])

                if c["has_receipt"] and c["claim_id"] in st.session_state.attachments:
                    att = st.session_state.attachments[c["claim_id"]]
                    st.download_button(
                        label="📎 View Receipt (" + att["name"] + ")",
                        data=att["bytes"],
                        file_name=att["name"],
                        mime=att["type"],
                        key="dl_mgr_" + c["claim_id"],
                    )

                note = st.text_input("Note to Employee (optional)", key="note_" + c["claim_id"])
                col_a, col_r = st.columns(2)

                with col_a:
                    if st.button("✅ Approve", key="approve_" + c["claim_id"], use_container_width=True, type="primary"):
                        for claim in st.session_state.claims:
                            if claim["claim_id"] == c["claim_id"]:
                                claim["status"]        = "Approved"
                                claim["reviewer_note"] = note
                                claim["reviewed_at"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.rerun()

                with col_r:
                    if st.button("❌ Reject", key="reject_" + c["claim_id"], use_container_width=True):
                        for claim in st.session_state.claims:
                            if claim["claim_id"] == c["claim_id"]:
                                claim["status"]        = "Rejected"
                                claim["reviewer_note"] = note
                                claim["reviewed_at"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.rerun()

    with tab2:
        if not reviewed:
            st.info("No reviewed claims yet.")
        for c in reversed(reviewed):
            badge = STATUS_COLOURS.get(c["status"], "⚪")
            with st.expander(
                badge + " " + c["claim_id"] + " | " + c["submitter"]
                + " | HKD " + str(c["amount"]) + " | " + c["status"]
            ):
                st.write("**Amoeba (Class):** " + c["amoeba"])
                st.write("**Category:** " + c["category"])
                st.write("**Reviewed At:** " + c["reviewed_at"])
                if c["reviewer_note"]:
                    st.write("**Note:** " + c["reviewer_note"])


# ──────────────────────────────────────────────
# FINANCE VIEW
# ──────────────────────────────────────────────
elif role == "Finance":
    st.header("💼 Finance Dashboard — QBO Export")

    approved   = [c for c in st.session_state.claims if c["status"] == "Approved"]
    all_claims = st.session_state.claims

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Claims",       len(all_claims))
    col2.metric("Approved",           len(approved))
    col3.metric("Pending",            len([c for c in all_claims if c["status"] == "Pending"]))
    col4.metric("Total Approved HKD", str(round(sum(c["amount"] for c in approved), 2)))

    st.divider()

    if approved:
        st.subheader("📊 Approved Spend by Amoeba (Class)")
        df_approved    = pd.DataFrame(approved)
        amoeba_summary = (
            df_approved.groupby("amoeba")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amoeba": "Amoeba (Class)", "amount": "Total HKD"})
            .sort_values("Total HKD", ascending=False)
        )
        st.dataframe(amoeba_summary, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("⬇️ QuickBooks Online — Bills Import CSV")

    if not approved:
        st.warning("No approved claims to export yet.")
    else:
        rows = []
        for c in approved:
            rows.append({
                "BillNo":          c["claim_id"],
                "Supplier":        c["submitter"],
                "BillDate":        c["expense_date"],
                "DueDate":         c["expense_date"],
                "Terms":           "",
                "Account":         c["category"],
                "LineDescription": c["description"],
                "LineAmount":      c["amount"],
                "LineTaxCode":     "Non",
                "Class":           c["amoeba"],
            })

        df_qbo = pd.DataFrame(rows)
        st.dataframe(df_qbo, use_container_width=True, hide_index=True)

        csv_buffer = io.StringIO()
        df_qbo.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename  = "qbo_bills_export_" + timestamp + ".csv"

        st.download_button(
            label="⬇️ Download QBO Bills CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

        st.divider()
        st.subheader("📋 All Claims Log")
        df_all = pd.DataFrame(all_claims)
        if not df_all.empty:
            st.dataframe(df_all, use
