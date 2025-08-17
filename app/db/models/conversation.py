from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
from db.database import Base
from sqlalchemy.orm import relationship

class Conversation(Base):
    
    """
    conversations 테이블 모델

    대화 흐름 기반의 이상현상 보고를 고려함
    """
    __tablename__ = 'conversations'
    __table_args__ = {
        #"schema": "", # 파일명
        #"mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4", 
        "mysql_collate": "utf8mb4_general_ci" 
    }
    # 대화 회기 id
    id = Column(UUID(as_uuid=True), primary_key=True)
    # 관계 사진 id
    photo_id = Column(UUID(as_uuid=True), ForeignKey('photos.id'))
    # 요약 텍스트
    summary_text = Column(Text, nullable=True)
    # 요약 음성
    summary_voice = Column(Text, nullable=True)
    # 대화 생성 일자
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))
    # Photo ↔ Conversation 
    photo = relationship("Photo", back_populates="conversations")
    # Conversation ↔ Turn
    turns = relationship("Turn", back_populates="conversation", cascade="all, delete-orphan")
    # Conversation ↔ AnomalyReport
    anomaly_report = relationship("AnomalyReport", back_populates="conversation", cascade="all, delete-orphan", uselist=False)