"""
LICENSE ACTIVATION INSTALLER
=============================
Windows .exe installer with GUI for:
1. Product key input
2. Machine fingerprint generation
3. Server activation
4. Certificate & credentials storage
5. Docker compose setup
6. Docker login and compose up

Build with: pyinstaller --onefile --windowed --icon=icon.ico installer.py
"""

import os
import sys
import json
import hashlib
import base64
import secrets
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import platform
import uuid

# Third-party imports
try:
    import requests
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "cryptography"])
    import requests
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ===========================================
# CONFIGURATION
# ===========================================

# License server URL - UPDATE THIS
LICENSE_SERVER = os.environ.get("LICENSE_SERVER", "http://localhost:8000")

# Installation directory
if platform.system() == "Windows":
    INSTALL_DIR = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "AILicenseDashboard"
else:
    INSTALL_DIR = Path("/var/license")

LICENSE_DIR = INSTALL_DIR / "license"
COMPOSE_DIR = INSTALL_DIR


# ===========================================
# FINGERPRINT GENERATION
# ===========================================

class MachineFingerprint:
    """Generate unique machine fingerprint"""
    
    @staticmethod
    def get_fingerprint() -> str:
        """Generate or load machine fingerprint"""
        
        # Check for saved fingerprint first
        fp_file = LICENSE_DIR / "machine_id.json"
        if fp_file.exists():
            try:
                with open(fp_file, "r") as f:
                    data = json.load(f)
                    return data.get("fingerprint", "")
            except:
                pass
        
        # Generate new fingerprint
        fingerprint = MachineFingerprint._generate_fingerprint()
        
        # Save it
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        with open(fp_file, "w") as f:
            json.dump({
                "fingerprint": fingerprint,
                "generated_at": datetime.now().isoformat(),
                "hostname": platform.node()
            }, f, indent=2)
        
        return fingerprint
    
    @staticmethod
    def _generate_fingerprint() -> str:
        """Generate fingerprint from hardware info"""
        components = []
        
        # Hostname
        components.append(f"hostname:{platform.node()}")
        
        # Platform info
        components.append(f"system:{platform.system()}")
        components.append(f"machine:{platform.machine()}")
        
        # Try to get more hardware info on Windows
        if platform.system() == "Windows":
            try:
                # Get machine GUID from registry
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography"
                )
                machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                components.append(f"machine_guid:{machine_guid}")
                winreg.CloseKey(key)
            except:
                pass
            
            try:
                # Get CPU info via WMIC
                result = subprocess.run(
                    ["wmic", "cpu", "get", "ProcessorId"],
                    capture_output=True, text=True
                )
                cpu_id = result.stdout.strip().split('\n')[-1].strip()
                if cpu_id:
                    components.append(f"cpu:{cpu_id}")
            except:
                pass
            
            try:
                # Get disk serial
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    capture_output=True, text=True
                )
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) > 1:
                    components.append(f"disk:{lines[1]}")
            except:
                pass
        
        else:
            # Linux
            try:
                with open("/etc/machine-id", "r") as f:
                    machine_id = f.read().strip()
                    components.append(f"machine_id:{machine_id}")
            except:
                pass
            
            try:
                result = subprocess.run(
                    ["cat", "/sys/class/dmi/id/product_uuid"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    components.append(f"product_uuid:{result.stdout.strip()}")
            except:
                pass
        
        # Add a random component for uniqueness if we don't have enough
        if len(components) < 3:
            components.append(f"random:{uuid.uuid4().hex}")
        
        # Create fingerprint hash
        combined = "|".join(sorted(components))
        fingerprint = hashlib.sha3_512(combined.encode()).hexdigest()
        
        return fingerprint


# ===========================================
# ENCRYPTION UTILITIES
# ===========================================

class CryptoUtils:
    """Encryption/decryption utilities"""
    
    @staticmethod
    def decrypt_credentials(encrypted_data: str, machine_fingerprint: str) -> dict:
        """Decrypt Docker credentials using machine fingerprint"""
        derived_key = hashlib.sha256(machine_fingerprint.encode()).digest()
        aesgcm = AESGCM(derived_key)
        
        raw = base64.b64decode(encrypted_data)
        nonce = raw[:12]
        ciphertext = raw[12:]
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode())
    
    @staticmethod
    def encrypt_file(data: bytes, key: bytes) -> bytes:
        """Encrypt data for storage"""
        derived_key = hashlib.sha256(key).digest()
        aesgcm = AESGCM(derived_key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext


# ===========================================
# LICENSE ACTIVATION CLIENT
# ===========================================

class ActivationClient:
    """Handle license activation with server"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
    
    def activate(self, product_key: str, fingerprint: str, hostname: str, os_info: str) -> dict:
        """Activate license with server"""
        
        response = requests.post(
            f"{self.server_url}/api/v1/activate",
            json={
                "product_key": product_key,
                "machine_fingerprint": fingerprint,
                "hostname": hostname,
                "os_info": os_info,
                "app_version": "1.0.0"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            raise Exception(f"Activation failed: {error_detail}")
    
    def check_connection(self) -> bool:
        """Check if server is reachable"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# ===========================================
# FILE MANAGER
# ===========================================

class FileManager:
    """Handle saving activation files"""
    
    def __init__(self, install_dir: Path, license_dir: Path):
        self.install_dir = install_dir
        self.license_dir = license_dir
        self.data_dir = install_dir / "data"  # ← Add data directory
    
    def setup_directories(self):
        """Create installation directories"""
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.license_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)  # ← Create data folder
        
        # Create sample data files for testing
        self._create_sample_data()
    
    def save_certificate(self, certificate: dict, fingerprint: str):
        """Save encrypted certificate"""
        cert_data = json.dumps(certificate, indent=2).encode()
        encrypted = CryptoUtils.encrypt_file(cert_data, fingerprint.encode())
        
        cert_file = self.license_dir / "certificate.dat"
        with open(cert_file, "wb") as f:
            f.write(encrypted)
        
        # Also save unencrypted for Docker container (read-only mount)
        cert_json = self.license_dir / "certificate.json"
        with open(cert_json, "w") as f:
            json.dump(certificate, f, indent=2)
    
    def save_docker_credentials(self, encrypted_creds: str):
        """Save encrypted Docker credentials"""
        creds_file = self.license_dir / "docker_credentials.dat"
        with open(creds_file, "w") as f:
            f.write(encrypted_creds)
    
    def save_compose_file(self, compose_content: str):
        """Save docker-compose.yml"""
        compose_file = self.install_dir / "docker-compose.yml"
        with open(compose_file, "w") as f:
            f.write(compose_content)
    
    def save_public_key(self, public_key: str):
        """Save public key for verification"""
        key_file = self.license_dir / "public_key.pem"
        with open(key_file, "w") as f:
            f.write(public_key)
    
    def is_already_activated(self) -> bool:
        """Check if already activated"""
        return (self.license_dir / "certificate.json").exists()
    
    def _create_sample_data(self):
        """Create sample mock data for testing"""
        # Create sample JSON file
        sample_json = self.data_dir / "sample.json"
        if not sample_json.exists():
            with open(sample_json, "w") as f:
                json.dump({
                    "app": "AI Dashboard",
                    "version": "1.0.0",
                    "initialized": datetime.now().isoformat()
                }, f, indent=2)
        
        # Create README
        readme = self.data_dir / "README.txt"
        if not readme.exists():
            with open(readme, "w") as f:
                f.write("This folder contains application data.\n")
                f.write("You can store uploads, cache, logs, etc. here.\n")


# ===========================================
# DOCKER MANAGER
# ===========================================

class DockerManager:
    """Handle Docker operations"""
    
    def __init__(self, install_dir: Path, license_dir: Path):
        self.install_dir = install_dir
        self.license_dir = license_dir
    
    def check_docker_installed(self) -> bool:
        """Check if Docker is installed"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def check_docker_compose_installed(self) -> bool:
        """Check if Docker Compose is installed"""
        try:
            # Try docker compose (v2)
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True
            
            # Try docker-compose (v1)
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def docker_login(self, registry: str, username: str, token: str) -> bool:
        """Login to Docker registry"""
        try:
            result = subprocess.run(
                ["docker", "login", registry, "-u", username, "--password-stdin"],
                input=token,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Docker login failed: {e}")
            return False
    
    def compose_up(self) -> tuple:
        """Run docker-compose up"""
        compose_file = self.install_dir / "docker-compose.yml"
        
        try:
            # Try docker compose (v2)
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "up", "-d"],
                capture_output=True,
                text=True,
                cwd=str(self.install_dir)
            )
            
            if result.returncode != 0:
                # Try docker-compose (v1)
                result = subprocess.run(
                    ["docker-compose", "-f", str(compose_file), "up", "-d"],
                    capture_output=True,
                    text=True,
                    cwd=str(self.install_dir)
                )
            
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def compose_down(self) -> bool:
        """Run docker-compose down"""
        compose_file = self.install_dir / "docker-compose.yml"
        
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down"],
                capture_output=True,
                text=True,
                cwd=str(self.install_dir)
            )
            return result.returncode == 0
        except:
            return False


# ===========================================
# GUI APPLICATION
# ===========================================

class InstallerApp:
    """Main installer GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Dashboard - License Activation")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 600) // 2
        y = (self.root.winfo_screenheight() - 500) // 2
        self.root.geometry(f"600x500+{x}+{y}")
        
        # Style
        self.style = ttk.Style()
        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        self.style.configure("Info.TLabel", font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", font=("Segoe UI", 9))
        
        # Components
        self.file_manager = FileManager(INSTALL_DIR, LICENSE_DIR)
        self.docker_manager = DockerManager(INSTALL_DIR, LICENSE_DIR)
        self.activation_client = ActivationClient(LICENSE_SERVER)
        
        # Variables
        self.product_key_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        
        self._create_widgets()
        self._check_existing_activation()
    
    def _create_widgets(self):
        """Create GUI widgets"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(
            main_frame,
            text="🔐 AI Dashboard License Activation",
            style="Title.TLabel"
        ).pack(pady=(0, 20))
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.hostname_label = ttk.Label(info_frame, text=f"Hostname: {platform.node()}", style="Info.TLabel")
        self.hostname_label.pack(anchor=tk.W)
        
        self.os_label = ttk.Label(info_frame, text=f"OS: {platform.system()} {platform.release()}", style="Info.TLabel")
        self.os_label.pack(anchor=tk.W)
        
        self.install_label = ttk.Label(info_frame, text=f"Install Path: {INSTALL_DIR}", style="Info.TLabel")
        self.install_label.pack(anchor=tk.W)
        
        # Docker status
        docker_ok = self.docker_manager.check_docker_installed()
        compose_ok = self.docker_manager.check_docker_compose_installed()
        
        docker_status = "✓ Docker installed" if docker_ok else "✗ Docker not found"
        compose_status = "✓ Docker Compose installed" if compose_ok else "✗ Docker Compose not found"
        
        self.docker_label = ttk.Label(info_frame, text=docker_status, style="Info.TLabel")
        self.docker_label.pack(anchor=tk.W)
        
        self.compose_label = ttk.Label(info_frame, text=compose_status, style="Info.TLabel")
        self.compose_label.pack(anchor=tk.W)
        
        # Product Key frame
        key_frame = ttk.LabelFrame(main_frame, text="Product Key", padding=10)
        key_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(key_frame, text="Enter your product key:").pack(anchor=tk.W)
        
        self.key_entry = ttk.Entry(key_frame, textvariable=self.product_key_var, width=50, font=("Consolas", 12))
        self.key_entry.pack(fill=tk.X, pady=(5, 0))
        self.key_entry.focus()
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.activate_btn = ttk.Button(btn_frame, text="🚀 Activate License", command=self._start_activation)
        self.activate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Services", command=self._start_services, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop Services", command=self._stop_services, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        
        # Progress
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Status
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(status_frame, height=8, font=("Consolas", 9))
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
    
    def _log(self, message: str):
        """Add message to status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
    
    def _check_existing_activation(self):
        """Check if already activated"""
        if self.file_manager.is_already_activated():
            self._log("✓ Existing activation found")
            self.activate_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.key_entry.config(state=tk.DISABLED)
            
            # Load certificate to show info
            try:
                cert_file = LICENSE_DIR / "certificate.json"
                with open(cert_file, "r") as f:
                    cert = json.load(f)
                self._log(f"  Customer: {cert['customer']['customer_name']}")
                self._log(f"  Tier: {cert['tier'].upper()}")
                self._log(f"  Valid until: {cert['validity']['valid_until'][:10]}")
            except:
                pass
    
    def _start_activation(self):
        """Start activation process in background thread"""
        product_key = self.product_key_var.get().strip()
        
        if not product_key:
            messagebox.showerror("Error", "Please enter a product key")
            return
        
        # Check Docker
        if not self.docker_manager.check_docker_installed():
            messagebox.showerror("Error", "Docker is not installed. Please install Docker first.")
            return
        
        self.activate_btn.config(state=tk.DISABLED)
        self.key_entry.config(state=tk.DISABLED)
        
        # Run in background thread
        thread = threading.Thread(target=self._do_activation, args=(product_key,))
        thread.daemon = True
        thread.start()
    
    def _do_activation(self, product_key: str):
        """Perform activation (runs in background thread)"""
        try:
            self.progress_var.set(0)
            
            # Step 1: Check server connection
            self._log("Checking server connection...")
            if not self.activation_client.check_connection():
                raise Exception(f"Cannot connect to license server: {LICENSE_SERVER}")
            self._log("✓ Server connected")
            self.progress_var.set(10)
            
            # Step 2: Generate fingerprint
            self._log("Generating machine fingerprint...")
            fingerprint = MachineFingerprint.get_fingerprint()
            self._log(f"✓ Fingerprint: {fingerprint[:32]}...")
            self.progress_var.set(20)
            
            # Step 3: Setup directories
            self._log("Setting up installation directories...")
            self.file_manager.setup_directories()
            self._log(f"✓ Created: {INSTALL_DIR}")
            self.progress_var.set(30)
            
            # Step 4: Activate with server
            self._log("Activating license with server...")
            result = self.activation_client.activate(
                product_key=product_key,
                fingerprint=fingerprint,
                hostname=platform.node(),
                os_info=f"{platform.system()} {platform.release()}"
            )
            self._log(f"✓ {result.get('message', 'Activation successful')}")
            self.progress_var.set(50)
            
            bundle = result.get("bundle", {})
            certificate = bundle.get("certificate", {})
            
            # Step 5: Save certificate
            self._log("Saving license certificate...")
            self.file_manager.save_certificate(certificate, fingerprint)
            self._log("✓ Certificate saved")
            self.progress_var.set(60)
            
            # Step 6: Save Docker credentials
            if "docker_credentials" in bundle:
                self._log("Saving Docker credentials...")
                creds = bundle["docker_credentials"]
                self.file_manager.save_docker_credentials(creds["encrypted_credentials"])
                self._log("✓ Docker credentials saved (encrypted)")
            self.progress_var.set(70)
            
            # Step 7: Save compose file
            if "compose_file" in bundle:
                self._log("Saving docker-compose.yml...")
                self.file_manager.save_compose_file(bundle["compose_file"])
                self._log("✓ Compose file saved")
            self.progress_var.set(80)
            
            # Step 8: Save public key
            if "public_key" in bundle:
                self._log("Saving public key...")
                self.file_manager.save_public_key(bundle["public_key"])
                self._log("✓ Public key saved")
            self.progress_var.set(90)
            
            # Step 9: Docker login
            if "docker_credentials" in bundle:
                self._log("Logging into Docker registry...")
                try:
                    creds = CryptoUtils.decrypt_credentials(
                        bundle["docker_credentials"]["encrypted_credentials"],
                        fingerprint
                    )
                    success = self.docker_manager.docker_login(
                        creds["registry"],
                        creds["username"],
                        creds["token"]
                    )
                    if success:
                        self._log("✓ Docker login successful")
                    else:
                        self._log("⚠ Docker login failed - you may need to login manually")
                except Exception as e:
                    self._log(f"⚠ Docker login error: {e}")
            self.progress_var.set(100)
            
            # Done!
            self._log("")
            self._log("=" * 50)
            self._log("✓ ACTIVATION COMPLETE!")
            self._log(f"  Customer: {certificate['customer']['customer_name']}")
            self._log(f"  Tier: {certificate['tier'].upper()}")
            self._log(f"  Services: {result.get('services_enabled', [])}")
            self._log("=" * 50)
            self._log("")
            self._log("Click 'Start Services' to launch the application.")
            
            # Enable start button
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
            
            messagebox.showinfo("Success", "License activated successfully!\n\nClick 'Start Services' to launch.")
            
        except Exception as e:
            self._log(f"✗ Error: {e}")
            self.progress_var.set(0)
            self.root.after(0, lambda: self.activate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.key_entry.config(state=tk.NORMAL))
            messagebox.showerror("Activation Failed", str(e))
    
    def _start_services(self):
        """Start Docker services"""
        self._log("Starting services...")
        self.start_btn.config(state=tk.DISABLED)
        
        def do_start():
            success, output = self.docker_manager.compose_up()
            if success:
                self._log("✓ Services started successfully!")
                self._log("  Frontend: http://localhost:3005")
                self._log("  Backend: http://localhost:8000")
                self.root.after(0, lambda: messagebox.showinfo("Success", "Services started!\n\nFrontend: http://localhost:3005"))
            else:
                self._log(f"✗ Failed to start services: {output}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to start services:\n{output}"))
            
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        
        thread = threading.Thread(target=do_start)
        thread.daemon = True
        thread.start()
    
    def _stop_services(self):
        """Stop Docker services"""
        self._log("Stopping services...")
        
        if self.docker_manager.compose_down():
            self._log("✓ Services stopped")
        else:
            self._log("✗ Failed to stop services")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    app = InstallerApp()
    app.run()