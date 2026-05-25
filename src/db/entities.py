from datetime import datetime
from sqlalchemy import String, BIGINT, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import UUID


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    public_user_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    first_name: Mapped[str] = mapped_column(String(150))
    last_name: Mapped[str] = mapped_column(String(150))
    username: Mapped[str] = mapped_column(String(150), unique=True)
    password: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool]
    is_staff: Mapped[bool]
    is_superuser: Mapped[bool]
    date_joined: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f'User with id: {self.public_user_id}'


class Camera(Base):
    __tablename__ = 'camera_camera'
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    public_camera_id: Mapped[UUID] = mapped_column(unique=True)
    owner_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey('users.id'), nullable=False)
    location: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return (
            f'Camera id: {self.public_camera_id} '
            f'for user: {self.owner_id} in {self.location}'
        )


class Rule(Base):
    __tablename__ = 'rules_rule'
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    public_rule_id: Mapped[UUID] = mapped_column(unique=True)
    owner_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey('users.id'), nullable=False)
    camera_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey('camera_camera.id'), nullable=False)
    rule: Mapped[str] = mapped_column(String(240))
    rule_nickname: Mapped[str] = mapped_column(String(240))
    is_enabled: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f'Rule id: {self.public_rule_id} for user: {self.owner_id}'
