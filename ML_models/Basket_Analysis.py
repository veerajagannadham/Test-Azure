import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# Database configuration for Azure MySQL
db_connection_config = {
    "user": "admin_user",
    "password": "Root123***",
    "host": "azure-retail-webapp.mysql.database.azure.com",
    "database": "azure_retail",
    "port": 3306,
}

# Connection string
db_connection_string = (
    f"mysql+pymysql://{db_connection_config['user']}:{db_connection_config['password']}"
    f"@{db_connection_config['host']}:{db_connection_config['port']}/{db_connection_config['database']}"
    "?ssl_ca=DigiCertGlobalRootCA.crt.pem&ssl_verify_cert=true"
)
engine = create_engine(db_connection_string)


# Step 2: Load the data
transactions = pd.read_sql('SELECT * FROM transactions', engine)

# Step 3: Data Cleaning
# Ensure 'spend' and 'units' are numeric
transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')
transactions['units'] = pd.to_numeric(transactions['units'], errors='coerce')

# Drop rows with missing spend or units
transactions = transactions.dropna(subset=['spend', 'units'])

# Step 4: Feature Engineering
# Create a target variable: high_purchase (1 if units > 3, else 0)
transactions['high_purchase'] = (transactions['units'] > 3).astype(int)

# Step 5: Prepare features and labels
X = transactions[['spend', 'units']]  # Features
y = transactions['high_purchase']     # Target

# Step 6: Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 7: Model Training
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# Step 8: Prediction and Evaluation
y_pred = clf.predict(X_test)

print("Classification Report:")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print("Training Accuracy:", clf.score(X_train, y_train))
print("Testing Accuracy:", clf.score(X_test, y_test))

# Scatter plot of Spend vs Units, colored by high_purchase
plt.figure(figsize=(8,6))
plt.scatter(transactions['spend'], transactions['units'], c=transactions['high_purchase'], cmap='coolwarm', alpha=0.6)
plt.title('Spend vs Units (colored by High Purchase)')
plt.xlabel('Spend')
plt.ylabel('Units')
plt.colorbar(label='High Purchase (0 = No, 1 = Yes)')
plt.grid(True)
plt.show()


