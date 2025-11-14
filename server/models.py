# models.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class RegisterRequest(BaseModel):
    customer: str
    machine_id: str


class LicenseResponse(BaseModel):
    license_id: str
    license: Dict[str, Any]


class RevokeRequest(BaseModel):
    license_id: str


class ValidateRequest(BaseModel):
    license: Dict[str, Any]