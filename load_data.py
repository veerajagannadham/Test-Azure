import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import datetime

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

def clean_data(df):
    """Clean and standardize column names"""
    df.columns = [col.strip().lower() for col in df.columns]
    return df

def validate_data(df, table_name):
    """Basic data validation"""
    if df.empty:
        raise ValueError(f"No data found for {table_name}")
    print(f"Validating {table_name} data... {len(df)} records found")
    return True

def load_data():
    try:
        # Create database engine
        engine = create_engine(db_connection_string)
        
        # Verify data directory exists
        data_dir = 'data'
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Data directory '{data_dir}' not found")

        # Load and clean data files
        print("\nLoading data files...")
        
        # Load households data
        households_path = os.path.join(data_dir, '400_households.csv')
        households = pd.read_csv(households_path)
        households = clean_data(households)
        validate_data(households, 'households')
        
        # Load transactions data
        transactions_path = os.path.join(data_dir, '400_transactions.csv')
        transactions = pd.read_csv(transactions_path)
        transactions = clean_data(transactions)
        validate_data(transactions, 'transactions')
        
        # Load products data if available
        products_path = os.path.join(data_dir, '400_products.csv')
        products = None
        if os.path.exists(products_path):
            products = pd.read_csv(products_path)
            products = clean_data(products)
            validate_data(products, 'products')
        else:
            print("Products file not found, skipping")

        # Upload data to database
        print("\nUploading data to database...")
        
        # Households table
        households.to_sql(
            'households', 
            engine, 
            if_exists='replace', 
            index=False,
            method='multi',
            chunksize=1000
        )
        print("Successfully uploaded households data")
        
        # Transactions table
        transactions.to_sql(
            'transactions', 
            engine, 
            if_exists='replace', 
            index=False,
            method='multi',
            chunksize=1000
        )
        print("Successfully uploaded transactions data")
        
        # Products table if available
        if products is not None:
            products.to_sql(
                'products', 
                engine, 
                if_exists='replace', 
                index=False,
                method='multi',
                chunksize=1000
            )
            print("Successfully uploaded products data")
        
        print("\nData loading completed successfully!")
        
    except Exception as e:
        print(f"\nError loading data: {str(e)}")
        raise
    finally:
        # Ensure connection is closed
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    print("Starting data loading process...")
    load_data()
    print("Process completed.")