from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from settings import env_settings

DATABASE_URL = env_settings.sqlalchemy_postgres_uri

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session factory
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
