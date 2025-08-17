from sqlalchemy import Column, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from db.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta


class Turn(Base):
    """
    turns 테이블 모델

    해당 테이블의 text들과 voice를 JSON으로 묶는 것을 고려중
    1) 묶을 경우 summary 생성이 유연해고, anomalies_reports의 종속성 증가
    1-1) 만약 묶는다면, v/t로 묶을 것인지, 질답으로 묶을 것인지도 추가 고민 요인
    2) But 답변 목소리가 별도 학습이 필요해서 고민됨

    결론:
    현재 단계에서 요약, 검색, AI 입력 구조화, 이상탐지 모델 입력/요약/문맥기억의 편의성을 위하여
    질답쌍 {q_text:txt, a_text:txt, q_voice: url, a_voice: url}형태로 대화 정보 구조화하여 저장

    단점:
    추후 사용자를 배려해 내용 쿼리 검색 기능을 구현하려면 재분리가 필요할 것
    """
    __tablename__ = 'turns'
    __table_args__ = {
        #"schema": "", # 파일명
        #"mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4", 
        "mysql_collate": "utf8mb4_general_ci" 
    }
    # mention id (질답 1쌍으로 관리)
    id = Column(UUID(as_uuid=True), primary_key=True)
    # 관계 회기 id
    conv_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'))
    # 질답쌍 {q_text:txt, a_text:txt, q_voice: url, a_voice: url}
    turn = Column(JSON, nullable=True)
    # 기록일자
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))
    # Conversation ↔ Turn 
    conversation = relationship("Conversation", back_populates="turns")