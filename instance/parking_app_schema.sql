-- Parking Management System v2 - Database Schema
-- This file contains the complete database structure and sample data
-- Use this with SQLite viewer to explore the database tables

-- =====================================================
-- DATABASE SCHEMA CREATION
-- =====================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    full_name VARCHAR(100),
    address VARCHAR(200),
    pin_code VARCHAR(20),
    vehicle_no VARCHAR(20) UNIQUE,
    is_admin BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notification_preference VARCHAR(20) DEFAULT 'email',
    gchat_email VARCHAR(120),
    reminder_time VARCHAR(5) DEFAULT '18:00',
    report_format VARCHAR(10) DEFAULT 'html',
    last_reminder_date DATE
);

-- Parking Lots table
CREATE TABLE IF NOT EXISTS parking_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    prime_location_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    address VARCHAR(200) NOT NULL,
    pin_code VARCHAR(10) NOT NULL,
    maximum_number_of_spots INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Parking Spots table
CREATE TABLE IF NOT EXISTS parking_spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id INTEGER NOT NULL,
    spot_number INTEGER NOT NULL,
    status VARCHAR(1) DEFAULT 'A',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lot_id) REFERENCES parking_lots(id) ON DELETE CASCADE
);

-- Parking Reservations table
CREATE TABLE IF NOT EXISTS parking_reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    spot_id INTEGER NOT NULL,
    vehicle_no VARCHAR(20),
    parking_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    leaving_timestamp DATETIME,
    parking_cost DECIMAL(10,2),
    active BOOLEAN DEFAULT 1,
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    payment_date DATETIME,
    payment_method VARCHAR(20),
    transaction_id VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (spot_id) REFERENCES parking_spots(id) ON DELETE CASCADE
);

-- Saved Payment Methods table
CREATE TABLE IF NOT EXISTS saved_payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    card_last_four VARCHAR(4),
    card_type VARCHAR(20),
    card_holder_name VARCHAR(100),
    card_expiry VARCHAR(5),
    upi_id VARCHAR(50),
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =====================================================
-- SAMPLE DATA INSERTION
-- =====================================================

-- Insert sample users
INSERT INTO users (username, email, password_hash, phone, full_name, address, pin_code, vehicle_no, is_admin, notification_preference, reminder_time, report_format) VALUES
('Admin User', 'admin@parking.com', 'pbkdf2:sha256:600000$hash_here', '+91-9876543210', 'Admin User', '123 Admin Street, City', '123456', 'AD12MN3456', 1, 'email', '09:00', 'pdf'),
('John Doe', 'john.doe@gmail.com', 'pbkdf2:sha256:600000$hash_here', '+91-9876543211', 'John Doe', '456 User Avenue, City', '123457', 'JD12AB3456', 0, 'email', '18:00', 'html'),
('Jane Smith', 'jane.smith@yahoo.com', 'pbkdf2:sha256:600000$hash_here', '+91-9876543212', 'Jane Smith', '789 User Road, City', '123458', 'JS12CD3456', 0, 'gchat', '17:30', 'html'),
('Bob Wilson', 'bob.wilson@outlook.com', 'pbkdf2:sha256:600000$hash_here', '+91-9876543213', 'Bob Wilson', '321 User Lane, City', '123459', 'BW12EF3456', 0, 'email', '19:00', 'pdf'),
('Alice Brown', 'alice.brown@hotmail.com', 'pbkdf2:sha256:600000$hash_here', '+91-9876543214', 'Alice Brown', '654 User Drive, City', '123460', 'AB12GH3456', 0, 'email', '16:00', 'html');

-- Insert sample parking lots
INSERT INTO parking_lots (name, prime_location_name, price, address, pin_code, maximum_number_of_spots) VALUES
('Central Mall Parking', 'Central Mall', 50.00, '123 Central Street, Downtown', '123456', 100),
('Airport Terminal 1', 'Airport Terminal 1', 75.00, '456 Airport Road, Airport Area', '123457', 200),
('Business District Lot', 'Business District', 60.00, '789 Business Avenue, Business Area', '123458', 150),
('Shopping Complex A', 'Shopping Complex A', 40.00, '321 Shopping Street, Shopping Area', '123459', 80),
('Hospital Parking', 'City Hospital', 30.00, '654 Hospital Road, Medical Area', '123460', 120);

-- Insert sample parking spots for Central Mall
INSERT INTO parking_spots (lot_id, spot_number, status) VALUES
(1, 1, 'A'), (1, 2, 'A'), (1, 3, 'O'), (1, 4, 'A'), (1, 5, 'A'),
(1, 6, 'A'), (1, 7, 'O'), (1, 8, 'A'), (1, 9, 'A'), (1, 10, 'A');

-- Insert sample parking spots for Airport Terminal 1
INSERT INTO parking_spots (lot_id, spot_number, status) VALUES
(2, 1, 'A'), (2, 2, 'A'), (2, 3, 'A'), (2, 4, 'O'), (2, 5, 'A'),
(2, 6, 'A'), (2, 7, 'A'), (2, 8, 'A'), (2, 9, 'O'), (2, 10, 'A');

