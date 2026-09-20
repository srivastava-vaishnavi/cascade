INSERT INTO demo_source_db.customers (customer_id, customer_email, full_name, signup_date, country)
VALUES
(1, 'alice.kumar@example.com', 'Alice Kumar', '2023-01-15', 'India'),
(2, 'bob.sharma@example.com', 'Bob Sharma', '2023-02-20', 'India'),
(3, 'carol.dsouza@example.com', 'Carol D''Souza', '2023-03-10', 'USA'),
(4, 'dev.patel@example.com', 'Dev Patel', '2023-04-05', 'India'),
(5, 'emma.wilson@example.com', 'Emma Wilson', '2023-05-18', 'UK');

INSERT INTO demo_source_db.orders (order_id, customer_id, order_amount, order_date, status)
VALUES
(101, 1, 250.00, '2024-01-05', 'completed'),
(102, 1, 75.50, '2024-01-20', 'completed'),
(103, 2, 500.00, '2024-01-12', 'pending'),
(104, 3, 120.00, '2024-01-15', 'completed'),
(105, 3, 340.75, '2024-02-02', 'completed'),
(106, 4, 90.00, '2024-02-10', 'cancelled'),
(107, 5, 610.00, '2024-02-14', 'completed'),
(108, 1, 45.25, '2024-02-18', 'completed');