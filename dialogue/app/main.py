# dialog-service/app/main.py
import uuid
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from database import SessionLocal, Message as DBMessage, Report, init_db
from preprocess import preprocess_wav_file
from voice_openai_client import (
    ask_openai,
    transcribe_audio_from_file,
    synthesize_speech_to_file,
)

app = FastAPI()
init_db()


# ── Pydantic 모델 정의 ────────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_id: Optional[str] = "anonymous"
    messages: List[Message]
# ────────────────────────────────────────────────────────────────────────────────────────


@app.post("/chat")
async def chat_endpoint(chat: ChatRequest):
    """
    기존 텍스트 채팅 전용 엔드포인트. JSON body로 messages 리스트를 받고,
    DB에 저장 → GPT 호출 → 응답(텍스트) 리턴
    """
    user_id = chat.user_id
    messages = chat.messages

    db = SessionLocal()

    # 1) 요청으로 들어온 새 메시지들만 DB에 저장
    for m in messages:
        db_message = DBMessage(
            user_id=user_id,
            role=m.role,
            content=m.content,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)
    try:
        db.commit()
    except Exception as e:
        return {"type": "error", "message": f"DB 저장 중 오류: {e}"}

    # 2) 종료 처리 (마지막 메시지가 “종료”, “그만”, “끝” 중 하나일 때)
    last_content = messages[-1].content.strip().lower()
    if last_content in ["종료", "그만", "끝"]:
        # 2-1) DB에 저장된 user_id의 전체 대화 기록을 시간순으로 불러오기
        db = SessionLocal()
        history = (
            db.query(DBMessage)
              .filter(DBMessage.user_id == user_id)
              .order_by(DBMessage.timestamp)
              .all()
        )
        # 2-2) OpenAI에 보낼 메시지 리스트 구성
        full_chat = []
        # 시스템 프롬프트
        full_chat.append({
            "role": "system",
            "content": "지금까지 사용자와 나눈 대화를 토대로, 사용자의 관점에서 할머니가 옛날이야기를 하는 느낌의 스크립트를 만들어 주세요."
        })
        # DB에서 가져온 모든 메시지를 차례대로 추가
        for record in history:
            full_chat.append({
                "role": record.role,
                "content": record.content
            })

        # 2-3) OpenAI 호출 (텍스트 응답: 리포트 생성)
        try:
            report = await ask_openai(messages=full_chat)
        except Exception as ai_err:
            return {"type": "error", "message": f"OpenAI 호출 오류(리포트 생성): {ai_err}"}

        # 2-4) 생성된 리포트를 DB에 저장
        try:
            db_report = Report(
                user_id=user_id,
                content=report,
                timestamp=datetime.utcnow()
            )
            db.add(db_report)
            db.commit()
        except Exception as db_report_err:
            return {"type": "error", "message": f"리포트 DB 저장 중 오류: {db_report_err}"}

        return {
            "type": "report",
            "response": report
        }

    # 3) 일반 채팅 로직 (종료 키워드가 아니면)
    formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
    try:
        response_text = await ask_openai(messages=formatted_messages)
    except Exception as ai_err:
        return {"type": "error", "message": f"OpenAI 호출 오류(채팅): {ai_err}"}

    return {
        "type": "chat",
        "response": response_text
    }


# @app.post("/chat_audio")
# async def chat_audio_endpoint(
#     user_id: str = Form("anonymous"),
#     wav_file: UploadFile = File(...)
# ):
#     """
#     음성(STT → GPT → TTS) 전용 엔드포인트.
#     multipart/form-data로 user_id와 wav_file(오디오 파일)을 받아서:
#       1) 임시 디스크에 저장
#       2) STT → GPT → TTS 처리
#       3) 생성된 TTS WAV 파일을 FileResponse로 바로 반환
#          → 클라이언트(curl, 브라우저 등)에서 다운로드/재생 가능
#     """
#     # 1) 업로드된 WAV 파일을 임시 경로에 저장
#     temp_input = f"/tmp/input_audio_{int(datetime.utcnow().timestamp())}.wav"
#     raw = await wav_file.read()
#     # (디버깅용) 실제로 받아온 바이트 크기를 찍어볼 수 있습니다.
#     # print(f"▶ 서버에 도착한 WAV 바이트 크기: {len(raw)} bytes")
#     with open(temp_input, "wb") as f:
#         f.write(raw)

