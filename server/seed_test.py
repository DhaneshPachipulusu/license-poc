"""
Seed Script - Populate Database with Dummy Data (FIXED)
========================================================
Creates 7 customers with various states:
- Active (not expiring)
- Active (expiring soon)
- Expired
- Revoked
- Different tiers
"""

import sys
import json
from datetime import datetime, timedelta, timezone

# Import database functions
from db import (
    init_db,
    create_customer,
    register_machine,
    revoke_machine,
    get_db_connection
)


def create_simple_certificate(
    customer,
    machine_fingerprint,
    hostname,
    days_until_expiry
):
    """Generate simple certificate with specific expiry date"""
    
    issued_at = datetime.now(timezone.utc)
    valid_until = issued_at + timedelta(days=days_until_expiry)
    
    # Get tier and allowed services
    tier = customer.get('tier', 'basic')
    allowed_services = customer.get('allowed_services', [])
    
    if isinstance(allowed_services, str):
        try:
            allowed_services = json.loads(allowed_services)
        except:
            allowed_services = ['frontend']
    
    certificate = {
        "version": "3.0",
        "license_id": f"LIC-{customer['id'][:8]}",
        "customer": {
            "id": customer['id'],
            "company_name": customer['company_name'],
            "product_key": customer['product_key']
        },
        "machine": {
            "fingerprint": machine_fingerprint,
            "hostname": hostname,
            "fingerprint_algorithm": "SHA3-512"
        },
        "tier": tier,
        "limits": {
            "max_machines": customer.get('machine_limit', 3)
        },
        "validity": {
            "issued_at": issued_at.isoformat(),
            "valid_until": valid_until.isoformat(),
            "grace_period_days": 7
        },
        "services": {},
        "docker": {
            "registry": "nainovate",
            "services": {}
        },
        "signature": "dummy_signature_for_seed_data"
    }
    
    # Add services
    for service in allowed_services:
        certificate['services'][service] = {
            "enabled": True,
            "name": service
        }
        
        # Add basic Docker config
        certificate['docker']['services'][service] = {
            "enabled": True,
            "image": f"nainovate/nia-{service}",
            "tag": "v3.0",
            "port": 3005 if service == 'frontend' else 8001
        }
    
    return certificate


