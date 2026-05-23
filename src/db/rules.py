from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from src.db.entities import Rule

def get_rules_by_id(camera_id: str, sql_engine: Engine) -> list[str]:
    with Session(sql_engine) as session:
        return session.scalars(Rule.rule).where(Rule.camera_id == camera_id)