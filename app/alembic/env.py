import sys
import os
import logging
from datetime import timezone, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine.url import make_url
from alembic import context
from dotenv import load_dotenv
from db.database import Base
from db.models import user, family, photo, conversation, turn, anomaly_report

# 로깅 설정
logger = logging.getLogger('alembic.env')

# .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
sync_url = os.getenv("SYNC_DATABASE_URL")
if not sync_url:
    raise ValueError("SYNC_DATABASE_URL environment variable is not set")

logger.info(f'Using database URL: {sync_url}')

# Alembic 설정
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    try:
        context.configure(
            url=sync_url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            timezone=timezone(timedelta(hours=9))  # 한국 시간대 설정
        )
        with context.begin_transaction():
            context.run_migrations()
    except Exception as e:
        logger.error(f"Error during offline migration: {str(e)}")
        raise

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        from sqlalchemy import create_engine
        connectable = create_engine(
            sync_url,
            poolclass=pool.NullPool,
            connect_args={"options": "-c timezone=Asia/Seoul"}  # PostgreSQL 타임존 설정
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_schemas=True,
                timezone=timezone(timedelta(hours=9))  # 한국 시간대 설정
            )
            with context.begin_transaction():
                context.run_migrations()
    except Exception as e:
        logger.error(f"Error during online migration: {str(e)}")
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()