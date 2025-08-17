import requests
from datetime import timedelta
from fastapi import APIRouter, Request, Body, Depends, HTTPException, status
from db.database import async_session, get_db
from db.models.user import User
from db.models.family import Family
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models.user import User
from core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 로그인 및 JWT 토큰 발급
    """
    # 카카오 ID로 사용자 조회
    result = await db.execute(
        select(User).where(User.kakao_id == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 로그인 정보입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    } 
    
    
@router.post("/kakao_login")
async def kakao_login(request: Request):
    data = await request.json()
    access_token = data.get("access_token")
    if not access_token:
        return JSONResponse({"error": "No access token"}, status_code=400)

    user_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_res = requests.get(user_url, headers=headers)
    user_info = user_res.json()
    
    kakao_id = str(user_info["id"])
    name = user_info["kakao_account"].get("name", "")
    profile_img = user_info["kakao_account"]["profile"].get("profile_image_url", "")
    gender = user_info["kakao_account"].get("gender", "")
    birthday = user_info["kakao_account"].get("birthday", "")
    email = user_info["kakao_account"].get("email", "")
    phone = user_info["kakao_account"].get("phone_number", "")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.kakao_id == kakao_id))
        existing_user = result.scalar_one_or_none()
        
        family_code = None
        family_name = None
        if existing_user and existing_user.family_id:
            family = await session.get(Family, existing_user.family_id)
            if family:
                family_code = family.code
                family_name = family.name
        
        if existing_user:
            return JSONResponse(
                content={
                    "kakao_id": existing_user.kakao_id,
                    "name": existing_user.name, # name
                    "profile_img": existing_user.profile_img,
                    "gender": existing_user.gender,
                    "birthday": existing_user.birthday,
                    "email": existing_user.email,
                    "phone": existing_user.phone,
                    "family_id": str(existing_user.family_id) if existing_user.family_id else None,
                    "family_code": family_code,   
                    "family_name": family_name,
                    "family_role": existing_user.family_role,
                    "created_at": existing_user.created_at.isoformat() if existing_user.created_at else None,
                    "is_guardian": bool(existing_user.is_guardian) if existing_user.is_guardian is not None else None,
                    "is_registered": True
                },
                media_type="application/json; charset=utf-8"
            )
        else:
            return JSONResponse(
                content={
                    "kakao_id": kakao_id,
                    "name": name,
                    "profile_img": profile_img,
                    "gender": gender,
                    "birthday": birthday,
                    "email": email,
                    "phone": phone,
                    "is_registered": False
                },
                media_type="application/json; charset=utf-8"
            )

@router.post("/register_user")
async def register_user(user_data: dict = Body(...)):
    kakao_id = user_data.get("kakao_id")
    if not kakao_id:
        return JSONResponse({"error": "No kakao_id provided"}, status_code=400)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.kakao_id == kakao_id))
        user = result.scalar_one_or_none()
        family_id = user_data.get("family_id")
        family_code = user_data.get("family_code")
        family_name = user_data.get("family_name")

        # 1. user 테이블에는 family_id만 저장
        if user:
            user.name = user_data.get("name", user.name)
            user.profile_img = user_data.get("profile_img", user.profile_img)
            user.gender = user_data.get("gender", user.gender)
            user.birthday = user_data.get("birthday", user.birthday)
            user.email = user_data.get("email", user.email)
            user.phone = user_data.get("phone", user.phone)
            user.family_id = family_id or user.family_id
            user.family_role = user_data.get("family_role", user.family_role)
            user.created_at = user_data.get("created_at", user.created_at)
            user.is_guardian = user_data.get("is_guardian", user.is_guardian)
        else:
            new_user = User(
                kakao_id=user_data.get("kakao_id"),
                name=user_data.get("name"),
                profile_img=user_data.get("profile_img"),
                gender=user_data.get("gender"),
                birthday=user_data.get("birthday"),
                email=user_data.get("email"),
                phone=user_data.get("phone"),
                family_id=family_id,
                family_role=user_data.get("family_role"),
                created_at=user_data.get("created_at"),
                is_guardian=user_data.get("is_guardian"),
                password=get_password_hash("test1234")
            )
            session.add(new_user)

        # 2. family_code, family_name이 있으면 family 테이블에 업데이트
        if family_id and (family_code or family_name):
            family = await session.get(Family, family_id)
            if family:
                if family_code:
                    family.code = family_code
                if family_name:
                    family.name = family_name

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return JSONResponse({"error": "DB integrity error"}, status_code=500)
    return {"message": "User saved"}

@router.delete("/delete_by_kakao_id/{kakao_id}")
async def delete_user_by_kakao_id(
    kakao_id: str,
):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.kakao_id == kakao_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="해당 kakao_id의 사용자를 찾을 수 없습니다.")
        await session.delete(user)
        await session.commit()
        return {"message": f"{kakao_id} 사용자가 삭제되었습니다."} 
    
    
