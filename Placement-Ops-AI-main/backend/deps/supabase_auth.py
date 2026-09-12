"""
Supabase-only identity verification for the FastAPI backend.

Replaces the previous three parallel auth systems (custom users table +
password hashing, hand-rolled OAuth, and a partially-wired Supabase check)
with a single flow:

  1. Frontend authenticates the user with Supabase Auth (email/password,
     Google, GitHub, LinkedIn -- whatever Supabase is configured for).
  2. Frontend sends the Supabase access token as a normal `Authorization:
     Bearer <token>` header on every backend request.
  3. This module verifies that token's signature and resolves `role` from
     our own `profile_roles` table -- never from the token's
     `user_metadata`, which is writable by the end user via the Supabase
     client SDK and therefore cannot be trusted for authorization
     decisions.

Signature verification supports BOTH Supabase signing modes:

  - Legacy projects: a single shared HS256 secret (SUPABASE_JWT_SECRET,
    found under Project Settings -> API -> JWT Settings).
  - Current projects (Supabase's "JWT Signing Keys" feature, on by default
    for new projects): asymmetric ES256 (or RS256), verified against the
    project's public JWKS at
    {SUPABASE_URL}/auth/v1/.well-known/jwks.json. No secret is needed for
    this path -- the keys are public by design; only the private signing
    key (which never leaves Supabase) can produce a valid signature.

Which path runs is decided per-token from the (unverified) JWT header's
`alg`/`kid`, not from a single global assumption -- so this keeps working
across a Supabase project migrating between signing modes, and across
multiple environments (e.g. an old project's HS256 secret in one .env and
a new project's JWKS in another) without code changes.
"""
import os
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import ProfileRole

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_JWKS_URL = os.environ.get("SUPABASE_JWKS_URL") or (
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
)

# PyJWKClient caches fetched keys in-process and refetches on kid miss, so
# this is safe to build once at import time and reuse across requests.
_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_JWKS_URL else None

HS256_ALGS = ["HS256"]
ASYMMETRIC_ALGS = ["ES256", "RS256"]


class CurrentUser(BaseModel):
    profile_id: str
    email: str
    role: str


def decode_supabase_jwt(token: str) -> dict:
    if token.count(".") != 2:
        raise HTTPException(status_code=401, detail="Malformed access token.")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")

    alg = header.get("alg")

    try:
        if alg in ASYMMETRIC_ALGS:
            # Current Supabase default: asymmetric signing key, verified
            # against the project's public JWKS. Requires SUPABASE_URL (or
            # SUPABASE_JWKS_URL) to be set -- no shared secret involved.
            if _jwks_client is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Backend received a JWT signed with "
                        f"{alg}, which requires JWKS verification, but "
                        "SUPABASE_URL is not configured on the backend."
                    ),
                )
            signing_key = _jwks_client.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token, signing_key, algorithms=[alg], audience="authenticated"
            )
        elif alg in HS256_ALGS:
            # Legacy Supabase project: shared HS256 secret.
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Backend received an HS256-signed JWT, but "
                        "SUPABASE_JWT_SECRET is not configured on the backend."
                    ),
                )
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=HS256_ALGS,
                audience="authenticated",
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid session token: The specified alg value is not allowed: {alg}",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.PyJWKClientError as e:
        # JWKS fetch/lookup failure (network issue, wrong SUPABASE_URL, or
        # a kid that no longer exists on Supabase's side).
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return auth_header.split(" ", 1)[1]


def get_verified_claims(request: Request) -> dict:
    """Verifies the token's signature/expiry only. Does NOT resolve a role --
    used by /auth/sync-profile, which runs before a ProfileRole row exists."""
    token = _extract_bearer_token(request)
    return decode_supabase_jwt(token)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> CurrentUser:
    """Verifies the token AND resolves the caller's role from our own
    profile_roles table. Use this (or require_role) on every route that
    needs to know who's calling."""
    payload = get_verified_claims(request)

    profile_id = payload.get("sub")
    email = payload.get("email")
    if not profile_id or not email:
        raise HTTPException(status_code=401, detail="Token payload missing sub/email.")

    record = db.query(ProfileRole).filter(ProfileRole.profile_id == profile_id).first()
    if not record:
        raise HTTPException(
            status_code=403,
            detail="No profile on file for this account. Call /auth/sync-profile first.",
        )

    return CurrentUser(profile_id=profile_id, email=email, role=record.role)


def require_role(*allowed_roles: str):
    """Dependency factory: Depends(require_role("recruiter", "tpo"))"""

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires role: {', '.join(allowed_roles)}.",
            )
        return user

    return _dependency
