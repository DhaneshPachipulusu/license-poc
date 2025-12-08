"""
AI DASHBOARD SETUP WIZARD v2.0
===============================
Professional multi-step installer with:
- Step-by-step wizard flow
- Prerequisites blocking
- Port availability check
- Visual progress indicators
- License activation
- Service management

Build: pyinstaller --onefile --windowed --icon=icon.ico installer_wizard.py
"""

import os
import sys
import json
import hashlib
import base64
import secrets
import subprocess
import threading
import socket
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
# CONFIGURATION - EDIT THESE VALUES
# ===========================================

# Server and App Info
LICENSE_SERVER = os.environ.get("LICENSE_SERVER", "http://localhost:8000")
APP_NAME = "GenX Platform"          # ← Change your app name here
APP_VERSION = "1.0.0"               # ← Change version here

# Renewal/Contact URL
RENEW_URL = "https://your-company.com/renew"    # ← Change to your renewal page
CONTACT_EMAIL = "support@your-company.com"      # ← Change to your email

# Icon file (place .ico file in same folder as this script)
ICON_FILE = "GENXLOGO.ico"          # ← Change to your icon filename

# Required ports for your services
REQUIRED_PORTS = {
    3005: "Frontend",       # ← Modify ports as needed
    8100: "Backend API",
    27017: "MongoDB"
}

# Installation directory - IMPORTANT: Must match where your certificates are stored!
if platform.system() == "Windows":
    INSTALL_DIR = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "AILicenseDashboard"
else:
    INSTALL_DIR = Path.home() / ".genx-platform"  # User directory (no sudo needed)

LICENSE_DIR = INSTALL_DIR / "license"


# ===========================================
# UTILITY CLASSES
# ===========================================

class MachineFingerprint:
    """Generate unique machine fingerprint"""
    
    @staticmethod
    def get_fingerprint() -> str:
        fp_file = LICENSE_DIR / "machine_id.json"
        if fp_file.exists():
            try:
                with open(fp_file, "r") as f:
                    data = json.load(f)
                    return data.get("fingerprint", "")
            except:
                pass
        
        fingerprint = MachineFingerprint._generate_fingerprint()
        
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
        components = []
        components.append(f"hostname:{platform.node()}")
        components.append(f"system:{platform.system()}")
        components.append(f"machine:{platform.machine()}")
        
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
                machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                components.append(f"machine_guid:{machine_guid}")
                winreg.CloseKey(key)
            except:
                pass
            
            try:
                result = subprocess.run(["wmic", "cpu", "get", "ProcessorId"], capture_output=True, text=True)
                cpu_id = result.stdout.strip().split('\n')[-1].strip()
                if cpu_id:
                    components.append(f"cpu:{cpu_id}")
            except:
                pass
        else:
            try:
                with open("/etc/machine-id", "r") as f:
                    components.append(f"machine_id:{f.read().strip()}")
            except:
                pass
        
        if len(components) < 3:
            components.append(f"random:{uuid.uuid4().hex}")
        
        combined = "|".join(sorted(components))
        return hashlib.sha3_512(combined.encode()).hexdigest()


