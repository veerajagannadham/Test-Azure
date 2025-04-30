from flask import Flask, render_template, request, redirect, url_for, session, flash, json
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "ce7583aac90d46c4846459342e69d0d7"  # Replace with a strong secret key

# Database connection configuration
db_connection_config = {
    "user": "admin13",
    "password": "Thepassword12",
    "host": "retail-server-name.mysql.database.azure.com",
    "database": "retail_db",
    "port": 3306,
}


# Connection string without SSL
db_connection_string = (
    f"mysql+pymysql://{db_connection_config['user']}:{db_connection_config['password']}"
    f"@{db_connection_config['host']}:{db_connection_config['port']}/{db_connection_config['database']}"
    f"?ssl_ca=DigiCertGlobalRootCA.crt.pem&ssl_verify_cert=true"
)

# Create SQLAlchemy engine
engine = create_engine(
    f"mysql+pymysql://{db_connection_config['user']}:{db_connection_config['password']}"
    f"@{db_connection_config['host']}:{db_connection_config['port']}/{db_connection_config['database']}"
    f"?ssl_ca=DigiCertGlobalRootCA.crt.pem&ssl_verify_cert=true",
    echo=False,  # Set to True for debugging SQL queries
    pool_pre_ping=True,  # Check connections before using them
    pool_recycle=3600  # Recycle connections after 1 hour
)



# Custom CSS for templates
def add_custom_css():
    return """
    <style>
        /* Your custom styles here */
    </style>
    """

# Template filter for formatting numbers
@app.template_filter("format_number")
def format_number(value):
    if isinstance(value, (int, float)):
        return f"{value:,.2f}" if value >= 1000 else f"{value:.2f}"
    return value

