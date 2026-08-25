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


def current_entity(x_entity_id: str | None = Header(default=None)) -> str | None:
    """The reporting entity the caller is acting as (MVP simulated login via X-Entity-Id)."""
    return x_entity_id


def require_entity_scope(role: Role, entity_id: str | None, company_id: str) -> None:
    """Subsidiary role is bound to exactly one entity (companies.id).

    Called explicitly inside endpoints because the company_id to validate comes
    from the request payload/path at runtime.
    """
    if role != Role.SUBSIDIARY:
        return
    if not entity_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Entity-Id header is required for subsidiary role")
    if entity_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subsidiary role is restricted to its own entity")
