import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import date

DB_FILE = "expense_app.db"

st.set_page_config(page_title="TaxHacker Expense Module", page_icon="💸", layout="wide")


def conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def exec_sql(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    c.close()


def fetch_df(sql, params=()):
    c = conn()
    df = pd.read_sql_query(sql, c, params=params)
    c.close()
    return df


def fetch_one(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    c.close()
    return row


def init_db():
    exec_sql("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, password TEXT, role TEXT)")
    exec_sql("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT, user_email TEXT, amoeba TEXT, category TEXT, description TEXT, amount REAL, payment_method TEXT, receipt_name TEXT, status TEXT)")
    exec_sql("CREATE TABLE IF NOT EXISTS amoebas (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    exec_sql("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    exec_sql("CREATE TABLE IF NOT EXISTS payment_methods (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")

    admin_count = fetch_one("SELECT COUNT(*) FROM users WHERE role = 'admin'")[0]
    if admin_count == 0:
        exec_sql(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("admin@taxhacker.com", "Admin", hash_pw("Admin123!"), "admin")
        )

    amoeba_count = fetch_one("SELECT COUNT(*) FROM amoebas")[0]
    if amoeba_count == 0:
        exec_sql("INSERT INTO amoebas (name) VALUES (?)", ("Marketing",))
        exec_sql("INSERT INTO amoebas (name) VALUES (?)", ("Sales",))
        exec_sql("INSERT INTO amoebas (name) VALUES (?)", ("Finance",))
        exec_sql("INSERT INTO amoebas (name) VALUES (?)", ("Operations",))
        exec_sql("INSERT INTO amoebas (name) VALUES (?)", ("Product",))

    category_count = fetch_one("SELECT COUNT(*) FROM categories")[0]
    if category_count == 0:
        exec_sql("INSERT INTO categories (name) VALUES (?)", ("Travel",))
        exec_sql("INSERT INTO categories (name) VALUES (?)", ("Meal",))
        exec_sql("INSERT INTO categories (name) VALUES (?)", ("Software",))
        exec_sql("INSERT INTO categories (name) VALUES (?)", ("Office Supplies",))
        exec_sql("INSERT INTO categories (name) VALUES (?)", ("Other",))

    payment_count = fetch_one("SELECT COUNT(*) FROM payment_methods")[0]
    if payment_count == 0:
        exec_sql("INSERT INTO payment_methods (name) VALUES (?)", ("Corporate Card",))
        exec_sql("INSERT INTO payment_methods (name) VALUES (?)", ("Cash",))
        exec_sql("INSERT INTO payment_methods (name) VALUES (?)", ("Personal Card",))
        exec_sql("INSERT INTO payment_methods (name) VALUES (?)", ("Bank Transfer",))


def create_user(email, name, password, role="user"):
    try:
        exec_sql(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            (email, name, hash_pw(password), role)
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

st.title("💸 TaxHacker Expense Module")

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
        menu = st.sidebar.radio("Navigation", ["Expense Form", "My Expenses", "All Expenses", "User Management", "Master Data"])
    else:
        menu = st.sidebar.radio("Navigation", ["Expense Form", "My Expenses"])

    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    if menu == "Expense Form":
        st.subheader("Submit Expense")

        amoebas = get_names("amoebas")
        categories = get_names("categories")
        payment_methods = get_names("payment_methods")

        with st.form("expense_form"):
            col1, col2 = st.columns(2)

            with col1:
                expense_date = st.date_input("Expense Date", value=date.today())
                amoeba = st.selectbox("Amoeba / Department", amoebas)
                category = st.selectbox("Expense Category", categories)

            with col2:
                amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
                payment_method = st.selectbox("Payment Method", payment_methods)
                receipt = st.file_uploader("Upload Receipt (optional)", type=["pdf", "png", "jpg", "jpeg"])

            description = st.text_area("Description")
            save_btn = st.form_submit_button("Save Expense")

            if save_btn:
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    receipt_name = receipt.name if receipt else ""
                    exec_sql(
                        "INSERT INTO expenses (expense_date, user_email, amoeba, category, description, amount, payment_method, receipt_name, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            str(expense_date),
                            st.session_state.user_email,
                            amoeba,
                            category,
                            description,
                            amount,
                            payment_method,
                            receipt_name,
                            "Submitted"
                        )
                    )
                    st.success("Expense saved successfully.")
                    st.rerun()

    elif menu == "My Expenses":
        st.subheader("My Expenses")
        df = fetch_df("SELECT * FROM expenses WHERE user_email = ? ORDER BY id DESC", (st.session_state.user_email,))

        if df.empty:
            st.info("No expenses submitted yet.")
        else:
            st.metric("My Total Expenses", f"${df['amount'].sum():,.2f}")
            st.dataframe(df, use_container_width=True)
            st.download_button("Download My Expenses CSV", df.to_csv(index=False).encode("utf-8"), "my_expenses.csv", "text/csv")

    elif menu == "All Expenses" and st.session_state.user_role == "admin":
        st.subheader("All Expenses")
        df = fetch_df("SELECT * FROM expenses ORDER BY id DESC")

        if df.empty:
            st.info("No expense records found.")
        else:
            st.metric("Company Total Expenses", f"${df['amount'].sum():,.2f}")
            st.dataframe(df, use_container_width=True)
            st.download_button("Download All Expenses CSV", df.to_csv(index=False).encode("utf-8"), "all_expenses.csv", "text/csv")

    elif menu == "User Management" and st.session_state.user_role == "admin":
        st.subheader("User Management")

        users_df = fetch_df("SELECT id, email, name, role FROM users ORDER BY id")
        st.dataframe(users_df, use_container_width=True)

        with st.form("add_user_form"):
            st.markdown("### Add New User")
            new_name = st.text_input("User Name")
            new_email = st.text_input("User Email")
            new_password = st.text_input("Temporary Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            add_user_btn = st.form_submit_button("Add User")

            if add_user_btn:
                if not new_name or not new_email or not new_password:
                    st.error("Please fill in all fields.")
                else:
                    ok, msg = create_user(new_email, new_name, new_password, new_role)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        non_admin_df = users_df[users_df["role"] != "admin"]
        if not non_admin_df.empty:
            user_map = {f"{row['name']} ({row['email']})": row["id"] for _, row in non_admin_df.iterrows()}
            selected_user = st.selectbox("Select user to delete", list(user_map.keys()))
            if st.button("Delete Selected User"):
                exec_sql("DELETE FROM users WHERE id = ?", (user_map[selected_user],))
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