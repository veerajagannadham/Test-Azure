import pandas as pd
from sqlalchemy import create_engine
from db_utils import get_connection
import os

def clean_data(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df

def validate_data(df, table_name):
    if df.empty:
        raise ValueError(f"No data found for {table_name}")
    print(f"✔ {table_name} validated with {len(df)} records")
    return True

def load_data():
    try:
        # Load CSVs
        data_dir = 'data'
        households = clean_data(pd.read_csv(os.path.join(data_dir, '400_households.csv')))
        transactions = clean_data(pd.read_csv(os.path.join(data_dir, '400_transactions.csv')))
        products = clean_data(pd.read_csv(os.path.join(data_dir, '400_products.csv')))

        validate_data(households, 'households')
        validate_data(transactions, 'transactions')
        validate_data(products, 'products')

        # Create SQLAlchemy engine using raw MySQL connector
        conn = get_connection()
        engine = create_engine(f"mysql+pymysql://root:admin@localhost:3306/retail_db")

        # Upload data
        households.to_sql('households', con=engine, if_exists='replace', index=False, chunksize=1000, method='multi')
        print("✅ Households uploaded")

        transactions.to_sql('transactions', con=engine, if_exists='replace', index=False, chunksize=1000, method='multi')
        print("✅ Transactions uploaded")

        products.to_sql('products', con=engine, if_exists='replace', index=False, chunksize=1000, method='multi')
        print("✅ Products uploaded")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Data load...")
    load_data()
    print("✅ Data load complete.")
