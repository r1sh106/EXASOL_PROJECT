-- name: now
SELECT CURRENT_TIMESTAMP;

-- name: customer_exists
SELECT COUNT(*) FROM CUSTOMERS WHERE customer_phone = {phone};

-- name: update_customer
UPDATE CUSTOMERS SET customer_name = {name}, location = {loc}
WHERE customer_phone = {phone};

-- name: insert_customer
INSERT INTO CUSTOMERS (customer_phone, customer_name, location)
VALUES ({phone}, {name}, {loc});

-- name: get_customer_name
SELECT customer_name FROM CUSTOMERS WHERE customer_phone = {phone};

-- name: insert_order
INSERT INTO ORDERS (store_id, customer_name, customer_phone, delivery_time, status)
VALUES ({sid}, {name}, {phone}, {dt}, 'NEW');

-- name: latest_order_id
SELECT MAX(order_id) FROM ORDERS WHERE customer_phone = {phone};

-- name: insert_item
INSERT INTO ORDER_ITEMS (order_id, item, quantity, price)
VALUES ({oid}, {item}, {qty}, {price});

-- name: order_info
SELECT status, delivery_time, created_at FROM ORDERS WHERE order_id = {oid};

-- name: order_items
SELECT item, quantity FROM ORDER_ITEMS WHERE order_id = {oid};

-- name: current_status
SELECT status FROM ORDERS WHERE order_id = {oid};

-- name: update_status
UPDATE ORDERS SET status = {st} WHERE order_id = {oid};

-- name: record_delivered_sales
INSERT INTO SALES (store_id, product_name, product_price, product_quantity, date_of_sale, credit)
SELECT o.store_id, i.item, i.price, i.quantity, CURRENT_DATE, FALSE
FROM ORDERS o JOIN ORDER_ITEMS i ON o.order_id = i.order_id
WHERE o.order_id = {oid};

-- name: sales_summary
SELECT COUNT(*), COALESCE(SUM(product_price * product_quantity), 0),
       COALESCE(SUM(product_quantity), 0)
FROM SALES WHERE store_id = {sid};

-- name: credits_due
SELECT customer_name, current_credit_balance FROM CREDIT
WHERE store_id = {sid} AND current_credit_balance > 0
ORDER BY current_credit_balance DESC;
