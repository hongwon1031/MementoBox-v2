import secrets
import base64

def generate_secret_key():
    """32바이트 랜덤 키를 생성하고 base64로 인코딩"""
    random_bytes = secrets.token_bytes(32)
    secret_key = base64.b64encode(random_bytes).decode('utf-8')
    return secret_key

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print(f"생성된 SECRET_KEY: {secret_key}")
    print("\n.env 파일에 다음 줄을 추가하세요:")
    print(f"SECRET_KEY={secret_key}") 