from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Response
from fastapi.responses import FileResponse, JSONResponse
from uuid import UUID
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.blob_storage import BlobStorageService, get_blob_service_client
from db.database import get_db
from services.llm_system import OptimizedDementiaSystem, upload_audio_to_blob
from services.blob_storage import get_blob_service_client, download_file_from_url
from db.models.user import User
from db.models.turn import Turn
from db.models.conversation import Conversation
from db.models.anomaly_report import AnomalyReport
from db.models.photo import Photo
from schemas.turn import TurnRequest
from schemas.chat import ConversationCreate, TurnCreate, SummaryUpdateRequest

import uuid
import os
import tempfile
from fastapi import UploadFile


router = APIRouter(
    prefix="/chat",
    tags=["llm"]
)
system = OptimizedDementiaSystem()

# 이미지 기반 대화 세션 시작 (질문 생성) 
@router.post("/start")
async def start_chat(image_id: str, db: Session = Depends(get_db)):
    TEMP_DIR = "./temp_images"
    
    # [0] DB에서 photo 정보 조회
    try:
        # image_id를 UUID로 변환하여 DB에서 조회
        photo_uuid = UUID(image_id)
        stmt = select(Photo).where(Photo.id == photo_uuid)
        result = await db.execute(stmt)
        photo = result.scalar_one_or_none()
        
        if not photo:
            raise HTTPException(status_code=404, detail=f"Photo not found with id: {image_id}")
        
        # Azure Blob Storage에서 이미지 다운로드 (URL에서 직접)
        print(f"📥 이미지 다운로드 시작: {photo.url}")
        image_bytes = await download_file_from_url(photo.url)
        
        # 임시 디렉토리 생성
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        
        # 임시 파일로 저장
        file_extension = os.path.splitext(photo.url)[-1] or '.jpg'
        temp_filename = f"{image_id}{file_extension}"
        image_path = os.path.join(TEMP_DIR, temp_filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
            
        print(f"✅ 이미지 다운로드 완료: {image_path}")
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format for image_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 다운로드 실패: {str(e)}")
    
    # 해당 이미지에 대한 가장 최근 대화 확인
    stmt = select(Conversation).where(
        Conversation.photo_id == photo_uuid
    ).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    latest_conversation = result.scalars().first()

    first_question = None
    audio_path = None
    is_continuation = False

    if latest_conversation:
        # 가장 최근 턴 가져오기
        stmt = select(Turn).where(
            Turn.conv_id == latest_conversation.id
        ).order_by(Turn.recorded_at.desc())
        result = await db.execute(stmt)
        latest_turn = result.scalars().first()

        if latest_turn and latest_turn.turn:
            # 세션이 완료되었는지 확인
            is_session_completed = (
                latest_turn.turn.get("q_text") == "session_completed" or 
                latest_turn.turn.get("a_text") == "session_completed"
            )
            
            if not is_session_completed:
                # 이전 대화가 있고 세션이 완료되지 않은 경우에만 이어서 대화 생성
                conversation_id = latest_conversation.id
                previous_question = latest_turn.turn.get("q_text")
                previous_answer = latest_turn.turn.get("a_text")
                
                if previous_answer and previous_answer != "session_completed":
                    first_question, audio_path = system.generate_next_question(previous_question, previous_answer)
                    is_continuation = True

    # conversation 생성이 필요한 경우 first_question,audio_path 만들어야 함
    if not is_continuation:
        # [1] Conversation 데이터 생성 & 첫 질문 LLM 생성 및 
        try:
            new_conversation = Conversation(
                id=uuid4(),
                photo_id=photo_uuid,
                # created_at은 자동으로 처리됨 -> 과연
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            db.add(new_conversation)
            await db.commit()
            await db.refresh(new_conversation)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")
        
        first_question, audio_path = system.analyze_and_start_conversation(image_path)
        conversation_id = new_conversation.id
    
    # [2] audio Blob 저장
    try:
        blob_service_client = get_blob_service_client("talking-voice")
        original_filename = os.path.basename(audio_path)
        blob_url = await upload_audio_to_blob(audio_path, original_filename, blob_service_client)
    except:
        blob_url = "블롭 스토리지 에러"
    
    # [3] turn 데이터 추가
    new_turn = Turn(
        id=uuid4(),
        conv_id=conversation_id,
        turn={
            "q_text": first_question,
            "q_voice": blob_url,
            "a_text": None,
            "a_voice": None
        },
        recorded_at=datetime.now()
    )
    db.add(new_turn)
    db.commit()

    # [4] 응답 생성
    response_data = {
        "status": "ok",
        "conversation_id": str(conversation_id),
        "question": first_question,
        "audio_url": blob_url,
        "photo_info": {
            "id": str(photo.id),
            "name": photo.name,
            "url": photo.url
        },
        "is_continuation": is_continuation
    }
    
    # [5] 임시 파일 정리
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"🗑️ 임시 파일 삭제: {image_path}")
    except Exception as e:
        print(f"⚠️ 임시 파일 삭제 실패: {str(e)}")
    
    return JSONResponse(content=response_data)

# 답변 받고 Turn DB 업데이트
@router.post("/user_answer")
async def answer_chat(
    conversation_id: UUID = Form(...), 
    db: Session = Depends(get_db)
):
    # 1. 마지막 턴 가져오기
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.desc())
    result = await db.execute(stmt)
    last_turn = result.scalars().first()

    if not last_turn or not last_turn.turn:
        raise HTTPException(status_code=404, detail="No previous turn found")
    
    question = last_turn.turn.get("q_text")
    user_answer, audio_path, should_end = system._run_conversation(question, is_voice=True)
    
    # [2] audio Blob 저장
    try:
        # Blob Storage에 업로드
        blob_service_client = get_blob_service_client("talking-voice")
        original_filename = os.path.basename(audio_path)
        blob_url = await upload_audio_to_blob(audio_path, original_filename, blob_service_client)
    except:
        blob_url = "블롭 스토리지 에러"

    # 3. 기존 턴에 유저 응답 업데이트
    updated_turn = last_turn.turn.copy()
    updated_turn["a_text"] = user_answer
    updated_turn["a_voice"] = blob_url

    last_turn.turn = updated_turn
    db.commit()

    
    return JSONResponse(content={
        "answer": user_answer, 
        "audio_url": blob_url, 
        "should_end": should_end
    })

