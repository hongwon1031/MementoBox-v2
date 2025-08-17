from dotenv import load_dotenv
from dataclasses import dataclass
from openai import AzureOpenAI
import os, time
import tiktoken
from pathlib import Path
import numpy as np
from datetime import datetime
import soundfile as sf
# import sounddevice as sd
import json

from services.chat_system import StrangeResponse
from core.config import settings

class StoryGenerator:
    def __init__(self, chat_system):
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        self.chat_system = chat_system
        self.client = chat_system.client
        self.strange_responses = []
        self.rule_based_alerts = []
        self.conversation_id = ""
    
    def _create_conversation_folders(self, image_path):
        image_basename = os.path.splitext(os.path.basename(image_path))[0]
        
        # conversation_log/{이미지명}/ 폴더 생성
        image_dir = Path("conversation_log") / image_basename
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # 기존 대화 폴더들 확인하여 다음 번호 결정
        existing_dirs = list(image_dir.glob(f"{image_basename}_conv*"))
        conv_number = len(existing_dirs) + 1
        
        # 대화 ID: {이미지명}_conv{번호}
        self.conversation_id = f"{image_basename}_conv{conv_number}"
        
        # 대화별 폴더: {이미지명}_conv{번호}/
        conversation_dir = image_dir / self.conversation_id
        conversation_dir.mkdir(exist_ok=True)
        
        print(f"📁 저장 구조:")
        print(f"   메인 폴더: conversation_log/{image_basename}/{self.conversation_id}/")
        print(f"   대화 파일: {self.conversation_id}.txt")
        return conversation_dir
    

    
    def _load_qa_pairs_for_report(self, pairs_dir):
        qa_files = sorted([f for f in pairs_dir.glob("qa_*.txt")])
        qa_data = []
        for qa_file in qa_files:
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    qa_data.append({'file': qa_file.name, 'content': f.read()})
            except Exception:
                continue
        return qa_data
    
    def analyze_speech_patterns(self):
        if not self.chat_system.conversation_turns:
            return
        
        patterns = {
            'severe_depression': ["죽고싶", "살기싫", "의미없", "포기하고싶", "지쳤", "힘들어죽겠", "세상이싫", "절망"],
            'severe_anxiety': ["무서워죽겠", "불안해미쳐", "걱정돼죽겠", "두려워", "숨막혀", "공황", "패닉"],
            'severe_anger': ["화나죽겠", "미쳐버리겠", "짜증나죽겠", "열받아", "빡쳐", "분해", "참을수없"],
            'cognitive_decline': ["기억안나", "모르겠", "잊어버렸", "생각안나", "까먹었", "헷갈려", "누구였는지", "몰라"]
        }
        
        memory_issues = very_short_answers = meaningless_answers = 0
        repetitive_patterns = []
        
        for i, turn in enumerate(self.chat_system.conversation_turns):
            answer = turn.answer.replace(" ", "").lower()
            
            for pattern_type, keywords in patterns.items():
                for keyword in keywords:
                    if keyword in answer:
                        severity = "critical" if pattern_type == 'severe_depression' else "high"
                        self.rule_based_alerts.append({
                            "type": pattern_type,
                            "turn_number": i + 1,
                            "keyword": keyword,
                            "answer": turn.answer,
                            "timestamp": turn.timestamp,
                            "severity": severity
                        })
                        if pattern_type == 'cognitive_decline':
                            memory_issues += 1
            
            if len(turn.answer.strip()) <= 5:
                very_short_answers += 1
            
            if turn.answer.strip() in ["음", "어", "그냥", "네", "아니", "응", "어?"]:
                meaningless_answers += 1
            
            if i >= 3:
                recent_answers = [t.answer.strip() for t in self.chat_system.conversation_turns[i-3:i]]
                if turn.answer.strip() in recent_answers:
                    repetitive_patterns.append(i + 1)
        
        total_turns = len(self.chat_system.conversation_turns)
        
        thresholds = [
            (memory_issues >= total_turns * 0.7, "severe_memory_loss", "critical", f"전체 {total_turns}회 중 {memory_issues}회 기억 문제"),
            (very_short_answers >= total_turns * 0.8, "communication_difficulty", "high", f"전체 {total_turns}회 중 {very_short_answers}회 짧은 답변"),
            (meaningless_answers >= total_turns * 0.6, "cognitive_confusion", "high", f"전체 {total_turns}회 중 {meaningless_answers}회 무의미한 답변"),
            (len(repetitive_patterns) >= 3, "repetitive_behavior", "moderate", f"답변 반복 {len(repetitive_patterns)}회")
        ]
        
        for condition, alert_type, severity, description in thresholds:
            if condition:
                self.rule_based_alerts.append({"type": alert_type, "description": description, "severity": severity})

    def calculate_ratings(self):
        total_responses = len(self.chat_system.conversation_turns)
        strange_count = len(self.strange_responses)
        
        if total_responses == 0:
            return {"emotion": 3, "coherence": 3, "overall": 3}
        
        emotions = [turn.emotion for turn in self.chat_system.conversation_turns if hasattr(turn, 'emotion')]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        positive_emotions = ["기쁨", "그리움", "감사", "애정", "흥미"]
        negative_emotions = ["슬픔", "무력감", "우울감", "분노", "불안", "짜증"]
        
        positive_count = sum(emotion_counts.get(e, 0) for e in positive_emotions)
        negative_count = sum(emotion_counts.get(e, 0) for e in negative_emotions)
        
        critical_emotion_alerts = [alert for alert in self.rule_based_alerts 
                                 if alert.get('severity') == 'critical' and 
                                 alert.get('type') in ['severe_depression', 'severe_anxiety', 'severe_anger']]
        
        if len(critical_emotion_alerts) > 0:
            emotion_rating = 1
        elif negative_count > positive_count * 2:
            emotion_rating = 2
        elif negative_count > positive_count:
            emotion_rating = 3
        elif positive_count > negative_count:
            emotion_rating = 4
        else:
            emotion_rating = 5 if positive_count > negative_count * 2 else 3
        
        strange_percentage = (strange_count / total_responses * 100) if total_responses > 0 else 0
        severe_count = sum(1 for resp in self.strange_responses if resp.severity == 'severe')
        
        if strange_percentage == 0:
            coherence_rating = 5
        elif strange_percentage <= 20 and severe_count == 0:
            coherence_rating = 4
        elif strange_percentage <= 40 and severe_count <= 1:
            coherence_rating = 3
        elif strange_percentage <= 60 or severe_count <= 2:
            coherence_rating = 2
        else:
            coherence_rating = 1
        
        answer_qualities = [turn.answer_quality for turn in self.chat_system.conversation_turns if hasattr(turn, 'answer_quality')]
        quality_counts = {"poor": 0, "normal": 0, "good": 0, "excellent": 0}
        for quality in answer_qualities:
            quality_counts[quality] += 1
        
        excellent_percentage = (quality_counts["excellent"] / total_responses * 100) if total_responses > 0 else 0
        good_percentage = (quality_counts["good"] / total_responses * 100) if total_responses > 0 else 0
        poor_percentage = (quality_counts["poor"] / total_responses * 100) if total_responses > 0 else 0
        
        critical_cognitive_alerts = [alert for alert in self.rule_based_alerts 
                                   if alert.get('severity') == 'critical' and 
                                   alert.get('type') in ['severe_memory_loss', 'communication_difficulty']]
        
        if len(critical_cognitive_alerts) > 0 or poor_percentage >= 50:
            overall_rating = 1
        elif poor_percentage >= 30 or (strange_percentage > 50 and severe_count >= 2):
            overall_rating = 2
        elif excellent_percentage >= 30 or (good_percentage >= 50 and strange_percentage <= 20):
            overall_rating = 5
        elif good_percentage >= 30 or strange_percentage <= 30:
            overall_rating = 4
        else:
            overall_rating = 3
        
        return {"emotion": emotion_rating, "coherence": coherence_rating, "overall": overall_rating}
    
    def format_star_rating(self, rating):
        stars = "⭐" * rating + "☆" * (5 - rating)
        return f"{stars} ({rating}/5)"

    def analyze_entire_conversation(self):
        if not self.chat_system.conversation_turns:
            return
        
        self.strange_responses = []
        self.rule_based_alerts = []
        self.analyze_speech_patterns()
        
        conversation_text = ""
        for i, turn in enumerate(self.chat_system.conversation_turns, 1):
            conversation_text += f"[{i}] 질문: {turn.question}\n답변: {turn.answer} (길이: {turn.answer_length}자)\n\n"
        
        analysis_prompt = f"""치매 환자 대화 분석하여 JSON 응답:
{conversation_text}

JSON: {{"conversation_analysis": [{{"turn_number": 1, "is_strange": true/false, "severity": "normal/mild/moderate/severe", "emotion": "감정", "answer_quality": "poor/normal/good/excellent", "reason": "이유"}}], "overall_assessment": {{"dominant_emotion": "주요감정", "cognitive_level": "normal/mild_concern/moderate_concern/severe_concern"}}}}

감정: 기쁨,슬픔,그리움,무력감,우울감,분노,불안,중립,감사,애정,흥미,짜증"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "치매 환자 대화 분석 전문 AI"},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1024,
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content
            
            if "```json" in analysis_text:
                json_start = analysis_text.find("```json") + 7
                json_end = analysis_text.find("```", json_start)
                analysis_text = analysis_text[json_start:json_end].strip()
            elif "{" in analysis_text:
                json_start = analysis_text.find("{")
                json_end = analysis_text.rfind("}") + 1
                analysis_text = analysis_text[json_start:json_end]
            
            analysis_result = json.loads(analysis_text)
            
            conversation_analyses = analysis_result.get("conversation_analysis", [])
            for i, analysis in enumerate(conversation_analyses):
                if i < len(self.chat_system.conversation_turns):
                    turn = self.chat_system.conversation_turns[i]
                    turn.emotion = analysis.get("emotion", "중립")
                    turn.answer_quality = analysis.get("answer_quality", "normal")
                    
                    if analysis.get("is_strange", False):
                        strange_response = StrangeResponse(
                            question=turn.question,
                            answer=turn.answer,
                            timestamp=turn.timestamp,
                            severity=analysis.get("severity", "mild"),
                            emotion=turn.emotion,
                            answer_quality=turn.answer_quality
                        )
                        self.strange_responses.append(strange_response)
            
            return analysis_result
            
        except Exception as e:
            return None
        
    def generate_story_from_conversation(self, image_path):
        conversation_text = ""
        for turn in self.chat_system.conversation_turns:
            conversation_text += f"질문: {turn.question}\n답변: {turn.answer}\n\n"
        
        if not conversation_text.strip():
            return None, None
        
        story_prompt = f"""대화 기반으로 어르신 1인칭 추억 스토리 15줄 작성:
{conversation_text}
지침: 답변 기반 작성, 감정과 감각 포함, 따뜻한 톤, 손자/손녀에게 들려주는 어투"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "노인 추억 스토리텔러"},
                    {"role": "user", "content": story_prompt}
                ],
                max_tokens=512,
                temperature=0.8
            )
            
            story = response.choices[0].message.content
            story_dir = "story_telling"
            os.makedirs(story_dir, exist_ok=True)
            
            image_basename = os.path.splitext(os.path.basename(image_path))[0]
            story_filename = os.path.join(story_dir, f"{image_basename}_story.txt")
            
            with open(story_filename, 'w', encoding='utf-8') as f:
                f.write(story)
            
            return story, story_filename
            
        except Exception:
            return None, None
    
    def save_conversation_summary(self, conversation_dir=None):
        if conversation_dir:
            qa_data = self._load_qa_pairs_for_report(conversation_dir)
        
        analysis_result = self.analyze_entire_conversation()
        total_responses = len(self.chat_system.conversation_turns)
        strange_count = len(self.strange_responses)
        
        if total_responses == 0:
            return "대화가 진행되지 않았습니다."
        
        emotions = [turn.emotion for turn in self.chat_system.conversation_turns if hasattr(turn, 'emotion')]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            positive_emotions = ["기쁨", "그리움", "감사", "애정", "흥미"]
            negative_emotions = ["슬픔", "무력감", "우울감", "분노", "불안", "짜증"]
            
            positive_count = sum(emotion_counts.get(e, 0) for e in positive_emotions)
            negative_count = sum(emotion_counts.get(e, 0) for e in negative_emotions)
            
            if positive_count > negative_count:
                overall_mood = "긍정적"
                mood_icon = "😊"
            elif negative_count > positive_count:
                overall_mood = "부정적" 
                mood_icon = "😔"
            else:
                overall_mood = "중립적"
                mood_icon = "😐"
        else:
            dominant_emotion = "중립"
            overall_mood = "중립적"
            mood_icon = "😐"
        
        critical_alerts = [alert for alert in self.rule_based_alerts if alert.get('severity') == 'critical']
        high_alerts = [alert for alert in self.rule_based_alerts if alert.get('severity') == 'high']
        ratings = self.calculate_ratings()
        
        summary = f"\n{'='*60}\n📋 치매 진단 대화 분석 리포트\n{'='*60}\n"
        summary += f"📅 분석 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}\n"
        summary += f"🆔 대화 ID: {self.conversation_id}\n{'='*60}\n\n"
        
        summary += f"🎯 종합 평가\n{'─'*30}\n"
        summary += f"😊 감정 상태:     {self.format_star_rating(ratings['emotion'])}\n"
        summary += f"💬 답변 일관성:   {self.format_star_rating(ratings['coherence'])}\n"
        summary += f"🧠 전반적 인지:   {self.format_star_rating(ratings['overall'])}\n{'─'*30}\n\n"
        
        summary += f"📊 대화 개요\n{'─'*30}\n"
        summary += f"💬 총 대화 횟수: {total_responses}회\n"
        summary += f"{mood_icon} 전반적 감정: {overall_mood} (주요: {dominant_emotion})\n"
        summary += f"{'✅ 어긋난 답변: 없음' if strange_count == 0 else f'⚠️ 어긋난 답변: {strange_count}회'}\n"
        summary += f"{'✅ 발화 패턴: 특이사항 없음' if len(self.rule_based_alerts) == 0 else f'🔍 발화 패턴: {len(self.rule_based_alerts)}건 관찰'}"
        if len(critical_alerts) > 0:
            summary += f" (⚠️ 주의: {len(critical_alerts)}건)"
        summary += f"\n{'─'*30}\n\n"
        
        if strange_count == 0 and len(critical_alerts) == 0:
            summary += f"🎉 대화 결과\n{'─'*30}\n"
            summary += f"✅ 대화 중 특별히 걱정되는 답변은 없었습니다.\n"
            summary += f"💚 어르신께서 안정적으로 잘 응답해주셨어요.\n"
            if len(high_alerts) > 0:
                summary += f"💡 참고: {len(high_alerts)}번의 발화 패턴이 관찰되었습니다.\n"
            summary += f"🌟 지금처럼 따뜻한 환경과 꾸준한 관심 속에 계시면 좋겠습니다.\n"
            summary += f"{'='*60}\n"
            return summary
        
        if len(self.rule_based_alerts) > 0 or strange_count > 0:
            summary += f"🚨 주요 발견사항\n{'─'*30}\n"
            
            if len(self.rule_based_alerts) > 0:
                alert_types = {
                    'severe_depression': '😔 우울한 표현',
                    'severe_anxiety': '😰 불안한 표현', 
                    'severe_anger': '😡 화가 난 표현',
                    'severe_memory_loss': '🧠 기억 관련 어려움',
                    'communication_difficulty': '💬 대화 어려움',
                    'cognitive_confusion': '❓ 혼란스러운 답변',
                    'repetitive_behavior': '🔄 반복되는 답변'
                }
                
                alert_summary = {}
                for alert in self.rule_based_alerts:
                    alert_name = alert_types.get(alert['type'], f"⚠️ {alert['type']}")
                    alert_summary[alert_name] = alert_summary.get(alert_name, 0) + 1
                
                for alert_name, count in alert_summary.items():
                    summary += f"{alert_name}: {count}번\n"
                summary += f"\n"
            
            if strange_count > 0:
                severity_counts = {"mild": 0, "moderate": 0, "severe": 0}
                for response in self.strange_responses:
                    severity_counts[response.severity] += 1
                
                summary += f"🔍 어긋난 답변 분석:\n"
                if severity_counts['mild'] > 0:
                    summary += f"  🟡 조금 어긋남: {severity_counts['mild']}회\n"
                if severity_counts['moderate'] > 0:
                    summary += f"  🟠 꽤 어긋남: {severity_counts['moderate']}회\n"
                if severity_counts['severe'] > 0:
                    summary += f"  🔴 많이 어긋남: {severity_counts['severe']}회\n"
                summary += f"\n"
            
            summary += f"{'─'*30}\n\n"
        
        if strange_count > 0 and strange_count <= 5:
            summary += f"📝 어긋난 답변 상세\n{'─'*30}\n"
            for i, response in enumerate(self.strange_responses, 1):
                summary += f"{i}. {response.timestamp}\n"
                summary += f"   ❓ 질문: {response.question}\n"
                summary += f"   💬 답변: {response.answer}\n"
                summary += f"   😊 상태: {response.emotion} | 🎯 품질: {response.answer_quality}\n\n"
            summary += f"{'─'*30}\n\n"
        
        summary += f"💡 권장사항\n{'─'*30}\n"
        
        if len(critical_alerts) > 0:
            summary += f"🚨 긴급 권장사항:\n   심각한 정신건강 위험 신호가 감지되었습니다.\n   빠른 시일 내로 연락을 드리는 것을 권장합니다.\n\n"
            for alert in critical_alerts:
                if alert['type'] == 'severe_depression':
                    summary += f"   ⚠️ 극심한 우울감 표현 감지\n      → 연락드려 기분전환을 도와드리세요.\n\n"
                elif alert['type'] == 'severe_memory_loss':
                    summary += f"   ⚠️ 심각한 기억력 저하 감지\n      → 가족과 함께 추억을 되새겨보세요.\n\n"
        elif len(high_alerts) >= 2:
            summary += f"⚠️ 주의 권장사항:\n   최근 대화에서 혼란스러운 답변이 자주 보였습니다.\n   가족과 함께 이야기를 나눠보시길 권장합니다.\n\n"
        elif len(high_alerts) >= 1:
            summary += f"🔶 일반 권장사항:\n   약간 걱정되는 답변이 있었습니다.\n   시간을 내어 안부 전화를 드려보세요.\n\n"
        elif strange_count > 0:
            summary += f"💙 관심 권장사항:\n   전반적으로 잘 응답해주셨지만, 간혹 어긋난 답변이 보입니다.\n   가볍게라도 주변의 관심과 확인이 있으면 좋겠습니다.\n\n"
        else:
            summary += f"💚 훌륭한 상태:\n   어르신께서 무척 안정적으로 잘 응답해주셨습니다.\n   지금처럼 따뜻한 환경과 꾸준한 관심을 유지해주세요.\n\n"
        
        summary += f"🏠 가족을 위한 조언\n{'─'*30}\n"
        
        emotion_advice = {
            "짜증": "🔴 최근 짜증스러운 감정을 표현하셨어요.\n   → 감정을 자연스럽게 표현하도록 따뜻하게 공감해주세요.\n   → 요즘 어떠신지 자주 안부를 여쭤보시면 큰 힘이 됩니다.",
            "우울감": "🟠 슬픔이나 우울감을 표현하셨어요.\n   → 함께 옛 추억을 나누거나 좋아하시던 이야기를 꺼내보세요.\n   → 감정을 안정시키는 데 도움이 될 수 있습니다.",
            "슬픔": "🟠 슬픔이나 우울감을 표현하셨어요.\n   → 함께 옛 추억을 나누거나 좋아하시던 이야기를 꺼내보세요.\n   → 감정을 안정시키는 데 도움이 될 수 있습니다.",
            "무력감": "😞 무기력하거나 소외감을 표현하셨어요.\n   → '어르신 덕분이에요'처럼 인정해드리면 자존감 회복에 도움됩니다.\n   → 함께 의미 있는 활동을 하며 힘이 되어 주세요.",
            "분노": "😡 갑작스럽게 화를 내시거나 강한 어조를 보이셨어요.\n   → 감정 뒤에 불안이나 혼란감이 있을 수 있으니 조용히 공감해주세요.\n   → 환경을 점검하고 반복 자극을 줄이면 안정에 도움됩니다.",
            "불안": "🟤 불안감을 느끼시는 것 같아요.\n   → 어르신의 이야기를 잘 들어주시고, 따뜻한 말 한마디가 큰 위로가 됩니다.",
            "그리움": "💙 과거를 그리워하시는 마음을 표현하셨어요.\n   → 함께 옛날 이야기를 나누거나 추억 속 장소나 사람들에 대해 대화해보세요.\n   → 마음의 평안을 찾는 데 도움이 될 수 있습니다."
        }
        
        if dominant_emotion in emotion_advice:
            summary += emotion_advice[dominant_emotion]
        elif dominant_emotion in ["기쁨", "감사", "애정", "흥미"]:
            summary += "😊 긍정적인 감정을 표현하셨어요. 정말 좋네요!\n   → 이런 밝은 모습을 계속 유지하실 수 있도록 즐거운 대화와 활동을 함께 해보세요."
        elif dominant_emotion == "중립":
            summary += "💬 대부분의 대화에서 큰 감정 변화 없이 차분히 응답하셨어요.\n   → 무던해 보이지만 내면의 감정을 잘 표현하지 못하실 수도 있으니\n   → 따뜻한 말 한마디가 큰 위로가 될 수 있습니다."
        else:
            summary += "🌈 다양한 감정이 섞여 있었지만, 전반적으로 안정적인 편입니다.\n   → 지금처럼 관심과 애정을 꾸준히 표현해 주시면 좋습니다."
        
        summary += f"\n{'─'*30}\n\n"
        summary += f"📈 평가 기준\n{'─'*30}\n"
        summary += f"😊 감정 상태: 긍정적이고 안정적인 감정 표현일수록 높은 점수\n"
        summary += f"💬 답변 일관성: 질문과 관련된 적절한 답변일수록 높은 점수\n"
        summary += f"🧠 전반적 인지: 답변의 품질과 소통 능력을 종합한 점수\n"
        summary += f"{'─'*30}\n\n"
        summary += f"{'='*60}\n📋 리포트 끝 - 어르신의 건강과 행복을 위해\n{'='*60}\n"
        
        return summary
    
    def save_conversation_to_file(self, image_path=None):
        if len(self.strange_responses) == 0 and len(self.rule_based_alerts) == 0:
            self.analyze_entire_conversation()
        
        # 폴더 구조 생성
        conversation_dir = self._create_conversation_folders(image_path)
        
        # 메인 대화 파일 저장: {이미지명}_conv{번호}/{이미지명}_conv{번호}.txt
        conversation_filename = conversation_dir / f"{self.conversation_id}.txt"
        with open(conversation_filename, 'w', encoding='utf-8') as f:
            f.write(f"{'='*50}\n")
            f.write(f"💬 치매 진단 대화 기록\n")
            f.write(f"{'='*50}\n")
            f.write(f"🆔 대화 ID: {self.conversation_id}\n")
            f.write(f"📊 총 대화 수: {len(self.chat_system.conversation_turns)}회\n")
            f.write(f"{'='*50}\n\n")
            
            # 대화 내용만 간단히 출력 (타임스탬프 + 대화)
            for i, turn in enumerate(self.chat_system.conversation_turns, 1):
                f.write(f"[{turn.timestamp}]\n")
                f.write(f"🤖 질문: {turn.question}\n")
                f.write(f"👤 답변: {turn.answer}\n")
                f.write(f"{'-'*30}\n\n")
        
        # analysis 폴더에 분석 리포트 저장
        analysis_dir = Path("analysis")
        analysis_dir.mkdir(exist_ok=True)
        analysis_filename = analysis_dir / f"{self.conversation_id}_analysis.txt"
        
        with open(analysis_filename, 'w', encoding='utf-8') as f:
            f.write(self.save_conversation_summary(conversation_dir))
        
        # 저장 완료 메시지
        print(f"\n✅ 파일 저장 완료!")
        print(f"📁 대화 폴더: {conversation_dir}")
        print(f"📄 대화 파일: {conversation_filename}")
        print(f"📊 분석 파일: {analysis_filename}")
        
        return str(conversation_filename), str(analysis_filename)

    def generate_story_from_turns(self, turns):
        """Turn 데이터로부터 직접 스토리 생성"""
        conversation_text = ""
        for turn in turns:
            # 답변이 null이거나 비어있는 경우 건너뛰기
            if turn.answer and turn.answer.strip():
                conversation_text += f"질문: {turn.question}\n답변: {turn.answer}\n\n"
        
        if not conversation_text.strip():
            return None
        
        story_prompt = f"""대화 기반으로 어르신 1인칭 추억 스토리 15줄 작성:
{conversation_text}
지침: 답변 기반 작성, 감정과 감각 포함, 따뜻한 톤, 손자/손녀에게 들려주는 어투"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "노인 추억 스토리텔러"},
                    {"role": "user", "content": story_prompt}
                ],
                max_tokens=512,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating story: {str(e)}")
            return None

    def save_conversation_to_file_from_turns(self, conversation_turns, conversation_id):
        """Turn 데이터로부터 직접 대화 기록 저장"""
        # 대화 ID 설정
        self.conversation_id = conversation_id
        
        # 폴더 구조 생성 (대화 ID 기반)
        conversation_dir = Path("conversation_log") / conversation_id
        conversation_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 저장 구조:")
        print(f"   메인 폴더: conversation_log/{conversation_id}/")
        print(f"   대화 파일: {conversation_id}.txt")
        
        # 메인 대화 파일 저장
        conversation_filename = conversation_dir / f"{conversation_id}.txt"
        with open(conversation_filename, 'w', encoding='utf-8') as f:
            f.write(f"{'='*50}\n")
            f.write(f"💬 치매 진단 대화 기록\n")
            f.write(f"{'='*50}\n")
            f.write(f"🆔 대화 ID: {conversation_id}\n")
            f.write(f"📊 총 대화 수: {len(conversation_turns)}회\n")
            f.write(f"{'='*50}\n\n")
            
            # 대화 내용 출력
            for i, turn in enumerate(conversation_turns, 1):
                f.write(f"[{turn.timestamp}]\n")
                f.write(f"🤖 질문: {turn.question}\n")
                f.write(f"👤 답변: {turn.answer}\n")
                f.write(f"{'-'*30}\n\n")
        
        # analysis 폴더에 분석 리포트 저장
        analysis_dir = Path("analysis")
        analysis_dir.mkdir(exist_ok=True)
        analysis_filename = analysis_dir / f"{conversation_id}_analysis.txt"
        
        # 분석을 위해 chat_system.conversation_turns 설정
        self.chat_system.conversation_turns = conversation_turns
        
        with open(analysis_filename, 'w', encoding='utf-8') as f:
            f.write(self.save_conversation_summary(conversation_dir))
        
        # 저장 완료 메시지
        print(f"\n✅ 파일 저장 완료!")
        print(f"📁 대화 폴더: {conversation_dir}")
        print(f"📄 대화 파일: {conversation_filename}")
        print(f"📊 분석 파일: {analysis_filename}")
        
        return str(conversation_filename), str(analysis_filename)