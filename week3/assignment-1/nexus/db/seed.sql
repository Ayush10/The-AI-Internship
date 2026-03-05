-- Nexus Multi-Agent Support — Seed Data
-- Demo-optimized: each customer maps to a test scenario

-- ============================================================
-- CUSTOMERS (5)
-- ============================================================
INSERT INTO customers (id, name, email, phone, plan, created_at, lifetime_value) VALUES
(1, 'Alice Chen',     'alice@example.com',     '+1-555-0101', 'enterprise', '2025-06-15 10:00:00+00', 4500.00),
(2, 'Bob Martinez',   'bob@example.com',       '+1-555-0102', 'pro',        '2025-09-20 14:30:00+00', 1200.00),
(3, 'Sarah Kim',      'customer3@example.com', '+1-555-0103', 'basic',      '2025-11-01 09:00:00+00',  350.00),
(4, 'David Okafor',   'david@example.com',     '+1-555-0104', 'pro',        '2025-12-10 16:45:00+00',  800.00),
(5, 'Emily Zhang',    'emily@example.com',     '+1-555-0105', 'enterprise', '2025-08-05 11:20:00+00', 6200.00);

-- ============================================================
-- ORDERS (12)
-- Key design:
--   Orders 3,7  → delivered within 30 days (return-eligible)
--   Order 10    → already refunded (not return-eligible)
--   Orders 4,5  → duplicate charge scenario for Sarah (billing test)
-- ============================================================
INSERT INTO orders (id, customer_id, product, amount, status, order_date, delivery_date, return_eligible, return_by_date) VALUES
-- Alice: enterprise customer, multiple orders
(1,  1, 'Enterprise Analytics Suite',     1200.00, 'delivered', '2025-10-01 10:00:00+00', '2025-10-05 14:00:00+00', FALSE, '2025-11-04 14:00:00+00'),
(2,  1, 'Cloud Storage Expansion Pack',    350.00, 'delivered', '2025-12-15 09:00:00+00', '2025-12-18 11:00:00+00', FALSE, '2026-01-17 11:00:00+00'),

-- Bob: recent order, return-eligible (delivered 10 days ago)
(3,  2, 'Wireless Noise-Canceling Headphones', 249.99, 'delivered', '2026-02-10 13:00:00+00', '2026-02-14 10:00:00+00', TRUE, '2026-03-16 10:00:00+00'),

-- Sarah: duplicate charge scenario (billing test)
(4,  3, 'Premium Keyboard - MX Keys',      129.99, 'delivered', '2026-01-20 15:00:00+00', '2026-01-24 09:00:00+00', FALSE, '2026-02-23 09:00:00+00'),
(5,  3, 'Premium Keyboard - MX Keys',      129.99, 'delivered', '2026-01-20 15:02:00+00', '2026-01-24 09:00:00+00', FALSE, '2026-02-23 09:00:00+00'),
(6,  3, 'USB-C Hub Adapter',                49.99, 'shipped',   '2026-02-25 10:00:00+00', NULL, TRUE, NULL),

-- David: recent order, return-eligible (delivered 5 days ago)
(7,  4, '4K Portable Monitor',             399.99, 'delivered', '2026-02-18 08:00:00+00', '2026-02-22 15:00:00+00', TRUE, '2026-03-24 15:00:00+00'),
(8,  4, 'Monitor Stand - Adjustable',       79.99, 'delivered', '2026-01-05 12:00:00+00', '2026-01-09 10:00:00+00', FALSE, '2026-02-08 10:00:00+00'),

-- Emily: enterprise, multiple orders including one refunded
(9,  5, 'Team Collaboration License (10 seats)', 2400.00, 'delivered', '2025-11-10 10:00:00+00', '2025-11-10 10:05:00+00', FALSE, '2025-12-10 10:05:00+00'),
(10, 5, 'AI Training Credits Bundle',       500.00, 'refunded', '2026-01-15 14:00:00+00', '2026-01-15 14:05:00+00', FALSE, NULL),
(11, 5, 'Premium Support Addon',            199.00, 'delivered', '2026-02-01 09:00:00+00', '2026-02-01 09:05:00+00', FALSE, '2026-03-03 09:05:00+00'),

-- Bob: pending order
(12, 2, 'Ergonomic Mouse - MX Master',     99.99, 'pending',  '2026-02-28 16:00:00+00', NULL, TRUE, NULL);

-- ============================================================
-- SUPPORT TICKETS (8)
-- Key design:
--   Ticket 1 → billing dispute (Sarah's duplicate charge)
--   Ticket 4 → escalation-worthy (angry Emily)
--   Mix of statuses for dashboard variety
-- ============================================================
INSERT INTO support_tickets (id, customer_id, order_id, subject, description, status, priority, assigned_to, created_at) VALUES
-- Sarah's billing dispute (billing test scenario)
(1, 3, 5, 'Charged twice for MX Keys keyboard',
    'I ordered one Premium Keyboard MX Keys but I see two charges of $129.99 on my account from the same date (Jan 20). Please investigate and refund the duplicate.',
    'open', 'high', NULL, '2026-01-25 10:00:00+00'),

-- Alice: resolved ticket
(2, 1, 1, 'Analytics dashboard loading slowly',
    'The Enterprise Analytics Suite dashboard takes 15+ seconds to load since last update.',
    'resolved', 'normal', 'tech_support', '2025-10-10 08:30:00+00'),

-- Bob: return inquiry
(3, 2, 3, 'Headphones arrived with scratched case',
    'The Wireless Noise-Canceling Headphones box was damaged during shipping and the case has visible scratches. Product works fine but I want to return it.',
    'open', 'normal', NULL, '2026-02-15 14:00:00+00'),

-- Emily: angry escalation-worthy ticket
(4, 5, 10, 'STILL waiting for my refund - 3 weeks now!',
    'I was promised a refund for the AI Training Credits Bundle THREE WEEKS AGO and nothing has happened. This is completely unacceptable for an enterprise customer paying $6000+. I want this resolved TODAY or I am canceling everything.',
    'open', 'urgent', NULL, '2026-02-05 09:00:00+00'),

-- David: shipping inquiry
(5, 4, NULL, 'General question about shipping times',
    'How long does standard shipping usually take for accessories? Planning to order a few items.',
    'resolved', 'low', 'sales_team', '2026-02-10 11:00:00+00'),

-- Alice: feature request
(6, 1, NULL, 'Request: Export analytics data to CSV',
    'Would love the ability to export analytics dashboard data to CSV format for offline analysis.',
    'in_progress', 'normal', 'product_team', '2026-01-15 16:00:00+00'),

-- Emily: previous escalation (already resolved)
(7, 5, 9, 'License activation failed for 3 seats',
    'Three of our ten Team Collaboration licenses failed to activate. Getting error code TCL-403.',
    'closed', 'high', 'tech_support', '2025-11-15 10:00:00+00'),

-- Bob: order tracking
(8, 2, 12, 'When will my MX Master ship?',
    'Ordered the Ergonomic Mouse 3 days ago and it still shows pending. Any update on when it will ship?',
    'open', 'normal', NULL, '2026-03-01 09:00:00+00');

-- Reset sequences to avoid ID conflicts
SELECT setval('customers_id_seq', (SELECT MAX(id) FROM customers));
SELECT setval('orders_id_seq', (SELECT MAX(id) FROM orders));
SELECT setval('support_tickets_id_seq', (SELECT MAX(id) FROM support_tickets));
