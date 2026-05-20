from fastapi import APIRouter, Depends, HTTPException
from ..services.auth_service import AuthService
from ..models.auth_models import LoginRequest, LoginResponse, ProfileResponse
from ..utils.token_manager import token_manager

router = APIRouter(prefix="/api/broker/angel", tags=["AngelOne Auth"])
auth_service = AuthService()

@router.post("/login", response_model=LoginResponse)
async def login():
    """
    Login to Angel One using environment credentials and TOTP.
    The request body is ignored as we use env vars for security.
    """
    try:
        data = await auth_service.login()
        return LoginResponse(
            jwt_token=data['jwtToken'],
            refresh_token=data['refreshToken'],
            feed_token=data['feedToken'],
            mac_address=data.get('macAddress')
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout():
    try:
        await auth_service.logout()
        return {"status": "success", "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
async def profile():
    try:
        data = await auth_service.get_profile()
        return data
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/session/status")
async def session_status():
    tokens = token_manager.get_tokens()
    if not tokens:
        return {"is_valid": False, "has_tokens": False}
    return {
        "is_valid": True,
        "has_tokens": True,
        "has_jwt": bool(tokens.get('jwt_token')),
        "has_refresh": bool(tokens.get('refresh_token')),
        "has_feed": bool(tokens.get('feed_token'))
    }

@router.post("/session/refresh")
async def session_refresh():
    try:
        success = token_manager.refresh_tokens()
        return {"status": "success" if success else "failed", "message": "Token refreshed" if success else "Refresh failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
