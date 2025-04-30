import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
import importlib.util
import sys

# Create directories for outputs
os.makedirs('static/images', exist_ok=True)
os.makedirs('static/data', exist_ok=True)

# Database connection configuration
db_connection_config = {
    "user": "admin13",
    "password": "Thepassword12",
    "host": "retail-server-name.mysql.database.azure.com",
    "database": "retail_db",
    "port": 3306
}

# Connection string with SSL
db_connection_string = (
    f"mysql+pymysql://{db_connection_config['user']}:{db_connection_config['password']}"
    f"@{db_connection_config['host']}:{db_connection_config['port']}/{db_connection_config['database']}"
    f"?ssl_ca=DigiCertGlobalRootCA.crt.pem&ssl_verify_cert=true"
)

# Create SQLAlchemy engine
engine = create_engine(
    db_connection_string,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Function to load a module from file path
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Modified versions of the scripts that save outputs
def run_basket_analysis():
    engine = create_engine(db_connection_string)
    metrics = {}

    # Load the data
    transactions = pd.read_sql('SELECT * FROM transactions', engine)

    # Data Cleaning
    transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')
    transactions['units'] = pd.to_numeric(transactions['units'], errors='coerce')
    transactions = transactions.dropna(subset=['spend', 'units'])

    # Feature Engineering
    transactions['high_purchase'] = (transactions['units'] > 3).astype(int)

    # Calculate metrics
    metrics['avg_spend'] = f"${transactions['spend'].mean():.2f}"
    metrics['high_purchase_rate'] = f"{(transactions['high_purchase'].mean() * 100):.1f}%"

    # Prepare features and labels
    X = transactions[['spend', 'units']]
    y = transactions['high_purchase']

    # Train-Test Split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Model Training
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    # Model Evaluation
    from sklearn.metrics import classification_report, confusion_matrix
    y_pred = clf.predict(X_test)
    train_accuracy = clf.score(X_train, y_train)
    test_accuracy = clf.score(X_test, y_test)
    metrics['model_accuracy'] = f"{test_accuracy * 100:.1f}%"

    # Visualization
    plt.figure(figsize=(10,8))
    plt.scatter(transactions['spend'], transactions['units'], c=transactions['high_purchase'], cmap='coolwarm', alpha=0.6)
    plt.title('Spend vs Units (colored by High Purchase)')
    plt.xlabel('Spend')
    plt.ylabel('Units')
    plt.colorbar(label='High Purchase (0 = No, 1 = Yes)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('static/images/basket_analysis.png', dpi=300)
    plt.close()

    # Save metrics
    with open('static/data/basket_analysis_metrics.json', 'w') as f:
        json.dump(metrics, f)

    return metrics

def run_churn_prediction():
    engine = create_engine(db_connection_string)
    metrics = {}

    # Load data
    transactions = pd.read_sql('SELECT * FROM transactions', engine)

    # Data Cleaning
    transactions['purchase_date'] = pd.to_datetime(transactions['purchase_date'], errors='coerce')
    transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')
    transactions = transactions.dropna(subset=['purchase_date', 'spend', 'hshd_num'])

    # Feature Engineering
    transactions['month'] = transactions['purchase_date'].dt.month
    monthly_spend = transactions.groupby(['hshd_num', 'month']).agg({'spend':'sum'}).reset_index()
    pivot = monthly_spend.pivot(index='hshd_num', columns='month', values='spend').fillna(0)

    # Create churn label
    pivot['churn_risk'] = (pivot[8] < pivot[7]*0.5).astype(int)

    # Calculate metrics
    metrics['churn_rate'] = f"{pivot['churn_risk'].mean() * 100:.1f}%"
    metrics['at_risk_households'] = str(int(pivot['churn_risk'].sum()))

    # Train-Test Split
    from sklearn.model_selection import train_test_split
    X = pivot.drop('churn_risk', axis=1)
    y = pivot['churn_risk']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Model Training
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Predictions
    from sklearn.metrics import classification_report, confusion_matrix, precision_score
    y_pred = model.predict(X_test)

    # Calculate precision
    precision = precision_score(y_test, y_pred)
    metrics['model_precision'] = f"{precision * 100:.1f}%"

    # Visualization
    plt.figure(figsize=(10,8))
    pivot['churn_risk'].value_counts().plot(kind='bar')
    plt.title('Churn Risk Distribution')
    plt.xlabel('Churn Risk (0 = No, 1 = Yes)')
    plt.ylabel('Number of Households')
    plt.tight_layout()
    plt.savefig('static/images/churn_prediction.png', dpi=300)
    plt.close()

    # Save metrics
    with open('static/data/churn_prediction_metrics.json', 'w') as f:
        json.dump(metrics, f)

    return metrics

def run_clv_analysis():
    engine = create_engine(db_connection_string)
    metrics = {}

    # Load transaction data
    transactions = pd.read_sql('SELECT * FROM transactions', engine)

    # Data Cleaning
    transactions['spend'] = pd.to_numeric(transactions['spend'], errors='coerce')
    transactions['units'] = pd.to_numeric(transactions['units'], errors='coerce')
    transactions = transactions.dropna(subset=['hshd_num', 'spend', 'units'])

    # Feature Engineering
    data = transactions.groupby('hshd_num').agg({
        'spend': 'sum',
        'units': 'sum'
    }).reset_index()

    # Calculate metrics
    metrics['avg_clv'] = f"${data['spend'].mean():.2f}"

    # Train-Test Split
    from sklearn.model_selection import train_test_split
    X = data[['units']]
    y = data['spend']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Model Training
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    model = XGBRegressor(objective='reg:squarederror', random_state=42)
    model.fit(X_train, y_train)

    # Prediction and Evaluation
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    metrics['mse'] = f"{mse:.2f}"
    metrics['r2_score'] = f"{r2:.2f}"

    # Visualization
    plt.figure(figsize=(10,8))
    plt.scatter(y_test, y_pred, alpha=0.7, color='royalblue')
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
    plt.xlabel('Actual Spend (CLV)')
    plt.ylabel('Predicted Spend (CLV)')
    plt.title('Actual vs Predicted Customer Lifetime Value (CLV)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('static/images/clv_analysis.png', dpi=300)
    plt.close()

    # Save metrics
    with open('static/data/clv_analysis_metrics.json', 'w') as f:
        json.dump(metrics, f)

    return metrics

if __name__ == "__main__":
    # Run all analyses
    basket_metrics = run_basket_analysis()
    churn_metrics = run_churn_prediction()
    clv_metrics = run_clv_analysis()
    print("Analysis complete. Results saved to static/images and static/data directories.")

    # Generate HTML file with dynamic content
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Retail Analytics Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --accent-color: #e74c3c;
            --dark-color: #2c3e50;
            --light-color: #ecf0f1;
            --text-color: #333;
            --border-radius: 8px;
            --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Roboto', sans-serif;
            background-color: #f5f7fa;
            color: var(--text-color);
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--dark-color));
            color: white;
            padding: 30px;
            border-radius: var(--border-radius);
            margin-bottom: 30px;
            text-align: center;
            box-shadow: var(--box-shadow);
        }}

        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        .subtitle {{
            font-weight: 300;
            opacity: 0.9;
        }}

        .dashboard-section {{
            background: white;
            border-radius: var(--border-radius);
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: var(--box-shadow);
            transition: var(--transition);
        }}

        .dashboard-section:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }}

        h2 {{
            color: var(--dark-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--light-color);
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}

        .metric-card {{
            background: var(--light-color);
            padding: 20px;
            border-radius: var(--border-radius);
            text-align: center;
            border-left: 4px solid var(--primary-color);
        }}

        .metric-card.warning {{
            border-left-color: var(--accent-color);
        }}

        .metric-card.success {{
            border-left-color: var(--secondary-color);
        }}

        .metric-title {{
            font-size: 1rem;
            color: #7f8c8d;
            margin-bottom: 10px;
        }}

        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--dark-color);
        }}

        .chart-container {{
            margin: 25px 0;
            text-align: center;
        }}

        .chart-img {{
            max-width: 100%;
            height: auto;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
        }}

        .chart-caption {{
            font-style: italic;
            color: #7f8c8d;
            margin-top: 10px;
            text-align: center;
        }}

        .analysis-text {{
            margin-top: 20px;
            line-height: 1.7;
        }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2rem;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Retail Analytics Dashboard</h1>
            <p class="subtitle">Comprehensive insights into customer behavior and sales performance</p>
        </header>

        <div class="dashboard-section">
            <h2>Basket Analysis</h2>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Model Accuracy</div>
                    <div class="metric-value">{model_accuracy}</div>
                </div>
                
                <div class="metric-card warning">
                    <div class="metric-title">High Purchase Rate</div>
                    <div class="metric-value">{high_purchase_rate}</div>
                </div>
                
                <div class="metric-card success">
                    <div class="metric-title">Average Spend</div>
                    <div class="metric-value">{avg_spend}</div>
                </div>
            </div>

            <div class="chart-container">
                <img src="static/images/basket_analysis.png" alt="Basket Analysis Chart" class="chart-img">
                <p class="chart-caption">Spend vs Units (colored by High Purchase)</p>
            </div>

            <div class="analysis-text">
                <p>The scatter plot visualizes the relationship between spend amount and units purchased, with points colored based on "high purchase" classification (greater than 3 units). This analysis helps identify customer segments for targeted marketing strategies.</p>
                <p>Clusters in the visualization indicate distinct purchasing patterns that can inform inventory decisions and promotional campaigns.</p>
            </div>
        </div>

        <div class="dashboard-section">
            <h2>Churn Prediction</h2>
            
            <div class="metrics-grid">
                <div class="metric-card warning">
                    <div class="metric-title">Churn Rate</div>
                    <div class="metric-value">{churn_rate}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Model Precision</div>
                    <div class="metric-value">{model_precision}</div>
                </div>
                
                <div class="metric-card warning">
                    <div class="metric-title">At-Risk Households</div>
                    <div class="metric-value">{at_risk_households}</div>
                </div>
            </div>

            <div class="chart-container">
                <img src="static/images/churn_prediction.png" alt="Churn Prediction Chart" class="chart-img">
                <p class="chart-caption">Churn Risk Distribution</p>
            </div>

            <div class="analysis-text">
                <p>The bar chart displays the distribution of households at risk of churning versus those likely to remain. Churn risk is determined by a significant drop in spending (greater than 50% decrease from month 7 to month 8).</p>
                <p>Predictive features include monthly spending patterns and purchase frequency. This insight is valuable for retention campaigns and loyalty programs.</p>
            </div>
        </div>

        <div class="dashboard-section">
            <h2>Customer Lifetime Value (CLV)</h2>
            
            <div class="metrics-grid">
                <div class="metric-card success">
                    <div class="metric-title">Avg CLV</div>
                    <div class="metric-value">{avg_clv}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">R² Score</div>
                    <div class="metric-value">{r2_score}</div>
                </div>
                
                <div class="metric-card warning">
                    <div class="metric-title">MSE</div>
                    <div class="metric-value">{mse}</div>
                </div>
            </div>

            <div class="chart-container">
                <img src="static/images/clv_analysis.png" alt="CLV Analysis Chart" class="chart-img">
                <p class="chart-caption">Actual vs Predicted Customer Lifetime Value</p>
            </div>

            <div class="analysis-text">
                <p>The scatter plot compares actual versus predicted customer lifetime value (using total spend as a proxy). Points closer to the red diagonal line indicate more accurate predictions.</p>
                <p>The model uses total units purchased as the primary predictor of customer spending potential. This analysis helps identify high-value customers for premium services and personalized offers.</p>
            </div>
        </div>

        <footer>
            <p>Retail Analytics Dashboard | Generated on {current_date}</p>
            <p>Data source: Azure Retail Database | Analysis performed using Python</p>
        </footer>
    </div>
</body>
</html>"""

    # Create a dictionary with all the values needed for the template
    template_data = {
        'model_accuracy': basket_metrics.get('model_accuracy', 'N/A'),
        'high_purchase_rate': basket_metrics.get('high_purchase_rate', 'N/A'),
        'avg_spend': basket_metrics.get('avg_spend', 'N/A'),
        'churn_rate': churn_metrics.get('churn_rate', 'N/A'),
        'model_precision': churn_metrics.get('model_precision', 'N/A'),
        'at_risk_households': churn_metrics.get('at_risk_households', 'N/A'),
        'avg_clv': clv_metrics.get('avg_clv', 'N/A'),
        'r2_score': clv_metrics.get('r2_score', 'N/A'),
        'mse': clv_metrics.get('mse', 'N/A'),
        'current_date': pd.Timestamp.now().strftime('%B %d, %Y')
    }

    # Ensure templates directory exists
    os.makedirs('templates', exist_ok=True)

    # Write the formatted HTML to file
    with open('templates/analytics.html', 'w', encoding='utf-8') as f:
        f.write(html_template.format(**template_data))

    print("templates/analytics.html file generated successfully.")