-- Insert sample parking spots for Business District
INSERT INTO parking_spots (lot_id, spot_number, status) VALUES
(3, 1, 'A'), (3, 2, 'O'), (3, 3, 'A'), (3, 4, 'A'), (3, 5, 'A'),
(3, 6, 'A'), (3, 7, 'A'), (3, 8, 'O'), (3, 9, 'A'), (3, 10, 'A');

-- Insert sample parking spots for Shopping Complex A
INSERT INTO parking_spots (lot_id, spot_number, status) VALUES
(4, 1, 'A'), (4, 2, 'A'), (4, 3, 'A'), (4, 4, 'A'), (4, 5, 'O'),
(4, 6, 'A'), (4, 7, 'A'), (4, 8, 'A');

-- Insert sample parking spots for Hospital
INSERT INTO parking_spots (lot_id, spot_number, status) VALUES
(5, 1, 'A'), (5, 2, 'O'), (5, 3, 'A'), (5, 4, 'A'), (5, 5, 'A'),
(5, 6, 'A'), (5, 7, 'O'), (5, 8, 'A'), (5, 9, 'A'), (5, 10, 'A');

-- Insert sample parking reservations
INSERT INTO parking_reservations (user_id, spot_id, vehicle_no, parking_timestamp, leaving_timestamp, parking_cost, active, payment_status, payment_method, transaction_id) VALUES
(2, 3, 'JD12AB3456', '2024-12-20 09:00:00', '2024-12-20 17:00:00', 400.00, 0, 'PAID', 'credit-card', 'TXN001'),
(3, 7, 'JS12CD3456', '2024-12-20 10:00:00', '2024-12-20 16:00:00', 300.00, 0, 'PAID', 'upi', 'TXN002'),
(4, 2, 'BW12EF3456', '2024-12-20 08:00:00', '2024-12-20 18:00:00', 600.00, 0, 'PAID', 'credit-card', 'TXN003'),
(5, 8, 'AB12GH3456', '2024-12-20 11:00:00', '2024-12-20 15:00:00', 240.00, 0, 'PAID', 'upi', 'TXN004'),
(2, 4, 'JD12AB3456', '2024-12-21 09:00:00', NULL, NULL, 1, 'PENDING', NULL, NULL),
(3, 9, 'JS12CD3456', '2024-12-21 10:00:00', NULL, NULL, 1, 'PENDING', NULL, NULL);

-- Insert sample saved payment methods
INSERT INTO saved_payment_methods (user_id, payment_type, card_last_four, card_type, card_holder_name, card_expiry, is_default) VALUES
(2, 'card', '1234', 'visa', 'John Doe', '12/25', 1),
(2, 'card', '5678', 'mastercard', 'John Doe', '06/26', 0),
(3, 'upi', NULL, NULL, NULL, NULL, 'jane.smith@okicici', 1),
(4, 'card', '9012', 'visa', 'Bob Wilson', '09/25', 1),
(5, 'card', '3456', 'mastercard', 'Alice Brown', '03/26', 1);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_vehicle_no ON users(vehicle_no);

CREATE INDEX IF NOT EXISTS idx_parking_lots_name ON parking_lots(name);
CREATE INDEX IF NOT EXISTS idx_parking_lots_pin_code ON parking_lots(pin_code);

CREATE INDEX IF NOT EXISTS idx_parking_spots_lot_id ON parking_spots(lot_id);
CREATE INDEX IF NOT EXISTS idx_parking_spots_status ON parking_spots(status);

CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON parking_reservations(user_id);
CREATE INDEX IF NOT EXISTS idx_reservations_spot_id ON parking_reservations(spot_id);
CREATE INDEX IF NOT EXISTS idx_reservations_active ON parking_reservations(active);
CREATE INDEX IF NOT EXISTS idx_reservations_parking_timestamp ON parking_reservations(parking_timestamp);

CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id ON saved_payment_methods(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_is_default ON saved_payment_methods(is_default);

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for available spots in each lot
CREATE VIEW IF NOT EXISTS available_spots_view AS
SELECT 
    pl.name as lot_name,
    pl.prime_location_name,
    pl.price as hourly_rate,
    COUNT(ps.id) as total_spots,
    SUM(CASE WHEN ps.status = 'A' THEN 1 ELSE 0 END) as available_spots,
    SUM(CASE WHEN ps.status = 'O' THEN 1 ELSE 0 END) as occupied_spots
FROM parking_lots pl
LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
GROUP BY pl.id, pl.name, pl.prime_location_name, pl.price;

-- View for user reservation summary
CREATE VIEW IF NOT EXISTS user_reservation_summary AS
SELECT 
    u.username,
    u.email,
    u.full_name,
    COUNT(pr.id) as total_reservations,
    SUM(CASE WHEN pr.active = 1 THEN 1 ELSE 0 END) as active_reservations,
    SUM(CASE WHEN pr.active = 0 THEN 1 ELSE 0 END) as completed_reservations,
    SUM(COALESCE(pr.parking_cost, 0)) as total_spent
FROM users u
LEFT JOIN parking_reservations pr ON u.id = pr.user_id
WHERE u.is_admin = 0
GROUP BY u.id, u.username, u.email, u.full_name;

-- View for daily revenue
CREATE VIEW IF NOT EXISTS daily_revenue_view AS
SELECT 
    DATE(pr.parking_timestamp) as date,
    COUNT(pr.id) as total_bookings,
    SUM(COALESCE(pr.parking_cost, 0)) as total_revenue,
    AVG(COALESCE(pr.parking_cost, 0)) as average_revenue_per_booking
FROM parking_reservations pr
WHERE pr.active = 0 AND pr.payment_status = 'PAID'
GROUP BY DATE(pr.parking_timestamp)
ORDER BY date DESC;

-- =====================================================
-- SAMPLE QUERIES FOR TESTING
-- =====================================================

-- Query 1: Find all available spots in a specific lot
-- SELECT ps.spot_number, pl.name as lot_name, pl.price as hourly_rate
-- FROM parking_spots ps
-- JOIN parking_lots pl ON ps.lot_id = pl.id
-- WHERE ps.status = 'A' AND pl.name = 'Central Mall Parking';

-- Query 2: Get user's active reservations with lot details
-- SELECT 
--     pr.id as reservation_id,
--     pl.name as lot_name,
--     ps.spot_number,
--     pr.parking_timestamp,
--     pr.vehicle_no,
--     pl.price as hourly_rate
-- FROM parking_reservations pr
-- JOIN parking_spots ps ON pr.spot_id = ps.id
-- JOIN parking_lots pl ON ps.lot_id = pl.id
-- WHERE pr.user_id = 2 AND pr.active = 1;

-- Query 3: Calculate total revenue by lot
-- SELECT 
--     pl.name as lot_name,
--     COUNT(pr.id) as total_bookings,
--     SUM(COALESCE(pr.parking_cost, 0)) as total_revenue
-- FROM parking_lots pl
-- LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
-- LEFT JOIN parking_reservations pr ON ps.id = pr.spot_id AND pr.active = 0
-- GROUP BY pl.id, pl.name
-- ORDER BY total_revenue DESC;

-- Query 4: Find users with most bookings
-- SELECT 
--     u.username,
--     u.full_name,
--     COUNT(pr.id) as total_bookings,
--     SUM(COALESCE(pr.parking_cost, 0)) as total_spent
-- FROM users u
-- LEFT JOIN parking_reservations pr ON u.id = pr.user_id
-- WHERE u.is_admin = 0
-- GROUP BY u.id, u.username, u.full_name
-- ORDER BY total_bookings DESC;

-- =====================================================
-- DATABASE STATISTICS
-- =====================================================

-- Get table row counts
-- SELECT 'users' as table_name, COUNT(*) as row_count FROM users
-- UNION ALL
-- SELECT 'parking_lots', COUNT(*) FROM parking_lots
-- UNION ALL
-- SELECT 'parking_spots', COUNT(*) FROM parking_spots
-- UNION ALL
-- SELECT 'parking_reservations', COUNT(*) FROM parking_reservations
-- UNION ALL
-- SELECT 'saved_payment_methods', COUNT(*) FROM saved_payment_methods;

-- Get lot occupancy statistics
-- SELECT 
--     pl.name as lot_name,
--     COUNT(ps.id) as total_spots,
--     SUM(CASE WHEN ps.status = 'A' THEN 1 ELSE 0 END) as available_spots,
--     SUM(CASE WHEN ps.status = 'O' THEN 1 ELSE 0 END) as occupied_spots,
--     ROUND((SUM(CASE WHEN ps.status = 'O' THEN 1 ELSE 0 END) * 100.0 / COUNT(ps.id)), 2) as occupancy_percentage
-- FROM parking_lots pl
-- LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
-- GROUP BY pl.id, pl.name
-- ORDER BY occupancy_percentage DESC;

-- =====================================================
-- NOTES FOR SQLITE VIEWER
-- =====================================================

/*
This SQL file contains the complete database schema for the Parking Management System v2.

To use this file with SQLite Viewer:

1. Open SQLite Viewer
2. Create a new database or open existing one
3. Execute this SQL file to create all tables and sample data
4. Explore the database structure using the viewer's interface

Key Tables:
- users: User accounts and profiles
- parking_lots: Parking lot information
- parking_spots: Individual parking spots
- parking_reservations: Booking records
- saved_payment_methods: User payment methods

Sample Data:
- 5 users (1 admin, 4 regular users)
- 5 parking lots with different capacities
- 56 parking spots across all lots
- 6 sample reservations (4 completed, 2 active)
- 5 sample payment methods

Views Available:
- available_spots_view: Shows availability by lot
- user_reservation_summary: User booking statistics
- daily_revenue_view: Revenue tracking by date

Indexes: Created for optimal query performance on frequently accessed columns.
*/