def seed_database():
    """Populate database with dummy data"""
    
    print("=" * 70)
    print("SEEDING DATABASE WITH DUMMY DATA")
    print("=" * 70)
    
    # Initialize database
    init_db()
    print("\n✓ Database initialized\n")
    
    # Define dummy customers
    dummy_customers = [
        {
            "company_name": "ACME Corporation",
            "tier": "enterprise",
            "machine_limit": 5,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard", "backend-workflow", "backend-chat"],
            "days_until_expiry": 60,  # Active, not expiring soon
            "num_machines": 2,
            "machine_status": "active"
        },
        {
            "company_name": "Beta Technologies Inc",
            "tier": "pro",
            "machine_limit": 3,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard", "backend-workflow"],
            "days_until_expiry": 15,  # Expiring soon (within 30 days)
            "num_machines": 1,
            "machine_status": "active"
        },
        {
            "company_name": "Gamma Solutions LLC",
            "tier": "basic",
            "machine_limit": 3,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard"],
            "days_until_expiry": -5,  # Expired (5 days ago)
            "num_machines": 1,
            "machine_status": "active"
        },
        {
            "company_name": "Delta Systems",
            "tier": "pro",
            "machine_limit": 3,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard", "backend-workflow"],
            "days_until_expiry": 45,  # Would be active, but revoked
            "num_machines": 1,
            "machine_status": "revoked"
        },
        {
            "company_name": "Epsilon Innovations",
            "tier": "enterprise",
            "machine_limit": 10,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard", "backend-workflow", "backend-chat"],
            "days_until_expiry": 90,  # Active, long time
            "num_machines": 3,
            "machine_status": "active"
        },
        {
            "company_name": "Zeta Labs",
            "tier": "trial",
            "machine_limit": 1,
            "valid_days": 30,
            "allowed_services": ["frontend"],
            "days_until_expiry": 5,  # Expiring very soon
            "num_machines": 1,
            "machine_status": "active"
        },
        {
            "company_name": "Theta Enterprises",
            "tier": "basic",
            "machine_limit": 3,
            "valid_days": 365,
            "allowed_services": ["frontend", "backend-dashboard"],
            "days_until_expiry": -20,  # Expired long ago
            "num_machines": 1,
            "machine_status": "active"
        }
    ]
    
    created_count = 0
    total_machines = 0
    
    for idx, customer_data in enumerate(dummy_customers, 1):
        print(f"[{idx}/{len(dummy_customers)}] Creating: {customer_data['company_name']}")
        
        # Create customer
        customer = create_customer(
            company_name=customer_data['company_name'],
            tier=customer_data['tier'],
            machine_limit=customer_data['machine_limit'],
            valid_days=customer_data['valid_days'],
            allowed_services=customer_data['allowed_services']
        )
        
        print(f"  ✓ Customer created: {customer['product_key']}")
        print(f"  ✓ Tier: {customer_data['tier']}")
        print(f"  ✓ Machine limit: {customer_data['machine_limit']}")
        
        # Create machines for this customer
        for machine_num in range(customer_data['num_machines']):
            # Generate unique fingerprint
            import hashlib
            fingerprint_seed = f"{customer['id']}-{machine_num}-{customer['company_name']}"
            machine_fingerprint = hashlib.sha256(fingerprint_seed.encode()).hexdigest()[:32]
            
            hostname = f"{customer_data['company_name'].split()[0].lower()}-machine-{machine_num + 1}"
            
            # Generate certificate with specific expiry
            certificate = create_simple_certificate(
                customer=customer,
                machine_fingerprint=machine_fingerprint,
                hostname=hostname,
                days_until_expiry=customer_data['days_until_expiry']
            )
            
            # Register machine
            machine = register_machine(
                customer_id=customer['id'],
                fingerprint=machine_fingerprint,
                hostname=hostname,
                os_info="Windows 10",
                app_version="1.0.0",
                certificate=certificate
            )
            
            expiry_status = "ACTIVE"
            if customer_data['days_until_expiry'] < 0:
                expiry_status = f"EXPIRED ({abs(customer_data['days_until_expiry'])} days ago)"
            elif customer_data['days_until_expiry'] <= 30:
                expiry_status = f"EXPIRING SOON ({customer_data['days_until_expiry']} days)"
            else:
                expiry_status = f"ACTIVE ({customer_data['days_until_expiry']} days)"
            
            print(f"    ✓ Machine {machine_num + 1}: {hostname} - {expiry_status}")
            
            # Revoke if needed
            if customer_data['machine_status'] == 'revoked':
                revoke_machine(machine['id'])
                print(f"    ⚠ Machine REVOKED")
            
            total_machines += 1
        
        created_count += 1
        print()
    
    print("=" * 70)
    print(f"✅ SEED COMPLETED!")
    print("=" * 70)
    print(f"\nCreated {created_count} customers with diverse states:")
    print("  • Active (not expiring): 2 customers")
    print("  • Expiring soon (≤30 days): 2 customers")
    print("  • Expired: 2 customers")
    print("  • Revoked: 1 customer")
    print(f"\nTotal machines: {total_machines}")
    print("\nRun your server and check /api/v1/dashboard/stats!")
    print()


def clear_database():
    """Clear all data from database"""
    print("\n⚠ Clearing database...")
    conn = get_db_connection()
    
    conn.execute("DELETE FROM activity_logs")
    conn.execute("DELETE FROM machines")
    conn.execute("DELETE FROM customers")
    
    conn.commit()
    conn.close()
    
    print("✓ Database cleared\n")


if __name__ == "__main__":
    # Check if user wants to clear first
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_database()
    
    seed_database()