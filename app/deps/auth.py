import os
from fastapi import HTTPException, Request, status

from jose import jwt, JWTError

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_ISS = os.getenv("SUPABASE_ISS")
ALGORITHM = "HS256"

if not SUPABASE_JWT_SECRET or not SUPABASE_ISS:
    raise RuntimeError("Missing SUPABASE_JWT_SECRET or SUPABASE_ISS")

def get_claims_and_token(request: Request):
    """Authorization: Bearer <access_token> (Supabase 발급)을 검증하고 (claims, token)을 반환."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1]
    try:
        claims = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            issuer=SUPABASE_ISS,
            options={"verify_aud": False},  # aud 검증은 생략 (필요시 'authenticated' 확인)
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    return claims, token
