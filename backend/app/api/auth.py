"""Demo-level admin login.

Enough to show "admin has a username + password" during a demo without standing
up a users table: a single credential pair from settings, and a login endpoint
that returns the admin role. Every other role is still switched via the demo
role picker (X-User-Role header) — the rest of the API is unchanged.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from ..config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    role: str
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    settings = get_settings()
    if payload.username != settings.admin_username or payload.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"role": "admin", "username": payload.username}
