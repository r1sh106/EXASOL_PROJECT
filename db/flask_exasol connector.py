import os
import pyexasol

# Exasol connection settings
EXASOL_DSN = os.getenv("EXASOL_DSN", "your_host:8563")
EXASOL_USER = os.getenv("EXASOL_USER", "sys")
EXASOL_PASSWORD = os.getenv("EXASOL_PASSWORD", "exasol")

def get_exasol_connection():
    """Helper function to open a connection to your Exasol database."""
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


# 1. Add Customer Function
def add_customer(d):
    name = d.get("customerName")
    ph_no = d.get("phoneNumber")
    location = d.get("location")
    
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed"}
    
    try:
        query = "INSERT INTO customers (customer_name, phone_number, location) VALUES (:name, :ph_no, :location)"
        conn.execute(query, {'name': name, 'ph_no': ph_no, 'location': location})
        conn.close()
        return {"status": "success", "message": "Customer added successfully!"}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


# 2. Add Order Function -> returns generated order ID
def add_order(d):
    ph_no = d.get("phoneNumber")
    items = d.get("items", {})  # Nested dictionary of items
    delivery = d.get("delivery")  # quick/normal/after n days
    
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed"}
    
    try:
        query = """
            INSERT INTO orders (phone_number, items_json, delivery_type, order_status) 
            VALUES (:ph_no, :items, :delivery)
        """
        conn.execute(query, {
            'ph_no': ph_no, 
            'items': str(items), 
            'delivery': delivery
        })
        
        # Fetch the latest generated order ID for this customer
        id_query = "SELECT MAX(order_id) FROM orders WHERE phone_number = :ph_no"
        stmt = conn.execute(id_query, {'ph_no': ph_no})
        order_id = stmt.fetchone()[0]
        
        conn.close()
        return {"status": "success", "orderID": order_id, "message": "Order placed successfully!"}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


# 3. Get Order Status Function
def get_order_status(orderID):
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed"}
    
    try:
        query = "SELECT order_status FROM orders WHERE order_id = :order_id"
        stmt = conn.execute(query, {'order_id': orderID})
        result = stmt.fetchone()
        conn.close()
        
        if result:
            return {"status": "success", "orderID": orderID, "order_status": result[0]}
        else:
            return {"status": "error", "message": "Order not found"}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


# 4. Get Report Function (aggregated total sales & credits due in single response)
def get_report(storeID):
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed"}
    
    try:
        # Aggregated sales data across all customers for the store
        sales_query = "SELECT SUM(total_amount) FROM sales WHERE store_id = :store_id"
        sales_stmt = conn.execute(sales_query, {'store_id': storeID})
        total_sales = sales_stmt.fetchone()[0] or 0.0
        
        # List of credits due
        credit_query = "SELECT customer_name, credit_due FROM credit WHERE store_id = :store_id AND credit_due > 0"
        credit_stmt = conn.execute(credit_query, {'store_id': storeID})
        credits_due = [{"customer": row[0], "dueAmount": row[1]} for row in credit_stmt.fetchall()]
        
        conn.close()
        return {
            "status": "success",
            "storeID": storeID,
            "totalSales": total_sales,
            "creditsDue": credits_due
        }
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


# Setup Tables Function (executes all sql files including orders.sql)
def setup_tables():
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error", "message": "Could not connect to Exasol"}

    sql_files = ['store.sql', 'sales.sql', 'credit.sql', 'orders.sql']
    executed_files = []

    try:
        for file_name in sql_files:
            if os.path.exists(file_name):
                with open(file_name, 'r') as f:
                    script = f.read()
                    conn.execute(script)
                    executed_files.append(file_name)
        
        conn.close()
        return {"status": "success", "executed_tables": executed_files}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


def test_db():
    """Quickly tests if the database responds."""
    conn = get_exasol_connection()
    if not conn:
        return {"status": "error"}
    
    stmt = conn.execute("SELECT CURRENT_TIMESTAMP")
    result = stmt.fetchone()
    conn.close()
    return {"status": "success", "current_time": str(result[0])}
if __name__ == "__main__":
    app.run(debug=True)
