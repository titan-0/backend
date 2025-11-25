from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Use host.docker.internal to connect to host machine's MySQL from Docker
# Falls back to localhost for local development
# DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
# DB_PORT = os.getenv("DB_PORT", "3307")
# DATABASE_URL = f"mysql+aiomysql://root:harshal123@{DB_HOST}:{DB_PORT}/deccan"

DB_HOST = os.getenv("DB_HOST", "host.docker.internal")
DATABASE_URL = f"mysql+aiomysql://root:Deccan115@{DB_HOST}:3306/tradingdatabase"


engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    # CHANGE: Remove invalid connect_args for aiomysql
    # aiomysql doesn't use 'timeout' or 'command_timeout'
    connect_args={
        "connect_timeout": 10,  # Changed from 'timeout'
        "charset": "utf8mb4",
        "autocommit": False,
    }
)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



        