from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from db.database import Base
from uuid import uuid4
from datetime import datetime, timezone, timedelta

class Photo(Base):
    """
    photos 테이블 모델 (S3 전환)
    """
    __tablename__ = "photos"

    # 사진 id
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # 원본 파일명
    name = Column(String, nullable=True)

    # S3 전환: bucket/key 중심
    bucket = Column(String, nullable=True)       # 운영에서 버킷이 하나면 nullable로 두고 서버에서 기본값 채움
    key = Column(String, nullable=True, index=True)

    # (선택) 메타데이터
    content_type = Column(String, nullable=True)
    size = Column(BigInteger, nullable=True)
    etag = Column(String, nullable=True)

    # 과거 호환: Azure/S3 정적 URL 저장 (점진 전환 후 제거 가능)
    url = Column(Text, nullable=True)

    # 연/계절/설명
    year = Column(Integer)
    season = Column(String)
    description = Column(Text, nullable=True)

    # 관계
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    family_id = Column(PGUUID(as_uuid=True), ForeignKey("families.id"))

    # 업로드 일자 (KST 기준)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))

    # 관계 매핑
    family = relationship("Family", back_populates="photos")
    user = relationship("User", back_populates="photos")
    conversations = relationship("Conversation", back_populates="photo", cascade="all, delete-orphan")

    # 인덱스 보강 (선택)
    __table_args__ = (
        Index("ix_photos_family_year_season", "family_id", "year", "season"),
    )