# 강제 대화 종료 (프런트에서 종료 버튼 클릭 시)
@router.post("/force-end")
async def force_end_chat(
    conversation_id: UUID = Form(...), 
    current_question: str = Form(None),  # 현재 진행 중인 질문 (있다면)
    db: Session = Depends(get_db)
):
    """프런트에서 강제 종료 버튼을 눌렀을 때 사용"""
    
    # 현재 진행 중인 질문이 있다면 답변 null로 저장
    if current_question and current_question.strip():
        # 사용자가 답변하지 않은 질문을 답변 null로 저장
        force_end_turn = Turn(
            id=uuid4(),
            conv_id=conversation_id,
            turn={
                "q_text": current_question,
                "q_voice": None,
                "a_text": "session_completed",  # 답변하지 않고 종료된 경우
                "a_voice": None
            },
            recorded_at=datetime.now()
        )
        db.add(force_end_turn)
        await db.commit()
        
        print(f"🔚 강제 종료: 미답변 질문을 session_completed로 처리하여 저장했습니다. (conversation_id: {conversation_id})")
    else:
        # 마지막 턴을 찾아서 질문에 session_completed 표시
        stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.desc())
        result = await db.execute(stmt)
        latest_turn = result.scalar_one_or_none()
        
        if latest_turn:
            latest_turn.turn["q_text"] = "session_completed"
            await db.commit()
            print(f"🔚 강제 종료: 마지막 질문을 session_completed로 처리했습니다. (conversation_id: {conversation_id})")
    
    # 기존 end 로직 호출
    return await end_chat(conversation_id, db)

