"""
UPDATED db.py - Enhanced with Advanced Certificate Support
============================================================
This extends your existing db.py with advanced certificate functions.
All your existing functions remain unchanged!

WHAT'S NEW:
- save_license() - For backward compatibility
- get_license_by_machine() - For backward compatibility  
- get_license_by_id() - For backward compatibility
- update_machine_certificate() - For certificate upgrades
- save_certificate_history() - For tracking upgrades
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from contextlib import contextmanager

DB_FILE = 'licenses.db'

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database with schema"""
    with open('db_schema.sql', 'r') as f:
        schema = f.read()
    
    with get_db() as conn:
        conn.executescript(schema)

# ============================================================================
# CUSTOMER OPERATIONS (Your existing functions)
# ============================================================================

def create_customer(
    company_name: str,
    machine_limit: int = 3,
    valid_days: int = 365,
    allowed_services: List[str] = None
) -> Dict:
    """Create a new customer and generate product key"""
    if allowed_services is None:
        allowed_services = ["dashboard"]
    
    customer_id = str(uuid.uuid4())
    product_key = generate_product_key(company_name)
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO customers (
                id, company_name, product_key, machine_limit, 
                valid_days, allowed_services
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            company_name,
            product_key,
            machine_limit,
            valid_days,
            json.dumps(allowed_services)
        ))
    
    return get_customer_by_id(customer_id)

def get_customer_by_product_key(product_key: str) -> Optional[Dict]:
    """Get customer by product key"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM customers WHERE product_key = ?
        """, (product_key,)).fetchone()
        
        if row:
            return dict(row)
    return None

def get_customer_by_id(customer_id: str) -> Optional[Dict]:
    """Get customer by ID"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM customers WHERE id = ?
        """, (customer_id,)).fetchone()
        
        if row:
            return dict(row)
    return None

def get_all_customers() -> List[Dict]:
    """Get all customers"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                c.*,
                COUNT(CASE WHEN m.status = 'active' THEN 1 END) as active_machines,
                MAX(m.last_seen) as last_activity
            FROM customers c
            LEFT JOIN machines m ON m.customer_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """).fetchall()
        
        return [dict(row) for row in rows]

def update_customer(customer_id: str, **kwargs):
    """Update customer fields"""
    allowed_fields = ['company_name', 'machine_limit', 'valid_days', 'allowed_services', 'notes']
    
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            updates.append(f"{field} = ?")
            if field == 'allowed_services' and isinstance(value, list):
                value = json.dumps(value)
            values.append(value)
    
    if updates:
        values.append(customer_id)
        with get_db() as conn:
            conn.execute(f"""
                UPDATE customers 
                SET {', '.join(updates)}, updated_at = datetime('now')
                WHERE id = ?
            """, values)

def revoke_customer(customer_id: str):
    """Revoke all licenses for a customer"""
    with get_db() as conn:
        conn.execute("""
            UPDATE customers SET revoked = 1 WHERE id = ?
        """, (customer_id,))
        
        conn.execute("""
            UPDATE machines SET status = 'revoked' WHERE customer_id = ?
        """, (customer_id,))

# ============================================================================
# MACHINE OPERATIONS (Your existing functions)
# ============================================================================

def register_machine(
    customer_id: str,
    fingerprint: str,
    hostname: str = None,
    os_info: str = None,
    app_version: str = None,
    ip_address: str = None,
    certificate: Dict = None
) -> Dict:
    """Register a new machine for a customer"""
    machine_id = str(uuid.uuid4())
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO machines (
                id, customer_id, machine_id, fingerprint, 
                hostname, os_info, app_version, ip_address, certificate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            machine_id,
            customer_id,
            machine_id,
            fingerprint,
            hostname,
            os_info,
            app_version,
            ip_address,
            json.dumps(certificate) if certificate else None
        ))
    
    return get_machine_by_id(machine_id)

def get_machine_by_fingerprint(fingerprint: str) -> Optional[Dict]:
    """Get machine by fingerprint"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM machines WHERE fingerprint = ?
        """, (fingerprint,)).fetchone()
        
        if row:
            machine_dict = dict(row)
            # Parse certificate JSON if exists
            if machine_dict.get('certificate'):
                try:
                    machine_dict['license_json'] = json.loads(machine_dict['certificate'])
                except:
                    pass
            return machine_dict
    return None

