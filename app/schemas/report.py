from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional, Any
from datetime import datetime

class AnomalyReportResponse(BaseModel):
    reportId: UUID
    convId: UUID
    anomalyReport: Optional[str] = Field(default=None, description="이상 보고서 내용")
    anomalyTurn: Optional[Any] = Field(default=None, description="이상이 발생한 대화 턴")
    created_at: Optional[datetime] = Field(default=None, description="리포트 생성 시간")

class AnomalyReportListResponse(BaseModel):
    status: str = Field(default="ok", description="응답 상태")
    data: List[AnomalyReportResponse] = Field(description="이상 보고서 목록")

class AnomalyReportDetailResponse(BaseModel):
    status: str = Field(default="ok", description="응답 상태")
    mentionId: UUID = Field(description="리포트 ID")
    severity: str = Field(description="이상 심각도")
    event_interval: str = Field(description="이상 발생 구간")
    created_at: datetime = Field(description="리포트 생성 시간")
    anomalyReport: Optional[str] = Field(default=None, description="이상 보고서 상세 내용")
    anomalyTurn: Optional[Any] = Field(default=None, description="이상이 발생한 대화 턴")
