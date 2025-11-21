"""
Machine Fingerprinting Module
Generates unique hardware-based identifier for license binding

Works on:
- Windows (10, 11, Server)
- Linux (Ubuntu, Debian, CentOS, etc.)
- Docker containers (with persistent volume)

Usage:
    from fingerprint import get_machine_fingerprint
    
    fingerprint = get_machine_fingerprint()
    print(f"Machine ID: {fingerprint}")
"""

import hashlib
import platform
import subprocess
import os
import uuid
import json
from pathlib import Path
from typing import Optional

# Path to store machine ID (for Docker persistence)
MACHINE_ID_FILE = "/var/license/machine_id.json"


def get_machine_fingerprint(force_regenerate: bool = False) -> str:
    """
    Get machine fingerprint (unique hardware-based ID)
    
    Strategy:
    1. Check if saved fingerprint exists (Docker persistence)
    2. If not, generate from hardware
    3. Save for future use
    
    Args:
        force_regenerate: Force regeneration even if saved exists
        
    Returns:
        32-character hex string (unique machine ID)
    """
    
    # Try to load saved fingerprint first
    if not force_regenerate:
        saved_fp = _load_saved_fingerprint()
        if saved_fp:
            print(f"✓ Using saved machine fingerprint: {saved_fp[:16]}...")
            return saved_fp
    
    # Generate new fingerprint from hardware
    print("Generating new machine fingerprint from hardware...")
    fingerprint = _generate_hardware_fingerprint()
    
    # Save for next time
    _save_fingerprint(fingerprint)
    
    print(f"✓ Generated fingerprint: {fingerprint[:16]}...")
    return fingerprint


def _generate_hardware_fingerprint() -> str:
    """
    Generate fingerprint from hardware components
    Combines multiple sources for uniqueness and stability
    """
    
    components = []
    system = platform.system()
    
    # 1. MAC Address (primary identifier)
    mac = _get_mac_address()
    if mac:
        components.append(f"MAC:{mac}")
    
    # 2. Machine ID (OS-level unique ID)
    machine_id = _get_machine_id()
    if machine_id:
        components.append(f"MID:{machine_id}")
    
    # 3. CPU Info
    cpu_info = _get_cpu_info()
    if cpu_info:
        components.append(f"CPU:{cpu_info}")
    
    # 4. Disk Serial (boot disk)
    disk_serial = _get_disk_serial()
    if disk_serial:
        components.append(f"DISK:{disk_serial}")
    
    # 5. Motherboard UUID (if available)
    mb_uuid = _get_motherboard_uuid()
    if mb_uuid:
        components.append(f"MB:{mb_uuid}")
    
    # 6. Hostname (less reliable but helpful)
    hostname = platform.node()
    if hostname:
        components.append(f"HOST:{hostname}")
    
    # Combine all components
    if not components:
        # Fallback: use random UUID (not ideal but better than failing)
        print("⚠ Warning: Using random UUID as fallback")
        components.append(f"FALLBACK:{uuid.uuid4().hex}")
    
    combined = "-".join(components)
    
    # Hash to create consistent 32-char fingerprint
    fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    return fingerprint


def _get_mac_address() -> Optional[str]:
    """Get primary MAC address"""
    try:
        # Get MAC of first non-loopback interface
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                       for i in range(0, 8*6, 8)][::-1])
        
        # Validate MAC (not all zeros or all Fs)
        if mac != "00:00:00:00:00:00" and mac != "ff:ff:ff:ff:ff:ff":
            return mac
    except:
        pass
    
    return None


