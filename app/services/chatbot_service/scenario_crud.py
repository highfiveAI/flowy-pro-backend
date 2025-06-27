from sqlalchemy import select, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Scenario

async def search_similar_scenario(db: AsyncSession, query_embedding: list[float]):
    stmt = (
        select(
            Scenario,
            (Scenario.embedding.cosine_distance(query_embedding)).label("similarity")
        )
        .order_by(Scenario.embedding.cosine_distance(query_embedding))
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()  # row is (Scenario, similarity)
    if row:
        scenario, similarity = row
        if similarity < 0.9:  # 예: 유사도 기준이 0.8 이상일 때만 유사하다고 판단
            scenario.similarity = similarity
            return scenario
    return None