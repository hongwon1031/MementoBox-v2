from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

# 공통 베이스 (응답 기준)
class PhotoBase(BaseModel):
    id: UUID
    name: Optional[str] = None

    # S3 전환: key/bucket 중심
    key: Optional[str] = None
    bucket: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    etag: Optional[str] = None

    # 과거 호환용 (있으면 내려주고, 없으면 presigned URL을 라우터에서 생성해서 내려도 됨)
    url: Optional[str] = None

    year: int
    season: Literal["spring", "summer", "autumn", "winter"]
    description: Optional[str] = None
    user_id: UUID
    family_id: UUID

class PhotoCreate(BaseModel):
    """
    생성 시 서버가 업로드 후 key/bucket/meta를 채우므로
    클라이언트는 보통 파일만 올리고 메타만 보냄. (url 제거)
    """
    name: Optional[str] = None
    year: int
    season: Literal["spring", "summer", "autumn", "winter"]
    description: Optional[str] = None
    user_id: UUID
    family_id: UUID

class PhotoResponse(PhotoBase):
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)
