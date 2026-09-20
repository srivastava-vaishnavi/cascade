-- Logic: every order row gets the customer's email attached via join, then renamed to email. 
-- Tests whether Cascade can trace the column through a join + alias.

DROP VIEW IF EXISTS marts.fct_orders_enriched;
CREATE VIEW marts.fct_orders_enriched AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_amount,
    o.order_date,
    o.status,
    c.customer_email AS email
FROM stage.stg_orders o
JOIN stage.stg_customers c
    ON o.customer_id = c.customer_id;