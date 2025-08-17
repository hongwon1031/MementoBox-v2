import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.auth import get_current_user
from db.database import get_db
from db.models.photo import Photo
from db.models.user import User
from db.models.conversation import Conversation
from schemas.photo import PhotoCreate, PhotoResponse
from services.photo import PhotoService, upload_photo_to_blob, save_photo_to_db, get_photos_by_family
from services.blob_storage import get_blob_service_client

router = APIRouter(
    prefix="/api/photos",
    tags=["photos"]
)

@router.post("/upload", response_model=PhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    year: int = Form(...),
    season: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    사진을 업로드하고 메타데이터를 저장합니다.
    
    Args:
        file: 업로드할 이미지 파일
        year: 사진 연도
        season: 사진 계절 (spring, summer, autumn, winter)
        description: 사진 설명 (텍스트)
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    # season 유효성 검사
    valid_seasons = ["spring", "summer", "autumn", "winter"]
    if season not in valid_seasons:
        raise HTTPException(
            status_code=400, 
            detail=f"유효하지 않은 계절입니다. 다음 중 하나여야 합니다: {', '.join(valid_seasons)}"
        )

    try:
        photo_service = PhotoService(db)
        photo = await photo_service.create_photo(
            file=file,
            current_user=current_user,
            year=year,
            season=season,
            description=description
        )
        return PhotoResponse.from_orm(photo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[PhotoResponse])
async def list_photos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    현재 사용자가 속한 가족의 모든 사진을 조회합니다.
    연도와 계절별로 정렬되어 반환됩니다.
    """
    photos = await get_photos_by_family(current_user.family_id, db)
    return photos

@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 사진의 상세 정보를 조회합니다.
    현재 사용자가 속한 가족의 사진만 조회 가능합니다.
    """
    result = await db.execute(
        select(Photo).where(
            Photo.id == photo_id,
            Photo.family_id == current_user.family_id
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없거나 접근 권한이 없습니다.")
    return photo

@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 사진을 삭제합니다.
    현재 사용자가 속한 가족의 사진만 삭제 가능합니다.
    """
    # 먼저 사진이 존재하고 접근 권한이 있는지 확인
    result = await db.execute(
        select(Photo).where(
            Photo.id == photo_id,
            Photo.family_id == current_user.family_id
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없거나 삭제 권한이 없습니다.")

    photo_service = PhotoService(db)
    try:
        if await photo_service.delete_photo(photo_id):
            return {"message": "사진이 삭제되었습니다."}
        raise HTTPException(status_code=500, detail="사진 삭제 중 오류가 발생했습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 