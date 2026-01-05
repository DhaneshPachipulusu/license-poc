"""
Complete db.py with tier support - FULLY FIXED
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List

DB_FILE = 'licenses.db'


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    conn = get_db_connection()
    
    # Customers table with tier
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            product_key TEXT UNIQUE NOT NULL,
            machine_limit INTEGER DEFAULT 3,
            valid_days INTEGER DEFAULT 365,
            allowed_services TEXT,
            tier TEXT DEFAULT 'basic',
            revoked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Machines table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            machine_id TEXT,
            fingerprint TEXT UNIQUE NOT NULL,
            hostname TEXT,
            os_info TEXT,
            app_version TEXT,
            ip_address TEXT,
            certificate TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)
    
    # Activity logs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            customer_id TEXT,
            machine_id TEXT,
            details TEXT,
            ip_address TEXT
        )
    """)

    # Admin authentication tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            id TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def generate_product_key(company_name: str = None) -> str:
    """Generate unique product key"""
    import random
    import string
    
    if company_name:
        prefix = ''.join(c for c in company_name.upper() if c.isalnum())[:4]
        if len(prefix) < 4:
            prefix = prefix + ''.join(random.choices(string.ascii_uppercase, k=4-len(prefix)))
    else:
        prefix = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    parts = [
        prefix,
        str(datetime.now().year),
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    ]
    return '-'.join(parts)

# ============================================================================
# CUSTOMER OPERATIONS
# ============================================================================

def create_customer(
    company_name: str,
    machine_limit: int = 3,
    valid_days: int = 365,
    allowed_services: list = None,
    tier: str = "basic"
) -> dict:
    conn = get_db_connection()
    
    customer_id = str(uuid.uuid4())
    product_key = generate_product_key(company_name)
    
    conn.execute("""
        INSERT INTO customers (
            id, company_name, product_key, machine_limit,
            valid_days, allowed_services, tier
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        company_name,
        product_key,
        machine_limit,
        valid_days,
        json.dumps(allowed_services or []),
        tier
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "id": customer_id,
        "company_name": company_name,
        "product_key": product_key,
        "machine_limit": machine_limit,
        "valid_days": valid_days,
        "allowed_services": allowed_services or [],
        "tier": tier,
        "revoked": False
    }

def get_customer_by_id(customer_id: str) -> dict:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT id, company_name, product_key, machine_limit,
               valid_days, allowed_services, revoked, created_at, tier
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def get_customer_by_product_key(product_key: str) -> dict:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT id, company_name, product_key, machine_limit,
               valid_days, allowed_services, revoked, created_at, tier
        FROM customers
        WHERE product_key = ?
    """, (product_key,)).fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def get_all_customers() -> list:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, company_name, product_key, machine_limit,
               valid_days, allowed_services, revoked, created_at, tier
        FROM customers
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_customer(customer_id: str, updates: dict):
    conn = get_db_connection()
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [customer_id]
    
    conn.execute(f"""
        UPDATE customers
        SET {set_clause}
        WHERE id = ?
    """, values)
    
    conn.commit()
    conn.close()

def revoke_customer(customer_id: str):
    conn = get_db_connection()
    conn.execute("UPDATE customers SET revoked = 1 WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()

# ============================================================================
# MACHINE OPERATIONS
# ============================================================================

def register_machine(
    customer_id: str,
    fingerprint: str,
    hostname: str,
    os_info: str = None,
    app_version: str = None,
    ip_address: str = None,
    certificate: dict = None
) -> dict:
    conn = get_db_connection()
    
    machine_id = str(uuid.uuid4())
    
    conn.execute("""
        INSERT INTO machines (
            id, customer_id, fingerprint, hostname,
            os_info, app_version, ip_address, certificate, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (
        machine_id,
        customer_id,
        fingerprint,
        hostname,
        os_info,
        app_version,
        ip_address,
        json.dumps(certificate) if certificate else None
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "id": machine_id,
        "customer_id": customer_id,
        "fingerprint": fingerprint,
        "hostname": hostname,
        "status": "active"
    }

def get_machine_by_fingerprint(fingerprint: str) -> dict:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT id, customer_id, machine_id, fingerprint, hostname,
               os_info, app_version, ip_address, certificate, status,
               created_at, last_seen
        FROM machines
        WHERE fingerprint = ?
    """, (fingerprint,)).fetchone()
    conn.close()
    
    if row:
        result = dict(row)
        if result.get('certificate'):
            try:
                result['certificate'] = json.loads(result['certificate'])
            except:
                pass
        return result
    return None

def get_machine_by_id(machine_id: str) -> dict:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT id, customer_id, machine_id, fingerprint, hostname,
               os_info, app_version, ip_address, certificate, status,
               created_at, last_seen
        FROM machines
        WHERE id = ?
    """, (machine_id,)).fetchone()
    conn.close()
    
    if row:
        result = dict(row)
        if result.get('certificate'):
            try:
                result['certificate'] = json.loads(result['certificate'])
            except:
                pass
        return result
    return None

def get_customer_machines(customer_id: str) -> list:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, customer_id, machine_id, fingerprint, hostname,
               os_info, app_version, ip_address, status,
               created_at, last_seen, certificate
        FROM machines
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,)).fetchall()
    conn.close()
    
    machines = [dict(row) for row in rows]
    # Parse certificate JSON
    for m in machines:
        if m.get('certificate'):
            try:
                m['certificate'] = json.loads(m['certificate'])
            except:
                m['certificate'] = {}
    return machines

def count_active_machines(customer_id: str) -> int:
    conn = get_db_connection()
    result = conn.execute("""
        SELECT COUNT(*) as count
        FROM machines
        WHERE customer_id = ? AND status = 'active'
    """, (customer_id,)).fetchone()
    conn.close()
    
    return result['count'] if result else 0

def update_machine_last_seen(machine_id: str):
    conn = get_db_connection()
    conn.execute("""
        UPDATE machines
        SET last_seen = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (machine_id,))
    conn.commit()
    conn.close()

