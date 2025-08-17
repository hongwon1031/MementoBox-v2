from dotenv import load_dotenv
from openai import AzureOpenAI
import os
import base64
import json

from core.config import settings

class ImageAnalyzer:
    """GPT-4o를 사용한 이미지 분석"""
    
    def __init__(self):
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
        )
    
    def analyze_image(self, image_path):
        """이미지 분석"""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": """이미지를 분석해서 JSON으로 답해주세요:
{
    "caption": "전체 설명",
    "dense_captions": ["세부 설명1", "세부 설명2"],
    "mood": "분위기",
    "time_period": "시대",
    "key_objects": ["객체1", "객체2"],
    "people_description": "인물 설명",
    "people_count": 숫자,
    "time_of_day": "시간대"
}"""
                    }, {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }]
                }],
                max_tokens=1000,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content
            
            # JSON 추출
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                response_text = response_text[json_start:json_end]
            
            return json.loads(response_text)
            
        except Exception:
            return None
