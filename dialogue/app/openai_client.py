import os
import httpx
from dotenv import load_dotenv

# 환경변수 로드 후 값 출력
load_dotenv()
API_KEY    = os.getenv("AZURE_OPENAI_KEY")
ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

print("▶ [openai_client] AZURE_OPENAI_KEY       =", API_KEY)
print("▶ [openai_client] AZURE_OPENAI_ENDPOINT  =", ENDPOINT)
print("▶ [openai_client] AZURE_OPENAI_DEPLOYMENT =", DEPLOYMENT)

async def ask_openai(messages):
    """
    Azure OpenAI Chat Completions 호출 함수 (디버깅 로그 포함)
    """
    # 요청 헤더 및 바디 준비
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

    #request_url = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version=2023-05-15"
    request_url = ENDPOINT
    print("▶ [openai_client] Request URL   :", request_url)
    print("▶ [openai_client] Request headers:", headers)
    print("▶ [openai_client] Request body   :", body)

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(request_url, headers=headers, json=body)
        except Exception as conn_err:
            # 네트워크/타임아웃 등 HTTP 요청 자체가 실패한 경우
            print("▶ [openai_client] HTTP 요청 예외 발생:", repr(conn_err))
            raise

        # 응답 상태코드와 바디 출력
        status_code = response.status_code
        response_text = response.text  # 'text'는 이미 str이므로 await나 () 불필요
        print(f"▶ [openai_client] Response status code: {status_code}")
        print(f"▶ [openai_client] Response body: {response_text}")

        if status_code != 200:
            # 200이 아니면 예외 던지기
            raise RuntimeError(f"OpenAI API 호출 실패: status={status_code}, body={response_text}")

        # JSON 파싱 및 구조 검사
        try:
            data = response.json()
        except Exception as json_err:
            print("▶ [openai_client] JSON 파싱 예외 발생:", repr(json_err))
            raise RuntimeError(f"응답 JSON 파싱 실패: {repr(json_err)}, raw_response={response_text}")

        if "choices" not in data or len(data["choices"]) == 0:
            raise RuntimeError(f"응답 JSON에 choices가 없습니다: {data}")
        choice0 = data["choices"][0]
        if "message" not in choice0 or "content" not in choice0["message"]:
            raise RuntimeError(f"responses[0].message.content 키가 없습니다: {data}")

        return choice0["message"]["content"]
