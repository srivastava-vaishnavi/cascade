DROP TABLE IF EXISTS demo_source_db.customers CASCADE;

CREATE TABLE demo_source_db.customers (
    customer_id bigint primary key,
    customer_email varchar(255),
    full_name varchar(255),
    signup_date date,
    country varchar(100)
);