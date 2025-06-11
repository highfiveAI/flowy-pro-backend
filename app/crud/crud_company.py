from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Company, Sysrole

# 회사 목록과 시스템 역할 목록 함께 조회 (조인 없이)
async def get_signup_meta(db: AsyncSession):
    # 회사 + 직급 로딩
    stmt_company = (
        select(Company)
        .options(selectinload(Company.company_positions))
    )
    company_result = await db.execute(stmt_company)
    companies = company_result.scalars().all()

    # 시스템 역할 로딩
    stmt_sysrole = select(Sysrole)
    sysrole_result = await db.execute(stmt_sysrole)
    sysroles = sysrole_result.scalars().all()

    return {
        "companies": companies,
        "sysroles": sysroles
    }