# Routes
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        
        app.logger.info(f"Attempting to register: {username}, {email}")
        
        try:
            insert_query = text(
                "INSERT INTO users (username, password, email) VALUES (:username, :password, :email)"
            )
            with engine.connect() as connection:
                result = connection.execute(insert_query, {"username": username, "password": password, "email": email})
                connection.commit()
                app.logger.info(f"Inserted {result.rowcount} rows")

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}", exc_info=True)
            flash(f"Registration failed: {str(e)}", "danger")
            # Stay on the same page to see the error message
            return render_template("home.html", custom_css=add_custom_css())

    return render_template("home.html", custom_custom_css=add_custom_css())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        query = text("SELECT * FROM users WHERE username=:username AND password=:password")
        with engine.connect() as connection:
            user = connection.execute(query, {"username": username, "password": password}).fetchone()

        if user:
            session["username"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", custom_css=add_custom_css())

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        flash("Please log in to access the dashboard.", "danger")
        return redirect(url_for("login"))

    try:
        with engine.connect() as connection:
            # Check if transactions exist
            check_query = text("SELECT COUNT(*) as count FROM transactions")
            has_transactions = connection.execute(check_query).scalar() > 0

            if not has_transactions:
                return render_template("dashboard.html", has_data=False, custom_css=add_custom_css())

            # Get metrics
            metrics_query = text("""
                SELECT 
                    SUM(spend) as total_sales,
                    AVG(spend) as avg_order,
                    COUNT(DISTINCT hshd_num) as total_customers,
                    COUNT(*) as total_transactions
                FROM transactions
            """)
            metrics = connection.execute(metrics_query).fetchone()
            metrics = {
                "total_sales": metrics[0] or 0,
                "avg_order": metrics[1] or 0,
                "total_customers": metrics[2] or 0,
                "total_transactions": metrics[3] or 0
            }

            # Get spend data
            spend_query = text("""
                SELECT purchase_date as date, SUM(spend) as spend
                FROM transactions
                GROUP BY purchase_date
                ORDER BY purchase_date
            """)
            spend_data = [
                {"date": str(row.date), "spend": float(row.spend)} 
                for row in connection.execute(spend_query)
            ]

            # Get department data
            dept_query = text("""
                SELECT department, COUNT(*) as count
                FROM products
                GROUP BY department
                ORDER BY count DESC
                LIMIT 10
            """)
            dept_data = [
                {"department": row.department, "count": int(row.count)} 
                for row in connection.execute(dept_query)
            ]

            # Get household data - using correct column names from CSV
            household_query = text("""
                SELECT HH_SIZE as household_size, COUNT(*) as count
                FROM households
                WHERE HH_SIZE IS NOT NULL
                GROUP BY HH_SIZE
            """)
            household_data = [
                {"composition": str(row.household_size), "count": int(row.count)} 
                for row in connection.execute(household_query)
            ]

            # Get region data
            region_query = text("""
                SELECT store_r as region, COUNT(*) as count
                FROM transactions
                GROUP BY store_r
            """)
            region_data = [
                {"region": row.region, "count": int(row.count)} 
                for row in connection.execute(region_query)
            ]

            # Get recent transactions
            recent_query = text("""
                SELECT hshd_num, basket_num, purchase_date, product_num, spend, units, store_r
                FROM transactions
                ORDER BY purchase_date DESC
                LIMIT 10
            """)
            recent_transactions = []
            for row in connection.execute(recent_query):
                trans = {
                    "hshd_num": row.hshd_num,
                    "basket_num": row.basket_num,
                    "purchase_date": str(row.purchase_date),
                    "product_num": row.product_num,
                    "spend": float(row.spend),
                    "units": row.units,
                    "store_region": row.store_r
                }
                recent_transactions.append(trans)

        return render_template(
            "dashboard.html",
            has_data=True,
            total_sales=metrics["total_sales"],
            avg_order=metrics["avg_order"],
            total_customers=metrics["total_customers"],
            total_transactions=metrics["total_transactions"],
            spend_data=json.dumps(spend_data),
            dept_data=json.dumps(dept_data),
            household_data=json.dumps(household_data),
            region_data=json.dumps(region_data),
            recent_transactions=recent_transactions,
            custom_css=add_custom_css(),
        )

    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template("dashboard.html", has_data=False, custom_css=add_custom_css())


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "username" not in session:
        flash("Please log in to access this page.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files["file"]
        table_name = request.form["table_name"]

        if not file:
            flash("No file selected.", "danger")
            return redirect(url_for("upload"))

        try:
            df_upload = pd.read_csv(file)
            df_upload.columns = df_upload.columns.str.strip().str.lower()

            if table_name.lower() == "transactions":
                df_upload = df_upload.head(10000)

            df_upload.to_sql(table_name, engine, if_exists="replace", index=False)
            flash(f"Table {table_name} uploaded successfully with {len(df_upload)} records!", "success")
        except Exception as e:
            flash(f"Error uploading data: {str(e)}", "danger")

    return render_template("upload.html", custom_css=add_custom_css())

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    household_info = None
    transactions = None
    
    if request.method == 'POST':
        hshd_num = request.form.get('hshd_num', '').strip()
        if not hshd_num:
            flash('Please enter a household number', 'warning')
            return render_template('search.html', custom_css=add_custom_css())
        
        try:
            with engine.connect() as conn:
                # First, let's check what columns actually exist in the households table
                columns_query = text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = :database 
                    AND TABLE_NAME = 'households'
                """)
                columns_result = conn.execute(columns_query, {"database": db_connection_config['database']})
                available_columns = [row.COLUMN_NAME for row in columns_result]
                
                # Build the query based on available columns
                select_fields = []
                if 'hshd_num' in available_columns:
                    select_fields.append('hshd_num')
                if 'loyalty_flag' in available_columns:
                    select_fields.append('loyalty_flag')
                if 'age_range' in available_columns:
                    select_fields.append('age_range')
                if 'marital_status' in available_columns:
                    select_fields.append('marital_status')
                elif 'marital_s' in available_columns:  # Alternative column name
                    select_fields.append('marital_s as marital_status')
                if 'income_range' in available_columns:
                    select_fields.append('income_range')
                if 'home_ownership' in available_columns:
                    select_fields.append('home_ownership')
                if 'household_size' in available_columns:
                    select_fields.append('household_size')
                elif 'hh_size' in available_columns:  # Alternative column name
                    select_fields.append('hh_size as household_size')
                
                if not select_fields:
                    flash("No valid columns found in households table", 'danger')
                    return render_template('search.html', custom_css=add_custom_css())
                
                household_query = text(f"""
                    SELECT {', '.join(select_fields)}
                    FROM households 
                    WHERE hshd_num = :hshd_num 
                    LIMIT 1
                """)
                
                household_result = conn.execute(household_query, {"hshd_num": hshd_num}).fetchone()
                
                if household_result:
                    household_info = dict(household_result._mapping)  # Convert to dict
                
                # Get transactions with product info
                transaction_query = text("""
                    SELECT 
                        t.basket_num, 
                        t.purchase_date, 
                        t.product_num, 
                        t.spend, 
                        t.units, 
                        t.store_r as store_region,
                        p.department,
                        p.commodity
                    FROM transactions t
                    LEFT JOIN products p ON t.product_num = p.product_num
                    WHERE t.hshd_num = :hshd_num
                    ORDER BY t.purchase_date DESC
                    LIMIT 100
                """)
                
                transaction_result = conn.execute(transaction_query, {"hshd_num": hshd_num}).fetchall()
                
                if transaction_result:
                    transactions = []
                    for row in transaction_result:
                        transactions.append({
                            'basket_num': row.basket_num,
                            'purchase_date': str(row.purchase_date),
                            'product_num': row.product_num,
                            'spend': float(row.spend),
                            'units': row.units,
                            'store_region': row.store_region,
                            'department': row.department,
                            'commodity': row.commodity
                        })
                
                if not household_info and not transactions:
                    flash(f"No data found for household {hshd_num}", 'info')
                
        except Exception as e:
            flash(f"Error searching data: {str(e)}", 'danger')
            app.logger.error(f"Search error: {str(e)}")

    return render_template('search.html',
                         household_info=household_info,
                         transactions=transactions,
                         custom_css=add_custom_css())

@app.route("/analytics")
def analytics():
    if "username" not in session:
        flash("Please log in to access this page.", "danger")
        return redirect(url_for("login"))
    
    return render_template("analytics.html", custom_css=add_custom_css())

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
