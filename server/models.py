"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime

# ============================================================================
# REQUEST MODELS
# ============================================================================

class ActivateRequest(BaseModel):
    """Request to activate a license"""
    product_key: str = Field(..., min_length=20, max_length=30)
    machine_fingerprint: str = Field(..., min_length=16, max_length=128)
    hostname: Optional[str] = Field(None, max_length=255)
    os_info: Optional[str] = Field(None, max_length=255)
    app_version: Optional[str] = Field(None, max_length=32)
    
    @validator('product_key')
    def validate_key_format(cls, v):
        """Validate product key format"""
        if not v or '-' not in v:
            raise ValueError('Invalid product key format')
        return v.upper()

class ValidateRequest(BaseModel):
    """Request to validate a certificate"""
    certificate: Dict = Field(...)
    
    @validator('certificate')
    def validate_cert_structure(cls, v):
        """Validate certificate has required fields"""
        required = ['machine_id', 'machine_fingerprint', 'signature']
        for field in required:
            if field not in v:
                raise ValueError(f'Certificate missing required field: {field}')
        return v

class HeartbeatRequest(BaseModel):
    """Heartbeat ping from client"""
    machine_id: str = Field(..., min_length=1)
    app_version: Optional[str] = None
    status: str = Field(default='running')

class CreateCustomerRequest(BaseModel):
    """Request to create a new customer"""
    company_name: str = Field(..., min_length=2, max_length=255)
    machine_limit: int = Field(default=3, ge=1, le=100)
    valid_days: int = Field(default=365, ge=1, le=3650)
    allowed_services: List[str] = Field(default=['dashboard'])
    notes: Optional[str] = None

class RenewRequest(BaseModel):
    """Request to renew a license"""
    customer_id: str = Field(...)
    extend_days: int = Field(..., ge=1, le=3650)

class RevokeRequest(BaseModel):
    """Request to revoke a license or machine"""
    machine_id: Optional[str] = None
    customer_id: Optional[str] = None
    reason: Optional[str] = None

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ActivateResponse(BaseModel):
    """Response to activation request"""
    success: bool
    certificate: Optional[Dict] = None
    message: str
    error: Optional[str] = None
    active_machines: Optional[List[Dict]] = None

class ValidateResponse(BaseModel):
    """Response to validation request"""
    valid: bool
    reason: str
    details: Optional[Dict] = None

class HeartbeatResponse(BaseModel):
    """Response to heartbeat"""
    status: str
    cert_update: Optional[Dict] = None
    message: Optional[str] = None

class CustomerResponse(BaseModel):
    """Customer details response"""
    id: str
    company_name: str
    product_key: str
    machine_limit: int
    valid_days: int
    allowed_services: List[str]
    created_at: str
    updated_at: str
    revoked: bool
    active_machines: int = 0
    notes: Optional[str] = None

class MachineResponse(BaseModel):
    """Machine details response"""
    id: str
    customer_id: str
    machine_id: str
    fingerprint: str
    hostname: Optional[str]
    os_info: Optional[str]
    app_version: Optional[str]
    activated_at: str
    last_seen: str
    status: str

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    message: str
    details: Optional[Dict] = None