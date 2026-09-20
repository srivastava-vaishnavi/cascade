DROP VIEW IF EXISTS stage.stg_customers;
CREATE VIEW stage.stg_customers AS
SELECT
    customer_id,
    customer_email,
    full_name,
    signup_date,
    country
FROM demo_source_db.customers;