def _get_machine_id() -> Optional[str]:
    """Get OS-level machine ID"""
    system = platform.system()
    
    try:
        if system == "Linux":
            # Linux: /etc/machine-id or /var/lib/dbus/machine-id
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        machine_id = f.read().strip()
                        if machine_id:
                            return machine_id
        
        elif system == "Windows":
            # Windows: Get machine GUID from registry
            try:
                output = subprocess.check_output(
                    'wmic csproduct get uuid',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode()
                
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    machine_id = lines[1].strip()
                    if machine_id and machine_id != "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF":
                        return machine_id
            except:
                pass
    except:
        pass
    
    return None


def _get_cpu_info() -> Optional[str]:
    """Get CPU identifier"""
    system = platform.system()
    
    try:
        if system == "Linux":
            # Linux: CPU info from /proc/cpuinfo
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'serial' in line.lower():
                        return line.split(':')[1].strip()
            
            # Fallback: CPU model
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line.lower():
                        return hashlib.md5(line.encode()).hexdigest()[:16]
        
        elif system == "Windows":
            # Windows: CPU ProcessorId
            try:
                output = subprocess.check_output(
                    'wmic cpu get processorid',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode()
                
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    cpu_id = lines[1].strip()
                    if cpu_id:
                        return cpu_id
            except:
                pass
    except:
        pass
    
    return None


def _get_disk_serial() -> Optional[str]:
    """Get boot disk serial number"""
    system = platform.system()
    
    try:
        if system == "Linux":
            # Linux: Try to get disk serial
            try:
                output = subprocess.check_output(
                    ['lsblk', '-o', 'SERIAL', '-n'],
                    stderr=subprocess.DEVNULL
                ).decode()
                
                serials = [s.strip() for s in output.split('\n') if s.strip()]
                if serials:
                    return serials[0]
            except:
                pass
        
        elif system == "Windows":
            # Windows: Get C: drive serial
            try:
                output = subprocess.check_output(
                    'wmic diskdrive get serialnumber',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode()
                
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    serial = lines[1].strip()
                    if serial:
                        return serial
            except:
                pass
    except:
        pass
    
    return None


def _get_motherboard_uuid() -> Optional[str]:
    """Get motherboard UUID"""
    system = platform.system()
    
    try:
        if system == "Linux":
            # Linux: DMI/SMBIOS UUID
            paths = [
                "/sys/class/dmi/id/product_uuid",
                "/sys/devices/virtual/dmi/id/product_uuid"
            ]
            
            for path in paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as f:
                            uuid = f.read().strip()
                            if uuid:
                                return uuid
                    except:
                        pass
        
        elif system == "Windows":
            # Windows: Already covered in machine_id
            pass
    except:
        pass
    
    return None


def _load_saved_fingerprint() -> Optional[str]:
    """Load saved fingerprint from file"""
    try:
        if os.path.exists(MACHINE_ID_FILE):
            with open(MACHINE_ID_FILE, 'r') as f:
                data = json.load(f)
                return data.get('fingerprint')
    except:
        pass
    
    return None


def _save_fingerprint(fingerprint: str):
    """Save fingerprint to file for persistence"""
    try:
        # Create directory if not exists
        os.makedirs(os.path.dirname(MACHINE_ID_FILE), exist_ok=True)
        
        data = {
            'fingerprint': fingerprint,
            'generated_at': platform.node(),
            'system': platform.system(),
            'version': '1.0'
        }
        
        with open(MACHINE_ID_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Fingerprint saved to {MACHINE_ID_FILE}")
    except Exception as e:
        print(f"⚠ Warning: Could not save fingerprint: {e}")


def get_system_info() -> dict:
    """Get detailed system information (for debugging)"""
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'hostname': platform.node(),
        'python_version': platform.python_version()
    }


# CLI interface for testing
if __name__ == "__main__":
    print("="*70)
    print("MACHINE FINGERPRINTING TEST")
    print("="*70)
    print()
    
    # Get system info
    print("System Information:")
    info = get_system_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()
    
    # Generate fingerprint
    print("Generating fingerprint...")
    fingerprint = get_machine_fingerprint()
    print()
    print(f"✓ Machine Fingerprint: {fingerprint}")
    print()
    
    # Generate again (should load from file)
    print("Loading again (should use saved)...")
    fingerprint2 = get_machine_fingerprint()
    print()
    
    # Verify consistency
    if fingerprint == fingerprint2:
        print("✓ Fingerprint is consistent!")
    else:
        print("✗ WARNING: Fingerprint changed!")
    print()
    
    print("="*70)