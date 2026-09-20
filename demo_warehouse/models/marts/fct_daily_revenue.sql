-- Logic: revenue aggregated by day and country. 
-- Joins to stg_customers for country only, never touches customer_email. 
-- This must stay untouched when Cascade runs.

DROP VIEW IF EXISTS marts.fct_daily_revenue;
CREATE VIEW marts.fct_daily_revenue AS
SELECT
    o.order_date,
    c.country,
    SUM(o.order_amount) AS total_revenue
FROM stage.stg_orders o
JOIN stage.stg_customers c
    ON o.customer_id = c.customer_id
GROUP BY o.order_date, c.country;