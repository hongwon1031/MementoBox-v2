from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL 설정
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    
    # 데이터베이스 URL
    ASYNC_DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # JWT 설정
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Azure Blob Storage 설정
    AZURE_BLOBSTORAGE_ACCOUNT: str
    AZURE_BLOBSTORAGE_KEY: str

    # Azure OpenAI 설정
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_MAX_TOKENS: int
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_KEY: str

    # Azure Speech 설정
    AZURE_SPEECH_ENDPOINT: str
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str

    # JWT 인증 설정
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

# 설정 인스턴스
settings = Settings()