class CryptoUtils:
    """Encryption utilities"""
    
    @staticmethod
    def decrypt_credentials(encrypted_data: str, machine_fingerprint: str) -> dict:
        derived_key = hashlib.sha256(machine_fingerprint.encode()).digest()
        aesgcm = AESGCM(derived_key)
        raw = base64.b64decode(encrypted_data)
        nonce = raw[:12]
        ciphertext = raw[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode())
    
    @staticmethod
    def encrypt_file(data: bytes, key: bytes) -> bytes:
        derived_key = hashlib.sha256(key).digest()
        aesgcm = AESGCM(derived_key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    @staticmethod
    def decrypt_file(encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data encrypted with encrypt_file"""
        derived_key = hashlib.sha256(key).digest()
        aesgcm = AESGCM(derived_key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)


class SystemChecker:
    """System requirements checker"""
    
    @staticmethod
    def check_docker_installed() -> tuple:
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split(',')[0].replace('Docker version ', '')
                return True, f"Docker {version}"
            return False, "Not installed"
        except:
            return False, "Not installed"
    
    @staticmethod
    def check_docker_compose() -> tuple:
        try:
            result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "Not installed"
        except:
            return False, "Not installed"
    
    @staticmethod
    def check_docker_running() -> tuple:
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if result.returncode == 0:
                return True, "Running"
            return False, "Not running"
        except:
            return False, "Not running"
    
    @staticmethod
    def check_port_available(port: int) -> tuple:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:
                return True, "Available"
            else:
                # Try to find what's using it
                try:
                    if platform.system() == "Windows":
                        result = subprocess.run(
                            ["netstat", "-ano"],
                            capture_output=True, text=True
                        )
                        for line in result.stdout.split('\n'):
                            if f":{port}" in line and "LISTENING" in line:
                                pid = line.strip().split()[-1]
                                return False, f"In use (PID: {pid})"
                except:
                    pass
                return False, "In use"
        except:
            return True, "Available"
    
    @staticmethod
    def check_disk_space() -> tuple:
        try:
            free_gb = 0  # Default value
            
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                # Get drive from install dir or default to C:
                drive = str(INSTALL_DIR)[:3] if len(str(INSTALL_DIR)) >= 3 else "C:\\"
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(drive),
                    None, None, ctypes.pointer(free_bytes)
                )
                free_gb = free_bytes.value / (1024**3)
            else:
                check_path = INSTALL_DIR.parent if INSTALL_DIR.exists() else Path("/")
                st = os.statvfs(str(check_path))
                free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
            
            if free_gb >= 2:
                return True, f"{free_gb:.1f} GB free"
            elif free_gb > 0:
                return False, f"Only {free_gb:.1f} GB free (need 2GB)"
            else:
                return True, "Unknown"
        except Exception:
            return True, "Unknown"
    
    @staticmethod
    def check_memory() -> tuple:
        try:
            total_gb = 0  # Default value
            
            if platform.system() == "Windows":
                import ctypes
                
                # Use GlobalMemoryStatusEx for modern Windows (handles >4GB RAM)
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                    ]
                
                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
                total_gb = memory_status.ullTotalPhys / (1024**3)
            else:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            total_gb = int(line.split()[1]) / (1024**2)
                            break
            
            if total_gb >= 2:
                return True, f"{total_gb:.1f} GB RAM"
            elif total_gb > 0:
                return False, f"Only {total_gb:.1f} GB (need 2GB)"
            else:
                return True, "Unknown"
        except Exception:
            return True, "Unknown"


class ActivationClient:
    """License activation client"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
    
    def check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def activate(self, product_key: str, fingerprint: str, hostname: str, os_info: str) -> dict:
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/activate",
                json={
                    "product_key": product_key,
                    "machine_fingerprint": fingerprint,
                    "hostname": hostname,
                    "os_info": os_info,
                    "app_version": APP_VERSION
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    raise Exception(data.get("message", "Activation failed"))
                return data
            elif response.status_code == 404:
                raise Exception("Invalid product key. Please check and try again.")
            elif response.status_code == 403:
                try:
                    error_msg = response.json().get("detail", "Access forbidden")
                except:
                    error_msg = "Access forbidden"
                raise Exception(f"Activation blocked: {error_msg}")
            elif response.status_code >= 500:
                raise Exception("Server error. Please try again later.")
            else:
                raise Exception(f"Activation failed (HTTP {response.status_code})")
        
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to license server.\nCheck your internet connection.")
        except requests.exceptions.Timeout:
            raise Exception("Server timeout. Please try again.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")


class FileManager:
    """File management utilities"""
    
    def __init__(self):
        self.install_dir = INSTALL_DIR
        self.license_dir = LICENSE_DIR
        self.data_dir = INSTALL_DIR / "data"
    
    def setup_directories(self):
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.license_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_certificate(self, certificate: dict, fingerprint: str):
        """Save certificate - encrypted .dat is the source of truth"""
        cert_data = json.dumps(certificate, indent=2).encode()
        encrypted = CryptoUtils.encrypt_file(cert_data, fingerprint.encode())
        
        # Save encrypted (PRIMARY - source of truth)
        with open(self.license_dir / "certificate.dat", "wb") as f:
            f.write(encrypted)
        
        # Save fingerprint for later decryption
        with open(self.license_dir / ".fingerprint", "w") as f:
            f.write(fingerprint)
        
        # Also save JSON for container (container needs it)
        with open(self.license_dir / "certificate.json", "w") as f:
            json.dump(certificate, f, indent=2)
    
    def save_docker_credentials(self, encrypted_creds: str):
        with open(self.license_dir / "docker_credentials.dat", "w") as f:
            f.write(encrypted_creds)
    
    def save_compose_file(self, compose_content: str):
        with open(self.install_dir / "docker-compose.yml", "w") as f:
            f.write(compose_content)
    
    def save_public_key(self, public_key: str):
        with open(self.license_dir / "public_key.pem", "w") as f:
            f.write(public_key)
    
    def is_activated(self) -> bool:
        """Check if activated - uses encrypted .dat file"""
        return (self.license_dir / "certificate.dat").exists()
    
    def get_certificate(self) -> dict:
        """
        Get certificate from ENCRYPTED .dat file.
        This prevents users from manually editing dates.
        Falls back to .json if .dat doesn't exist (backward compatibility).
        """
        dat_file = self.license_dir / "certificate.dat"
        json_file = self.license_dir / "certificate.json"
        fingerprint_file = self.license_dir / ".fingerprint"
        
        # Try encrypted .dat file first (secure)
        if dat_file.exists() and fingerprint_file.exists():
            try:
                with open(fingerprint_file, "r") as f:
                    fingerprint = f.read().strip()
                
                with open(dat_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted = CryptoUtils.decrypt_file(encrypted_data, fingerprint.encode())
                return json.loads(decrypted.decode())
            except Exception as e:
                print(f"Error reading encrypted certificate: {e}")
                # Fall through to JSON fallback
        
        # Fallback to JSON (backward compatibility)
        if json_file.exists():
            try:
                with open(json_file, "r") as f:
                    return json.load(f)
            except:
                pass
        
        return None


class DockerManager:
    """Docker operations manager"""
    
    def __init__(self):
        self.install_dir = INSTALL_DIR
    
    def docker_login(self, registry: str, username: str, token: str) -> bool:
        try:
            result = subprocess.run(
                ["docker", "login", registry, "-u", username, "--password-stdin"],
                input=token,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def compose_up(self) -> tuple:
        compose_file = self.install_dir / "docker-compose.yml"
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "up", "-d"],
                capture_output=True,
                text=True,
                cwd=str(self.install_dir)
            )
            if result.returncode != 0:
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
    
    def check_services_running(self) -> bool:
        compose_file = self.install_dir / "docker-compose.yml"
        if not compose_file.exists():
            return False
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "ps", "-q"],
                capture_output=True,
                text=True,
                cwd=str(self.install_dir)
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except:
            return False


# ===========================================
# WIZARD PAGES
# ===========================================

class WizardPage(tk.Frame):
    """Base class for wizard pages"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, bg="white")
        self.wizard = wizard
        self.can_proceed = False
    
    def on_enter(self):
        """Called when page is shown"""
        pass
    
    def on_leave(self):
        """Called when leaving page"""
        pass
    
    def validate(self) -> bool:
        """Validate page before proceeding"""
        return self.can_proceed


class ManagementPage(WizardPage):
    """Management page for already installed systems - Start/Stop services"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.can_proceed = True
        self.docker_manager = DockerManager()
        self.file_manager = FileManager()
        self._create_widgets()
    
    def _create_widgets(self):
        # Main container
        main = tk.Frame(self, bg="white")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # License info card
        card = tk.Frame(main, bg="#f8f9fa", relief="solid", bd=1)
        card.pack(fill=tk.X, pady=(0, 8))
        
        inner = tk.Frame(card, bg="#f8f9fa")
        inner.pack(fill=tk.X, padx=15, pady=12)
        
        # Row helper function
        def add_row(parent, label_text, is_bold=False):
            row = tk.Frame(parent, bg="#f8f9fa")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label_text, font=("Segoe UI", 9), bg="#f8f9fa", 
                    fg="#666", width=10, anchor="w").pack(side=tk.LEFT)
            val = tk.Label(row, text="...", font=("Segoe UI", 9, "bold" if is_bold else "normal"), 
                          bg="#f8f9fa", anchor="w")
            val.pack(side=tk.LEFT, fill=tk.X)
            return val
        
        self.customer_val = add_row(inner, "Customer:")
        self.tier_val = add_row(inner, "Tier:")
        self.valid_val = add_row(inner, "Valid Until:")
        self.days_val = add_row(inner, "Remaining:", True)
        
        # Separator
        tk.Frame(inner, bg="#dee2e6", height=1).pack(fill=tk.X, pady=8)
        
        self.status_val = add_row(inner, "Services:", True)
        
        # Warning box (hidden initially)
        self.warning_box = tk.Frame(main, bg="#fff3cd", relief="solid", bd=1)
        self.warning_inner = tk.Frame(self.warning_box, bg="#fff3cd")
        self.warning_inner.pack(fill=tk.X, padx=12, pady=10)
        
        self.warning_text = tk.Label(self.warning_inner, text="", font=("Segoe UI", 9),
                                     bg="#fff3cd", fg="#856404", wraplength=320, justify=tk.LEFT)
        self.warning_text.pack(anchor="w")
        
        self.renew_btn = ttk.Button(self.warning_inner, text="🔄 Renew", 
                                    command=self._open_renew, width=12)
        
        # Action buttons
        self.btns = tk.Frame(main, bg="white")
        self.btns.pack(pady=10)
        
        self.start_btn = ttk.Button(self.btns, text="▶ Start", command=self._start, width=12)
        self.stop_btn = ttk.Button(self.btns, text="⏹ Stop", command=self._stop, width=12)
        self.open_btn = ttk.Button(self.btns, text="🌐 Open", command=self._open_dash, width=12)
        
        # Log
        tk.Label(main, text="Log:", font=("Segoe UI", 8), bg="white", fg="#999", 
                anchor="w").pack(anchor="w", pady=(8,2))
        self.log = tk.Text(main, height=3, font=("Consolas", 8), bg="#f8f9fa", 
                          relief="solid", bd=1, padx=6, pady=4)
        self.log.pack(fill=tk.BOTH, expand=True)
    
    def on_enter(self):
        """Load certificate and update UI"""
        cert = self.file_manager.get_certificate()
        
        if not cert:
            self.customer_val.config(text="No license found")
            return
        
        # Customer
        customer = cert.get("customer", {})
        if isinstance(customer, dict):
            name = customer.get("customer_name", customer.get("name", "N/A"))
        else:
            name = str(customer)
        self.customer_val.config(text=name)
        
        # Tier
        tier = cert.get("tier", cert.get("license_tier", "N/A"))
        self.tier_val.config(text=str(tier).upper())
        
        # Find valid_until - check multiple possible locations
        valid_until = None
        for key in ["valid_until", "expires", "expiry", "expiration"]:
            if key in cert:
                valid_until = cert[key]
                break
        if not valid_until and "validity" in cert:
            v = cert["validity"]
            if isinstance(v, dict):
                valid_until = v.get("valid_until", v.get("expires", ""))
        
        if valid_until:
            self._show_expiry(str(valid_until))
        else:
            self.valid_val.config(text="N/A")
            self.days_val.config(text="Unknown", fg="#666")
        
        self._update_status()
    
    def _show_expiry(self, date_str: str):
        """Parse date and show appropriate warning"""
        from datetime import datetime
        
        try:
            # Try to parse date
            clean = date_str.replace("Z", "").replace("+00:00", "").strip()
            
            # Try formats
            exp = None
            for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    exp = datetime.strptime(clean[:len("2025-12-06T23:59:59.000000")], fmt)
                    break
                except:
                    continue
            
            if not exp:
                exp = datetime.strptime(clean[:10], "%Y-%m-%d")
            
            # Display
            self.valid_val.config(text=exp.strftime("%b %d, %Y"))
            
            # Days left
            days = (exp - datetime.now()).days
            
            if days < 0:
                self.days_val.config(text=f"EXPIRED ({abs(days)}d ago)", fg="#dc3545")
                self._warn("expired", abs(days))
            elif days == 0:
                self.days_val.config(text="EXPIRES TODAY!", fg="#dc3545")
                self._warn("today", 0)
            elif days <= 3:
                self.days_val.config(text=f"{days} day{'s' if days>1 else ''} left!", fg="#dc3545")
                self._warn("critical", days)
            elif days <= 7:
                self.days_val.config(text=f"{days} days left", fg="#fd7e14")
                self._warn("warning", days)
            elif days <= 30:
                self.days_val.config(text=f"{days} days", fg="#ffc107")
                self._warn("notice", days)
            else:
                self.days_val.config(text=f"{days} days", fg="#28a745")
                self.warning_box.pack_forget()
                
        except Exception as e:
            self.valid_val.config(text=date_str[:10] if len(date_str)>=10 else date_str)
            self.days_val.config(text="Parse error", fg="#666")
            self._log(f"Date error: {e}")
    
    def _warn(self, level: str, days: int):
        """Show warning banner"""
        self.warning_box.pack(fill=tk.X, pady=(0, 8))
        self.renew_btn.pack_forget()
        
        msgs = {
            "expired": ("⛔ LICENSE EXPIRED!\nServices may stop. Contact admin or renew.", "#f8d7da", "#721c24", "📧 Contact"),
            "today": ("⚠️ EXPIRES TODAY!\nRenew immediately.", "#f8d7da", "#721c24", "🔄 Renew Now"),
            "critical": (f"⚠️ Expires in {days} day{'s' if days>1 else ''}!\nRenew now.", "#f8d7da", "#721c24", "🔄 Renew Now"),
            "warning": (f"⏰ Expires in {days} days.\nRenew soon.", "#fff3cd", "#856404", "🔄 Renew"),
            "notice": (f"License expires in {days} days.", "#fff3cd", "#856404", "🔄 Renew"),
        }
        
        msg, bg, fg, btn = msgs.get(level, msgs["notice"])
        self.warning_box.config(bg=bg)
        self.warning_inner.config(bg=bg)
        self.warning_text.config(text=msg, bg=bg, fg=fg)
        self.renew_btn.config(text=btn)
        self.renew_btn.pack(anchor="w", pady=(6, 0))
    
    def _open_renew(self):
        import webbrowser
        webbrowser.open(RENEW_URL)
    
    def _update_status(self):
        """Update service buttons"""
        self.start_btn.pack_forget()
        self.stop_btn.pack_forget()
        self.open_btn.pack_forget()
        
        running = self.docker_manager.check_services_running()
        if running:
            self.status_val.config(text="✓ Running", fg="#28a745")
            self.stop_btn.pack(side=tk.LEFT, padx=3)
            self.open_btn.pack(side=tk.LEFT, padx=3)
        else:
            self.status_val.config(text="○ Stopped", fg="#6c757d")
            self.start_btn.pack(side=tk.LEFT, padx=3)
    
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {msg}\n")
        self.log.see(tk.END)
        self.update()
    
    def _start(self):
        self.start_btn.pack_forget()
        self._log("Starting services...")
        def do():
            ok, out = self.docker_manager.compose_up()
            self._log("✓ Started" if ok else f"✗ Failed: {out}")
            self.after(0, self._update_status)
        threading.Thread(target=do, daemon=True).start()
    
    def _stop(self):
        self.stop_btn.pack_forget()
        self.open_btn.pack_forget()
        self._log("Stopping services...")
        def do():
            self.docker_manager.compose_down()
            self._log("✓ Stopped")
            self.after(0, self._update_status)
        threading.Thread(target=do, daemon=True).start()
    
    def _open_dash(self):
        import webbrowser
        webbrowser.open("http://localhost:3005")
        self._log("Opening dashboard...")


class WelcomePage(WizardPage):
    """Welcome page"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.can_proceed = True
        self._create_widgets()
    
    def _create_widgets(self):
        # Logo/Icon area
        icon_frame = tk.Frame(self, bg="white")
        icon_frame.pack(pady=(25, 12))
        
        tk.Label(
            icon_frame,
            text="🔐",
            font=("Segoe UI", 36),
            bg="white"
        ).pack()
        
        # Title
        tk.Label(
            self,
            text=f"Welcome to {APP_NAME} Setup",
            font=("Segoe UI", 16, "bold"),
            bg="white"
        ).pack(pady=(0, 6))
        
        # Version
        tk.Label(
            self,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 9),
            fg="#666666",
            bg="white"
        ).pack(pady=(0, 20))
        
        # Description
        desc_frame = tk.Frame(self, bg="white")
        desc_frame.pack(fill=tk.X, padx=60)
        
        tk.Label(
            desc_frame,
            text="This wizard will help you:",
            font=("Segoe UI", 10),
            bg="white",
            anchor="w"
        ).pack(anchor="w", pady=(0, 8))
        
        steps = [
            "• Check system requirements",
            "• Verify Docker installation",
            "• Activate your license",
            "• Install and configure the application",
            "• Start the services"
        ]
        
        for step in steps:
            tk.Label(
                desc_frame,
                text=step,
                font=("Segoe UI", 9),
                bg="white",
                fg="#444444",
                anchor="w"
            ).pack(anchor="w", pady=1)
        
        # System info
        info_frame = tk.Frame(self, bg="#f8f9fa", relief="solid", bd=1)
        info_frame.pack(fill=tk.X, padx=60, pady=(20, 0))
        
        tk.Label(
            info_frame,
            text=f"  Hostname: {platform.node()}",
            font=("Segoe UI", 8),
            bg="#f8f9fa",
            anchor="w"
        ).pack(anchor="w", pady=(8, 1), padx=10)
        
        tk.Label(
            info_frame,
            text=f"  OS: {platform.system()} {platform.release()}",
            font=("Segoe UI", 8),
            bg="#f8f9fa",
            anchor="w"
        ).pack(anchor="w", pady=1, padx=10)
        
        tk.Label(
            info_frame,
            text=f"  Install Path: {INSTALL_DIR}",
            font=("Segoe UI", 8),
            bg="#f8f9fa",
            anchor="w"
        ).pack(anchor="w", pady=(1, 8), padx=10)


class PrerequisitesPage(WizardPage):
    """Prerequisites check page"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.checks = {}
        self.check_thread = None
        self._create_widgets()
    
    def _create_widgets(self):
        # Title
        tk.Label(
            self,
            text="System Requirements",
            font=("Segoe UI", 14, "bold"),
            bg="white"
        ).pack(pady=(20, 3))
        
        tk.Label(
            self,
            text="Checking system requirements...",
            font=("Segoe UI", 9),
            fg="#666666",
            bg="white"
        ).pack(pady=(0, 12))
        
        # Checks container
        self.checks_frame = tk.Frame(self, bg="white")
        self.checks_frame.pack(fill=tk.BOTH, expand=True, padx=50)
        
        # Define all checks
        check_items = [
            ("docker", "Docker Desktop", "Required for running containers"),
            ("compose", "Docker Compose", "Required for multi-container setup"),
            ("docker_running", "Docker Daemon", "Docker must be running"),
            ("disk", "Disk Space", "Minimum 2GB required"),
            ("memory", "System Memory", "Minimum 2GB RAM recommended"),
        ]
        
        # Add port checks
        for port, name in REQUIRED_PORTS.items():
            check_items.append((f"port_{port}", f"Port {port} ({name})", "Must be available"))
        
        # Create check rows
        for check_id, name, desc in check_items:
            row = tk.Frame(self.checks_frame, bg="white")
            row.pack(fill=tk.X, pady=3)
            
            # Status icon
            icon_label = tk.Label(
                row,
                text="○",
                font=("Segoe UI", 10),
                fg="#6c757d",
                bg="white",
                width=2
            )
            icon_label.pack(side=tk.LEFT)
            
            # Name and description
            text_frame = tk.Frame(row, bg="white")
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            name_label = tk.Label(
                text_frame,
                text=name,
                font=("Segoe UI", 9),
                bg="white",
                anchor="w"
            )
            name_label.pack(anchor="w")
            
            desc_label = tk.Label(
                text_frame,
                text=desc,
                font=("Segoe UI", 7),
                fg="#888888",
                bg="white",
                anchor="w"
            )
            desc_label.pack(anchor="w")
            
            # Status text
            status_label = tk.Label(
                row,
                text="Checking...",
                font=("Segoe UI", 8),
                fg="#6c757d",
                bg="white",
                width=22,
                anchor="e"
            )
            status_label.pack(side=tk.RIGHT)
            
            self.checks[check_id] = {
                "icon": icon_label,
                "status": status_label,
                "passed": False
            }
        
        # Action buttons frame (for retry, start docker, etc.)
        self.action_frame = tk.Frame(self, bg="white")
        self.action_frame.pack(fill=tk.X, padx=50, pady=(10, 0))
        
        # Retry button
        self.retry_btn = ttk.Button(
            self.action_frame,
            text="🔄 Re-check",
            command=self._run_checks
        )
        
        # Status message
        self.status_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="white"
        )
        self.status_label.pack(pady=(12, 0))
    
    def on_enter(self):
        """Run checks when page is shown"""
        self._run_checks()
    
    def _run_checks(self):
        """Run all prerequisite checks"""
        self.can_proceed = False
        self.wizard.update_buttons()
        self.retry_btn.pack_forget()
        self.status_label.config(text="Checking prerequisites...", fg="#666666")
        
        # Reset all checks
        for check_id, check in self.checks.items():
            check["icon"].config(text="○", fg="#6c757d")
            check["status"].config(text="Checking...", fg="#6c757d")
            check["passed"] = False
        
        def do_checks():
            import time
            all_passed = True
            
            try:
                # Docker installed
                time.sleep(0.2)
                passed, info = SystemChecker.check_docker_installed()
                self._update_check("docker", passed, info)
                if not passed:
                    all_passed = False
                
                # Docker Compose
                time.sleep(0.2)
                passed, info = SystemChecker.check_docker_compose()
                self._update_check("compose", passed, info)
                if not passed:
                    all_passed = False
                
                # Docker running
                time.sleep(0.2)
                passed, info = SystemChecker.check_docker_running()
                self._update_check("docker_running", passed, info)
                if not passed:
                    all_passed = False
                
                # Disk space (check only, doesn't block)
                time.sleep(0.2)
                passed, info = SystemChecker.check_disk_space()
                self._update_check("disk", passed, info)
                # Temporarily disabled - uncomment to enforce
                # if not passed:
                #     all_passed = False
                
                # Memory
                time.sleep(0.2)
                passed, info = SystemChecker.check_memory()
                self._update_check("memory", passed, info)
                # Memory check doesn't block - just informational
                # if not passed:
                #     all_passed = False
                
                # Ports
                for port in REQUIRED_PORTS.keys():
                    time.sleep(0.1)
                    try:
                        passed, info = SystemChecker.check_port_available(port)
                        self._update_check(f"port_{port}", passed, info)
                        if not passed:
                            all_passed = False
                    except Exception as e:
                        self._update_check(f"port_{port}", True, "Unknown")
                
            except Exception as e:
                # If any check fails catastrophically, log it but continue
                print(f"Check error: {e}")
            
            # Final status - always call this
            try:
                self.after(0, lambda: self._finish_checks(all_passed))
            except Exception as e:
                print(f"Finish error: {e}")
        
        self.check_thread = threading.Thread(target=do_checks)
        self.check_thread.daemon = True
        self.check_thread.start()
    
    def _update_check(self, check_id: str, passed: bool, info: str):
        """Update a single check status"""
        def update():
            check = self.checks[check_id]
            check["passed"] = passed
            if passed:
                check["icon"].config(text="✓", fg="#28a745")
                check["status"].config(text=info, fg="#28a745")
            else:
                check["icon"].config(text="✗", fg="#dc3545")
                check["status"].config(text=info, fg="#dc3545")
        
        self.after(0, update)
    
    def _finish_checks(self, all_passed: bool):
        """Finish checking and update UI"""
        try:
            self.can_proceed = all_passed
            
            if all_passed:
                self.status_label.config(
                    text="✓ All requirements met! Click Next to continue.",
                    fg="#28a745"
                )
                self.retry_btn.pack_forget()
            else:
                self.status_label.config(
                    text="✗ Some requirements not met. Please fix and retry.",
                    fg="#dc3545"
                )
                self.retry_btn.pack(pady=(10, 0))
            
            self.wizard.update_buttons()
        except Exception as e:
            print(f"Error in _finish_checks: {e}")


