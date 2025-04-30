import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

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
        

# Step 1: Load data
transactions = pd.read_sql('SELECT * FROM transactions', engine)

# Step 2: Data Cleaning
# Ensure 'purchase_date' and 'spend' are correct types
transactions['purchase_date'] = pd.to_datetime(transactions['purchase_date'], errors='coerce')
transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')

# Drop rows where essential fields are missing
transactions = transactions.dropna(subset=['purchase_date', 'spend', 'hshd_num'])

# Step 3: Feature Engineering
transactions['month'] = transactions['purchase_date'].dt.month

monthly_spend = transactions.groupby(['hshd_num', 'month']).agg({'spend':'sum'}).reset_index()

pivot = monthly_spend.pivot(index='hshd_num', columns='month', values='spend').fillna(0)

# Create churn label
pivot['churn_risk'] = (pivot[8] < pivot[7]*0.5).astype(int)

# Step 4: Prepare features and labels
X = pivot.drop('churn_risk', axis=1)   # Features: monthly spend patterns
y = pivot['churn_risk']                # Label: churn (0/1)

# Step 5: Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 6: Model Training
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 7: Predictions
y_pred = model.predict(X_test)

# Step 8: Evaluation
print("Classification Report:")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Step 9: Visualization
pivot['churn_risk'].value_counts().plot(kind='bar')
plt.title('Churn Risk Distribution')
plt.xlabel('Churn Risk (0 = No, 1 = Yes)')
plt.ylabel('Number of Households')
plt.show()
