# expense_app_qbo.py
# Expense Claim Web App — SaaS Martech Edition
# QBO Bills CSV export with Class (Amoeba) tracking
# Run: streamlit run expense_app_qbo.py

import streamlit as st
import pandas as pd
import uuid
from datetime import date, datetime
import io
import base64

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Expense Claims",
    page_icon="🧾",
    layout="wide",
)

# ──────────────────────────────────────────────
# MASTER DATA  ← customise to your org
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

# Map each Amoeba to its approving manager
AMOEBA_MANAGERS = {
    "Sales - Enterprise":      "Alice Ng",
    "Sales - SMB":             "Alice Ng",
    "Marketing - Growth":      "Brian Chan",
    "Marketing - Brand":       "Brian Chan",
    "Customer Success":        "Carol Lam",
    "Product & Engineering":   "David Wu",
    "Finance & Operations":    "Eva Cheung",
    "People & Culture":        "Eva Cheung",
}

# QBO Chart of Accounts labels — match exactly to your QBO setup
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
# SESSION STATE BOOTSTRAP
# ──────────────────────────────────────────────
if "claims" not in st.session_state:
    st.session_state.claims = []          # list of dicts
if "attachments" not in st.session_state:
    st.session_state.attachments = {}     # claim_id → file bytes


def generate_claim_id():
    return "EXP-" + str(uuid.uuid4())[:8].upper()


# ──────────────────────────────────────────────
# SIDEBAR — role & user switcher
# ──────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/invoice.png",
        width=64,
    )
    st.title("Expense Claims")
    st.divider()

    role = st.selectbox("🔑 Login as Role", ROLES)

    if role == "Employee":
        user_name = st.text_input("Your Name", value="New Employee")
        user_amoeba = st.selectbox("Your Amoeba (Department)", AMOEBAS)
    elif role == "Manager":
        manager_name = st.selectbox(
            "Manager Name", list(set(AMOEBA_MANAGERS.values()))
        )
        # derive which amoebas this manager owns
        managed_amoebas = [
            a for a, m in AMOEBA_MANAGERS.items() if m == manager_name
        ]
    else:
        user_name = "Finance Team"

    st.divider()
    st.caption("© 2026 SaaS Martech — Internal Tool")

# ──────────────────────────────────────────────
# EMPLOYEE VIEW — Submit a claim
# ──────────────────────────────────────────────
if role == "Employee":
    st.header("📋 Submit Expense Claim")

    with st.form("claim_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            expense_date = st.date_input("Expense Date", value=date.today())
            amount = st.number_input(
                "Amount (HKD)", min_value=0.01, step=0.01, format="%.2f"
            )
            category = st.selectbox("Category (QBO Account)", QBO_ACCOUNTS)

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
            f"💡 This claim will be routed to **{AMOEBA_MANAGERS[user_amoeba]}** "
            f"for approval on behalf of **{user_amoeba}**."
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
                    f"✅ Claim **{claim_id}** submitted! "
                    f"Pending approval from {AMOEBA_MANAGERS[user_amoeba]}."
                )

    # ── My Claims history
    st.divider()
    st.subheader("📂 My Claims")
    my_claims = [c for c in st.session_state.claims if c["submitter"] == user_name]

    if not my_claims:
        st.info("No claims submitted yet.")
    else:
        for c in reversed(my_claims):
            badge = STATUS_COLOURS.get(c["status"], "⚪")
            with st.expander(
                f"{badge} {c['claim_id']} | HKD {c['amount']:,.2f} | "
                f"{c['category']} | {c['expense_date']}"
            ):
                st.write(f"**Amoeba (Class):** {c['amoeba']}")
                st.write(f"**Description:** {c['description']}")
                st.write(f"**Status:** {c['status']}")
                if c["reviewer_note"]:
                    st.write(f"**Manager Note:** {c['reviewer_note']}")
                if c["has_receipt"] and c["claim_id"] in st.session_state.attachments:
                    att = st.session_state.attachments[c["claim_id"]]
                    st.download_button(
                        f"⬇️ Download Receipt ({att['name']})",
                        data=att["bytes"],
                        file_name=att["name"],
                        mime=att["type"],
                        key=f"dl_emp_{c['claim_id']}",
                    )

