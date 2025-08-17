from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any

# 기본 응답용 스키마
class ConversationBase(BaseModel):
    id: UUID
    photo_id: UUID
    created_at: datetime

    class Config:
        orm_mode = True


# 생성용 스키마 (요청용)
class ConversationCreate(BaseModel):
    photo_id: UUID  # 생성 시에는 photo_id만 필요

    class Config:
        orm_mode = True



# 공통 출력용 스키마
class TurnBase(BaseModel):
    id: UUID
    conv_id: UUID
    turn: Optional[Dict[str, Any]] = None  # JSON 컬럼
    recorded_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 생성 요청용 스키마
class TurnCreate(BaseModel):
    conv_id: UUID
    turn: Optional[Dict[str, Any]] = None
    recorded_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# SummaryUpdate
class SummaryUpdateRequest(BaseModel):
    summary_text: str