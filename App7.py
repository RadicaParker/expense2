import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import date

DB_FILE = "expense_app.db"


st.set_page_config(
    page_title="Radica Amoeba Expense",
    page_icon="💸",
    layout="wide"
)


def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def exec_sql(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def fetch_one(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_df(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def safe_add_column(table_name, column_def):
    try:
        exec_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
    except:
        pass


def init_db():
    exec_sql(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT UNIQUE, "
        "name TEXT, "
        "password TEXT, "
        "role TEXT)"
    )

    exec_sql(
        "CREATE TABLE IF NOT EXISTS expenses ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "expense_date TEXT, "
        "user_email TEXT, "
        "amoeba TEXT, "
        "category TEXT, "
        "description TEXT, "
        "amount REAL, "
        "currency TEXT, "
        "payment_method TEXT, "
        "receipt_name TEXT, "
        "status TEXT, "
        "assigned_approver TEXT, "
        "approver_comment TEXT, "
        "approved_by TEXT)"
    )

    exec_sql(
        "CREATE TABLE IF NOT EXISTS amoebas ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name TEXT UNIQUE)"
    )

    exec_sql(
        "CREATE TABLE IF NOT EXISTS categories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name TEXT UNIQUE)"
    )

    exec_sql(
        "CREATE TABLE IF NOT EXISTS payment_methods ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name TEXT UNIQUE)"
    )

    safe_add_column("users", "approver_email TEXT")
    safe_add_column("users", "user_amoeba TEXT")
    safe_add_column("expenses", "assigned_approver TEXT")
    safe_add_column("expenses", "currency TEXT")
    safe_add_column("expenses", "approver_comment TEXT")
    safe_add_column("expenses", "approved_by TEXT")

    admin_count = fetch_one(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    )[0]

    if admin_count == 0:
        exec_sql(
            "INSERT INTO users (email, name, password, role, approver_email, user_amoeba) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("admin@taxhacker.com", "Admin", hash_pw("Admin123!"), "admin", "", "")
        )

    amoeba_count = fetch_one("SELECT COUNT(*) FROM amoebas")[0]
    if amoeba_count == 0:
        default_amoebas = ["Marketing", "Sales", "Finance", "Operations", "Product"]
        for item in default_amoebas:
            exec_sql("INSERT INTO amoebas (name) VALUES (?)", (item,))

    category_count = fetch_one("SELECT COUNT(*) FROM categories")[0]
    if category_count == 0:
        default_categories = ["Travel", "Meal", "Software", "Office Supplies", "Other"]
        for item in default_categories:
            exec_sql("INSERT INTO categories (name) VALUES (?)", (item,))

    payment_count = fetch_one("SELECT COUNT(*) FROM payment_methods")[0]
    if payment_count == 0:
        default_payments = ["Corporate Card", "Cash", "Personal Card", "Bank Transfer"]
        for item in default_payments:
            exec_sql("INSERT INTO payment_methods (name) VALUES (?)", (item,))


def create_user(email, name, password, role="user", approver_email="", user_amoeba=""):
    try:
        exec_sql(
            "INSERT INTO users (email, name, password, role, approver_email, user_amoeba) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (email, name, hash_pw(password), role, approver_email, user_amoeba)
        )
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."


def login_user(email, password):
    return fetch_one(
        "SELECT email, name, role FROM users WHERE email = ? AND password = ?",
        (email, hash_pw(password))
    )


def get_names(table_name):
    df = fetch_df(f"SELECT name FROM {table_name} ORDER BY name")
    if df.empty:
        return []
    return df["name"].tolist()


def add_item(table_name, name):
    try:
        exec_sql(f"INSERT INTO {table_name} (name) VALUES (?)", (name,))
        return True, "Added successfully."
    except sqlite3.IntegrityError:
        return False, "This item already exists."


def get_user_profile(user_email):
    row = fetch_one(
        "SELECT approver_email, user_amoeba FROM users WHERE email = ?",
        (user_email,)
    )
    if row:
        approver_email = row[0] if row[0] else ""
        user_amoeba = row[1] if row[1] else ""
        return approver_email, user_amoeba
    return "", ""


def logout():
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_name = ""
    st.session_state.user_role = ""


init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""


st.title("💸 Radica Amoeba Expense")


if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        st.subheader("Login")
        st.caption("Admin login: admin@taxhacker.com / Admin123!")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                user = login_user(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.user_role = user[2]
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")

    with tab2:
        st.subheader("Create Account")

        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_btn = st.form_submit_button("Create Account")

            if signup_btn:
                if not name or not email or not password:
                    st.error("Please fill in all fields.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok, msg = create_user(email, name, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

else:
    st.sidebar.success(f"Logged in as {st.session_state.user_name}")
    st.sidebar.write(f"Role: {st.session_state.user_role}")

    if st.session_state.user_role == "admin":
        menu = st.sidebar.radio(
            "Navigation",
            ["Expense Form", "My Expenses", "All Expenses", "Approval Queue", "User Management", "Master Data"]
        )
    else:
        menu = st.sidebar.radio(
            "Navigation",
            ["Expense Form", "My Expenses", "Approval Queue"]
        )

    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    if menu == "Expense Form":
        st.subheader("Submit Expense")

        categories = get_names("categories")
        payment_methods = get_names("payment_methods")
        currencies = ["HKD", "CNY", "USD"]

        approver_email, user_amoeba = get_user_profile(st.session_state.user_email)

        with st.form("expense_form"):
            col1, col2 = st.columns(2)

            with col1:
                expense_date = st.date_input("Expense Date", value=date.today())
                category = st.selectbox("Expense Category", categories)
                currency = st.selectbox("Currency", currencies)

            with col2:
                amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
                payment_method = st.selectbox("Payment Method", payment_methods)
                receipt = st.file_uploader(
                    "Upload Receipt (optional)",
                    type=["pdf", "png", "jpg", "jpeg"]
                )

            st.text_input("Amoeba / Department", value=user_amoeba, disabled=True)
            description = st.text_area("Description")
            save_btn = st.form_submit_button("Save Expense")

            if save_btn:
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                elif approver_email == "":
                    st.error("No approver is assigned to your account. Please contact admin.")
                elif user_amoeba == "":
                    st.error("No Amoeba / Department is assigned to your account. Please contact admin.")
                else:
                    receipt_name = receipt.name if receipt else ""
                    exec_sql(
                        "INSERT INTO expenses "
                        "(expense_date, user_email, amoeba, category, description, amount, currency, payment_method, receipt_name, status, assigned_approver, approver_comment, approved_by) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            str(expense_date),
                            st.session_state.user_email,
                            user_amoeba,
                            category,
                            description,
                            amount,
                            currency,
                            payment_method,
                            receipt_name,
                            "Submitted",
                            approver_email,
                            "",
                            ""
                        )
                    )
                    st.success("Expense submitted for approval.")
                    st.rerun()

    elif menu == "My Expenses":
        st.subheader("My Expenses")

        df = fetch_df(
            "SELECT id, expense_date, amoeba, category, description, amount, currency, payment_method, receipt_name, status, assigned_approver, approver_comment, approved_by "
            "FROM expenses WHERE user_email = ? ORDER BY id DESC",
            (st.session_state.user_email,)
        )

        if df.empty:
            st.info("No expenses submitted yet.")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Download My Expenses CSV",
                df.to_csv(index=False).encode("utf-8"),
                "my_expenses.csv",
                "text/csv"
            )

    elif menu == "All Expenses" and st.session_state.user_role == "admin":
        st.subheader("All Expenses")

        df = fetch_df("SELECT * FROM expenses ORDER BY id DESC")

        if df.empty:
            st.info("No expense records found.")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Download All Expenses CSV",
                df.to_csv(index=False).encode("utf-8"),
                "all_expenses.csv",
                "text/csv"
            )

    elif menu == "Approval Queue":
        st.subheader("Approval Queue")

        pending_df = fetch_df(
            "SELECT id, expense_date, user_email, amoeba, category, description, amount, currency, payment_method, receipt_name, status "
            "FROM expenses WHERE status = ? AND assigned_approver = ? ORDER BY id DESC",
            ("Submitted", st.session_state.user_email)
        )

        if pending_df.empty:
            st.info("No expenses waiting for your approval.")
        else:
            st.dataframe(pending_df, use_container_width=True)

            option_map = {
                f"ID {row['id']} | {row['user_email']} | {row['currency']} {row['amount']:.2f} | {row['category']}": row["id"]
                for _, row in pending_df.iterrows()
            }

            selected_label = st.selectbox("Select expense to review", list(option_map.keys()))
            selected_id = option_map[selected_label]
            selected = pending_df[pending_df["id"] == selected_id].iloc[0]

            st.markdown("### Selected Expense")
            st.write(f"Employee: {selected['user_email']}")
            st.write(f"Date: {selected['expense_date']}")
            st.write(f"Amoeba: {selected['amoeba']}")
            st.write(f"Category: {selected['category']}")
            st.write(f"Amount: {selected['currency']} {selected['amount']:.2f}")
            st.write(f"Payment Method: {selected['payment_method']}")
            st.write(f"Description: {selected['description']}")
            st.write(f"Receipt: {selected['receipt_name']}")

            comment = st.text_area("Approval Comment")
            col_a, col_b = st.columns(2)

            with col_a:
                if st.button("Approve Expense"):
                    exec_sql(
                        "UPDATE expenses SET status = ?, approver_comment = ?, approved_by = ? WHERE id = ?",
                        ("Approved", comment, st.session_state.user_email, selected_id)
                    )
                    st.success("Expense approved.")
                    st.rerun()

            with col_b:
                if st.button("Reject Expense"):
                    exec_sql(
                        "UPDATE expenses SET status = ?, approver_comment = ?, approved_by = ? WHERE id = ?",
                        ("Rejected", comment, st.session_state.user_email, selected_id)
                    )
                    st.warning("Expense rejected.")
                    st.rerun()

    elif menu == "User Management" and st.session_state.user_role == "admin":
        st.subheader("User Management")

        users_df = fetch_df(
            "SELECT id, email, name, role, approver_email, user_amoeba FROM users ORDER BY id"
        )
        st.dataframe(users_df, use_container_width=True)

        all_user_emails = [""] + users_df["email"].tolist()
        amoeba_choices = [""] + get_names("amoebas")

        with st.form("add_user_form"):
            st.markdown("### Add New User")
            new_name = st.text_input("User Name")
            new_email = st.text_input("User Email")
            new_password = st.text_input("Temporary Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            new_approver = st.selectbox("Assigned Approver", all_user_emails)
            new_amoeba = st.selectbox("Amoeba / Department", amoeba_choices)
            add_user_btn = st.form_submit_button("Add User")

            if add_user_btn:
                if not new_name or not new_email or not new_password:
                    st.error("Please fill in all fields.")
                else:
                    ok, msg = create_user(
                        new_email,
                        new_name,
                        new_password,
                        new_role,
                        new_approver,
                        new_amoeba
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("### Update User Profile")
        non_admin_df = users_df[users_df["role"] != "admin"]

        if not non_admin_df.empty:
            user_options = {
                f"{row['name']} ({row['email']})": row["email"]
                for _, row in non_admin_df.iterrows()
            }

            selected_user_label = st.selectbox("Select user", list(user_options.keys()))
            selected_user_email = user_options[selected_user_label]

            current_row = non_admin_df[non_admin_df["email"] == selected_user_email].iloc[0]
            current_approver = current_row["approver_email"] if pd.notna(current_row["approver_email"]) else ""
            current_amoeba = current_row["user_amoeba"] if pd.notna(current_row["user_amoeba"]) else ""

            approver_index = all_user_emails.index(current_approver) if current_approver in all_user_emails else 0
            amoeba_index = amoeba_choices.index(current_amoeba) if current_amoeba in amoeba_choices else 0

            selected_approver = st.selectbox(
                "Select approver",
                all_user_emails,
                index=approver_index,
                key="approver_update"
            )

            selected_amoeba = st.selectbox(
                "Select Amoeba / Department",
                amoeba_choices,
                index=amoeba_index,
                key="amoeba_update"
            )

            if st.button("Update User Profile"):
                exec_sql(
                    "UPDATE users SET approver_email = ?, user_amoeba = ? WHERE email = ?",
                    (selected_approver, selected_amoeba, selected_user_email)
                )
                st.success("User profile updated.")
                st.rerun()

            st.markdown("### Delete User")
            if st.button("Delete Selected User"):
                exec_sql("DELETE FROM users WHERE email = ?", (selected_user_email,))
                st.success("User deleted.")
                st.rerun()

    elif menu == "Master Data" and st.session_state.user_role == "admin":
        st.subheader("Master Data Control Portal")

        tab1, tab2, tab3 = st.tabs(["Amoeba", "Expense Category", "Payment Method"])

        with tab1:
            amoeba_df = fetch_df("SELECT id, name FROM amoebas ORDER BY name")
            st.dataframe(amoeba_df, use_container_width=True)

            with st.form("add_amoeba_form"):
                new_amoeba = st.text_input("New Amoeba / Department")
                add_amoeba_btn = st.form_submit_button("Add Amoeba")

                if add_amoeba_btn:
                    if not new_amoeba.strip():
                        st.error("Please enter a value.")
                    else:
                        ok, msg = add_item("amoebas", new_amoeba.strip())
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if not amoeba_df.empty:
                amoeba_map = {row["name"]: row["id"] for _, row in amoeba_df.iterrows()}
                selected_amoeba = st.selectbox("Select Amoeba to delete", list(amoeba_map.keys()))
                if st.button("Delete Amoeba"):
                    exec_sql("DELETE FROM amoebas WHERE id = ?", (amoeba_map[selected_amoeba],))
                    st.success("Amoeba deleted.")
                    st.rerun()

        with tab2:
            category_df = fetch_df("SELECT id, name FROM categories ORDER BY name")
            st.dataframe(category_df, use_container_width=True)

            with st.form("add_category_form"):
                new_category = st.text_input("New Expense Category")
                add_category_btn = st.form_submit_button("Add Category")

                if add_category_btn:
                    if not new_category.strip():
                        st.error("Please enter a value.")
                    else:
                        ok, msg = add_item("categories", new_category.strip())
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if not category_df.empty:
                category_map = {row["name"]: row["id"] for _, row in category_df.iterrows()}
                selected_category = st.selectbox("Select Category to delete", list(category_map.keys()))
                if st.button("Delete Category"):
                    exec_sql("DELETE FROM categories WHERE id = ?", (category_map[selected_category],))
                    st.success("Category deleted.")
                    st.rerun()

        with tab3:
            payment_df = fetch_df("SELECT id, name FROM payment_methods ORDER BY name")
            st.dataframe(payment_df, use_container_width=True)

            with st.form("add_payment_form"):
                new_payment = st.text_input("New Payment Method")
                add_payment_btn = st.form_submit_button("Add Payment Method")

                if add_payment_btn:
                    if not new_payment.strip():
                        st.error("Please enter a value.")
                    else:
                        ok, msg = add_item("payment_methods", new_payment.strip())
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if not payment_df.empty:
                payment_map = {row["name"]: row["id"] for _, row in payment_df.iterrows()}
                selected_payment = st.selectbox("Select Payment Method to delete", list(payment_map.keys()))
                if st.button("Delete Payment Method"):
                    exec_sql("DELETE FROM payment_methods WHERE id = ?", (payment_map[selected_payment],))
                    st.success("Payment method deleted.")
                    st.rerun()