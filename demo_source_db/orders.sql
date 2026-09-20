DROP TABLE IF EXISTS demo_source_db.orders CASCADE;

CREATE TABLE demo_source_db.orders (
    order_id bigint primary key,
    customer_id bigint,
    order_amount decimal(10, 2),
    order_date date,
    status varchar(10)
);