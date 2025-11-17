"""
Database connection and operations module
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def execute_query(db: AsyncSession, query: str, params: Optional[Dict] = None) -> List[Dict]:
    """
    Execute a SQL query and return results

    Args:
        db: Database session
        query: SQL query string
        params: Query parameters

    Returns:
        List of result dictionaries
    """
    try:
        result = await db.execute(text(query), params or {})
        if result.returns_rows:
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        return []
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise


async def save_to_database(
    db: AsyncSession,
    data: List[Dict[str, Any]],
    table_name: str,
    mode: str = "replace"
) -> int:
    """
    Save data to database table

    Args:
        db: Database session
        data: List of data dictionaries
        table_name: Target table name
        mode: 'replace' to truncate first, 'append' or 'add' to append

    Returns:
        Number of records saved
    """
    if not data:
        return 0

    try:
        # Truncate table if replace mode
        if mode == "replace":
            await db.execute(text(f"TRUNCATE TABLE {table_name}"))
            logger.info(f"Truncated table: {table_name}")

        # Prepare insert statement
        columns = list(data[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        columns_str = ", ".join(columns)

        insert_query = f"""
            INSERT INTO {table_name} ({columns_str})
            VALUES ({placeholders})
        """

        # Batch insert
        await db.execute(text(insert_query), data)
        await db.commit()

        logger.info(f"Saved {len(data)} records to {table_name}")
        return len(data)

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save to database: {str(e)}")
        raise


async def test_connection():
    """Test database connection"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False