def update_machine_certificate(machine_id: str, certificate: dict):
    """Update certificate for existing machine"""
    conn = get_db_connection()
    
    # Update certificate
    conn.execute("""
        UPDATE machines 
        SET certificate = ?
        WHERE id = ?
    """, (json.dumps(certificate), machine_id))
    
    conn.commit()
    conn.close()
    return {"success": True}

def revoke_machine(machine_id: str):
    conn = get_db_connection()
    conn.execute("""
        UPDATE machines
        SET status = 'revoked'
        WHERE id = ?
    """, (machine_id,))
    conn.commit()
    conn.close()

# ============================================================================
# AUTO EXPIRY: Mark machine as expired (called from frontend)
# ============================================================================

def mark_machine_expired(machine_id: str) -> bool:
    conn = get_db_connection()
    
    row = conn.execute("SELECT status FROM machines WHERE id = ?", (machine_id,)).fetchone()
    
    if not row:
        conn.close()
        return False
    
    if row['status'] == 'active':
        conn.execute("UPDATE machines SET status = 'expired' WHERE id = ?", (machine_id,))
        conn.commit()
        conn.close()
        print(f"[SYNC] Machine {machine_id} status updated to 'expired'")
        return True
    
    conn.close()
    return False

# ============================================================================
# REST OF YOUR FUNCTIONS (keep them as is)
# ============================================================================

# ... (keep all your other functions: get_dashboard_stats, get_customers_summary, etc.)

# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------
def log_action(action: str, customer_id: str = None, machine_id: str = None, details: dict = None, ip_address: str = None):
    """Insert an action into the activity_logs table."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO activity_logs (action, customer_id, machine_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            action,
            customer_id,
            machine_id,
            json.dumps(details) if details is not None else None,
            ip_address,
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Admin user / session helpers
# ---------------------------------------------------------------------------
def count_admin_users() -> int:
    conn = get_db_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM admin_users").fetchone()
    conn.close()
    return int(row['cnt']) if row else 0


def create_admin_user(username: str, password_hash: str) -> dict:
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    conn.commit()
    admin_id = cur.lastrowid
    conn.close()
    return {"id": admin_id, "username": username}


def get_admin_by_username(username: str) -> Optional[dict]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, username, password_hash, created_at FROM admin_users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_admin_by_id(admin_id: int) -> Optional[dict]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, username, password_hash, created_at FROM admin_users WHERE id = ?",
        (admin_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_admin_session(admin_id: int) -> dict:
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO admin_sessions (id, admin_id) VALUES (?, ?)",
        (session_id, admin_id)
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "admin_id": admin_id}


def get_admin_session(session_id: str) -> Optional[dict]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, admin_id, created_at FROM admin_sessions WHERE id = ?",
        (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_admin_session(session_id: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM admin_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def clear_admin_sessions(admin_id: int = None):
    conn = get_db_connection()
    if admin_id is None:
        conn.execute("DELETE FROM admin_sessions")
    else:
        conn.execute("DELETE FROM admin_sessions WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()

# Just make sure `mark_machine_expired` is at the bottom and named exactly this