#     # 2) (선택) DB에 raw audio 정보나 transcript를 저장하고 싶다면 여기에 로직 추가 가능
#     #    예시: 
#     #       db = SessionLocal()
#     #       db_message = DBMessage(user_id=user_id, role="user_audio", content=temp_input, timestamp=datetime.utcnow())
#     #       db.add(db_message); db.commit()

#     # 3) ask_openai(wav_filepath=…) 호출 → TTS 결과 WAV 경로를 반환받음
#     try:
#         tts_output_path = await ask_openai(wav_filepath=temp_input)
#     except Exception as e:
#         # TTS 파이프라인 중 에러가 발생하면, JSON 형태로 에러 메시지를 리턴
#         return {"type": "error", "message": f"음성 파이프라인 오류: {e}"}

#     # 4) FileResponse를 사용해 TTS WAV 파일을 직접 스트리밍으로 내려준다
#     try:
#         return FileResponse(
#             path=tts_output_path,
#             media_type="audio/wav",
#             filename=tts_output_path.split("/")[-1]
#         )
#     except Exception as fe:
#         # FileResponse 생성/전송 과정에서 문제 발생 시 500 에러 리턴
#         raise HTTPException(status_code=500, detail=f"파일 전송 오류: {fe}")


## v3 ##
# @app.post("/chat_audio")
# async def chat_audio_endpoint(
#     user_id: str = Form("anonymous"),
#     wav_file: UploadFile = File(...)
# ):
#     """
#     음성(STT → GPT → TTS) 전용 엔드포인트.
#     multipart/form-data로 user_id와 wav_file(오디오 파일)을 받아서:
#       1) 임시 디스크에 저장
#       2) STT 결과를 DB에 저장
#       3) STT → GPT → TTS 처리
#       4) 생성된 TTS WAV 파일을 FileResponse로 바로 반환
#          → 클라이언트(curl, 브라우저 등)에서 다운로드/재생 가능
#     """
#     # 1) 업로드된 WAV 파일을 임시 경로에 저장
#     temp_input = f"/tmp/input_audio_{uuid.uuid4().hex}.wav"
#     raw = await wav_file.read()
#     with open(temp_input, "wb") as f:
#         f.write(raw)

#     # 1-2) 전처리 파일 경로 생성 (예: temp_input_output.wav)
#     temp_processed = temp_input.replace(".wav", "_proc.wav")
    
#     # 1-3) ffmpeg 전처리 수행
#     try:
#         preprocess_wav_file(temp_input, temp_processed, sample_rate=16000)
#         # (원한다면 원본 temp_input 파일을 삭제할 수 있음)
#         # os.remove(temp_input)
#     except Exception as e:
#         return {"type": "error", "message": f"전처리 오류: {e}"}
    
#     # 2) STT 수행 및 DB 저장
#     try:
#         recognized_text = transcribe_audio_from_file(temp_processed)
#         print(f"▶ [main.py] STT 인식 결과: \"{recognized_text}\"")
#     except Exception as stt_err:
#         return {"type": "error", "message": f"STT 오류: {stt_err}"}

#     # DB에 사용자 발화(role="user") 저장
#     db = SessionLocal()
#     db_message = DBMessage(
#         user_id=user_id,
#         role="user",
#         content=recognized_text,
#         timestamp=datetime.utcnow()
#     )
#     db.add(db_message)
#     db.commit()

#     # 3) ask_openai(wav_filepath=…) 호출 → TTS 결과 WAV 경로를 반환받음
#     try:
#         tts_output_path = await ask_openai(wav_filepath=temp_processed)
#     except Exception as e:
#         # TTS 파이프라인 중 에러가 발생하면, JSON 형태로 에러 메시지를 리턴
#         return {"type": "error", "message": f"음성 파이프라인 오류: {e}"}

#     # 4) FileResponse를 사용해 TTS WAV 파일을 직접 스트리밍으로 내려준다
#     try:
#         return FileResponse(
#             path=tts_output_path,
#             media_type="audio/wav",
#             filename=tts_output_path.split("/")[-1]
#         )
#     except Exception as fe:
#         # FileResponse 생성/전송 과정에서 문제 발생 시 500 에러 리턴
#         raise HTTPException(status_code=500, detail=f"파일 전송 오류: {fe}")

# v4 종료 로직 추가

