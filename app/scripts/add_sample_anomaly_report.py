import os
import sys
# PYTHONPATH를 /app으로 설정, 다른 디렉토리를 참조하기 전에 다음 라인 명시 필요
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, select, desc
from db.models.anomaly_report import AnomalyReport
from db.models.conversation import Conversation
from core.config import settings
from uuid import uuid4
from datetime import datetime, timezone, timedelta

def add_fake_anomaly_report():
    # 동기 DB 엔진 및 세션 생성
    engine = create_engine(settings.SYNC_DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(bind=engine)
    db: Session = SessionLocal()
    try:
        # 가장 최근에 생성된 대화 조회
        result = db.execute(
            select(Conversation)
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            print("사용 가능한 대화가 없습니다. 먼저 대화를 생성해주세요.")
            return
            
        # 이미 해당 대화에 대한 이상 보고서가 있는지 확인
        existing_report = db.execute(
            select(AnomalyReport)
            .where(AnomalyReport.conv_id == conversation.id)
        ).scalar_one_or_none()
        
        if existing_report:
            print(f"이미 해당 대화(ID: {conversation.id})에 대한 이상 보고서가 존재합니다.")
            print(f"anomaly_report_id: {existing_report.id}")
            return
            
        # 가상 anomaly_report_id
        anomaly_report_id = uuid4()
        
        # AnomalyReport 생성
        anomaly_report = AnomalyReport(
            id=anomaly_report_id,
            conv_id=conversation.id,
            anomaly_report="❗️이 대화에서 감정적 불안정성이 감지되었습니다. 대화 중 급격한 감정 변화와 불안한 반응이 관찰되었습니다.",
            anomaly_turn={
                "start_turn": 2,
                "end_turn": 4,
                "anomaly_type": "emotional_instability",
                "severity": "moderate"
            }
        )
        db.add(anomaly_report)
        db.commit()
        
        print(f"가장 최근 생성된 대화에 대한 이상 보고서가 추가되었습니다.")
        print(f"conversation_id: {conversation.id}")
        print(f"anomaly_report_id: {anomaly_report_id}")
        
    except Exception as e:
        db.rollback()
        print(f"데이터 추가 중 오류가 발생했습니다: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_fake_anomaly_report() 