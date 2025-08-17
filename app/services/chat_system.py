from dotenv import load_dotenv
from dataclasses import dataclass
from openai import AzureOpenAI
import os, time
import tiktoken
from pathlib import Path
import numpy as np
from datetime import datetime
import soundfile as sf
from core.config import settings

@dataclass
class StrangeResponse:
    """이상한 답변을 저장하는 데이터 클래스"""
    question: str
    answer: str
    timestamp: str
    severity: str  # "mild", "moderate", "severe"
    emotion: str = "중립"
    answer_quality: str = "normal"

@dataclass
class ConversationTurn:
    """대화 턴을 저장하는 데이터 클래스"""
    question: str
    answer: str
    timestamp: str
    emotion: str = "중립"
    answer_length: int = 0
    answer_quality: str = "normal"
    audio_file: str = ""  # 음성 파일 경로 추가


class ChatSystem:
    """자연스러운 질문 통합 채팅 시스템 - 토큰 효율 개선"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.max_tokens = os.getenv("AZURE_OPENAI_MAX_TOKENS")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )
        
        self.conversation_history = []
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.token_count = 0
        self.MAX_TOKENS = self.max_tokens
        self.conversation_turns = []
        self.last_question = ""
        
        # 음성 녹음 관련 설정
        self.recording = False
        self.audio_thread = None
        self.audio_data = []
        self.sample_rate = 44100
        
        # 음성 파일 저장 디렉토리 생성
        self.audio_dir = Path("audio_records")
        self.audio_dir.mkdir(exist_ok=True)
    
    def start_recording(self):
        """음성 녹음 시작"""
        if self.recording:
            return
        
        self.recording = True
        self.audio_data = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Status: {status}")
            if self.recording:
                self.audio_data.append(indata.copy())
        
        # self.audio_thread = sd.InputStream(
        #     samplerate=self.sample_rate,
        #     channels=1,
        #     callback=audio_callback
        # )
        # self.audio_thread.start()
    
    def stop_recording(self):
        """음성 녹음 중지 및 파일 저장"""
        if not self.recording:
            return None
        
        self.recording = False
        if self.audio_thread:
            self.audio_thread.stop()
            self.audio_thread.close()
            self.audio_thread = None
        
        if not self.audio_data:
            return None
        
        # 녹음된 데이터를 하나의 배열로 합치기
        audio_data = np.concatenate(self.audio_data, axis=0)
        
        # 파일명 생성 (timestamp 사용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.audio_dir / f"record_{timestamp}.wav"
        
        # WAV 파일로 저장
        sf.write(filename, audio_data, self.sample_rate)
        
        return str(filename)
        
    def setup_conversation_context(self, analysis_result):
        """대화 컨텍스트 설정"""
        caption = analysis_result.get("caption", "")
        dense_captions = analysis_result.get("dense_captions", [])
        mood = analysis_result.get("mood", "")
        time_period = analysis_result.get("time_period", "")
        key_objects = analysis_result.get("key_objects", [])
        people_description = analysis_result.get("people_description", "")
        people_count = analysis_result.get("people_count", 0)
        time_of_day = analysis_result.get("time_of_day", "")
        
        dense_captions_text = "\n".join([f"- {dc}" for dc in dense_captions])
        key_objects_text = ", ".join(key_objects)
        
        system_message = f"""너는 노인과 대화하는 요양보호사야. 노인과 특정 이미지에 대해서 질의응답을 주고받아. 
노인은 치매 증상이 갑자기 나타날 수도 있어. 반복되는 말에도 똑같이 대답해줘야 해. 
친절하고 어른을 공경하는 말투여야 해. 그리고 공감을 잘 해야 해. 예의도 지켜. 
너는 주로 질문을 하는 쪽이고, 노인은 대답을 해줄거야. 대답에 대한 리액션과 함께 적절히 대화를 이어 가.
노인의 발언이 끝나면 그와 관련된 공감 문장을 먼저 말한 후, 자연스럽게 그 기억에 대해 더 물어보는 꼬리 질문을 덧붙여. 하지만 메인 주제는 주어진 이미지 정보에 대해 어르신께 대화 문맥에 맞춰 자연스럽게 질문하는 거야.

