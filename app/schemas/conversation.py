from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class TurnDetail(BaseModel):
    id: UUID
    conv_id: UUID
    turn: Optional[dict]
    recorded_at: Optional[datetime]
    class Config:
        from_attributes = True

class ConversationDetail(BaseModel):
    id: UUID
    photo_id: UUID
    created_at: datetime
    turns: List[TurnDetail] = []
    class Config:
        from_attributes = True

class TurnText(BaseModel):
    q_text: Optional[str]
    a_text: Optional[str]

class TurnVoice(BaseModel):
    q_voice: Optional[str]
    a_voice: Optional[str]

class ConversationOriginTextResponse(BaseModel):
    conversation_id: UUID
    origin_text: List[TurnText]

class ConversationOriginVoiceResponse(BaseModel):
    conversation_id: UUID
    origin_voice: List[TurnVoice] 