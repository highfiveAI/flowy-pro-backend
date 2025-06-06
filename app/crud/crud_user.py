from sqlalchemy.orm import Session
from app.models import CompanyPosition
from app.schemas.company_position import CompanyPositionCreate

def create_company_position(db: Session, position_in: CompanyPositionCreate) -> CompanyPosition:
    db_position = CompanyPosition(
        position_code=position_in.position_code,
        position_name=position_in.position_name,
        position_detail=position_in.position_detail,
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

def get_all_positions(db: Session):
    return db.query(CompanyPosition).all()
