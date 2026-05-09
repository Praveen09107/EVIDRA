"""
EVIDRA — Authentication API.

Handles user login, JWT generation, and MFA workflow.
For the hackathon, MFA is a required state transition but mocked.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import bcrypt

from core.database import db
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False

class MFARequest(BaseModel):
    code: str

class UserProfile(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    org_id: str

# ═══════════════════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════════════════

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate JWT and return user dict."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    user = await db.fetchrow(
        "SELECT user_id, email, full_name, role, org_id FROM users WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return dict(user)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and trigger MFA requirement."""
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Verify bcrypt hash
    if not bcrypt.checkpw(form_data.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")

    # In a real app, generate a temp token. For hackathon, just generate full token but signal MFA required.
    # The frontend should route to /mfa immediately.
    access_token = create_access_token(data={"sub": str(user["user_id"])})
    return {"access_token": access_token, "token_type": "bearer", "mfa_required": True}


@router.post("/mfa/verify")
async def verify_mfa(mfa_data: MFARequest, current_user: dict = Depends(get_current_user)):
    """Mock MFA verification (accepts any 6-digit code)."""
    if len(mfa_data.code) != 6 or not mfa_data.code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid MFA code format (must be 6 digits)")
    return {"status": "success", "message": "MFA verified"}


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return current_user