# 대화 종료 및 분석/요약 생성
@router.post("/end")
async def end_chat(conversation_id: UUID = Form(...), db: Session = Depends(get_db)):
    # 1. conversation_id로 모든 Turn 데이터 가져오기
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.asc())
    result = await db.execute(stmt)
    turns = result.scalars().all()
    
    if not turns:
        raise HTTPException(status_code=404, detail="No turns found for this conversation")
    
    # 2. Turn 데이터를 스토리 생성에 사용할 수 있는 형태로 변환
    results = system.generate_complete_analysis_from_turns(turns, conversation_id)
    analysis_file = results.get("analysis_file")
    story_txt = results.get("story_content")

    with open(analysis_file, "r", encoding="utf-8") as file:
        analysis_txt = file.read()

    try:
        # 기존 대화 찾기
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        
        # summary_text에 story_txt 저장
        conversation.summary_text = story_txt
        
        await db.commit()
        await db.refresh(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"요약 업데이트 실패: {str(e)}")
    

    # [] Anomaly Report 데이터 생성
    try:
        new_report = AnomalyReport(
            id=uuid4(),
            conv_id=conversation_id,
            anomaly_report = analysis_txt,
            anomaly_turn = None
        )
        db.add(new_report)
        await db.commit()
        await db.refresh(new_report)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")

    return results

# 🧪 테스트용 엔드포인트들
@router.post("/test/upload-image")
async def upload_test_image(image: UploadFile = File(...)):
    """테스트용 이미지 업로드"""
    TEMP_DIR = "./temp_images"
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    # 파일 저장
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{image.filename}"
    file_path = os.path.join(TEMP_DIR, filename)
    
    with open(file_path, "wb") as f:
        content = await image.read()
        f.write(content)
    
    return {
        "status": "success",
        "file_id": file_id,
        "filename": filename,
        "path": file_path,
        "message": "이미지가 업로드되었습니다. 이제 /start 엔드포인트에서 이 file_id를 사용하세요."
    }

@router.get("/test/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    """모든 대화 목록 조회"""
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "photo_id": conv.photo_id,
                "created_at": conv.created_at.isoformat()
            }
            for conv in conversations
        ]
    }

@router.get("/test/turns/{conversation_id}")
async def get_turns(conversation_id: UUID, db: Session = Depends(get_db)):
    """특정 대화의 모든 턴 조회"""
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.asc())
    result = await db.execute(stmt)
    turns = result.scalars().all()
    
    return {
        "conversation_id": str(conversation_id),
        "turns": [
            {
                "id": str(turn.id),
                "turn": turn.turn,
                "recorded_at": turn.recorded_at.isoformat()
            }
            for turn in turns
        ]
    }

@router.post("/test/quick-chat")
async def quick_chat_test(
    image_id: str = Form("test-image-001"),
    user_messages: str = Form("안녕하세요, 이 사진 정말 좋네요, 종료")  # 쉼표로 구분된 메시지들
):
    """빠른 대화 테스트 (여러 메시지를 한번에 처리)"""
    messages = [msg.strip() for msg in user_messages.split(",")]
    
    # 대화 시작
    conversation_id, first_question = system.analyze_and_start_conversation("./temp_images/test.jpg")
    
    results = {
        "conversation_id": str(conversation_id),
        "first_question": first_question,
        "turns": []
    }
    
    current_question = first_question
    
    # 각 메시지 처리
    for i, user_answer in enumerate(messages):
        # 종료 키워드 체크
        should_end = system.check_end_keywords(user_answer)
        
        # Turn 저장 (실제 DB 저장은 생략)
        turn_data = {
            "question": current_question,
            "answer": user_answer,
            "should_end": should_end
        }
        
        results["turns"].append(turn_data)
        
        if should_end:
            break
            
        # 다음 질문 생성
        try:
            next_question = system.generate_next_question(current_question, user_answer)
            current_question = next_question
            turn_data["next_question"] = next_question
        except:
            break
    
    return results