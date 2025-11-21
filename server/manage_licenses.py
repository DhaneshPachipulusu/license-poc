#!/usr/bin/env python3
"""
License Management Utility
Quick CLI tool to manage licenses without admin UI

Usage:
    python manage_licenses.py list-customers
    python manage_licenses.py customer-details <customer_id>
    python manage_licenses.py revoke-machine <machine_id>
    python manage_licenses.py create-customer <name> <limit> <days>
"""

import sys
import requests
import json
from datetime import datetime

SERVER_URL = "http://localhost:8000"

def list_customers():
    """List all customers"""
    print("\n" + "="*70)
    print("ALL CUSTOMERS")
    print("="*70 + "\n")
    
    response = requests.get(f"{SERVER_URL}/api/v1/admin/customers")
    customers = response.json()
    
    for i, c in enumerate(customers, 1):
        print(f"{i}. {c['company_name']}")
        print(f"   ID: {c['id']}")
        print(f"   Product Key: {c['product_key']}")
        print(f"   Machines: {c.get('active_machines', 0)}/{c['machine_limit']}")
        print(f"   Created: {c['created_at']}")
        print()

def customer_details(customer_id):
    """Show customer details with machines"""
    print("\n" + "="*70)
    print("CUSTOMER DETAILS")
    print("="*70 + "\n")
    
    response = requests.get(f"{SERVER_URL}/api/v1/admin/customers/{customer_id}")
    data = response.json()
    
    customer = data['customer']
    machines = data['machines']
    
    print(f"Company: {customer['company_name']}")
    print(f"Product Key: {customer['product_key']}")
    print(f"Machine Limit: {customer['machine_limit']}")
    print(f"Valid Days: {customer['valid_days']}")
    print(f"Created: {customer['created_at']}")
    print(f"Revoked: {customer['revoked']}")
    print()
    
    print(f"Active Machines ({len(machines)}/{customer['machine_limit']}):")
    print("-" * 70)
    
    if machines:
        for i, m in enumerate(machines, 1):
            print(f"{i}. {m['hostname']} (ID: {m['id'][:8]}...)")
            print(f"   Machine ID: {m['id']}")
            print(f"   Fingerprint: {m['fingerprint'][:16]}...")
            print(f"   OS: {m.get('os_info', 'Unknown')}")
            print(f"   Activated: {m['activated_at']}")
            print(f"   Last Seen: {m['last_seen']}")
            print(f"   Status: {m['status']}")
            print()
    else:
        print("  (No machines activated)")
        print()

def revoke_machine(machine_id):
    """Revoke a specific machine"""
    print("\n" + "="*70)
    print("REVOKING MACHINE")
    print("="*70 + "\n")
    
    print(f"Machine ID: {machine_id}")
    confirm = input("Are you sure? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Cancelled")
        return
    
    response = requests.post(f"{SERVER_URL}/api/v1/admin/machines/{machine_id}/revoke")
    result = response.json()
    
    if result.get('success'):
        print("✓ Machine revoked successfully!")
    else:
        print(f"✗ Error: {result}")

def create_customer(name, machine_limit, valid_days):
    """Create new customer"""
    print("\n" + "="*70)
    print("CREATING CUSTOMER")
    print("="*70 + "\n")
    
    payload = {
        "company_name": name,
        "machine_limit": int(machine_limit),
        "valid_days": int(valid_days),
        "allowed_services": ["dashboard", "frontend", "backend"]
    }
    
    print(f"Company: {name}")
    print(f"Machine Limit: {machine_limit}")
    print(f"Valid Days: {valid_days}")
    print()
    
    response = requests.post(
        f"{SERVER_URL}/api/v1/admin/customers",
        json=payload
    )
    
    if response.status_code == 200:
        customer = response.json()
        print("✓ Customer created successfully!")
        print()
        print(f"Product Key: {customer['product_key']}")
        print(f"Customer ID: {customer['id']}")
        print()
        print("Use this product key to activate:")
        print(f"  python activation_client.py --server {SERVER_URL} --key {customer['product_key']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_licenses.py list-customers")
        print("  python manage_licenses.py customer-details <customer_id>")
        print("  python manage_licenses.py revoke-machine <machine_id>")
        print("  python manage_licenses.py create-customer <name> <limit> <days>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "list-customers":
            list_customers()
        
        elif command == "customer-details":
            if len(sys.argv) < 3:
                print("Usage: python manage_licenses.py customer-details <customer_id>")
                sys.exit(1)
            customer_details(sys.argv[2])
        
        elif command == "revoke-machine":
            if len(sys.argv) < 3:
                print("Usage: python manage_licenses.py revoke-machine <machine_id>")
                sys.exit(1)
            revoke_machine(sys.argv[2])
        
        elif command == "create-customer":
            if len(sys.argv) < 5:
                print("Usage: python manage_licenses.py create-customer <name> <limit> <days>")
                sys.exit(1)
            create_customer(sys.argv[2], sys.argv[3], sys.argv[4])
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Error: Could not connect to server at {SERVER_URL}")
        print("  Make sure the license server is running:")
        print("  python server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()