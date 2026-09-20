DROP VIEW IF EXISTS stage.stg_orders;
CREATE VIEW stage.stg_orders AS
SELECT
    order_id,
    customer_id,
    order_amount,
    order_date,
    status
FROM demo_source_db.orders;