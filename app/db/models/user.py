from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
from db.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    """
    users 테이블 모델
    """
    __tablename__ = "users"
    __table_args__ = {
        #"schema": "", # 파일명
        #"mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4", 
        "mysql_collate": "utf8mb4_general_ci" 
    } 
    # uuid
    id = Column(UUID(as_uuid=True), primary_key=True) 
    # kakao 로그인 정보
    kakao_id = Column(String, index=True)
    # 비밀번호 (해시된 값)
    password = Column(String)
    # 사용자명
    name = Column(String)
    # 이메일
    email = Column(String, nullable=True)
    # 전화번호
    phone = Column(String, nullable=True)
    # 성별
    gender = Column(String, nullable=True)
    # 생년월일
    birthday = Column(Date, nullable=True)
    # 프로필 사진
    profile_img = Column(Text, nullable=True)
    # 관계 가족 id
    family_id = Column(UUID(as_uuid=True), ForeignKey('families.id'))
    # 가족 역할: 할머니/할아버지, 손자/손녀/자녀 > 접근권한 설정
    family_role = Column(String)
    # 보호자 여부
    is_guardian = Column(Boolean, default=False)
    # 계정 생성일자
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))
    # Family ↔ User
    family = relationship("Family", back_populates="users")
    # User ↔ Photo
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    