"""
Diagnostic script to check license server setup
Run this to identify issues: python diagnose.py
"""
import os
import sys

def check_file(filename, required=True):
    """Check if file exists"""
    exists = os.path.exists(filename)
    status = "✅" if exists else ("❌" if required else "⚠️ ")
    print(f"{status} {filename}: {'EXISTS' if exists else 'MISSING'}")
    return exists

def check_imports():
    """Check if all required packages are installed"""
    print("\n📦 Checking Python packages...")
    packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'cryptography': 'Cryptography',
        'dateutil': 'python-dateutil',
        'jinja2': 'Jinja2',
    }
    
    all_installed = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"✅ {name}: installed")
        except ImportError:
            print(f"❌ {name}: NOT INSTALLED")
            all_installed = False
    
    return all_installed

def check_directory_structure():
    """Check if all required files exist"""
    print("\n📁 Checking directory structure...")
    
    files = {
        'app.py': True,
        'models.py': True,
        'signer.py': True,
        'db.py': True,
        'templates': False,
        'templates/licenses.html': False,
        'templates/license_view.html': False,
        'private_key.pem': False,
        'public_key.pem': False,
    }
    
    all_ok = True
    for filename, required in files.items():
        if not check_file(filename, required):
            if required:
                all_ok = False
    
    return all_ok

def test_import_app():
    """Try to import the app"""
    print("\n🔍 Testing app import...")
    try:
        import app
        print("✅ app.py imports successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import app.py:")
        print(f"   Error: {e}")
        return False

def test_endpoints():
    """Test if server responds"""
    print("\n🌐 Testing server endpoints...")
    try:
        import requests
        
        endpoints = [
            'http://127.0.0.1:8000/',
            'http://127.0.0.1:8000/public_key',
            'http://127.0.0.1:8000/admin/licenses',
        ]
        
        for url in endpoints:
            try:
                response = requests.get(url, timeout=2)
                print(f"✅ {url}: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"❌ {url}: Server not responding")
            except Exception as e:
                print(f"⚠️  {url}: {e}")
    except ImportError:
        print("⚠️  requests package not installed, skipping endpoint tests")
        print("   Install with: pip install requests")

def main():
    print("=" * 60)
    print("🔍 LICENSE SERVER DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Check packages
    packages_ok = check_imports()
    
    # Check files
    files_ok = check_directory_structure()
    
    # Try import
    import_ok = test_import_app()
    
    # Test endpoints (if server is running)
    print("\n⚠️  Make sure server is running in another terminal:")
    print("   uvicorn app:app --reload --host 127.0.0.1 --port 8000")
    input("\nPress ENTER to test endpoints (or Ctrl+C to skip)...")
    test_endpoints()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Python Packages: {'✅ OK' if packages_ok else '❌ MISSING'}")
    print(f"Required Files:  {'✅ OK' if files_ok else '❌ MISSING'}")
    print(f"App Import:      {'✅ OK' if import_ok else '❌ FAILED'}")
    
    if not packages_ok:
        print("\n💡 Install missing packages:")
        print("   pip install fastapi uvicorn cryptography python-dateutil jinja2")
    
    if not files_ok:
        print("\n💡 Copy missing files from the package:")
        print("   - models.py")
        print("   - signer.py")
        print("   - db.py")
        print("   - templates/")
    
    if not import_ok:
        print("\n💡 Check the error above and fix app.py")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()