# @app.post("/chat_audio")
# async def chat_audio_endpoint(
#     user_id: str = Form("anonymous"),
#     wav_file: UploadFile = File(...)
# ):
#     # 1) 업로드된 WAV 파일을 임시 경로에 저장
#     temp_input = f"/tmp/input_audio_{uuid.uuid4().hex}.wav"
#     raw = await wav_file.read()
#     with open(temp_input, "wb") as f:
#         f.write(raw)

#     # 1-2) 전처리 파일 경로 생성
#     temp_processed = temp_input.replace(".wav", "_proc.wav")

#     # 1-3) ffmpeg 전처리 수행 (16kHz·모노·PCM)
#     try:
#         preprocess_wav_file(temp_input, temp_processed, sample_rate=16000)
#         # (원한다면 temp_input 삭제)
#         # os.remove(temp_input)
#     except Exception as e:
#         return {"type": "error", "message": f"전처리 오류: {e}"}

#     # 2) STT 수행 및 DB 저장 (전처리된 파일 사용)
#     try:
#         recognized_text = transcribe_audio_from_file(temp_processed)
#     except Exception as stt_err:
#         return {"type": "error", "message": f"STT 오류: {stt_err}"}

#     # DB에 사용자 발화(role="user") 저장
#     db = SessionLocal()
#     db_message = DBMessage(
#         user_id=user_id,
#         role="user",
#         content=recognized_text,
#         timestamp=datetime.utcnow()
#     )
#     db.add(db_message)
#     db.commit()

#     # 3) 종료 키워드 검사: 파일명 기반
#     filename = wav_file.filename or ""
#     if filename.lower() == "종료.wav":
#         # 3-1) 전체 히스토리 로드
#         history = (
#             db.query(DBMessage)
#               .filter(DBMessage.user_id == user_id)
#               .order_by(DBMessage.timestamp)
#               .all()
#         )

#         # 3-2) GPT 메시지 구성
#         full_chat = [{
#             "role": "system",
#             "content": "지금까지 사용자와 나눈 대화를 토대로, 사용자의 관점에서 할머니가 옛날이야기를 하는 느낌의 스크립트를 만들어 주세요."
#         }]
#         for record in history:
#             full_chat.append({
#                 "role": record.role,
#                 "content": record.content
#             })

#         # 3-3) GPT 호출 (리포트 생성)
#         try:
#             report_text = await ask_openai(messages=full_chat)
#         except Exception as ai_err:
#             return {"type": "error", "message": f"OpenAI 호출 오류(리포트 생성): {ai_err}"}

#         # 3-4) 리포트 DB 저장
#         try:
#             db_report = Report(
#                 user_id=user_id,
#                 content=report_text,
#                 timestamp=datetime.utcnow()
#             )
#             db.add(db_report)
#             db.commit()
#         except Exception as db_report_err:
#             return {"type": "error", "message": f"리포트 DB 저장 중 오류: {db_report_err}"}

#         # 3-5) 리포트 TTS 및 반환
#         try:
#             timestamp = int(datetime.utcnow().timestamp())
#             report_wav = f"/tmp/report_{timestamp}.wav"
#             synthesize_speech_to_file(report_text, report_wav)
#             return FileResponse(
#                 path=report_wav,
#                 media_type="audio/wav",
#                 filename=os.path.basename(report_wav)
#             )
#         except Exception as tts_err:
#             raise HTTPException(status_code=500, detail=f"TTS 처리 중 오류: {tts_err}")

#     # 4) 일반 음성 채팅 로직 (종료 키워드가 아니라면)
#     try:
#         tts_output_path = await ask_openai(wav_filepath=temp_processed)
#     except Exception as e:
#         return {"type": "error", "message": f"음성 파이프라인 오류: {e}"}

#     # 5) 최종 TTS WAV 파일 그대로 내려주기
#     try:
#         return FileResponse(
#             path=tts_output_path,
#             media_type="audio/wav",
#             filename=os.path.basename(tts_output_path)
#         )
#     except Exception as fe:
#         raise HTTPException(status_code=500, detail=f"파일 전송 오류: {fe}")

# v5 gpt 답변 저장 추가