class ActivationPage(WizardPage):
    """License activation page"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.activation_client = ActivationClient(LICENSE_SERVER)
        self.file_manager = FileManager()
        self.docker_manager = DockerManager()
        self.activation_result = None
        self._create_widgets()
    
    def _create_widgets(self):
        # Title
        tk.Label(
            self,
            text="License Activation",
            font=("Segoe UI", 16, "bold"),
            bg="white"
        ).pack(pady=(30, 5))
        
        tk.Label(
            self,
            text="Enter your product key to activate the license",
            font=("Segoe UI", 10),
            fg="#666666",
            bg="white"
        ).pack(pady=(0, 30))
        
        # Product key input
        key_frame = tk.Frame(self, bg="white")
        key_frame.pack(fill=tk.X, padx=60)
        
        tk.Label(
            key_frame,
            text="Product Key:",
            font=("Segoe UI", 10),
            bg="white",
            anchor="w"
        ).pack(anchor="w")
        
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(
            key_frame,
            textvariable=self.key_var,
            font=("Consolas", 14),
            width=40
        )
        self.key_entry.pack(fill=tk.X, pady=(5, 0), ipady=8)
        
        # Activate button
        self.activate_btn = ttk.Button(
            key_frame,
            text="🔑 Activate License",
            command=self._activate,
            style="Accent.TButton"
        )
        self.activate_btn.pack(pady=(15, 0))
        
        # Progress frame
        self.progress_frame = tk.Frame(self, bg="white")
        self.progress_frame.pack(fill=tk.X, padx=60, pady=(30, 0))
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        
        # Status log
        self.log_frame = tk.Frame(self, bg="white")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=60, pady=(20, 0))
        
        self.log_text = tk.Text(
            self.log_frame,
            height=8,
            font=("Consolas", 9),
            bg="#f8f9fa",
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def on_enter(self):
        """Check if already activated"""
        if self.file_manager.is_activated():
            cert = self.file_manager.get_certificate()
            if cert:
                self.can_proceed = True
                self.key_entry.config(state=tk.DISABLED)
                self.activate_btn.config(state=tk.DISABLED)
                self._log("✓ License already activated!")
                self._log(f"  Customer: {cert.get('customer', {}).get('customer_name', 'N/A')}")
                self._log(f"  Tier: {cert.get('tier', 'N/A').upper()}")
                self.wizard.update_buttons()
        else:
            self.key_entry.focus()
    
    def _log(self, message: str):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.update()
    
    def _activate(self):
        """Start activation process"""
        product_key = self.key_var.get().strip()
        
        if not product_key:
            messagebox.showerror("Error", "Please enter a product key")
            return
        
        self.key_entry.config(state=tk.DISABLED)
        self.activate_btn.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        thread = threading.Thread(target=self._do_activation, args=(product_key,))
        thread.daemon = True
        thread.start()
    
    def _do_activation(self, product_key: str):
        """Perform activation"""
        try:
            self.progress_var.set(0)
            
            # Check server
            self._log("→ Connecting to license server...")
            if not self.activation_client.check_connection():
                raise Exception("Cannot connect to license server")
            self._log("✓ Server connected")
            self.progress_var.set(10)
            
            # Generate fingerprint
            self._log("→ Generating machine fingerprint...")
            fingerprint = MachineFingerprint.get_fingerprint()
            self._log(f"✓ Fingerprint: {fingerprint[:24]}...")
            self.progress_var.set(20)
            
            # Setup directories
            self._log("→ Setting up directories...")
            self.file_manager.setup_directories()
            self._log("✓ Directories created")
            self.progress_var.set(30)
            
            # Activate
            self._log("→ Activating license...")
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
            
            # Save certificate
            self._log("→ Saving certificate...")
            self.file_manager.save_certificate(certificate, fingerprint)
            self._log("✓ Certificate saved")
            self.progress_var.set(60)
            
            # Save Docker credentials
            if "docker_credentials" in bundle:
                self._log("→ Saving Docker credentials...")
                self.file_manager.save_docker_credentials(
                    bundle["docker_credentials"]["encrypted_credentials"]
                )
                self._log("✓ Credentials saved (encrypted)")
            self.progress_var.set(70)
            
            # Save compose file
            if "compose_file" in bundle:
                self._log("→ Saving docker-compose.yml...")
                self.file_manager.save_compose_file(bundle["compose_file"])
                self._log("✓ Compose file saved")
            self.progress_var.set(80)
            
            # Save public key
            if "public_key" in bundle:
                self._log("→ Saving public key...")
                self.file_manager.save_public_key(bundle["public_key"])
                self._log("✓ Public key saved")
            self.progress_var.set(90)
            
            # Docker login
            if "docker_credentials" in bundle:
                self._log("→ Logging into Docker registry...")
                try:
                    creds = CryptoUtils.decrypt_credentials(
                        bundle["docker_credentials"]["encrypted_credentials"],
                        fingerprint
                    )
                    if self.docker_manager.docker_login(
                        creds["registry"],
                        creds["username"],
                        creds["token"]
                    ):
                        self._log("✓ Docker login successful")
                    else:
                        self._log("⚠ Docker login failed (may need manual login)")
                except Exception as e:
                    self._log(f"⚠ Docker login error: {e}")
            
            self.progress_var.set(100)
            
            # Success
            self._log("")
            self._log("═" * 40)
            self._log("✓ ACTIVATION COMPLETE!")
            self._log(f"  Customer: {certificate.get('customer', {}).get('customer_name', 'N/A')}")
            self._log(f"  Tier: {certificate.get('tier', 'N/A').upper()}")
            self._log("═" * 40)
            
            self.activation_result = result
            self.can_proceed = True
            self.after(0, self.wizard.update_buttons)
            
        except Exception as e:
            self._log(f"✗ Error: {e}")
            self.progress_var.set(0)
            self.after(0, lambda: self.key_entry.config(state=tk.NORMAL))
            self.after(0, lambda: self.activate_btn.config(state=tk.NORMAL))
            messagebox.showerror("Activation Failed", str(e))


class InstallationPage(WizardPage):
    """Installation/Service start page"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.docker_manager = DockerManager()
        self.file_manager = FileManager()
        self._create_widgets()
    
    def _create_widgets(self):
        # Title
        tk.Label(
            self,
            text="Installation",
            font=("Segoe UI", 16, "bold"),
            bg="white"
        ).pack(pady=(30, 5))
        
        tk.Label(
            self,
            text="Starting Docker services...",
            font=("Segoe UI", 10),
            fg="#666666",
            bg="white"
        ).pack(pady=(0, 30))
        
        # Progress
        progress_frame = tk.Frame(self, bg="white")
        progress_frame.pack(fill=tk.X, padx=60)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = tk.Label(
            progress_frame,
            text="Preparing...",
            font=("Segoe UI", 10),
            bg="white"
        )
        self.progress_label.pack()
        
        # Log
        self.log_frame = tk.Frame(self, bg="white")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=60, pady=(30, 0))
        
        self.log_text = tk.Text(
            self.log_frame,
            height=10,
            font=("Consolas", 9),
            bg="#f8f9fa",
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def on_enter(self):
        """Start installation when page is shown"""
        thread = threading.Thread(target=self._do_install)
        thread.daemon = True
        thread.start()
    
    def _log(self, message: str):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.update()
    
    def _do_install(self):
        """Perform installation"""
        import time
        
        try:
            self.progress_var.set(10)
            self.after(0, lambda: self.progress_label.config(text="Pulling Docker images..."))
            self._log("→ Pulling Docker images (this may take a few minutes)...")
            time.sleep(1)
            
            self.progress_var.set(30)
            self._log("→ Setting up containers...")
            
            self.progress_var.set(50)
            self.after(0, lambda: self.progress_label.config(text="Starting services..."))
            self._log("→ Starting Docker services...")
            
            success, output = self.docker_manager.compose_up()
            
            if success:
                self.progress_var.set(100)
                self.after(0, lambda: self.progress_label.config(text="Installation complete!"))
                self._log("✓ Services started successfully!")
                self._log("")
                self._log("Services running:")
                self._log("  • Frontend: http://localhost:3005")
                self._log("  • Backend: http://localhost:8000")
                
                self.can_proceed = True
                self.after(0, self.wizard.update_buttons)
            else:
                self.progress_var.set(0)
                self.after(0, lambda: self.progress_label.config(text="Installation failed"))
                self._log(f"✗ Failed to start services")
                self._log(f"  Error: {output}")
                
                # Show retry option
                self.after(0, self._show_retry)
        
        except Exception as e:
            self._log(f"✗ Error: {e}")
            self.after(0, self._show_retry)
    
    def _show_retry(self):
        """Show retry button"""
        retry_btn = ttk.Button(
            self,
            text="🔄 Retry Installation",
            command=lambda: threading.Thread(target=self._do_install).start()
        )
        retry_btn.pack(pady=10)


class FinishPage(WizardPage):
    """Finish/Summary page"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent, wizard)
        self.can_proceed = True
        self.docker_manager = DockerManager()
        self.file_manager = FileManager()
        self._create_widgets()
    
    def _create_widgets(self):
        # Success icon
        tk.Label(
            self,
            text="✓",
            font=("Segoe UI", 48),
            fg="#28a745",
            bg="white"
        ).pack(pady=(40, 10))
        
        # Title
        tk.Label(
            self,
            text="Setup Complete!",
            font=("Segoe UI", 20, "bold"),
            bg="white"
        ).pack(pady=(0, 30))
        
        # Summary frame
        summary_frame = tk.Frame(self, bg="#f8f9fa", relief="solid", bd=1)
        summary_frame.pack(fill=tk.X, padx=60, pady=(0, 20))
        
        self.summary_content = tk.Frame(summary_frame, bg="#f8f9fa")
        self.summary_content.pack(fill=tk.X, padx=20, pady=15)
        
        # Placeholders for summary info
        self.customer_label = tk.Label(
            self.summary_content,
            text="Customer: -",
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            anchor="w"
        )
        self.customer_label.pack(anchor="w", pady=2)
        
        self.tier_label = tk.Label(
            self.summary_content,
            text="Tier: -",
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            anchor="w"
        )
        self.tier_label.pack(anchor="w", pady=2)
        
        self.valid_label = tk.Label(
            self.summary_content,
            text="Valid Until: -",
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            anchor="w"
        )
        self.valid_label.pack(anchor="w", pady=2)
        
        self.services_label = tk.Label(
            self.summary_content,
            text="Services: -",
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            anchor="w"
        )
        self.services_label.pack(anchor="w", pady=2)
        
        # Options
        options_frame = tk.Frame(self, bg="white")
        options_frame.pack(fill=tk.X, padx=60, pady=(10, 0))
        
        self.launch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Open AI Dashboard in browser",
            variable=self.launch_var
        ).pack(anchor="w", pady=2)
        
        self.shortcut_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Create desktop shortcut",
            variable=self.shortcut_var
        ).pack(anchor="w", pady=2)
        
        # URLs
        urls_frame = tk.Frame(self, bg="white")
        urls_frame.pack(fill=tk.X, padx=60, pady=(30, 0))
        
        tk.Label(
            urls_frame,
            text="Access your application at:",
            font=("Segoe UI", 10),
            bg="white"
        ).pack(anchor="w")
        
        tk.Label(
            urls_frame,
            text="🌐  http://localhost:3005",
            font=("Segoe UI", 11, "bold"),
            fg="#0066cc",
            bg="white",
            cursor="hand2"
        ).pack(anchor="w", pady=(5, 0))
    
    def on_enter(self):
        """Load certificate info"""
        cert = self.file_manager.get_certificate()
        if cert:
            customer = cert.get("customer", {})
            self.customer_label.config(text=f"Customer: {customer.get('customer_name', 'N/A')}")
            self.tier_label.config(text=f"Tier: {cert.get('tier', 'N/A').upper()}")
            
            validity = cert.get("validity", {})
            valid_until = validity.get("valid_until", "N/A")
            if valid_until and valid_until != "N/A":
                valid_until = valid_until[:10]
            self.valid_label.config(text=f"Valid Until: {valid_until}")
            
            services = cert.get("docker", {}).get("services", {})
            enabled = [s for s, c in services.items() if c.get("enabled")]
            self.services_label.config(text=f"Services: {', '.join(enabled)}")
    
    def on_finish(self):
        """Handle finish actions"""
        if self.launch_var.get():
            import webbrowser
            webbrowser.open("http://localhost:3005")
        
        if self.shortcut_var.get():
            self._create_shortcut()
    
    def _create_shortcut(self):
        """Create desktop shortcut"""
        if platform.system() == "Windows":
            try:
                import winreg
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_path = os.path.join(desktop, "AI Dashboard.url")
                
                with open(shortcut_path, "w") as f:
                    f.write("[InternetShortcut]\n")
                    f.write("URL=http://localhost:3005\n")
            except:
                pass


# ===========================================
# MAIN WIZARD
# ===========================================

class SetupWizard:
    """Main setup wizard window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.configure(bg="white")
        
        # Set custom icon if exists
        self._set_icon()
        
        # Check if already installed
        self.file_manager = FileManager()
        self.is_installed = self.file_manager.is_activated()
        
        # Set window title and size based on mode
        if self.is_installed:
            self.root.title(f"{APP_NAME} Installer")
            self.root.geometry("420x480")
            x = (self.root.winfo_screenwidth() - 420) // 2
            y = (self.root.winfo_screenheight() - 480) // 2
            self.root.geometry(f"420x480+{x}+{y}")
        else:
            self.root.title(f"{APP_NAME} Installer")
            self.root.geometry("700x650")
            x = (self.root.winfo_screenwidth() - 700) // 2
            y = (self.root.winfo_screenheight() - 650) // 2
            self.root.geometry(f"700x650+{x}+{y}")
        
        self.root.resizable(False, False)
        
        # Style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(15, 8))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        
        # Pages
        self.pages = []
        self.current_page = 0
        self.step_labels = []
        
        if self.is_installed:
            self._create_management_layout()
        else:
            self._create_layout()
            self._create_pages()
            self._show_page(0)
    
    def _set_icon(self):
        """Set custom window icon"""
        try:
            # Try to load icon from current directory
            if os.path.exists(ICON_FILE):
                self.root.iconbitmap(ICON_FILE)
            # Try from script directory
            elif os.path.exists(os.path.join(os.path.dirname(__file__), ICON_FILE)):
                self.root.iconbitmap(os.path.join(os.path.dirname(__file__), ICON_FILE))
            # Try from install directory
            elif os.path.exists(INSTALL_DIR / ICON_FILE):
                self.root.iconbitmap(str(INSTALL_DIR / ICON_FILE))
        except Exception:
            pass  # Use default icon if custom icon fails
    
    def _create_management_layout(self):
        """Create layout for management mode (already installed)"""
        
        # Content (no header needed - window title is enough)
        self.content_frame = tk.Frame(self.root, bg="white")
        
        # Footer with close button (pack first so it stays at bottom)
        footer_frame = tk.Frame(self.root, bg="#f8f9fa", height=50)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        ttk.Button(
            footer_frame,
            text="Close",
            command=self.root.destroy
        ).pack(side=tk.RIGHT, padx=20, pady=10)
        
        ttk.Button(
            footer_frame,
            text="🔄 Reinstall",
            command=self._switch_to_install_mode
        ).pack(side=tk.LEFT, padx=20, pady=10)
        
        # Now pack content
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create and show management page
        self.management_page = ManagementPage(self.content_frame, self)
        self.management_page.pack(fill=tk.BOTH, expand=True)
        self.management_page.on_enter()
    
    def _switch_to_install_mode(self):
        """Switch from management to install mode"""
        if messagebox.askyesno("Reinstall", "This will run the setup wizard again.\n\nContinue?"):
            self.root.destroy()
            # Create new wizard in install mode
            new_wizard = SetupWizard.__new__(SetupWizard)
            new_wizard.root = tk.Tk()
            new_wizard.root.title(f"{APP_NAME} - Setup Wizard")
            new_wizard.root.geometry("700x650")
            new_wizard.root.resizable(False, False)
            new_wizard.root.configure(bg="white")
            
            x = (new_wizard.root.winfo_screenwidth() - 700) // 2
            y = (new_wizard.root.winfo_screenheight() - 650) // 2
            new_wizard.root.geometry(f"700x650+{x}+{y}")
            
            new_wizard.style = ttk.Style()
            new_wizard.style.configure("TButton", font=("Segoe UI", 10), padding=(15, 8))
            new_wizard.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
            
            new_wizard.file_manager = FileManager()
            new_wizard.is_installed = False
            new_wizard.pages = []
            new_wizard.current_page = 0
            new_wizard.step_labels = []
            
            new_wizard._create_layout()
            new_wizard._create_pages()
            new_wizard._show_page(0)
            new_wizard.root.mainloop()
    
    def _create_layout(self):
        """Create main layout"""
        
        # Header with steps
        self.header_frame = tk.Frame(self.root, bg="#f8f9fa", height=60)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)
        
        # Step indicators
        self.steps_frame = tk.Frame(self.header_frame, bg="#f8f9fa")
        self.steps_frame.pack(expand=True)
        
        self.step_labels = []
        step_names = ["Welcome", "Prerequisites", "Activate", "Install", "Finish"]
        
        for i, name in enumerate(step_names):
            step_frame = tk.Frame(self.steps_frame, bg="#f8f9fa")
            step_frame.pack(side=tk.LEFT, padx=10, pady=15)
            
            # Circle indicator
            circle = tk.Label(
                step_frame,
                text=str(i + 1),
                font=("Segoe UI", 9, "bold"),
                fg="white",
                bg="#6c757d",
                width=3,
                height=1
            )
            circle.pack(side=tk.LEFT, padx=(0, 5))
            
            # Step name
            label = tk.Label(
                step_frame,
                text=name,
                font=("Segoe UI", 9),
                fg="#6c757d",
                bg="#f8f9fa"
            )
            label.pack(side=tk.LEFT)
            
            self.step_labels.append((circle, label))
            
            # Connector line (except last)
            if i < len(step_names) - 1:
                line = tk.Frame(self.steps_frame, bg="#dee2e6", width=30, height=2)
                line.pack(side=tk.LEFT, pady=20)
        
        # Content area
        self.content_frame = tk.Frame(self.root, bg="white")
        
        # Footer with buttons (pack BEFORE content so it stays at bottom)
        self.footer_frame = tk.Frame(self.root, bg="#f8f9fa", height=60)
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.footer_frame.pack_propagate(False)
        
        # Now pack content frame
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        btn_container = tk.Frame(self.footer_frame, bg="#f8f9fa")
        btn_container.pack(side=tk.RIGHT, padx=20, pady=12)
        
        self.cancel_btn = ttk.Button(
            btn_container,
            text="Cancel",
            command=self._cancel
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.back_btn = ttk.Button(
            btn_container,
            text="← Back",
            command=self._back
        )
        self.back_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.next_btn = ttk.Button(
            btn_container,
            text="Next →",
            command=self._next,
            style="Accent.TButton"
        )
        self.next_btn.pack(side=tk.LEFT)
    
    def _create_pages(self):
        """Create wizard pages"""
        self.pages = [
            WelcomePage(self.content_frame, self),
            PrerequisitesPage(self.content_frame, self),
            ActivationPage(self.content_frame, self),
            InstallationPage(self.content_frame, self),
            FinishPage(self.content_frame, self)
        ]
    
    def _show_page(self, index: int):
        """Show a specific page"""
        # Hide all pages
        for page in self.pages:
            page.pack_forget()
        
        # Show current page
        self.current_page = index
        self.pages[index].pack(fill=tk.BOTH, expand=True)
        self.pages[index].on_enter()
        
        # Update step indicators
        for i, (circle, label) in enumerate(self.step_labels):
            if i < index:
                # Completed
                circle.config(text="✓", bg="#28a745")
                label.config(fg="#28a745")
            elif i == index:
                # Current
                circle.config(text=str(i + 1), bg="#0d6efd")
                label.config(fg="#0d6efd", font=("Segoe UI", 9, "bold"))
            else:
                # Future
                circle.config(text=str(i + 1), bg="#6c757d")
                label.config(fg="#6c757d", font=("Segoe UI", 9))
        
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states"""
        # Safety check
        if not self.pages or self.current_page >= len(self.pages):
            return
        
        page = self.pages[self.current_page]
        
        # Back button
        if self.current_page == 0:
            self.back_btn.pack_forget()
        else:
            self.back_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Next/Finish button
        if self.current_page == len(self.pages) - 1:
            self.next_btn.config(text="Finish", command=self._finish)
        else:
            self.next_btn.config(text="Next →", command=self._next)
        
        # Enable/disable based on page validation
        if page.can_proceed:
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.next_btn.config(state=tk.DISABLED)
    
    def _back(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.pages[self.current_page].on_leave()
            self._show_page(self.current_page - 1)
    
    def _next(self):
        """Go to next page"""
        page = self.pages[self.current_page]
        
        if page.validate():
            page.on_leave()
            if self.current_page < len(self.pages) - 1:
                self._show_page(self.current_page + 1)
    
    def _finish(self):
        """Finish wizard"""
        finish_page = self.pages[-1]
        if hasattr(finish_page, 'on_finish'):
            finish_page.on_finish()
        self.root.destroy()
    
    def _cancel(self):
        """Cancel wizard"""
        if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel the setup?"):
            self.root.destroy()
    
    def run(self):
        """Run the wizard"""
        self.root.mainloop()


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    wizard = SetupWizard()
    wizard.run()