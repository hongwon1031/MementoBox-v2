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

    # AWS S3 설정
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str
    AWS_S3_BUCKET: str

    # --- Azure ---
    # AZURE_BLOBSTORAGE_ACCOUNT: str
    # AZURE_BLOBSTORAGE_KEY: str
    # AZURE_OPENAI_ENDPOINT: str
    # AZURE_OPENAI_API_VERSION: str
    # AZURE_OPENAI_MAX_TOKENS: int
    # AZURE_OPENAI_DEPLOYMENT: str
    # AZURE_OPENAI_KEY: str
    # AZURE_SPEECH_ENDPOINT: str
    # AZURE_SPEECH_KEY: str
    # AZURE_SPEECH_REGION: str

    class Config:
        env_file = ".env"

settings = Settings()