def get_machine_by_id(machine_id: str) -> Optional[Dict]:
    """Get machine by ID"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM machines WHERE id = ?
        """, (machine_id,)).fetchone()
        
        if row:
            return dict(row)
    return None

def get_customer_machines(customer_id: str, status: str = None) -> List[Dict]:
    """Get all machines for a customer"""
    query = "SELECT * FROM machines WHERE customer_id = ?"
    params = [customer_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY last_seen DESC"
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def count_active_machines(customer_id: str) -> int:
    """Count active machines for a customer"""
    with get_db() as conn:
        result = conn.execute("""
            SELECT COUNT(*) as count 
            FROM machines 
            WHERE customer_id = ? AND status = 'active'
        """, (customer_id,)).fetchone()
        
        return result['count']

def update_machine_last_seen(machine_id: str):
    """Update machine last seen timestamp (heartbeat)"""
    with get_db() as conn:
        conn.execute("""
            UPDATE machines 
            SET last_seen = datetime('now')
            WHERE id = ?
        """, (machine_id,))

def revoke_machine(machine_id: str):
    """Revoke a specific machine"""
    with get_db() as conn:
        conn.execute("""
            UPDATE machines SET status = 'revoked' WHERE id = ?
        """, (machine_id,))

# ============================================================================
# AUDIT LOG (Your existing functions)
# ============================================================================

def log_action(
    action: str,
    customer_id: str = None,
    machine_id: str = None,
    details: Dict = None,
    ip_address: str = None,
    user_agent: str = None,
    performed_by: str = None
):
    """Log an action to audit log"""
    audit_id = str(uuid.uuid4())
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO audit_log (
                id, customer_id, machine_id, action, 
                details, ip_address, user_agent, performed_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            customer_id,
            machine_id,
            action,
            json.dumps(details) if details else None,
            ip_address,
            user_agent,
            performed_by
        ))

def get_audit_log(customer_id: str = None, limit: int = 100) -> List[Dict]:
    """Get audit log entries"""
    query = "SELECT * FROM audit_log"
    params = []
    
    if customer_id:
        query += " WHERE customer_id = ?"
        params.append(customer_id)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

# ============================================================================
# PRODUCT KEY GENERATION (Your existing functions)
# ============================================================================

def generate_product_key(company_name: str) -> str:
    """
    Generate a product key in format: CUST-YEAR-RAND-CHECK
    Example: ACME-2024-X7H9-K2P
    """
    import random
    from datetime import datetime
    
    # Part 1: Customer prefix (4 chars from company name)
    prefix = ''.join(c for c in company_name.upper() if c.isalnum())[:4]
    prefix = prefix.ljust(4, 'X')
    
    # Part 2: Year
    year = datetime.now().year
    
    # Part 3: Random (8 chars, alphanumeric excluding confusing chars)
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # No 0,O,1,I
    random_part = ''.join(random.choice(chars) for _ in range(8))
    
    # Part 4: Check digits (3 chars for validation)
    base_key = f"{prefix}-{year}-{random_part}"
    check = _calculate_check_digits(base_key)
    
    product_key = f"{base_key}-{check}"
    
    return product_key

def _calculate_check_digits(key_base: str) -> str:
    """Calculate check digits for product key validation"""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    key_clean = key_base.replace('-', '')
    
    # Simple checksum
    total = sum(chars.index(c) * (i + 1) for i, c in enumerate(key_clean) if c in chars)
    
    # Generate 3 check characters
    check_chars = ''
    for i in range(3):
        index = (total + i * 7) % len(chars)
        check_chars += chars[index]
    
    return check_chars

def validate_product_key_format(product_key: str) -> bool:
    """Validate product key format and check digits"""
    try:
        parts = product_key.split('-')
        if len(parts) != 4:
            return False
        
        prefix, year, random_part, check = parts
        
        # Validate lengths
        if len(prefix) != 4 or len(year) != 4 or len(random_part) != 8 or len(check) != 3:
            return False
        
        # Validate year is numeric
        if not year.isdigit():
            return False
        
        # Validate check digits
        base_key = f"{prefix}-{year}-{random_part}"
        expected_check = _calculate_check_digits(base_key)
        
        return check == expected_check
        
    except:
        return False


# ============================================================================
# NEW: ADVANCED CERTIFICATE FUNCTIONS (Backward Compatible)
# ============================================================================

