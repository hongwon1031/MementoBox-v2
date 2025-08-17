from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import UUID

class PhotoBase(BaseModel):
    id: UUID
    name: Optional[str] = None
    url: str
    year: int
    season: Literal["spring", "summer", "autumn", "winter"]
    description: Optional[str] = None
    user_id: UUID
    family_id: UUID

# PhotoCreate가 PhotoBase를 상속받지 않는 이유:
# 1. id는 DB에서 자동 생성되는 필드이므로 생성 시에는 필요하지 않음
# 2. PhotoBase는 id를 포함하고 있어서, 상속받으면 불필요한 id 필드가 생성 요청에 포함됨
# 3. 생성 요청과 응답의 스키마를 명확하게 분리하여 관리
class PhotoCreate(BaseModel):
    name: Optional[str] = None
    url: str
    year: int
    season: Literal["spring", "summer", "autumn", "winter"]
    description: Optional[str] = None
    user_id: UUID
    family_id: UUID

class PhotoResponse(PhotoBase):
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True) 