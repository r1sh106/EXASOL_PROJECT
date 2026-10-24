CREATE TABLE STORE(store_id DECIMAL(18,0) PRIMARY KEY,
  store_name VARCHAR(100) NOT NULL,
  store_owner_name VARCHAR(100),
  store_location VARCHAR(200),
  store_phone VARCHAR(20),
  daily_customers_estimate DECIMAL(18,0),
  store_type VARCHAR(50));
