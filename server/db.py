"""
Complete db.py with tier support
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
    
    conn.commit()
    conn.close()

def generate_product_key(company_name: str = None) -> str:
    """Generate unique product key"""
    import random
    import string
    
    # If company name provided, use first 4 letters
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
    """Update customer"""
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
    """Revoke customer"""
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
            os_info, app_version, ip_address, certificate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
               created_at, last_seen
        FROM machines
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,)).fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

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

def revoke_machine(machine_id: str):
    conn = get_db_connection()
    conn.execute("""
        UPDATE machines
        SET status = 'revoked'
        WHERE id = ?
    """, (machine_id,))
    conn.commit()
    conn.close()

def update_license(machine_id: str, certificate: dict):
    """Update machine certificate"""
    conn = get_db_connection()
    conn.execute("""
        UPDATE machines
        SET certificate = ?
        WHERE machine_id = ?
    """, (json.dumps(certificate), machine_id))
    conn.commit()
    conn.close()

# ============================================================================
# ACTIVITY LOG
# ============================================================================

def log_action(
    action: str,
    customer_id: str = None,
    machine_id: str = None,
    details: dict = None,
    ip_address: str = None
):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO activity_logs (action, customer_id, machine_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?)
    """, (
        action,
        customer_id,
        machine_id,
        json.dumps(details) if details else None,
        ip_address
    ))
    conn.commit()
    conn.close()

