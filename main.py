from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db_utils import (
    get_connection,
    verify_user,
    get_dashboard_metrics,
    get_department_spend
)
import pandas as pd
import os
from sqlalchemy import create_engine

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database configuration
DATABASE_URI = 'mysql+mysqlconnector://root:admin@localhost/retail_db'
engine = create_engine(DATABASE_URI)

# Table schemas
TABLE_SCHEMAS = {
    'households': ['HSHD_NUM', 'L', 'AGE_RANGE', 'MARITAL', 'INCOME_RANGE', 'HOMEOWNER', 'HSHD_COMPOSITION', 'HH_SIZE', 'CHILDREN'],
    'products': ['PRODUCT_NUM', 'DEPARTMENT', 'COMMODITY', 'BRAND_TY', 'NATURAL_ORGANIC_FLAG'],
    'transactions': ['BASKET_NUM', 'HSHD_NUM', 'PURCHASE_DATE', 'PRODUCT_NUM', 'SPEND', 'UNITS', 'STORE_R', 'WEEK_NUM', 'YEAR']
}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if verify_user(username, password):
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('login.html', error="Invalid credentials")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
    metrics = get_dashboard_metrics()
    chart_data = get_department_spend()
    labels = [row['DEPARTMENT'] for row in chart_data]
    values = [row['total_spend'] for row in chart_data]
    return render_template(
        'dashboard.html',
        username=session['username'],
        metrics=metrics,
        labels=labels,
        values=values
    )

@app.route('/validate_upload', methods=['POST'])
def validate_upload():
    if 'username' not in session:
        return jsonify({'valid': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    table_name = data.get('table_name', '').lower()
    csv_headers = [h.strip().upper() for h in data.get('headers', [])]
    
    if not table_name or not csv_headers:
        return jsonify({'valid': False, 'message': 'Missing parameters'}), 400
    
    expected_columns = TABLE_SCHEMAS.get(table_name)
    if not expected_columns:
        return jsonify({'valid': False, 'message': 'Invalid table name'}), 400
    
    missing_columns = [col for col in expected_columns if col not in csv_headers]
    if missing_columns:
        return jsonify({
            'valid': False,
            'message': f'Missing columns: {", ".join(missing_columns)}'
        }), 400
    
    return jsonify({'valid': True, 'message': 'CSV matches table structure'})

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        table_name = request.form.get('table_name', '').lower()
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not table_name or table_name not in TABLE_SCHEMAS:
            flash('Invalid table selected', 'danger')
            return redirect(request.url)
        
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip().str.upper()
            
            missing_cols = [col for col in TABLE_SCHEMAS[table_name] if col not in df.columns]
            if missing_cols:
                flash(f'Missing columns: {", ".join(missing_cols)}', 'danger')
                return redirect(request.url)
            
            with engine.begin() as connection:
                df.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
            
            flash(f'Successfully uploaded {len(df)} records to {table_name} table!', 'success')
            return redirect(url_for('upload'))
            
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('upload.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('dashboard'))

    hshd_num = None
    results = None
    error = None
    
    if request.method == 'POST':
        hshd_num = request.form.get('hshd_num')
        if hshd_num:
            try:
                results = get_household_data(hshd_num)
                if not results:
                    error = f"No transactions found for household #{hshd_num}"
            except Exception as e:
                error = f"Error fetching data: {str(e)}"
                results = None

    return render_template('search.html',
                        hshd_num=hshd_num,
                        results=results,
                        error=error)

if __name__ == '__main__':
    app.run(debug=True)