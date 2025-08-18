import os
import httpx
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Security
from deps.auth import get_claims_and_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)


router = APIRouter(prefix="/auth", tags=["auth"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

# ---------- (선택) 로그인 URL 생성: 브라우저에서 바로 테스트용 ----------
@router.get("/login-url")
def login_url(redirect_to: Optional[str] = "http://13.125.207.192/auth/me"):
    """
    카카오 OAuth 시작 URL을 반환(테스트용).
    redirect_to는 대시보드 URL Configuration의 Redirect URLs에 추가해두세요.
    """
    url = (
        f"{SUPABASE_URL}/auth/v1/authorize"
        f"?provider=kakao"
        f"&redirect_to={redirect_to}"
    )
    return {"authorize_url": url}

# ---------- 내 토큰/클레임 확인 ----------
@router.get("/me", dependencies=[Security(bearer)])
def me(dep=Depends(get_claims_and_token)):
    claims, _ = dep
    # sub = auth.users.id (uuid)
    return {"sub": claims.get("sub"), "email": claims.get("email"), "raw": claims}

# ---------- 내 프로필 조회 ----------
@router.get("/profile", dependencies=[Security(bearer)])
async def get_profile(dep=Depends(get_claims_and_token)):
    claims, token = dep
    user_id = claims["sub"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=*&id=eq.{user_id}&limit=1",
            headers={
                "apikey": ANON_KEY,
                "Authorization": f"Bearer {token}",  # 유저 권한으로 RLS 적용
            },
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        rows = r.json()
        return rows[0] if rows else {}

# ---------- 내 프로필 수정 (name/profile_img/email 중 일부 필드) ----------
class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    profile_img: Optional[str] = None

@router.patch("/profile", dependencies=[Security(bearer)])
async def update_profile(payload: ProfileUpdateBody = Body(...), dep=Depends(get_claims_and_token)):
    claims, token = dep
    user_id = claims["sub"]

    # 허용할 필드만 필터링 (테스트용)
    allowed = {k: payload[k] for k in ("name", "email", "profile_img") if k in payload}
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields")

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers={
                "apikey": ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=allowed,
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        rows = r.json()
        return rows[0] if rows else {}
