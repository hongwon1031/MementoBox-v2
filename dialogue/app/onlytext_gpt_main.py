from fastapi import FastAPI
from openai_client import ask_openai
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

    # 1. 요청으로 들어온 새 메시지들만 DB에 저장
    for m in messages:
        db_message = DBMessage(
            user_id=user_id,
            role=m.role,
            content=m.content,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)
    try:
        db.commit()
    except Exception as e:
        return {"type": "error", "message": f"DB 저장 중 오류: {e}"}

    # 2. 종료 처리
    if messages[-1].content.strip().lower() in ["종료", "그만", "끝"]:
        # 2-1) DB에 저장된 user_id의 전체 대화 기록을 시간순으로 불러오기
        history = (
            db.query(DBMessage)
              .filter(DBMessage.user_id == user_id)
              .order_by(DBMessage.timestamp)
              .all()
        )
        # 2-2) OpenAI에 보낼 메시지 리스트 구성
        full_chat = []
        # 먼저 시스템 프롬프트
        full_chat.append({
            "role": "system",
            "content": "지금까지 사용자와 너가 나눈 대화를 토대로 사용자의 입장에서 할머니가 옛날이야기를 하는 느낌으로 스크립트 만들어줘"
        })
        # 그다음 DB에서 가져온 모든 메시지를 차례대로 추가
        for record in history:
            full_chat.append({
                "role": record.role,
                "content": record.content
            })

        # 2-3) OpenAI 호출
        try:
            report = await ask_openai(full_chat)
        except Exception as ai_err:
            return {"type": "error", "message": f"OpenAI 호출 오류(리포트 생성): {ai_err}"}

        # 2-4) 생성된 리포트를 DB에 저장
        try:
            db_report = Report(
                user_id=user_id,
                content=report,
                timestamp=datetime.utcnow()
            )
            db.add(db_report)
            db.commit()
        except Exception as db_report_err:
            return {"type": "error", "message": f"리포트 DB 저장 중 오류: {db_report_err}"}

        return {
            "type": "report",
            "response": report
        }

    # 3. 일반 채팅 로직
    formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
    try:
        response = await ask_openai(formatted_messages)
    except Exception as ai_err:
        return {"type": "error", "message": f"OpenAI 호출 오류(채팅): {ai_err}"}

    return {
        "type": "chat",
        "response": response
    }