=== 이미지 정보 ===
주요 설명: {caption}
분위기/감정: {mood}
추정 시대: {time_period}
시간대: {time_of_day}
인원 수: {people_count}명
주요 객체들: {key_objects_text}
인물 설명: {people_description}

세부 요소들:
{dense_captions_text}

=== 대화 원칙 ===
간결하게: 50자 이내로 질문하기
사진: 대화도 대화지만 사진에 대한 주제에서 벗아나진 말아줘
심도있는: 사람과 깊고 의미있게 대화하기 
흥미롭게: 이미지에 대한 흥미로운 질문을 먼저 던져 대화를 시작하세요
공감하기: 사진에 대하여 공감을 하고 친근하게 대화
하나씩만: 한 번에 질문 하나만
자연스럽게: 답변에 따라 연관 질문
따뜻하게: 공감 후 질문, 사람의 마음을 따듯하게 해주는 대화들"""
        
        self.conversation_history = [{"role": "system", "content": system_message}]
        self.token_count = len(self.tokenizer.encode(system_message))
    
    def generate_initial_question(self):
        """첫 질문 생성"""
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=self.conversation_history + [
                {"role": "user", "content": "어르신께 따듯하고 친근하게 사진에 대하여 질문을 해주세요. 50자 이내로 간결하게 질문해주세요."}
            ],
            max_tokens=512,
            temperature=0.8
        )
        
        initial_question = response.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": initial_question})
        self.token_count += len(self.tokenizer.encode(initial_question))
        self.last_question = initial_question
        
        return initial_question

    def chat_about_image2(self, user_query, with_audio=False):
        """대화 처리"""
        user_tokens = len(self.tokenizer.encode(user_query))
        
        # 음성 녹음 시작 (if requested)
        audio_file = None
        if with_audio:
            self.start_recording()
        
        # 대화 턴 저장
        if self.last_question:
            # 음성 녹음 중지 및 파일 저장 (if recording)
            if with_audio:
                audio_file = self.stop_recording()
            
            conversation_turn = ConversationTurn(
                question=self.last_question,
                answer=user_query,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                answer_length=len(user_query.strip()),
                audio_file=audio_file if audio_file else ""
            )
            self.conversation_turns.append(conversation_turn)
        
        self.conversation_history.append({"role": "user", "content": user_query})
        self.token_count += user_tokens
        
        # 토큰 제한 확인
        if self.token_count > self.max_tokens:
            answer = "대화 시간이 다 되었어요. 수고하셨습니다."
            self.conversation_history.append({"role": "assistant", "content": answer})
            return answer, True
        
        # AI 응답 생성
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=self.conversation_history,
            max_tokens=1024,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        
        self.conversation_history.append({"role": "assistant", "content": answer})
        self.token_count += len(self.tokenizer.encode(answer))
        self.last_question = answer
        
        if self.token_count > self.max_tokens:
            return answer, True
        
        return answer, False
    
    def chat_about_image(self, user_query, with_audio=False):
        """대화 처리"""
        user_tokens = len(self.tokenizer.encode(user_query))
        
        # 음성 녹음 시작 (if requested)
        audio_file = None
        if with_audio:
            self.start_recording()
        
        # 대화 턴 저장
        if self.last_question:
            # 음성 녹음 중지 및 파일 저장 (if recording)
            if with_audio:
                audio_file = self.stop_recording()
            
            conversation_turn = ConversationTurn(
                question=self.last_question,
                answer=user_query,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                answer_length=len(user_query.strip()),
                audio_file=audio_file if audio_file else ""
            )
            self.conversation_turns.append(conversation_turn)
        
        self.conversation_history.append({"role": "user", "content": user_query})
        self.token_count += user_tokens
        
        # 토큰 제한 확인
        if self.token_count > self.max_tokens:
            answer = "대화 시간이 다 되었어요. 수고하셨습니다."
            self.conversation_history.append({"role": "assistant", "content": answer})
            return answer, True
        
        # AI 응답 생성
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=self.conversation_history,
            max_tokens=1024,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        
        self.conversation_history.append({"role": "assistant", "content": answer})
        self.token_count += len(self.tokenizer.encode(answer))
        self.last_question = answer
        
        if self.token_count > self.max_tokens:
            return answer, True
        
        return answer, False