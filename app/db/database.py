from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

# 모든 모델 클래스의 부모가 되는 기본 클래스 Base
Base = declarative_base()

# 1. 비동기 DB 엔진 생성
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,  # .env에서 불러온 연결 문자열
    echo=True               # 로그 출력 (개발 시 디버깅에 유용)
)

# 2. 비동기 세션 생성기
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # 커밋 후 객체가 expire되지 않도록 설정
)

# 3. DB 세션 의존성
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()