# ──────────────────────────────────────────────
# MANAGER VIEW — Approval Queue
# ──────────────────────────────────────────────
elif role == "Manager":
    st.header(f"✅ Approval Queue — {manager_name}")
    st.caption(f"Managing Amoebas: {', '.join(managed_amoebas)}")

    pending = [
        c for c in st.session_state.claims
        if c["manager"] == manager_name and c["status"] == "Pending"
    ]
    reviewed = [
        c for c in st.session_state.claims
        if c["manager"] == manager_name and c["status"] != "Pending"
    ]

    tab1, tab2 = st.tabs([f"⏳ Pending ({len(pending)})", f"📋 Reviewed ({len(reviewed)})"])

    with tab1:
        if not pending:
            st.success("No pending claims. All clear! 🎉")
        for idx, c in enumerate(pending):
            with st.expander(
                f"🟡 {c['claim_id']} | {c['submitter']} | "
                f"HKD {c['amount']:,.2f} | {c['amoeba']}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Submitter:** {c['submitter']}")
                    st.write(f"**Amoeba (Class):** {c['amoeba']}")
                    st.write(f"**Expense Date:** {c['expense_date']}")
                    st.write(f"**Amount:** HKD {c['amount']:,.2f}")
                with col2:
                    st.write(f"**Category:** {c['category']}")
                    st.write(f"**Submitted:** {c['submitted_at']}")
                    st.write(f"**Receipt Attached:** {'Yes ✅' if c['has_receipt'] else 'No ❌'}")

                st.write(f"**Description:** {c['description']}")

                if c["has_receipt"] and c["claim_id"] in st.session_state.attachments:
                    att = st.session_state.attachments[c["claim_id"]]
                    st.download_button(
                        f"📎 View Receipt ({att['name']})",
                        data=att["bytes"],
                        file_name=att["name"],
                        mime=att["type"],
                        key=f"dl_mgr_{c['claim_id']}",
                    )

                note = st.text_input(
                    "Note to Employee (optional)",
                    key=f"note_{c['claim_id']}",
                )
                col_a, col_r = st.columns(2)

                with col_a:
                    if st.button(
                        "✅ Approve", key=f"approve_{c['claim_id']}",
                        use_container_width=True, type="primary"
                    ):
                        for claim in st.session_state.claims:
                            if claim["claim_id"] == c["claim_id"]:
                                claim["status"] = "Approved"
                                claim["reviewer_note"] = note
                                claim["reviewed_at"] = datetime.now().strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                        st.rerun()

                with col_r:
                    if st.button(
                        "❌ Reject", key=f"reject_{c['claim_id']}",
                        use_container_width=True,
                    ):
                        for claim in st.session_state.claims:
                            if claim["claim_id"] == c["claim_id"]:
                                claim["status"] = "Rejected"
                                claim["reviewer_note"] = note
                                claim["reviewed_at"] = datetime.now().strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                        st.rerun()

    with tab2:
        if not reviewed:
            st.info("No reviewed claims yet.")
        for c in reversed(reviewed):
            badge = STATUS_COLOURS.get(c["status"], "⚪")
            with st.expander(
                f"{badge} {c['claim_id']} | {c['submitter']} | "
                f"HKD {c['amount']:,.2f} | {c['status']}"
            ):
                st.write(f"**Amoeba (Class):** {c['amoeba']}")
                st.write(f"**Category:** {c['category']}")
                st.write(f"**Reviewed At:** {c['reviewed_at']}")
                if c["reviewer_note"]:
                    st.write(f"**Note:** {c['reviewer_note']}")

# ──────────────────────────────────────────────
# FINANCE VIEW — QBO Bills CSV Export
# ──────────────────────────────────────────────
elif role == "Finance":
    st.header("💼 Finance Dashboard — QBO Export")

    approved = [c for c in st.session_state.claims if c["status"] == "Approved"]
    all_claims = st.session_state.claims

    # ── KPI Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Claims", len(all_claims))
    col2.metric("Approved", len(approved))
    col3.metric(
        "Pending",
        len([c for c in all_claims if c["status"] == "Pending"]),
    )
    col4.metric(
        "Total Approved (HKD)",
        f"{sum(c['amount'] for c in approved):,.2f}",
    )

    st.divider()

    # ── Amoeba breakdown
    if approved:
        st.subheader("📊 Approved Spend by Amoeba (Class)")
        df_approved = pd.DataFrame(approved)
        amoeba_summary = (
            df_approved.groupby("amoeba")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amoeba": "Amoeba (Class)", "amount": "Total HKD"})
            .sort_values("Total HKD", ascending=False)
        )
        st.dataframe(amoeba_summary, use_container_width=True, hide_index=True)

    st.divider()

    # ── QBO Bills CSV Export
    st.subheader("⬇️ QuickBooks Online — Bills Import CSV")

    if not approved:
        st.warning("No approved claims to export yet.")
    else:
        # ── Build QBO Bills CSV
        # QBO Bills import required columns:
        # BillNo, Supplier, BillDate, DueDate, Terms,
        # Location, Memo, Account, LineDescription,
        # LineAmount, LineTaxCode, Class
        rows = []
        for c in approved:
            rows.append({
                "BillNo":           c["claim_id"],
                "Supplier":         c["submitter"],
                "BillDate":         c["expense_date"],
                "
