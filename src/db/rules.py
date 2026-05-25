from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from src.db.entities import Camera, Rule


def get_rules_by_id(camera_public_id: str, sql_engine: Engine) -> list[Rule]:
    # TODO: 
    with Session(sql_engine) as session:
        return session.scalars(
            select(Rule)
            .join(Camera, Rule.camera_id == Camera.id)
            .where(Camera.public_camera_id == UUID(camera_public_id))
        ).all()