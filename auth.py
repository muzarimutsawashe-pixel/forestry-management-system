# ============================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "allied-timbers-dev-key-change-this-in-production-9f3a7b2e"
)
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8


# ------------------------------------------------------------
# ROLE LEVELS
# ------------------------------------------------------------

ROLE_LEVEL = {
    "forester":           1,
    "estate_manager":     2,
    "production_manager": 3,
    "admin":              4,
}

VALID_ROLES = list(ROLE_LEVEL.keys())


security = HTTPBearer(auto_error=False)


# ------------------------------------------------------------
# CREATE TOKEN
# ------------------------------------------------------------

def create_access_token(
    username: str,
    role: str,
    estate_id: Optional[int],
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":       username,
        "role":      role,
        "estate_id": estate_id,
        "iat":       now,
        "exp":       now + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ------------------------------------------------------------
# DECODE TOKEN
# ------------------------------------------------------------

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------
# CURRENT USER
# ------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    return {
        "username":  payload.get("sub"),
        "role":      payload.get("role"),
        "estate_id": payload.get("estate_id"),
    }


# ------------------------------------------------------------
# ROLE GATE FACTORY
# ------------------------------------------------------------

def require_min_level(min_level: int):
    def check(user: dict = Depends(get_current_user)) -> dict:
        if ROLE_LEVEL.get(user["role"], 0) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role '{user['role']}' does not have "
                    f"permission to perform this action."
                ),
            )
        return user
    return check


require_forester            = require_min_level(1)
require_estate_manager      = require_min_level(2)
require_production_manager  = require_min_level(3)
require_admin               = require_min_level(4)


# ------------------------------------------------------------
# ESTATE SCOPE
# ------------------------------------------------------------

def enforce_estate_scope(user: dict, estate_id: int) -> None:
    """
    Raise 403 if the user is not allowed to touch this estate.
    Production managers and admins bypass the check.
    """
    if user["role"] in ("production_manager", "admin"):
        return

    if user.get("estate_id") is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an estate.",
        )

    if int(user["estate_id"]) != int(estate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this estate.",
        )


# ------------------------------------------------------------
# PERMISSIONS MAP
# ------------------------------------------------------------

PERMISSIONS = {
    "forester": [
        "view_dashboard", "view_compartments", "view_operations",
        "view_map", "view_statistics",
        "add_operation", "edit_operation",
    ],
    "estate_manager": [
        "view_dashboard", "view_compartments", "view_operations",
        "view_map", "view_statistics",
        "add_operation", "edit_operation", "delete_operation",
        "add_compartment", "edit_compartment", "delete_compartment",
    ],
    "production_manager": [
        "view_dashboard", "view_compartments", "view_operations",
        "view_map", "view_statistics",
        "add_operation", "edit_operation", "delete_operation",
        "add_compartment", "edit_compartment", "delete_compartment",
        "view_all_estates",
    ],
    "admin": [
        "view_dashboard", "view_compartments", "view_operations",
        "view_map", "view_statistics",
        "add_operation", "edit_operation", "delete_operation",
        "add_compartment", "edit_compartment", "delete_compartment",
        "view_all_estates", "manage_users",
    ],
}