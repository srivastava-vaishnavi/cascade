-- Logic: one row per customer, summarizing their orders. 
-- customer_email is wrapped in LOWER() and also sits in the GROUP BY. 
-- Tests whether Cascade can find the column inside an expression, not just a plain select.

DROP VIEW IF EXISTS marts.fct_customer_activity;
CREATE VIEW marts.fct_customer_activity AS
SELECT
    c.customer_id,
    LOWER(c.customer_email) AS customer_email_normalized,
    COUNT(o.order_id) AS order_count,
    SUM(o.order_amount) AS total_spend
FROM stage.stg_customers c
JOIN stage.stg_orders o
    ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_email;