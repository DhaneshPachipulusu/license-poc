import sqlite3
import json
from datetime import datetime

DB_NAME = 'licenses.db'

def init_db():
    """Initialize database with licenses and activations tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Licenses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            license_id TEXT PRIMARY KEY,
            customer TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            license_json TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Activations table for tracking machine limits
    c.execute('''
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            customer TEXT NOT NULL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            hostname TEXT,
            UNIQUE(customer, machine_id)
        )
    ''')
    
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_machine_id ON licenses(machine_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_customer ON activations(customer)')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def save_license(license_id, customer, machine_id, license_json):
    """Save a new license"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO licenses (license_id, customer, machine_id, license_json)
        VALUES (?, ?, ?, ?)
    ''', (license_id, customer, machine_id, json.dumps(license_json)))
    
    conn.commit()
    conn.close()


def get_license_by_machine(machine_id):
    """Get license by machine ID"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM licenses WHERE machine_id = ?', (machine_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "license_id": row["license_id"],
            "customer": row["customer"],
            "machine_id": row["machine_id"],
            "license_json": json.loads(row["license_json"]),
            "revoked": bool(row["revoked"])
        }
    return None


def get_license_by_id(license_id):
    """Get license by license ID"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM licenses WHERE license_id = ?', (license_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "license_id": row["license_id"],
            "customer": row["customer"],
            "machine_id": row["machine_id"],
            "license_json": json.loads(row["license_json"]),
            "revoked": bool(row["revoked"])
        }
    return None


def revoke_license(license_id):
    """Revoke a license"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('UPDATE licenses SET revoked = 1 WHERE license_id = ?', (license_id,))
    
    conn.commit()
    conn.close()


def update_license(license_id, license_json):
    """Update license JSON (for renewal)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        UPDATE licenses 
        SET license_json = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE license_id = ?
    ''', (json.dumps(license_json), license_id))
    
    conn.commit()
    conn.close()


def get_all_licenses():
    """Get all licenses for admin dashboard"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM licenses ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    licenses = []
    for row in rows:
        licenses.append({
            "license_id": row["license_id"],
            "customer": row["customer"],
            "machine_id": row["machine_id"],
            "license_json": json.loads(row["license_json"]),
            "revoked": bool(row["revoked"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })
    
    return licenses


# ============================================
# ACTIVATION TRACKING (NEW)
# ============================================

def get_activations_count(customer):
    """Count active machines for a customer"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        SELECT COUNT(DISTINCT machine_id) 
        FROM activations 
        WHERE customer = ?
    ''', (customer,))
    
    count = c.fetchone()[0]
    conn.close()
    
    return count


def save_activation(license_id, machine_id, customer, ip_address=None, hostname=None):
    """Record a machine activation"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO activations (license_id, machine_id, customer, ip_address, hostname, last_seen)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (license_id, machine_id, customer, ip_address, hostname))
    except sqlite3.IntegrityError:
        # Machine already activated, update last_seen
        c.execute('''
            UPDATE activations 
            SET last_seen = CURRENT_TIMESTAMP,
                ip_address = COALESCE(?, ip_address),
                hostname = COALESCE(?, hostname)
            WHERE customer = ? AND machine_id = ?
        ''', (ip_address, hostname, customer, machine_id))
    
    conn.commit()
    conn.close()


def get_customer_activations(customer):
    """Get all activations for a customer"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM activations 
        WHERE customer = ? 
        ORDER BY last_seen DESC
    ''', (customer,))
    
    rows = c.fetchall()
    conn.close()
    
    activations = []
    for row in rows:
        activations.append({
            "license_id": row["license_id"],
            "machine_id": row["machine_id"],
            "customer": row["customer"],
            "activated_at": row["activated_at"],
            "last_seen": row["last_seen"],
            "ip_address": row["ip_address"],
            "hostname": row["hostname"]
        })
    
    return activations


def deactivate_machine(customer, machine_id):
    """Remove a machine activation"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        DELETE FROM activations 
        WHERE customer = ? AND machine_id = ?
    ''', (customer, machine_id))
    
    conn.commit()
    rows_affected = c.rowcount
    conn.close()
    
    return rows_affected > 0


def update_heartbeat(license_id, machine_id):
    """Update last_seen timestamp for heartbeat"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        UPDATE activations 
        SET last_seen = CURRENT_TIMESTAMP 
        WHERE license_id = ? AND machine_id = ?
    ''', (license_id, machine_id))
    
    conn.commit()
    conn.close()