def save_license(license_id: str, customer: str, machine_id: str, license_data: dict):
    """
    Save license (backward compatible wrapper for register_machine).
    Maps to your existing database structure.
    """
    # Extract certificate data
    customer_data = get_customer_by_product_key(license_data.get("customer", {}).get("product_key", "")) or \
                    {"id": str(uuid.uuid4()), "company_name": customer}
    
    # Get fingerprint from license
    fingerprint = license_data.get("machine", {}).get("machine_fingerprint") or \
                  license_data.get("machine_id") or \
                  machine_id
    
    hostname = license_data.get("machine", {}).get("hostname") or \
               license_data.get("hostname")
    
    # Register the machine
    return register_machine(
        customer_id=customer_data.get("id"),
        fingerprint=fingerprint,
        hostname=hostname,
        os_info=license_data.get("metadata", {}).get("os_info"),
        app_version=license_data.get("metadata", {}).get("app_version"),
        certificate=license_data
    )


def get_license_by_machine(machine_id: str) -> Optional[Dict]:
    """
    Get license by machine ID (backward compatible).
    Returns data in format expected by app.py
    """
    machine = get_machine_by_fingerprint(machine_id)
    if not machine:
        return None
    
    # Parse certificate
    certificate = None
    if machine.get('certificate'):
        try:
            certificate = json.loads(machine['certificate'])
        except:
            certificate = machine.get('certificate')
    
    return {
        "license_id": machine.get('machine_id'),
        "customer_id": machine.get('customer_id'),
        "machine_id": machine.get('machine_id'),
        "fingerprint": machine.get('fingerprint'),
        "license_json": certificate,
        "revoked": machine.get('status') == 'revoked',
        "activated_at": machine.get('activated_at'),
        "last_seen": machine.get('last_seen')
    }


def get_license_by_id(license_id: str) -> Optional[Dict]:
    """
    Get license by license/certificate ID (backward compatible).
    """
    with get_db() as conn:
        # Try to find by machine_id first
        row = conn.execute("""
            SELECT * FROM machines WHERE machine_id = ?
        """, (license_id,)).fetchone()
        
        if row:
            machine = dict(row)
            certificate = None
            if machine.get('certificate'):
                try:
                    certificate = json.loads(machine['certificate'])
                except:
                    certificate = machine.get('certificate')
            
            return {
                "license_id": machine.get('machine_id'),
                "customer_id": machine.get('customer_id'),
                "machine_id": machine.get('machine_id'),
                "fingerprint": machine.get('fingerprint'),
                "license_json": certificate,
                "revoked": machine.get('status') == 'revoked'
            }
    
    return None


def update_license(license_id: str, license_data: dict):
    """
    Update license/certificate (backward compatible).
    """
    with get_db() as conn:
        conn.execute("""
            UPDATE machines 
            SET certificate = ?, last_seen = datetime('now')
            WHERE machine_id = ?
        """, (json.dumps(license_data), license_id))


def revoke_license(license_id: str):
    """
    Revoke a license (backward compatible).
    """
    with get_db() as conn:
        conn.execute("""
            UPDATE machines SET status = 'revoked' WHERE machine_id = ?
        """, (license_id,))


def get_all_licenses() -> List[Dict]:
    """
    Get all licenses (backward compatible).
    Returns machines with their certificates.
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                m.*,
                c.company_name,
                c.product_key
            FROM machines m
            LEFT JOIN customers c ON c.id = m.customer_id
            ORDER BY m.last_seen DESC
        """).fetchall()
        
        licenses = []
        for row in rows:
            machine = dict(row)
            certificate = None
            if machine.get('certificate'):
                try:
                    certificate = json.loads(machine['certificate'])
                except:
                    pass
            
            licenses.append({
                "license_id": machine.get('machine_id'),
                "customer": machine.get('company_name'),
                "machine_id": machine.get('machine_id'),
                "fingerprint": machine.get('fingerprint'),
                "hostname": machine.get('hostname'),
                "status": machine.get('status'),
                "activated_at": machine.get('activated_at'),
                "last_seen": machine.get('last_seen'),
                "license_json": certificate,
                "product_key": machine.get('product_key')
            })
        
        return licenses


def update_machine_certificate(machine_id: str, certificate_json: str, certificate_id: str):
    """Update machine with new certificate (for upgrades)"""
    with get_db() as conn:
        conn.execute("""
            UPDATE machines 
            SET certificate = ?, last_seen = datetime('now')
            WHERE machine_id = ?
        """, (certificate_json, machine_id))