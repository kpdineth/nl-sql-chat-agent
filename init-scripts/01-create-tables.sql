-- 01-create-tables.sql
-- This runs AUTOMATICALLY the first time the database starts

-- Create a read-only user (for security — app will use this user)
CREATE USER readonly_user WITH PASSWORD 'readonly123';

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    city VARCHAR(50),
    joined_date DATE DEFAULT CURRENT_DATE
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2) NOT NULL
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample customers
INSERT INTO customers (name, email, city) VALUES
    ('Alice Smith', 'alice@email.com', 'London'),
    ('Bob Jones', 'bob@email.com', 'Sydney'),
    ('Charlie Brown', 'charlie@email.com', 'Perth'),
    ('Diana Prince', 'diana@email.com', 'Melbourne'),
    ('Eve Wilson', 'eve@email.com', 'Brisbane');

-- Insert sample products
INSERT INTO products (name, category, price) VALUES
    ('Laptop', 'Electronics', 999.99),
    ('Headphones', 'Electronics', 79.99),
    ('Coffee Maker', 'Kitchen', 49.99),
    ('Running Shoes', 'Sports', 129.99),
    ('Notebook', 'Stationery', 12.99);

-- Insert sample orders
INSERT INTO orders (customer_id, product_id, quantity, status, order_date) VALUES
    (1, 1, 1, 'delivered', '2025-01-15'),
    (1, 2, 2, 'delivered', '2025-01-20'),
    (2, 3, 1, 'shipped', '2025-02-01'),
    (3, 4, 1, 'pending', '2025-02-10'),
    (4, 1, 1, 'delivered', '2025-02-12'),
    (4, 5, 3, 'shipped', '2025-02-14'),
    (5, 2, 1, 'pending', '2025-02-20'),
    (2, 1, 1, 'cancelled', '2025-02-22'),
    (3, 3, 2, 'delivered', '2025-02-25'),
    (1, 4, 1, 'shipped', '2025-02-27');

-- Give read-only user permissions
GRANT CONNECT ON DATABASE shopdb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- Table to store visualizations later
CREATE TABLE saved_visualizations (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    chart_type VARCHAR(50),
    chart_script TEXT,
    chart_image BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT SELECT, INSERT ON saved_visualizations TO readonly_user;
GRANT USAGE ON SEQUENCE saved_visualizations_id_seq TO readonly_user;
