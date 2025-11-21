from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "mysql+aiomysql://root:harshal123@127.0.0.1:3307/deccan"

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



        