from enum import StrEnum
from fastapi import Depends, Header, HTTPException, status


class Role(StrEnum):
    SUBSIDIARY = "subsidiary"
    HQ = "hq"
    REVIEWER = "reviewer"
    ADMIN = "admin"


def current_role(x_user_role: str = Header(default=Role.HQ)) -> Role:
    try:
        return Role(x_user_role.lower())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-User-Role") from error


def require_roles(*allowed: Role):
    def dependency(role: Role = Depends(current_role)) -> Role:
        if role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not permitted for this action")
        return role
    return dependency
