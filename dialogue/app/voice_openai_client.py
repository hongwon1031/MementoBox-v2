# dialog-service/app/openai_client.py

import os
import httpx
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime

load_dotenv()

# ─────────────────────────────환경변수─────────────────────────────
API_KEY    = os.getenv("AZURE_OPENAI_KEY")
ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
SPEECH_KEY    = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
#──────────────────────────────────────────────────────────

# ── (A) STT: 로컬에 저장된 WAV 파일 경로를 받아 텍스트를 리턴 ─────────────────────────────
def transcribe_audio_from_file(wav_filepath: str) -> str:
    """
    Azure Speech SDK를 사용하여, wav_filepath에 저장된 오디오를 STT하고
    결과 문자열을 반환합니다.
    """
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION
    )
    speech_config.speech_recognition_language = "ko-KR"
    audio_input = speechsdk.AudioConfig(filename=wav_filepath)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_input
    )
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text.strip()
    else:
        raise RuntimeError(f"STT 실패: reason={result.reason}, detail={result.no_match_details if result.no_match_details else ''}")


# ── (B) TTS: 텍스트를 받아서 WAV 파일로 저장 ─────────────────────────────────────────────
def synthesize_speech_to_file(text: str, output_wav_path: str) -> None:
    """
    Azure Speech SDK를 사용하여, text를 음성으로 합성한 뒤
    output_wav_path에 PCM WAV로 저장합니다.
    """
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION
    )
    # 한국어 여성 신디얼 목소리 예시
    speech_config.speech_synthesis_voice_name = "ko-KR-SunHiNeural"
    # WAV(PCM) 포맷으로 출력
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    audio_output = speechsdk.AudioConfig(filename=output_wav_path)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_output
    )
    result = synthesizer.speak_text(text)
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(f"TTS 실패: reason={result.reason}, error_details={result.error_details}")


# ── (C) GPT 호출: messages(List[dict])를 받아 Azure OpenAI Chat Completions 호출 ─────────────────
async def ask_gpt(messages):
    """
    Azure OpenAI Chat Completions를 호출하여, choices[0].message.content를 반환합니다.
    """
    headers = {
        "api-key": API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    # ENDPOINT에는 이미 '?api-version=...'까지 포함되어 있다고 가정합니다.
    request_url = ENDPOINT

    print("▶ [openai_client] Request URL   :", request_url)
    print("▶ [openai_client] Request headers:", headers)
    print("▶ [openai_client] Request body   :", body)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(request_url, headers=headers, json=body)

    print(f"▶ [openai_client] Response status code: {resp.status_code}")
    print(f"▶ [openai_client] Response body: {resp.text}")

    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API 호출 실패: status={resp.status_code}, body={resp.text}")

    data = resp.json()
    if "choices" not in data or len(data["choices"]) == 0:
        raise RuntimeError(f"OpenAI 응답 형식 오류: {data}")

    choice0 = data["choices"][0]
    if "message" not in choice0 or "content" not in choice0["message"]:
        raise RuntimeError(f"OpenAI 응답 키 누락: {data}")

    return choice0["message"]["content"]


# ── (D) 통합 함수: 텍스트 or 음성 입력에 따라 STT→GPT→TTS 또는 순수 GPT만 수행 ─────────────────────
async def ask_openai(messages=None, wav_filepath: str = None) -> str:
    """
    - messages: 기존처럼 텍스트 채팅만 할 때 사용
    - wav_filepath: 클라이언트가 보낸 음성 파일을 STT→GPT→TTS 처리할 때 사용

    리턴값:
      - (wav_filepath 사용 시) → 생성된 TTS WAV 파일 경로 (str)
      - (messages 사용 시) → GPT가 생성한 텍스트 응답 (str)
    """
    # ── 음성 모드 (wav_filepath) ───────────────────────────────────────────────────────────────
    if wav_filepath:
        # 1) STT: WAV 파일을 텍스트로 변환
        try:
            recognized_text = transcribe_audio_from_file(wav_filepath)
            
            print(f"▶ [openai_client] STT 인식 완료, 반환된 텍스트: \"{recognized_text}\"")
            print("▶ [openai_client] STT 인식 결과:", recognized_text)
            
        except Exception as stt_err:
            raise RuntimeError(f"STT 처리 중 오류: {stt_err}")

        # 2) GPT 호출에 넣을 메시지 리스트 구성
        system_prompt = {
            "role": "system",
            "content": "사용자가 방금 전송한 음성 메시지를 바탕으로 답변을 생성해 주세요."
        }
        user_msg = {
            "role": "user",
            "content": recognized_text
        }
        gpt_messages = [system_prompt, user_msg]

        # 3) 실제 GPT 호출
        try:
            gpt_response_text = await ask_gpt(gpt_messages)
            print(f"▶ [openai_client] GPT 응답 텍스트: \"{gpt_response_text}\"")
            print("▶ [openai_client] GPT 응답 텍스트:", gpt_response_text)
        except Exception as gpt_err:
            raise RuntimeError(f"GPT 호출 중 오류: {gpt_err}")

        # 4) TTS: GPT가 생성한 텍스트를 WAV 파일로 합성
        timestamp = int(datetime.utcnow().timestamp())
        output_wav = f"/tmp/tts_response_{timestamp}.wav"
        try:
            synthesize_speech_to_file(gpt_response_text, output_wav)
            print("▶ [openai_client] TTS 파일 생성 완료:", output_wav)
        except Exception as tts_err:
            raise RuntimeError(f"TTS 처리 중 오류: {tts_err}")

        # 5) 최종 WAV 파일 경로를 반환
        #return output_wav
        return gpt_response_text, output_wav

    # ── 텍스트 채팅 모드 (messages) ───────────────────────────────────────────────────────────
    if messages:
        return await ask_gpt(messages)

    # ── 둘 다 없으면 에러 ─────────────────────────────────────────────────────────────────────
    raise ValueError("ask_openai 호출 시, 'messages' 또는 'wav_filepath' 중 하나는 반드시 제공되어야 합니다.")
