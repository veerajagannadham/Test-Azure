import mysql.connector
import hashlib

USE_AZURE = False

def get_connection():
    if USE_AZURE:
        return mysql.connector.connect(
            host='your-azure-host.mysql.database.azure.com',
            user='azure_user',
            password='your_password',
            database='azure_db',
            ssl_ca='DigiCertGlobalRootCA.crt.pem',
            ssl_verify_cert=True
        )
    else:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='admin',
            database='retail_db',
            port=3306
        )

def register_user(username, email, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Register Error: {err}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def verify_user(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()
        return user and user['password'] == password
    except mysql.connector.Error as err:
        print(f"Login Error: {err}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_household_data(hshd_num):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
         SELECT * FROM households 
            WHERE HSHD_NUM = %s
        """, (hshd_num,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Search Error: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_dashboard_metrics():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Basic metrics
        cursor.execute("SELECT COUNT(*) AS total_transactions FROM Transactions")
        total_tx = cursor.fetchone()['total_transactions']

        cursor.execute("SELECT COUNT(DISTINCT HSHD_NUM) AS unique_households FROM Transactions")
        households = cursor.fetchone()['unique_households']

        cursor.execute("SELECT SUM(SPEND) AS total_spend FROM Transactions")
        spend = cursor.fetchone()['total_spend']

        cursor.execute("SELECT COUNT(DISTINCT PRODUCT_NUM) AS total_products FROM Products")
        products = cursor.fetchone()['total_products']

        # Additional metrics
        cursor.execute("""
            SELECT ROUND(AVG(hh_spend), 2) AS avg_spend_per_household
            FROM (
                SELECT HSHD_NUM, SUM(SPEND) AS hh_spend
                FROM Transactions
                GROUP BY HSHD_NUM
            ) AS household_spends
        """)
        avg_spend = cursor.fetchone()['avg_spend_per_household']

        cursor.execute("""
            SELECT ROUND(AVG(tx_count), 2) AS avg_transactions_per_household
            FROM (
                SELECT HSHD_NUM, COUNT(*) AS tx_count
                FROM Transactions
                GROUP BY HSHD_NUM
            ) AS household_counts
        """)
        avg_tx = cursor.fetchone()['avg_transactions_per_household']

        return {
            "total_transactions": total_tx,
            "unique_households": households,
            "total_spend": round(spend or 0, 2),
            "total_products": products,
            "avg_spend_per_household": avg_spend,
            "avg_transactions_per_household": avg_tx
        }
    except Exception as e:
        print(f"Metrics Error: {e}")
        return {}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_department_spend():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT P.DEPARTMENT, ROUND(SUM(T.SPEND), 2) AS total_spend
            FROM Transactions T
            JOIN Products P ON T.PRODUCT_NUM = P.PRODUCT_NUM
            GROUP BY P.DEPARTMENT
            ORDER BY total_spend DESC
            LIMIT 10
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Chart Error: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_department_transactions():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT P.DEPARTMENT, COUNT(*) AS transaction_count
            FROM Transactions T
            JOIN Products P ON T.PRODUCT_NUM = P.PRODUCT_NUM
            GROUP BY P.DEPARTMENT
            ORDER BY transaction_count DESC
            LIMIT 10
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Transaction Count Error: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_recent_transactions(limit=10):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT T.HSHD_NUM, T.PRODUCT_NUM, P.DEPARTMENT, T.SPEND, T.PURCHASE_DATE
            FROM Transactions T
            JOIN Products P ON T.PRODUCT_NUM = P.PRODUCT_NUM
            ORDER BY T.PURCHASE_DATE DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Recent Transactions Error: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_household_data(hshd_num):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                T.BASKET_NUM,
                T.PURCHASE_DATE as DATE,
                T.PRODUCT_NUM,
                T.SPEND,
                T.UNITS,
                P.DEPARTMENT,
                P.COMMODITY,
                H.AGE_RANGE,
                H.INCOME_RANGE
            FROM Transactions T
            JOIN Products P ON T.PRODUCT_NUM = P.PRODUCT_NUM
            JOIN Households H ON T.HSHD_NUM = H.HSHD_NUM
            WHERE T.HSHD_NUM = %s
            ORDER BY T.PURCHASE_DATE DESC, T.BASKET_NUM
        """, (hshd_num,))
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Database Error: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def save_uploaded_data(table_name, data_frame):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create table if not exists (adjust columns based on your CSV structure)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255),
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON
            )
        """)
        
        # Insert the data
        cursor.execute(f"""
            INSERT INTO {table_name} (filename, data)
            VALUES (%s, %s)
        """, (table_name, data_frame.to_json(orient='records')))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving uploaded data: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def search_uploaded_data(table_name, search_term):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"""
            SELECT data FROM {table_name}
            WHERE filename = %s
            ORDER BY upload_time DESC
            LIMIT 1
        """, (table_name,))
        
        result = cursor.fetchone()
        if result:
            import json
            data = json.loads(result['data'])
            # Filter data based on search term
            filtered_data = [row for row in data if 
                           any(str(search_term).lower() in str(v).lower() 
                           for v in row.values())]
            return filtered_data
        return []
    except Exception as e:
        print(f"Error searching data: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def search_table_data(table_name, search_term=None, hshd_num=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if table_name == "households" and hshd_num:
            return get_household_data(hshd_num)
        
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if search_term:
            # Get column names for the table
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [col[0] for col in cursor.fetchall()]
            
            # Build WHERE clause to search across all columns
            conditions = []
            for col in columns:
                conditions.append(f"{col} LIKE %s")
                params.append(f"%{search_term}%")
            
            query += " WHERE " + " OR ".join(conditions)
        
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
        
    except Error as e:
        print(f"Error searching {table_name}: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()