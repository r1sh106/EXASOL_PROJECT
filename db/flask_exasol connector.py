import os
from flask import  jsonify
import pyexasol




EXASOL_DSN = os.getenv("EXASOL_DSN", "your_host:8563")
EXASOL_USER = os.getenv("EXASOL_USER", "sys")
EXASOL_PASSWORD = os.getenv("EXASOL_PASSWORD", "exasol")

def get_exasol_connection():
    
    try:
        conn = pyexasol.connect(
            dsn=EXASOL_DSN,
            user=EXASOL_USER,
            password=EXASOL_PASSWORD,
            encryption=True  
        )
        return conn
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def add_customer(d):
    name=d["customerName"]
    ph_no=d["phoneNumber"]
    location=d["location"]



def add_order(d):
    ph_no=d["customerName"]
    delivery=d["delivery"] #integer datatype

def get_order_status(orderID):
    pass

def get_report(storeID):
    pass





    


                   


def setup_tables():
    
    conn = get_exasol_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Could not connect to Exasol"}), 500

    sql_files = ['store.sql', 'sales.sql', 'credit.sql']
    executed_files = []

    try:
        for file_name in sql_files:
            if os.path.exists(file_name):
                with open(file_name, 'r') as f:
                    script = f.read()
                    conn.execute(script)
                    executed_files.append(file_name)
        
        conn.close()
        return jsonify({"status": "success", "executed_tables": executed_files})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500


def test_db():
    """Quickly tests if the database responds."""
    conn = get_exasol_connection()
    if not conn:
        return jsonify({"status": "error"}), 500
    
    stmt = conn.execute("SELECT CURRENT_TIMESTAMP")
    result = stmt.fetchone()
    conn.close()
    return jsonify({"status": "success", "current_time": str(result[0])})

if __name__ == "__main__":
    app.run(debug=True)
