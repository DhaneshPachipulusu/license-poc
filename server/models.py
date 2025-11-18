"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

class RegisterRequest(BaseModel):
    machine_id: str
    customer: str

class LicenseResponse(BaseModel):
    license_id: str
    license: Dict[str, Any]

class ValidateRequest(BaseModel):
    license: Dict[str, Any]

class RevokeRequest(BaseModel):
    license_id: str

class RenewRequest(BaseModel):
    license_id: str
    extend_days: int = 30