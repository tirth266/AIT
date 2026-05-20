from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LoginRequest(BaseModel):
    client_id: str
    password: str
    totp: str

class LoginResponse(BaseModel):
    jwt_token: str
    refresh_token: str
    feed_token: str
    mac_address: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    jwt_token: str
    refresh_token: str

class ProfileResponse(BaseModel):
    client_id: str
    name: str
    email: str
    mobile: str
    exchanges: List[str]
    products: List[str]
