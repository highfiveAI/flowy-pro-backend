from sqlalchemy.ext.asyncio import AsyncSession
from app.models.draft_log import DraftLog
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select

async def insert_draft_log(
    db: AsyncSession,
    meeting_id: Optional[str],
    draft_ref_reason: str,
    ref_interdoc_id: str,
    draft_trigger: str = "auto",
    docs_source_type: str = "internal",
    draft_created_date: Optional[datetime] = None
):
    draft_log = DraftLog(
        meeting_id=meeting_id,
        draft_trigger=draft_trigger,
        docs_source_type=docs_source_type,
        ref_interdoc_id=ref_interdoc_id,
        draft_ref_reason=draft_ref_reason,
        draft_created_date=draft_created_date or datetime.utcnow()
    )
    
    print(f"저장할 문서 데이터: {draft_log}")
    db.add(draft_log)
    await db.commit()
    await db.refresh(draft_log)
    return draft_log

async def get_draft_logs_by_meeting_id(
    db: AsyncSession,
    meeting_id: str
) -> List[DraftLog]:
    query = select(DraftLog).where(DraftLog.meeting_id == meeting_id)
    result = await db.execute(query)
    return result.scalars().all() 