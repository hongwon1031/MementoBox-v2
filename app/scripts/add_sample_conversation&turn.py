import os
import sys
# PYTHONPATH를 /app으로 설정, 다른 디렉토리를 참조하기 전에 다음 라인 명시 필요
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, select, desc
from db.models.conversation import Conversation
from db.models.turn import Turn
from db.models.photo import Photo
from core.config import settings
from uuid import uuid4
from datetime import datetime, timezone, timedelta

def add_fake_conversation():
    # 동기 DB 엔진 및 세션 생성
    engine = create_engine(settings.SYNC_DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(bind=engine)
    db: Session = SessionLocal()
    try:
        # 가장 최근에 업로드된 사진 조회
        result = db.execute(
            select(Photo)
            .order_by(desc(Photo.uploaded_at))
            .limit(1)
        )
        photo = result.scalar_one_or_none()
        
        if not photo:
            print("사용 가능한 사진이 없습니다. 먼저 사진을 업로드해주세요.")
            return
            
        # 가상 conversation_id
        conversation_id = uuid4()
        
        # Conversation 생성
        conversation = Conversation(
            id=conversation_id,
            photo_id=photo.id,
            created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
        )
        db.add(conversation)
        db.commit()

        # Turn 예시 데이터 2개 추가
        turn1 = Turn(
            id=uuid4(),
            conv_id=conversation_id,
            turn={
                "q_text": "이 사진은 언제 찍은 거야?",
                "a_text": f"{photo.year}년 {photo.season}에 찍었어!",
                "q_voice": None,
                "a_voice": None
            },
            recorded_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
        )
        turn2 = Turn(
            id=uuid4(),
            conv_id=conversation_id,
            turn={
                "q_text": "이 사진에 대해 설명해줄래?",
                "a_text": f"{photo.description if photo.description else '특별한 순간을 담은 사진이야!'}",
                "q_voice": None,
                "a_voice": None
            },
            recorded_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
        )
        db.add_all([turn1, turn2])
        db.commit()
        print(f"가장 최근 업로드된 사진에 대한 대화 데이터가 추가되었습니다.")
        print(f"photo_id: {photo.id}")
        print(f"photo_name: {photo.name}")
        print(f"conversation_id: {conversation_id}")
    except Exception as e:
        db.rollback()
        print(f"데이터 추가 중 오류가 발생했습니다: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_fake_conversation()