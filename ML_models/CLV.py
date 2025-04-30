import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# Step 1: Database configuration for Azure MySQL
db_connection_config = {
    "user": "admin_user",
    "password": "Root123***",
    "host": "azure-retail-webapp.mysql.database.azure.com",
    "database": "azure_retail",
    "port": 3306,
}

# Step 2: Build connection string
db_connection_string = (
    f"mysql+pymysql://{db_connection_config['user']}:{db_connection_config['password']}"
    f"@{db_connection_config['host']}:{db_connection_config['port']}/{db_connection_config['database']}"
    "?ssl_ca=DigiCertGlobalRootCA.crt.pem&ssl_verify_cert=true"
)

# Step 3: Connect to database
engine = create_engine(db_connection_string)

# Step 4: Load transaction data
transactions = pd.read_sql('SELECT * FROM transactions', engine)

# Step 5: Data Cleaning
transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')
transactions['units'] = pd.to_numeric(transactions['units'], errors='coerce')

# Drop any transactions with missing hshd_num, spend, or units
transactions = transactions.dropna(subset=['hshd_num', 'spend', 'units'])

# Step 6: Feature Engineering
# Group by household and calculate total spend and total units
data = transactions.groupby('hshd_num').agg({
    'spend': 'sum',
    'units': 'sum'
}).reset_index()

# Step 7: Prepare features and labels
X = data[['units']]  # Feature: total units bought
y = data['spend']    # Label: total spend (proxy for CLV)

# Step 8: Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 9: Model Training
model = XGBRegressor(objective='reg:squarederror', random_state=42)
model.fit(X_train, y_train)

# Step 10: Prediction and Evaluation
y_pred = model.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Squared Error (MSE): {mse:.2f}")
print(f"R-squared (R2 Score): {r2:.2f}")

# Step 11: Visualization

# Scatter plot of true vs predicted spend
plt.figure(figsize=(8,6))
plt.scatter(y_test, y_pred, alpha=0.7, color='royalblue')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
plt.xlabel('Actual Spend (CLV)')
plt.ylabel('Predicted Spend (CLV)')
plt.title('Actual vs Predicted Customer Lifetime Value (CLV)')
plt.grid(True)
plt.show()
