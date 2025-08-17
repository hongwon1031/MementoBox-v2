from pydantic import BaseModel, UUID4
from datetime import datetime

class TurnRequest(BaseModel):
    conv_id: UUID4
    turn: dict  # {"q_text": str, "a_text": str, "q_voice": str, "a_voice": str}
    recorded_at: datetime