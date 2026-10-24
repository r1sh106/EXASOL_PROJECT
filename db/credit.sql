CREATE TABLE CREDIT(store_id DECIMAL(18,0),customer_name VARCHAR(100) NOT NULL,current_credit_balance DECIMAL(10,2),CONSTRAINT fk_credit_store FOREIGN KEY(store_id) REFERENCES STORE(store_id));