@app.post("/chat_audio")
async def chat_audio_endpoint(
    user_id: str = Form("anonymous"),
    wav_file: UploadFile = File(...),
):
    """
    음성(STT → GPT → TTS) 전용 엔드포인트.
    multipart/form-data로 user_id와 wav_file(오디오 파일)을 받아서:
      1) 임시 디스크에 저장
      2) 전처리(리샘플링·모노·PCM) → STT → 사용자 발화 DB 저장
      3) 종료 키워드 검사(파일명) → 전체 대화 리포트 생성/DB 저장/리포트 TTS 
         또는 (종료 키워드가 아니면) STT→GPT→assistant 응답 저장→TTS
      4) 생성된 TTS WAV 파일을 FileResponse로 반환
    """
    # ─────────────────────────────────────────────────────────────────────────
    # 1) 업로드된 WAV 파일을 임시 경로에 저장
    temp_input = f"/tmp/input_audio_{uuid.uuid4().hex}.wav"
    raw = await wav_file.read()
    with open(temp_input, "wb") as f:
        f.write(raw)

    # 1-2) 전처리 파일 경로 생성 (예: /tmp/input_audio_xxx_proc.wav)
    temp_processed = temp_input.replace(".wav", "_proc.wav")

    # 1-3) ffmpeg 전처리 수행 (16kHz·모노·PCM)
    try:
        preprocess_wav_file(temp_input, temp_processed, sample_rate=16000)
    except Exception as e:
        return {"type": "error", "message": f"전처리 오류: {e}"}

    # ─────────────────────────────────────────────────────────────────────────
    # 2) STT 수행 (전처리된 파일 사용)
    try:
        recognized_text = transcribe_audio_from_file(temp_processed)
    except Exception as stt_err:
        return {"type": "error", "message": f"STT 오류: {stt_err}"}

    # 2-1) DB에 사용자 발화(role="user") 저장
    db = SessionLocal()
    try:
        db_user = DBMessage(
            user_id=user_id,
            role="user",
            content=recognized_text,
            timestamp=datetime.utcnow(),
        )
        db.add(db_user)
        db.commit()
    except Exception:
        db.rollback()

    # ─────────────────────────────────────────────────────────────────────────
    # 3) 종료 키워드 검사: 파일명 기반 (테스트용 “종료.wav” 업로드 시)
    filename = wav_file.filename or ""
    if filename.lower() == "종료.wav":
        # 3-1) DB에 저장된 user_id의 전체 대화 기록을 시간순으로 불러오기
        history = (
            db.query(DBMessage)
              .filter(DBMessage.user_id == user_id)
              .order_by(DBMessage.timestamp)
              .all()
        )

        # 3-2) GPT에 보낼 메시지 리스트 구성
        full_chat = [
            {
                "role": "system",
                "content": "지금까지 사용자와 나눈 대화를 토대로, 사용자의 관점에서 할머니가 옛날이야기를 하는 느낌의 스크립트를 만들어 주세요."
            }
        ]
        for record in history:
            full_chat.append({"role": record.role, "content": record.content})

        # 3-3) GPT 호출 (리포트 생성)
        try:
            report_text = await ask_openai(messages=full_chat)
        except Exception as ai_err:
            db.close()
            return {"type": "error", "message": f"OpenAI 호출 오류(리포트 생성): {ai_err}"}

        # 3-4) 생성된 리포트를 DB에 저장
        try:
            db_report = Report(
                user_id=user_id,
                content=report_text,
                timestamp=datetime.utcnow(),
            )
            db.add(db_report)
            db.commit()
        except Exception as db_report_err:
            db.close()
            return {"type": "error", "message": f"리포트 DB 저장 중 오류: {db_report_err}"}

        # 3-5) 리포트 텍스트 출력
        db.close()
        return {
            "type": "report",
            "response": report_text
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 4) 일반 음성 채팅 로직 (종료 키워드가 아니면)
    #    → STT된 텍스트를 GPT에 전달해서 (assistant 텍스트, TTS WAV) 둘 다 리턴받음
    try:
        # ask_openai가 (response_text, tts_output_path)를 반환
        response_text, tts_output_path = await ask_openai(wav_filepath=temp_processed)
    except Exception as e:
        db.close()
        return {"type": "error", "message": f"음성 파이프라인 오류: {e}"}

    # 4-1) assistant 응답(role="assistant")을 DB에 저장
    try:
        db_assistant = DBMessage(
            user_id=user_id,
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow(),
        )
        db.add(db_assistant)
        db.commit()
    except Exception:
        db.rollback()

    # 5) 최종 TTS WAV 파일을 FileResponse로 내려줌
    try:
        db.close()
        return FileResponse(
            path=tts_output_path,
            media_type="audio/wav",
            filename=os.path.basename(tts_output_path),
        )
    except Exception as fe:
        db.close()
        raise HTTPException(status_code=500, detail=f"파일 전송 오류: {fe}")