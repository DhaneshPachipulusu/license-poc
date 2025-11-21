-- PHASE 1: Core License Control System Database Schema
-- SQLite compatible

-- Customers table (the "account" or "company")
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,  -- UUID
    company_name TEXT NOT NULL,
    product_key TEXT UNIQUE NOT NULL,
    machine_limit INTEGER DEFAULT 3 CHECK (machine_limit > 0),
    valid_days INTEGER DEFAULT 365 CHECK (valid_days > 0),
    allowed_services TEXT DEFAULT '["dashboard"]',  -- JSON array as text
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    revoked INTEGER DEFAULT 0,  -- Boolean as integer (0 = false, 1 = true)
    notes TEXT
);

-- Machines table (each activated device)
CREATE TABLE IF NOT EXISTS machines (
    id TEXT PRIMARY KEY,  -- UUID
    customer_id TEXT NOT NULL,
    machine_id TEXT UNIQUE NOT NULL,  -- Will be stored in cert, for reference
    fingerprint TEXT NOT NULL,  -- Hardware fingerprint
    hostname TEXT,
    os_info TEXT,
    app_version TEXT,
    activated_at TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'revoked')),
    certificate TEXT,  -- JSON as text
    ip_address TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Audit log (track all actions)
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,  -- UUID
    customer_id TEXT,
    machine_id TEXT,
    action TEXT NOT NULL,
    details TEXT,  -- JSON as text
    ip_address TEXT,
    user_agent TEXT,
    performed_by TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_customers_product_key ON customers(product_key);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at);
CREATE INDEX IF NOT EXISTS idx_machines_customer ON machines(customer_id);
CREATE INDEX IF NOT EXISTS idx_machines_fingerprint ON machines(fingerprint);
CREATE INDEX IF NOT EXISTS idx_machines_last_seen ON machines(last_seen);
CREATE INDEX IF NOT EXISTS idx_machines_status ON machines(status);
CREATE INDEX IF NOT EXISTS idx_audit_customer ON audit_log(customer_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- Sample customer for testing
INSERT OR IGNORE INTO customers (id, company_name, product_key, machine_limit, valid_days, allowed_services)
VALUES (
    'test-customer-001',
    'Test Company',
    'TEST-2024-DEMO-ABC',
    3,
    10,
    '["dashboard", "analytics"]'
);