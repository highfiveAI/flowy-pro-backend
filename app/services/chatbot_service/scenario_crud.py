from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import literal
from app.models import Scenario
from pgvector.sqlalchemy import Vector

async def search_similar_scenario(db: AsyncSession, query_embedding: list[float]):
    stmt = (
        select(Scenario)
        .order_by(Scenario.embedding.op('<#>')(literal(query_embedding)))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()
