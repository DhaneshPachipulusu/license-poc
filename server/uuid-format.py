"""
WHAT THE SERVER EXPECTS
=======================

Based on your error, here's what's happening:

FRONTEND SENDS:
{
  "customer_id": "ee733da8-4935-4efc-9cd2-0e343a2871f6",  // UUID string
  "machine_fingerprint": "9ca76a772af5518ad148dd0cf189142a4ff2e6ece13d8aca9d3ee7941fcc4720b08e3",
  "hostname": "sivamani",
  "tier": "Trial",
  "valid_days": 9,
  ...
}

SERVER CODE (line 619 in server.py):
customer = get_customer_by_id(customer_id)
if not customer:
    raise HTTPException(404, "Customer not found")  # ← YOU ARE HERE

This calls db.get_customer_by_id() which does:
SELECT * FROM customers WHERE id = ?

THE PROBLEM:
Your database stores customer IDs as UUIDs, but the query might not be matching them properly.

SOLUTION:
Check how UUIDs are stored in your database.
"""

# Run this to check your database:
import sqlite3
import json

def check_database_customers():
    print("="*70)
    print("CHECKING DATABASE - CUSTOMER ID FORMAT")
    print("="*70)
    
    conn = sqlite3.connect('licenses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all customers
    cursor.execute("SELECT id, company_name, product_key FROM customers")
    customers = cursor.fetchall()
    
    if not customers:
        print("\n❌ NO CUSTOMERS IN DATABASE!")
        print("Create a customer first via the UI")
        return
    
    print(f"\n✅ Found {len(customers)} customer(s):\n")
    
    for i, customer in enumerate(customers, 1):
        row_dict = dict(customer)
        print(f"{i}. ID in database:")
        print(f"   Value: {row_dict['id']}")
        print(f"   Type: {type(row_dict['id']).__name__}")
        print(f"   Company: {row_dict['company_name']}")
        print(f"   Product Key: {row_dict['product_key']}")
        print()
    
    # Test lookup with exact UUID from your console
    test_uuid = "ee733da8-4935-4efc-9cd2-0e343a2871f6"
    print(f"Testing lookup with UUID from frontend: {test_uuid}")
    
    cursor.execute("SELECT * FROM customers WHERE id = ?", (test_uuid,))
    result = cursor.fetchone()
    
    if result:
        print(f"✅ SUCCESS - Found customer: {dict(result)['company_name']}")
    else:
        print(f"❌ FAILED - Customer not found with UUID: {test_uuid}")
        print(f"\nTrying variations:")
        
        # Try as uppercase
        cursor.execute("SELECT * FROM customers WHERE id = ?", (test_uuid.upper(),))
        result = cursor.fetchone()
        if result:
            print(f"  ✅ Found with UPPERCASE UUID")
        
        # Try as lowercase
        cursor.execute("SELECT * FROM customers WHERE id = ?", (test_uuid.lower(),))
        result = cursor.fetchone()
        if result:
            print(f"  ✅ Found with lowercase UUID")
        
        # Try LIKE query
        cursor.execute("SELECT * FROM customers WHERE id LIKE ?", (f"%{test_uuid}%",))
        result = cursor.fetchone()
        if result:
            print(f"  ✅ Found with LIKE query - exact ID: {dict(result)['id']}")
    
    conn.close()

if __name__ == "__main__":
    check_database_customers()