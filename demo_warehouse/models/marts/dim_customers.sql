DROP VIEW IF EXISTS marts.dim_customers;
CREATE VIEW marts.dim_customers AS
SELECT
    customer_id,
    customer_email,
    full_name,
    signup_date,
    country
FROM stage.stg_customers;