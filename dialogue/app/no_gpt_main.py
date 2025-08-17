from fastapi import FastAPI
from database import SessionLocal, Message as DBMessage, Report, init_db
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
init_db()

# Pydantic 모델 정의
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_id: Optional[str] = "anonymous"
    messages: List[Message]

@app.post("/chat")
async def chat_endpoint(chat: ChatRequest):
    user_id = chat.user_id
    messages = chat.messages

    db = SessionLocal()

    # 1. 메시지 저장
    for m in messages:
        db_message = DBMessage(
            user_id=user_id,
            role=m.role,
            content=m.content,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)
    db.commit()

    # 2. 종료 처리
    if messages[-1].content.strip().lower() in ["종료", "그만", "끝"]:
        report_text = "이것은 테스트 리포트입니다. 실제로는 OpenAI가 생성한 스크립트가 여기에 들어갑니다."

        db_report = Report(
            user_id=user_id,
            content=report_text,
            timestamp=datetime.utcnow()
        )
        db.add(db_report)
        db.commit()

        return {
            "type": "report",
            "response": report_text
        }

    # 3. 일반 응답
    dummy_response = "이것은 OpenAI 없이 반환된 테스트 응답입니다."
    return {
        "type": "chat",
        "response": dummy_response
    }
