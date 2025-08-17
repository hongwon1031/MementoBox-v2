from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
from db.database import Base
from sqlalchemy.orm import relationship
from uuid import uuid4

class Family(Base):
    """
    families 테이블 모델
    """
    __tablename__ = 'families'
    __table_args__ = {
        "mysql_charset": "utf8mb4", 
        "mysql_collate": "utf8mb4_general_ci" 
    }    

    # 가족 id
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # 외부 가족 코드
    code = Column(String, index=True)
    # 가족 이름
    name = Column(String(40), nullable=True)
    # 가족 생성 일자
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))
    # Family ↔ Photo 
    photos = relationship("Photo", back_populates="family", cascade="all, delete-orphan")
    # Family ↔ User 
    users = relationship("User", back_populates="family", cascade="all, delete-orphan")