def get_activity_logs(customer_id: str = None, limit: int = 100) -> list:
    conn = get_db_connection()
    
    if customer_id:
        rows = conn.execute("""
            SELECT * FROM activity_logs
            WHERE customer_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (customer_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM activity_logs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

def save_license(license_id: str, customer: str, machine_id: str, license_data: dict):
    """Backward compatibility"""
    pass

def get_license_by_machine(machine_id: str):
    """Backward compatibility"""
    return get_machine_by_fingerprint(machine_id)

def get_license_by_id(license_id: str):
    """Backward compatibility"""
    return get_machine_by_id(license_id)
# ===========================================
# Custom function to update machine certificate
# ===========================================
def update_machine_certificate(machine_id: int, certificate: dict):
    """Update certificate for existing machine"""
    conn = get_db_connection()
    
    # Get current machine
    machine = conn.execute(
        "SELECT * FROM machines WHERE id = ?",
        (machine_id,)
    ).fetchone()
    
    if not machine:
        return None
    
    # Update certificate
    conn.execute("""
        UPDATE machines 
        SET certificate = ?
        WHERE id = ?
    """, (json.dumps(certificate), machine_id))
    
    conn.commit()
    return {"success": True}
# ============================================================================
# DASHBOARD STATS FUNCTION - ADD THIS TO db.py
# ============================================================================

def get_dashboard_stats() -> dict:
    """
    Calculate dashboard statistics
    
    Returns:
        dict: Dashboard metrics including:
            - total_customers: Number of active customers
            - active_machines: Machines with valid, non-expired licenses
            - expiring_soon: Machines expiring within 30 days
            - revoked: Revoked machines
            - expired: Expired but not revoked machines
    """
    from datetime import datetime, timezone, timedelta
    from dateutil import parser
    
    conn = get_db_connection()
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    
    # Total customers (non-revoked)
    total_customers = conn.execute("""
        SELECT COUNT(*) as count
        FROM customers
        WHERE revoked = 0
    """).fetchone()['count']
    
    # Get all machines
    machines = conn.execute("""
        SELECT id, customer_id, fingerprint, status, certificate
        FROM machines
    """).fetchall()
    
    conn.close()
    
    # Initialize counters
    active_machines = 0
    expiring_soon = 0
    revoked_count = 0
    expired_count = 0
    
    for machine in machines:
        # Count revoked
        if machine['status'] == 'revoked':
            revoked_count += 1
            continue
        
        # Parse certificate to check expiry
        cert = machine['certificate']
        if cert:
            try:
                if isinstance(cert, str):
                    cert = json.loads(cert)
                
                # Get expiry date
                validity = cert.get('validity', {})
                valid_until_str = validity.get('valid_until') or cert.get('valid_till')
                
                if valid_until_str:
                    # Parse date
                    if valid_until_str.endswith('Z'):
                        valid_until_str = valid_until_str.replace('Z', '+00:00')
                    
                    valid_until = parser.isoparse(valid_until_str)
                    
                    # Check if expired
                    if now > valid_until:
                        expired_count += 1
                    # Check if expiring soon (within 30 days)
                    elif now <= valid_until <= thirty_days:
                        expiring_soon += 1
                        active_machines += 1  # Still active, just expiring soon
                    # Active and not expiring soon
                    else:
                        active_machines += 1
                else:
                    # No expiry date, consider active
                    active_machines += 1
                    
            except Exception as e:
                print(f"Error parsing certificate for machine {machine['id']}: {e}")
                # If can't parse, consider active
                active_machines += 1
        else:
            # No certificate, consider active
            active_machines += 1
    
    return {
        "total_customers": total_customers,
        "active_machines": active_machines,
        "expiring_soon": expiring_soon,
        "revoked": revoked_count,
        "expired": expired_count
    }


# ============================================================================
# ADDITIONAL HELPER FUNCTIONS (OPTIONAL)
# ============================================================================

def get_customers_summary() -> list:
    """
    Get summary of all customers with machine counts
    
    Returns:
        list: List of customer summaries with machine statistics
    """
    from datetime import datetime, timezone
    from dateutil import parser
    
    conn = get_db_connection()
    
    customers = conn.execute("""
        SELECT id, company_name, product_key, machine_limit,
               tier, revoked, created_at
        FROM customers
        ORDER BY created_at DESC
    """).fetchall()
    
    result = []
    
    for customer in customers:
        customer_dict = dict(customer)
        
        # Get machines for this customer
        machines = conn.execute("""
            SELECT status, certificate
            FROM machines
            WHERE customer_id = ?
        """, (customer['id'],)).fetchall()
        
        active_count = 0
        revoked_count = 0
        expired_count = 0
        expiring_soon_count = 0
        
        now = datetime.now(timezone.utc)
        
        for machine in machines:
            if machine['status'] == 'revoked':
                revoked_count += 1
                continue
            
            # Check expiry
            cert = machine['certificate']
            if cert:
                try:
                    if isinstance(cert, str):
                        cert = json.loads(cert)
                    
                    validity = cert.get('validity', {})
                    valid_until_str = validity.get('valid_until')
                    
                    if valid_until_str:
                        if valid_until_str.endswith('Z'):
                            valid_until_str = valid_until_str.replace('Z', '+00:00')
                        
                        valid_until = parser.isoparse(valid_until_str)
                        
                        if now > valid_until:
                            expired_count += 1
                        else:
                            active_count += 1
                            # Check if expiring in 30 days
                            days_remaining = (valid_until - now).days
                            if days_remaining <= 30:
                                expiring_soon_count += 1
                except:
                    active_count += 1
            else:
                active_count += 1
        
        customer_dict['machine_stats'] = {
            'total': len(machines),
            'active': active_count,
            'expired': expired_count,
            'revoked': revoked_count,
            'expiring_soon': expiring_soon_count
        }
        
        result.append(customer_dict)
    
    conn.close()
    return result


def get_expiring_machines(days: int = 30) -> list:
    """
    Get machines expiring within specified days
    
    Args:
        days: Number of days to look ahead (default 30)
    
    Returns:
        list: Machines expiring within the specified timeframe
    """
    from datetime import datetime, timezone, timedelta
    from dateutil import parser
    
    conn = get_db_connection()
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=days)
    
    machines = conn.execute("""
        SELECT m.id, m.customer_id, m.fingerprint, m.hostname, 
               m.certificate, c.company_name, c.product_key
        FROM machines m
        JOIN customers c ON m.customer_id = c.id
        WHERE m.status = 'active'
    """).fetchall()
    
    conn.close()
    
    expiring = []
    
    for machine in machines:
        cert = machine['certificate']
        if cert:
            try:
                if isinstance(cert, str):
                    cert = json.loads(cert)
                
                validity = cert.get('validity', {})
                valid_until_str = validity.get('valid_until')
                
                if valid_until_str:
                    if valid_until_str.endswith('Z'):
                        valid_until_str = valid_until_str.replace('Z', '+00:00')
                    
                    valid_until = parser.isoparse(valid_until_str)
                    
                    # Check if expiring within threshold
                    if now < valid_until <= threshold:
                        days_remaining = (valid_until - now).days
                        
                        machine_dict = dict(machine)
                        machine_dict['expires_at'] = valid_until_str
                        machine_dict['days_remaining'] = days_remaining
                        
                        expiring.append(machine_dict)
            except:
                pass
    
    # Sort by days remaining (ascending)
    expiring.sort(key=lambda x: x['days_remaining'])
    
    return expiring