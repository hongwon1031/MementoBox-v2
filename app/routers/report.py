import os
import uuid
import json
from core.auth import get_current_user
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from db.database import get_db
from db.models.user import User
from db.models.photo import Photo
from db.models.conversation import Conversation
from db.models.anomaly_report import AnomalyReport
from schemas.report import AnomalyReportResponse, AnomalyReportListResponse, AnomalyReportDetailResponse
from services.report import get_anomaly_reports, get_anomaly_report_detail

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"]
)


@router.get(
    "/",
    response_model=AnomalyReportListResponse,
    summary="가족의 이상 대화 리포트 목록 조회",
    description="현재 로그인한 사용자의 가족(family_id)에 속한 모든 이상 대화 리포트를 조회합니다. 최신 순 정렬"
)
async def get_family_anomaly_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_anomaly_reports(db, current_user.family_id)


@router.get(
    "/{report_id}",
    response_model=AnomalyReportDetailResponse,
    summary="이상 대화 리포트 단건 조회",
    description="현재 로그인한 사용자의 가족(family_id)에 속한 특정 이상 대화 리포트를 조회합니다."
)
async def get_anomaly_report_detail_endpoint(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_anomaly_report_detail(db, report_id, current_user.family_id)
