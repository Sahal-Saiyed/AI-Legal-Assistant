"""Authentication HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.dependencies import get_auth_service, get_current_user
from backend.app.schemas.auth import AuthenticatedUser, AuthResponse, LoginRequest, RegisterRequest
from backend.app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        return service.register(request.name, str(request.email), request.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        return service.login(str(request.email), request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/me", response_model=AuthenticatedUser)
def current_user(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
    return user


@router.post("/session", response_model=AuthenticatedUser)
def renew_session(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Renew and return the current sliding authentication session."""
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    service.revoke_session(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
